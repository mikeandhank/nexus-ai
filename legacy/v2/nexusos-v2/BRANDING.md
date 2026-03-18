# Agent Intelligence Engine (formerly "Inner Life")

## Rebranding

As of 2026-03-16, the "Inner Life" system has been renamed to:

**Agent Intelligence Engine (AIE)**

This better reflects the enterprise-focused positioning of NexusOS.

### Naming Convention

| Old | New |
|-----|-----|
| Inner Life | Agent Intelligence Engine (AIE) |
| inner_life | agent_intelligence_engine (module) |
| InnerLifeEngine | AgentIntelligenceEngine (class) |

### Backward Compatibility

The old module paths still work but are deprecated:

```python
# Old (deprecated)
from inner_life import get_inner_life
inner_life = get_inner_life("user123")

# New (recommended)
from agent_intelligence_engine import get_agent_engine
engine = get_agent_engine("user123")
```

### Files Affected

- `inner_life/` → `agent_intelligence_engine/`
- Database tables: no change (internal)
- API endpoints: no change (internal)

### Migration Timeline

- Phase 1 (2026-03-16): Documentation updated
- Phase 2 (2026-04-01): Module aliases created
- Phase 3 (2026-06-01): Old paths deprecated