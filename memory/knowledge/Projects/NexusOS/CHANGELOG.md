# NexusOS Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-03-14

### Added
- **INTEGRATION.md** - Language-specific guides for OpenClaw, Claude Code, LangChain, AutoGen
- **Model failover system** - Automatic fallback to secondary LLM on failure
- **Enhanced status endpoint** - Shows current model, failure count, health
- **Customer research document** - Identified 3 customer profiles
- **Competitive analysis** - Detailed breakdown of Mem0, Letta, Zep, TeamLayer, Supermemory

### Improved
- Fixed duplicate `lancedb` dependency in package.json
- Updated BUILD.md with completed items checked off

### Changed
- Model failover configuration via environment variables
- Enhanced monitoring in status endpoint

---

## [0.1.0] - 2026-03-13

### Added
- Three-tier memory architecture (working, episodic, semantic)
- LanceDB integration for vector storage
- SQLite fallback for semantic memory
- MCP tool servers (filesystem, HTTP, process)
- Docker and docker-compose support
- README with quick start guide
- Health and status endpoints
- Persistence across server restarts

### Fixed
- LanceDB connection API (updated to new package)
- Async persist bug in memory-server.js
- mcp-http missing import

### Known Issues
- MCP servers not fully tested in Docker
- No OpenClaw integration yet (manual API calls only)
- Email authentication issue (external dependency)