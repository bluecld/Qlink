## Vantage Bridge Progress

- Updated SmartThings Edge driver with LAN discovery, HTTPS client support, and documentation tweaks.
- Built and uploaded driver version `2025-11-03T20:06:28.680894576`, assigned to *My Vantage Bridge Channel*, installed on hub `92e0cdbe-81a5-49c6-91a5-45f31204b21b`.
- Need to capture logcat from `smartthings edge:drivers:logcat 0dd7f90d-9d6b-46e3-8d1f-6c46b7d2a11f --hub-address 192.168.1.155 --log-level INFO` and run `smartthings devices:commands 92e0cdbe-81a5-49c6-91a5-45f31204b21b refresh refresh --args "{}"` or scan via app to trigger discovery.
- Next step after logs: confirm parent *Vantage QLink Bridge* device creation and configure bridge preferences (IP `192.168.1.227`, port `8000`, HTTPS disabled unless Pi serves TLS).
