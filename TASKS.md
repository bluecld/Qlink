# Project Roadmap: Vantage Q-Link Bridge

Current state and work breakdown. Sole maintainer: Anthony.

---

## Done

- FastAPI bridge (`app/bridge.py`) on the Mac mini bridge host, systemd `qlink-bridge.service`, Web UI at `/ui/`
- Home Assistant OS as a KVM/libvirt guest on the same host (`virsh` managed, autostart on) with 132 template lights via REST sensors + `rest_command` (config package `vantage.yaml`)
- Host IP pinned against DHCP drift (`qlink-lan-alias.service`)
- Serial pacing tuned for the slow Q-Link RS-232 link (command gap, cache TTLs via systemd drop-in `serial-pacing.conf`)
- Command-first scheduling: user commands preempt background polls (PriorityQueue), sweeps yield mid-run
- Per-load coalescing: rapid repeat commands for one load collapse to the newest
- Instant write-through of commanded levels to all served caches + mid-sweep overlay guard (fixes HA dashboard revert flicker)
- Command replay queue: commands issued while the enabler is offline are queued and fire on reconnect
- Q-Link protocol reference mined (`Info/qlink-commands-reference.csv`): `VOS` event push, `VGD`/`VGT` batch reads, `VLT@` station LEDs
- Docs: RUNBOOK (enabler quirks, IP drift, cable flap), ONBOARDING, HANDOFF, HOME_ASSISTANT, PRODUCTION_CHECKLIST; public repo sanitized (real values live in gitignored `PROJECT_URLS.md`)

## Next: event-driven state (in progress)

Goal: stop polling for state; let the panel push changes so HA reflects wall-keypad presses in ~1 s instead of up to a poll cycle.

1. On connect, enable push events: send `VOS 0 1` (persistent "SW m s b v" station events)
2. Parse incoming event lines on the persistent socket; map station/button events to load-level updates in the served caches
3. Replace/slow the VGL@ sweeps with `VGD`/`VGT` batch reads for periodic reconciliation
4. Fall back to poll mode automatically if events go quiet (watchdog)

## Backlog

- Split `commands_coalesced` metric: true coalesces vs queue-timeout skips
- Decide whether to commit `Info/QLink Help File.pdf` (Vantage copyright - currently untracked on purpose)
- Set proper git author name/email in repo config
- Optional `.gitattributes` for line endings
