Run the mock Vantage server and test harness locally

1) Start the mock Vantage TCP server (listens on 127.0.0.1:2323 by default)

PowerShell:

```powershell
python .\scripts\mock_vantage.py --host 127.0.0.1 --port 2323
```

2) Start the bridge (if you want to run the project's FastAPI bridge locally), and point it to the mock server:

PowerShell example (temporary env override, run in same terminal before starting the bridge):

```powershell
$env:VANTAGE_IP = '127.0.0.1'; $env:VANTAGE_PORT = '2323'
# then start the bridge (example using uvicorn):
# python -m uvicorn app.bridge:app --reload --host 127.0.0.1 --port 8000
```

3) Run the test harness to exercise write/read flows:

PowerShell:

```powershell
python .\scripts\test_harness.py --bridge http://127.0.0.1:8000 --device 251 --level 50

python .\scripts\test_harness.py --bridge http://127.0.0.1:8000 --raw "VGL 251"
```

Notes:
- The harness depends on `requests` (pip install requests).
- If you cannot run the project bridge locally, the harness can still be used
  to call any remote bridge you have access to (change --bridge URL).
