"""
NexusOS Agent Executor
======================
The core loop that runs agents: receives message → calls LLM → executes tools → returns response.

With Inner Life integration:
- Processes messages through the six-layer personality system
- Adds memory/context to prompts
- Remembers important interactions
"""

import os
import sys
import json
import time
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

# Import NexusOS modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inner Life integration
INNER_LIFE_AVAILABLE = False
try:
    from inner_life import get_inner_life
    INNER_LIFE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Inner Life not available: {e}")


@dataclass
class AgentMessage:
    """A message in the agent conversation."""
    role: str  # "user", "assistant", "system"
    content: str
    tool_calls: List[Dict] = None
    tool_results: List[Dict] = None


@dataclass
class AgentResponse:
    """Response from agent execution."""
    success: bool
    content: str = None
    tool_calls: List[Dict] = None
    error: str = None
    tokens_used: int = 0
    execution_time_ms: float = 0.0


class AgentExecutor:
    """
    The core agent execution loop.
    
    Flow:
    1. Receive user message
    2. Process through Inner Life (if available)
    3. Build context (system prompt + history + memories)
    4. Call LLM with available tools
    5. If tool calls → execute → loop back to LLM with results
    6. Remember important interactions
    7. Return final response
    """
    
    def __init__(self, llm_provider=None, tool_engine=None, inner_life=None):
        self.llm = llm_provider
        self.tools = tool_engine
        self.inner_life = inner_life
        self.max_tool_iterations = 5
        self._inner_life_instances = {}  # Cache per-user instances
        
    def get_inner_life(self, user_id: str):
        """Get or create Inner Life instance for a user"""
        if not INNER_LIFE_AVAILABLE:
            return None
            
        if user_id not in self._inner_life_instances:
            try:
                self._inner_life_instances[user_id] = get_inner_life(user_id)
            except Exception as e:
                logger.warning(f"Failed to get Inner Life for {user_id}: {e}")
                return None
        return self._inner_life_instances[user_id]
        
    def set_llm_provider(self, provider):
        """Set the LLM provider."""
        self.llm = provider
        
    def set_tool_engine(self, engine):
        """Set the tool execution engine."""
        self.tools = engine
        
    def set_inner_life(self, inner_life):
        """Set the inner life module."""
        self.inner_life = inner_life
    
    def build_messages(self, system_prompt: str, history: List[AgentMessage], 
                       current_message: str, tool_results: List[Dict] = None) -> List[Dict]:
        """Build the message list for the LLM."""
        messages = []
        
        # System prompt
        messages.append({"role": "system", "content": system_prompt})
        
        # Conversation history
        for msg in history:
            msg_dict = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                msg_dict["tool_calls"] = msg.tool_calls
            if msg.tool_results:
                msg_dict["tool_results"] = msg.tool_results
            messages.append(msg_dict)
        
        # Current message
        messages.append({"role": "user", "content": current_message})
        
        # Tool results from previous iteration
        if tool_results:
            for result in tool_results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": result.get("call_id", ""),
                    "content": str(result.get("result", ""))
                })
        
        return messages
    
    def build_tools_schema(self) -> List[Dict]:
        """Build the tools schema for the LLM."""
        if not self.tools or not hasattr(self.tools, 'tools'):
            return []
        
        tools_schema = []
        for name, func in self.tools.tools.items():
            # Get function signature for schema
            import inspect
            sig = inspect.signature(func)
            
            # Build parameter schema
            params = {}
            for param_name, param in sig.parameters.items():
                if param_name in ('self', 'cls'):
                    continue
                params[param_name] = {
                    "type": "string",
                    "description": f"Parameter {param_name}"
                }
            
            tools_schema.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": func.__doc__ or f"Tool: {name}",
                    "parameters": {
                        "type": "object",
                        "properties": params,
                        "required": []
                    }
                }
            })
        
        return tools_schema
    
                      tools: List[str] = None,
                      optimize_context: bool = True) -> AgentResponse:
        """
        Execute an agent with a message.
        
        Args:
            agent_id: Unique agent identifier
            message: User's message
            user_id: User identifier (for Inner Life - use actual user, not agent_id)
            system_prompt: Agent's system prompt
            model: LLM model to use
            history: Previous conversation messages
            tools: List of tool names to enable
            optimize_context: Use local Ollama to optimize context (free)
            
        Returns:
            AgentResponse with content and metadata
        """
        start_time = time.time()
        history = history or []
        
        # ===== INNER LIFE PROCESSING =====
        # Use actual user_id if provided, fall back to agent_id
        user_id = user_id or agent_id
        
        inner_life_context = {}
        inner_life = self.get_inner_life(user_id)
        
        if inner_life:
            try:
                inner_life_context = inner_life.process(message, {
                    "agent_id": agent_id,
                    "model": model
                })
                logger.info(f"Inner Life active for {agent_id}")
            except Exception as e:
                logger.warning(f"Inner Life processing failed: {e}")
        
        # Build enhanced system prompt with Inner Life context
        enhanced_system_prompt = system_prompt
        if inner_life_context.get("memories"):
            memory_text = "\n".join([f"- {m['content']}" for m in inner_life_context["memories"]])
            enhanced_system_prompt += f"\n\nRelevant memories:\n{memory_text}"
        
        if inner_life_context.get("user_style"):
            enhanced_system_prompt += f"\n\nUser communication style: {inner_life_context['user_style']}"
        
        # Build initial messages
        messages = self.build_messages(enhanced_system_prompt, history, message)
        
        # Note: Context optimization not needed - Inner Life semantic recall
        # already extracts only relevant memories per query
        
        # Build tools schema
        tools_schema = self.build_tools_schema()
        
        # Filter tools if specified
        available_tools = {}
        if tools and self.tools:
            for tool_name in tools:
                if tool_name in self.tools.tools:
                    available_tools[tool_name] = self.tools.tools[tool_name]
        elif self.tools:
            available_tools = self.tools.tools
        
        # Add tool instructions to prompt (Ollama doesn't support native function calling)
        if available_tools:
            tool_names = list(available_tools.keys())
            messages[0]["content"] += f"\n\nAvailable tools: {', '.join(tool_names)}\nIf you need to use a tool, respond with: <tool_call>{{\"name\":\"tool_name\",\"arguments\":{{\"arg1\":\"value1\"}}}}</tool_call>"
        
        # ===== SMART PLANNING: Only plan for complex tasks =====
        # Heuristic: plan if query has multiple steps, comparisons, or complex intent
        needs_planning = any(word in message.lower() for word in [
            " and ", " then ", " also ", " compare ", " vs ", 
            " after ", " before ", " together", " both ",
            " research", " find information", " look up",
            "and tell", "and give", "and create"
        ])
        
        # Also plan if explicitly asking for tools
        tool_keywords = list(available_tools.keys()) + ["search", "find", "get", "check", "look"]
        if any(word in message.lower() for word in tool_keywords):
            # Check if it's complex enough to warrant planning
            words = message.split()
            if len(words) > 15 or len(message.split(" and ")) > 1:
                needs_planning = True
        
        plan = None
        if available_tools and needs_planning:
            tool_list = ", ".join(available_tools.keys())
            plan_prompt = f"Analyze this request and create a step-by-step plan: {message}\n\nAvailable tools: {tool_list}\n\nRespond with a JSON plan: {{'steps': [{{'tool': 'tool_name', 'reason': 'why'}}]}}\nIf no tools needed, respond with {{'steps': []}}"
            
            # Ask the LLM to create a plan
            plan_response = await self._call_llm(model, [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": plan_prompt}
            ], [])
            
            if plan_response.success and plan_response.content:
                try:
                    import re
                    json_match = re.search(r'\{.*\}', plan_response.content, re.DOTALL)
                    if json_match:
                        plan = json.loads(json_match.group())
                        logger.info(f"Plan created: {plan.get('steps', [])}")
                except:
                    pass
        
        # Tool execution loop with ReAct
        tool_results = []
        final_content = None
        
        for iteration in range(self.max_tool_iterations):
            # Build context with previous results (ReAct style)
            react_messages = messages.copy()
            
            # Add tool results with observation context
            for tr in tool_results:
                react_messages.append({
                    "role": "tool",
                    "content": f"Tool: {tr['tool']}\nResult: {tr['result']}\n\nThink: What does this result tell me? Should I continue or respond?"
                })
            
            # Add ReAct prompting
            react_messages.append({
                "role": "user", 
                "content": message + "\n\nThink step by step. If using a tool, respond with <tool_call>. If ready to answer, give your final response."
            })
            
            # Call LLM
            response = await self._call_llm(model, react_messages, tools_schema if available_tools else [])
            
            if not response.success:
                return AgentResponse(
                    success=False,
                    error=response.error,
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            content = response.content or ""
            
            # Check for tool calls
            tool_calls = self._extract_tool_calls(content)
            
            if not tool_calls:
                # No tool calls - this is the final response
                # Validate response quality
                if len(content) < 10 or "sorry" in content.lower() and iteration < 2:
                    # Too short or apologizing - might need more work
                    continue
                final_content = content
                break
            
            # Execute tool calls with validation
            for call in tool_calls:
                tool_name = call.get('name')
                args = call.get('arguments', {})
                
                # Validate tool call
                if tool_name not in available_tools:
                    logger.warning(f"Invalid tool requested: {tool_name}")
                    tool_results.append({
                        "call_id": call.get('id', ''),
                        "tool": tool_name,
                        "result": {"error": f"Tool '{tool_name}' not available"}
                    })
                    continue
                
                # Execute
                result = await self._execute_tool(tool_name, args)
                
                # Validate result
                if isinstance(result, dict) and result.get('error'):
                    logger.warning(f"Tool error: {tool_name} - {result.get('error')}")
                
                tool_results.append({
                    "call_id": call.get('id', ''),
                    "tool": tool_name,
                    "result": result
                })
            
            # Add tool results to messages and continue loop
            for result in tool_results:
                messages.append({
                    "role": "tool",
                    "content": str(result.get('result', {}))
                })
        
        # ===== REMEMBER IMPORTANT INTERACTIONS =====
        if inner_life and final_content:
            try:
                # Remember this interaction
                inner_life.remember(
                    f"Agent interaction: user said '{message[:100]}...', agent responded with '{final_content[:100]}...'",
                    memory_type="interaction",
                    confidence=0.7
                )
            except Exception as e:
                logger.warning(f"Failed to remember interaction: {e}")
        
        return AgentResponse(
            success=True,
            content=final_content or "No response generated",
            execution_time_ms=(time.time() - start_time) * 1000
        )
    
    async def _call_llm(self, model: str, messages: List[Dict], tools: List[Dict]):
        """Call the LLM provider."""
        if not self.llm:
            return type('obj', (object,), {
                'success': False,
                'error': 'No LLM provider configured'
            })()
        
        try:
            # Use the LLM provider
            if hasattr(self.llm, 'chat'):
                response = self.llm.chat(messages, model=model)
                return type('obj', (object,), {
                    'success': True,
                    'content': response.content if hasattr(response, 'content') else str(response)
                })()
            else:
                return type('obj', (object,), {
                    'success': False,
                    'error': 'LLM provider does not support chat'
                })()
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return type('obj', (object,), {
                'success': False,
                'error': str(e)
            })()
    
    def _extract_tool_calls(self, content: str) -> List[Dict]:
        """Extract tool calls from LLM response."""
        import re
        
        # Try to find JSON tool calls in the response
        tool_calls = []
        
        # Pattern 1: <tool_call>...</tool_call>
        pattern1 = r'<tool_call>(.*?)</tool_call>'
        matches = re.findall(pattern1, content, re.DOTALL)
        for match in matches:
            try:
                tool_calls.append(json.loads(match))
            except:
                pass
        
        # Pattern 2: <tool_call>{...}</tool_call> (no closing tag properly formatted)
        pattern2 = r'<tool_call>(\{.*?\})</tool_call>'
        matches = re.findall(pattern2, content, re.DOTALL)
        for match in matches:
            try:
                tool_calls.append(json.loads(match))
            except:
                pass
        
        # Pattern 3: Just { "name": ... } anywhere in content
        pattern3 = r'\{"name"\s*:\s*"([^"]+)"[^}]*\}'
        matches = re.findall(pattern3, content)
        for match in matches:
            tool_calls.append({"name": match, "arguments": {}})
        
        return tool_calls
    
    async def _execute_tool(self, tool_name: str, args: Dict) -> Any:
        """Execute a tool and return the result."""
        if not self.tools:
            return {"error": "No tool engine configured"}
        
        if tool_name not in self.tools.tools:
            return {"error": f"Tool '{tool_name}' not found"}
        
        try:
            func = self.tools.tools[tool_name]
            
            # Get function signature to determine how to call it
            import inspect
            sig = inspect.signature(func)
            
            # Execute in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            # Check if function takes arguments (more than just 'self')
            if len(sig.parameters) > 1:
                result = await loop.run_in_executor(None, lambda: func(args))
            else:
                result = await loop.run_in_executor(None, func)
            
            return result if result is not None else {"success": True}
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name} - {e}")
            return {"error": str(e)}


# Singleton instance
_executor = None

def get_agent_executor(llm_provider=None, tool_engine=None, inner_life=None) -> AgentExecutor:
    """Get or create the agent executor singleton."""
    global _executor
    if _executor is None:
        _executor = AgentExecutor(llm_provider, tool_engine, inner_life)
    else:
        if llm_provider:
            _executor.set_llm_provider(llm_provider)
        if tool_engine:
            _executor.set_tool_engine(tool_engine)
        if inner_life:
            _executor.set_inner_life(inner_life)
    return _executor
