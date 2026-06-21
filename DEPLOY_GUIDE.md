# DEPLOY GUIDE — ZFP Executive Dashboard

You are the Deployer agent. Deploy the exec dashboard to Azure VM.

## Target
- VM: askhr-zfp, UAE North
- App root: /home/azureuser/zfp-advisor/
- Service: zfp-advisor.service (uvicorn port 8001)
- URL: https://ceoassistant.uaenorth.cloudapp.azure.com/exec/

## CRITICAL CONSTRAINTS
- Azure Run Command wraps in /bin/sh -c
- NEVER use heredocs (<< EOF) — they corrupt Python files
- NEVER use multiline strings in -c arguments
- For file writes: use base64 encoding (encode locally, echo -n chunks, base64 -d)
- Each base64 chunk must be under 500 chars
- Test with: python3 -c "import ast; ast.parse(open('file.py').read()); print('OK')"

## Step 1 — Deploy HTML
Encode exec_dashboard.html to base64, split into 500-char chunks.
Use Azure Run Command to write each chunk, then decode.

## Step 2 — Deploy Routes
Add exec routes to main.py. Read current main.py first.
Add routes BEFORE the health check endpoint.
Routes needed:
```python
@app.get("/exec/")
async def serve_exec():
    return _static("exec_dashboard.html")

@app.get("/exec/actions")
async def get_actions():
    import json, os
    path = "/home/azureuser/zfp-advisor/Data/action_register.json"
    if os.path.exists(path):
        return JSONResponse(json.load(open(path)))
    return JSONResponse({"actions": [], "summary": {}})

@app.post("/exec/actions/{action_id}")
async def update_action(action_id: str, req: Request):
    import json, os
    data = await req.json()
    path = "/home/azureuser/zfp-advisor/Data/action_register.json"
    register = json.load(open(path)) if os.path.exists(path) else {"actions": []}
    for a in register.get("actions", []):
        if a["id"] == action_id:
            a["status"] = data.get("status", a["status"])
            if data.get("note"): a["note"] = data["note"]
    open(path, "w").write(json.dumps(register, indent=2))
    return JSONResponse({"ok": True})
```

## Step 3 — Deploy action_register.json
```bash
mkdir -p /home/azureuser/zfp-advisor/Data
# Write action_register.json using base64 method
```

## Step 4 — Update nginx
Add to /etc/nginx/sites-available/ceoassistant:
```nginx
location /exec/ {
    proxy_pass http://127.0.0.1:8001/exec/;
    proxy_set_header Host $host;
    proxy_read_timeout 120s;
}
location /exec/actions {
    proxy_pass http://127.0.0.1:8001/exec/actions;
    proxy_set_header Host $host;
}
```

## Step 5 — Restart and verify
```bash
systemctl restart zfp-advisor && sleep 2
curl -s http://127.0.0.1:8001/exec/ | head -c 100
curl -s http://127.0.0.1:8001/exec/actions | head -c 200
```

## Step 6 — Report back
Tell Orchestrator:
- Deployment status (success/failed)
- Live URL
- Any issues encountered
