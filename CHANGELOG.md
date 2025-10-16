# Changelog

All notable changes to this project will be documented in this file.

## 0.4.0 - 2025-10-16
### Added
- Real-time event monitoring via WebSocket (/events endpoint)
- Event listener background thread with auto-reconnect
- Support for SW (button), LO/LS/LV (load), and LE/LC (LED) events
- Persistent TCP connection to Vantage for event streaming
- GET /monitor/status endpoint for connection status
- GET /settings and POST /settings endpoints for runtime configuration
- Web-based settings interface at /ui/settings.html
- Live configuration changes without SSH or restart (most settings)
- Button extraction script (scripts/extract_buttons.py)
- Complete loads.json with 470 buttons across 71 stations
- Comprehensive button configuration documentation

### Changed
- Updated VSW@ command format (was VBTN@) per official Q-Link docs
- Default Vantage port changed to 3041 (read/write)
- Enhanced README with comprehensive documentation
- Improved .gitignore for better GitHub hygiene
- Expanded CONTRIBUTING.md with detailed guidelines

### Fixed
- VGL@ command now uses correct format
- Button LED status endpoint returns 501 (not implemented)

## 0.3.0 - 2025-10-14
- Add /healthz endpoint and structured JSON error handling
- Optional .env config, Q_LINK_EOL and QLINK_TIMEOUT support
- File logging with rotation (default /var/log/qlink-bridge.log)
- Add /config endpoint for runtime snapshot
- CI + tests + repo metadata for public sharing
