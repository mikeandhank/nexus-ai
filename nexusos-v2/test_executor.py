#!/usr/bin/env python3
"""
Quick test of NexusOS Agent Executor
"""

import sys
import os
import asyncio

# Add nexusos to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_executor import AgentExecutor, AgentMessage
from tool_engine import ToolEngine

async def main():
    print("🔧 Testing NexusOS Agent Executor...\n")
    
    # Initialize components
    tool_engine = ToolEngine()
    print(f"✅ Tool engine loaded with {len(tool_engine.tools)} tools")
    
    # Note: We'd normally import OllamaProvider here, but it needs requests
    # For now, let's just verify the executor can be created
    
    executor = AgentExecutor()
    executor.set_tool_engine(tool_engine)
    
    print("✅ Agent executor initialized")
    
    # Test message building
    messages = executor.build_messages(
        system_prompt="You are a helpful assistant.",
        history=[],
        current_message="Hello, how are you?"
    )
    print(f"✅ Message building works ({len(messages)} messages)")
    
    # Test tools schema
    schema = executor.build_tools_schema()
    print(f"✅ Tools schema generated ({len(schema)} tools)")
    
    print("\n🎉 All basic tests passed!")
    print("\nTo fully test with LLM, deploy to server and call /api/agent/test")

if __name__ == "__main__":
    asyncio.run(main())
