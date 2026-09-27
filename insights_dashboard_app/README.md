# Insights Dashboard

This directory contains the complete local source needed to run `insights_dashboard.py`.

## Setup and run (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Edit .env and set ONET_API_KEY before starting the app.
.\.venv\Scripts\python.exe insights_dashboard.py
```

Run these commands from this directory. The application opens in the default web browser. The local `.env` file is ignored by Git and should contain `ONET_API_KEY=your-v2-api-key`. The O*NET key stays in the Python process and is sent only in the `X-API-Key` request header; it is never included in search results or frontend controls. An existing process-level `ONET_API_KEY` takes precedence over the local file.
