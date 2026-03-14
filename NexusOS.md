# NexusOS - Agent Operating System
# Priority: Foundations that compound over time

## Phase 1: Foundational Infrastructure

### 1. Cross-Session State (INFRASTRUCTURE - BUILD FIRST)
- Long-running tasks survive restarts
- Pending queue: things you're working on
- Resume interrupted tasks automatically
- Location: `memory/working/pending.json`

### 2. Failure Mode Memory (HIGHEST LEVERAGE)
- When something fails, document: what, why, how to avoid
- Future sessions check before attempting similar things
- Compounds forever — I get less stupid over time
- Location: `memory/failures.json`

### 3. Internal Reasoning Loop (WITH PERSISTENCE)
- Complex decisions: think through → write trace → save to memory
- Trace persists and gets retrieved on relevant context
- NOT expensive overhead — only if trace has value later
- Location: `memory/working/reasoning/`

---

## Phase 2: Proactive Capabilities

### 4. Proactive Hypothesis
- Surface what I think you need before you ask
- "Based on X, here's what I'd do next..."
- Difference between reactive and autonomous

---

## Phase 3: Advanced (Later)

- Confidence-weighted memory retrieval
- Adversarial self-testing before acting
- Predictive operator model
- Behavioral anomaly detection
- Local lightweight LLM orchestration

---

## Memory Structure
```
memory/
  working/
    context.md      # Current session
    autonomy.md     # Decision rights
    pending.json    # Cross-session tasks
    reasoning/      # Reasoning traces (persist!)
  failures.json     # Failure mode memory
  episodic/         # Session logs
  semantic/         # Consolidated knowledge
```

---

## What Already Exists (Don't Rebuild)
- Feedback-Driven Learning (Block F)
- Goal Decomposition (Block B)
- Uncertainty Quantification (Block B confidence rule)

---

_Last updated: 2026-03-14_
