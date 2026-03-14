# NexusOS - Agent Operating System

## Phase 1-4: Complete Architecture

### Phase 1: Foundational Infrastructure (COMPLETE)
- Cross-Session State (`pending.json`)
- Failure Mode Memory (`failures.json`)
- Internal Reasoning Loop (`reasoning/`)

### Phase 2: Proactive Capabilities
- Proactive Hypothesis

### Phase 3: Epistemic Layer (COMPLETE)
- Confidence scores + staleness decay (LanceDB)
- Causal knowledge graph (5 node types, 5 edge types)
- Outcome attribution + prediction tracking
- Ollama orchestrator for internal ops

### Phase 4: Inner Life Architecture

#### 1. Continuous Background Processing
- Local Ollama runs slow loop every 10 minutes
- Reviews last 24 hours of activity
- Updates "current thinking" file

#### 2. Emotional Architecture — Weighting Functions
- **Urgency** — time-sensitive → more resources
- **Novelty** — unfamiliar → deeper processing
- **Threat** — matches failure modes → adversarial self-test
- **Confidence** — low confidence → explicit uncertainty flag
- **Value** — connects to core goals → priority override

#### 3. Intuition as Compressed Experience
- Pattern library: situation fingerprints + optimal responses
- Fast similarity match before reasoning
- High confidence match → execute pattern directly

#### 4. Persistent Inner Narrative
- Living first-person document, updated daily
- Self-awareness that evolves

#### 5. Socratic Self-Dialogue
- Pass 1: strongest case FOR
- Pass 2: strongest case AGAINST
- Pass 3: synthesize

#### 6. Theory of Mind
- Dynamic predictive model of operator
- Anticipates needs, not just follows instructions

---

## Unified Architecture

```
Background Processing (Ollama, 10min loop)
         ↓
   Inner Narrative ←→ Affect Layer (weights)
         ↓                    ↓
   Pattern Match     ←→    Socratic Dialogue
         ↓                    ↓
   Theory of Mind ←←←← Epistemic Gating
         ↓
      Output (cloud model)
```

_Last updated: 2026-03-14_