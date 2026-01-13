# Changelog

All notable changes to the **Onyx** (Local RAG Agent) project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - "Shadow" - 2026-01-06
### Added
- **Theme Customization**: Full Dark/Light/Auto theme support with persistent settings.
- **Accent Colors**: 5 user-selectable brand colors (Indigo, Emerald, Amber, Pink, Blue).
- **Desktop Notifications**: System-level notifications for app events with auto-close logic.
- **Settings Persistence**: Comprehensive saving of all user preferences (theme, notification duration, model config).
- **Async Processing**: File uploads now process in background (`/api/tasks/<id>` polling).
- **Logging**: Structured JSON/Text logging to `logs/app.log` with rotation.
- **Security**: 
    - Session-based Browser Context isolation (Fixed global leak).
    - TTL-based cleanup for Pending Tool Approvals.

### Changed
- **UI Polish**: Removed hardcoded dark styles from Light Mode (Inputs, History, Cards).
- **Knowledge Graph**: Implemented Degree Centrality filtering to reduce visual clutter.
- **API**: `/api/files/ingest` now returns `202 Accepted` (Async) or `207 Multi-Status` (Partial).

### Fixed
- **Notifications**: Fixed broken Desktop Notifications and `notification_duration` setting.
- **Access Control**: Fixed `setAccentColor` reference error.
- **Security**: Hardened file path validation in `tools.py` (Path Traversal fix).
- **Stability**: Fixed `ChatOllama` missing import and duplicate `PIL` imports.
- **Critical**: Fixed `BM25Index` load crash on legacy archives.
- **CLI Mode**: Implemented singleton process management (Windows) to prevent multiple terminal windows.
- **Dev**: Enabled `debug=True` in `app.py` for auto-reloading during development.

---

## [2.0.0] - "Obsidian" - 2025-12-25
### Added
- **Complete Rebrand**: "Onyx" identity with dark/cyan theme.
- **Bulk Operations**: Bulk delete sessions via API and UI.
- **Dual Mode**: CLI (`start_cli_chat`) vs Browser mode toggles.
- **UI/UX**:
    - Custom Modal/Toast system (replacing `alert()`).
    - Responsive Grid Header.
    - Glassmorphism design elements.
- **CLI Tool**: Unified `onyx` command and `setup-path` script.

### Changed
- Migrated frontend from Spaghetti JS to modular structure (partial).
- Standardized API response formats.

---

## [1.2.0] - 2025-12-10
### Added
- Hybrid Search (BM25 + FAISS) implementation.
- `RAG_Chain` with dynamic model loading.
- Initial "Prompt Library" feature.

---

## [1.1.0] - 2025-11-29
### Added
- File Ingestion System (PDF, DOCX, TXT).
- Basic Ollama integration (`gemma2:2b`).
- Simple Chat UI.

---

## [1.0.0] - "Prototype" - 2025-11-15
### Initial Release
- Basic Flask Server.
- In-memory session storage (later moved to SQLite).
- Proof of Concept RAG pipeline.
