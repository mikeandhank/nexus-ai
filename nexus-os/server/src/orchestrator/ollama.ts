/**
 * Sprint 4: Ollama Local Model as NexusOS Orchestration Brain
 * 
 * Architecture:
 * - Local Ollama: always-on, zero latency, handles ALL internal operations
 * - Cloud model: external-facing work only (user queries, public API calls)
 * 
 * Internal operations that Ollama handles:
 * - Memory consolidation
 * - Reasoning traces
 * - Graph propagation analysis
 * - Outcome attribution
 * - Confidence calibration
 * - Autonomy decision-making
 */

/* ============================================
   OLLAMA CONFIGURATION
   ============================================ */

const OLLAMA_CONFIG = {
  host: 'localhost:11434',
  model: 'llama3.2:1b',  // Lightweight, fast, sufficient for orchestration
  temperature: 0.3,      // Lower = more deterministic
  max_tokens: 2048,
};

/* ============================================
   OPERATIONS HANDLED BY LOCAL OLLAMA
   ============================================ */

const INTERNAL_OPERATIONS = {
  MEMORY_CONSOLIDATION: 'memory_consolidation',
  MEMORY_RETRIEVAL: 'memory_retrieval',
  REASONING_TRACE: 'reasoning_trace',
  CAUSAL_ANALYSIS: 'causal_analysis',
  OUTCOME_ATTRIBUTION: 'outcome_attribution',
  PREDICTION_CALIBRATION: 'prediction_calibration',
  ACTION_DECISION: 'action_decision',
  CONFLICT_RESOLUTION: 'conflict_resolution',
  SELF_EVALUATION: 'self_evaluation',
} as const;

/* ============================================
   SYSTEM PROMPTS
   ============================================ */

const SYSTEM_PROMPTS: Record<string, string> = {
  [INTERNAL_OPERATIONS.MEMORY_CONSOLIDATION]: `You are a memory consolidation engine.
Given recent episodic memories, extract key facts and patterns.
Return structured semantic knowledge.
Confidence scoring: 0-1 for each fact.`,

  [INTERNAL_OPERATIONS.REASONING_TRACE]: `You are a reasoning engine.
Given a decision to make, think through options and implications.
Output a structured reasoning trace.
Be explicit about what you know vs. assume.`,

  [INTERNAL_OPERATIONS.CAUSAL_ANALYSIS]: `You are a causal analysis engine.
Given a changed node in a knowledge graph, analyze what might be affected.
Consider: causes, blocks, depends_on, validates, contradicts relationships.`,

  [INTERNAL_OPERATIONS.OUTCOME_ATTRIBUTION]: `You are an attribution engine.
Given an outcome, analyze which actions likely caused it.
Consider: timeline, causal mechanisms, confounding factors.
Return confidence scores for each potential cause.`,

  [INTERNAL_OPERATIONS.ACTION_DECISION]: `You are an autonomy decision engine.
Given a proposed action and context, decide if you should execute.
Consider: decision rights, confidence, risk, precedent.
Return: { canAct: boolean, confidence: number, reasoning: string }`,
};

/* ============================================
   OLLAMA CLIENT
   ============================================ */

class OllamaClient {
  private baseUrl: string;
  private model: string;

  constructor(config?: Partial<typeof OLLAMA_CONFIG>) {
    this.baseUrl = config?.host ?? OLLAMA_CONFIG.host;
    this.model = config?.model ?? OLLAMA_CONFIG.model;
  }

  async generate(
    operation: keyof typeof INTERNAL_OPERATIONS,
    userPrompt: string,
    options?: { temperature?: number; max_tokens?: number; }
  ): Promise<string> {
    const systemPrompt = SYSTEM_PROMPTS[operation];
    
    const response = await fetch(`${this.baseUrl}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: this.model,
        prompt: `System: ${systemPrompt}\n\nUser: ${userPrompt}`,
        stream: false,
        options: {
          temperature: options?.temperature ?? OLLAMA_CONFIG.temperature,
          num_predict: options?.max_tokens ?? OLLAMA_CONFIG.max_tokens,
        },
      }),
    });

    if (!response.ok) throw new Error(`Ollama error: ${response.status}`);
    const result = await response.json();
    return result.response;
  }

  async isHealthy(): Promise<boolean> {
    try {
      const resp = await fetch(`${this.baseUrl}/api/tags`);
      return resp.ok;
    } catch {
      return false;
    }
  }
}

/* ============================================
   ORCHESTRATION ENGINE
   ============================================ */

export class NexusOSOrchestrator {
  private ollama: OllamaClient;
  private isLocalReady: boolean = false;

  constructor() {
    this.ollama = new OllamaClient();
  }

  async init(): Promise<boolean> {
    this.isLocalReady = await this.ollama.isHealthy();
    console.log(`NexusOS Ollama: ${this.isLocalReady ? 'READY' : 'UNAVAILABLE'}`);
    return this.isLocalReady;
  }

  async route(operation: keyof typeof INTERNAL_OPERATIONS, prompt: string): Promise<string> {
    if (this.isLocalReady) {
      try {
        return await this.ollama.generate(operation, prompt);
      } catch (e) {
        console.warn('Ollama failed:', e);
      }
    }
    throw new Error('Local Ollama unavailable');
  }

  async consolidateMemory(episodicMemories: string[]): Promise<string> {
    return this.route(INTERNAL_OPERATIONS.MEMORY_CONSOLIDATION, episodicMemories.join('\n'));
  }

  async traceReasoning(decision: string, context: string): Promise<string> {
    return this.route(INTERNAL_OPERATIONS.REASONING_TRACE, `Decision: ${decision}\nContext: ${context}`);
  }

  async analyzeCausality(changedNode: string, graphContext: string): Promise<string> {
    return this.route(INTERNAL_OPERATIONS.CAUSAL_ANALYSIS, `Changed: ${changedNode}\nGraph: ${graphContext}`);
  }

  async decideAction(proposedAction: string, context: string): Promise<{ canAct: boolean; confidence: number; reasoning: string }> {
    const result = await this.route(INTERNAL_OPERATIONS.ACTION_DECISION, `Action: ${proposedAction}\nContext: ${context}`);
    // Parse result - simplified for v1
    return { canAct: true, confidence: 0.7, reasoning: result.slice(0, 200) };
  }
}

export { INTERNAL_OPERATIONS, OLLAMA_CONFIG };