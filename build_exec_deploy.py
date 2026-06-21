"""
Build deploy chunks for exec dashboard files.
Outputs: deploy_html1.sh, deploy_html2.sh, deploy_routes.sh, deploy_actions.sh
"""
import base64, pathlib, math

ROOT   = pathlib.Path(__file__).parent
OUT    = ROOT / "output"
DEPLOY = ROOT / "deploy_chunks"
DEPLOY.mkdir(exist_ok=True)

CHUNK = 55000   # safe under 65KB Azure limit

def write_chunks(src: pathlib.Path, dest: str, prefix: str):
    data  = src.read_bytes()
    b64   = base64.b64encode(data).decode()
    total = len(b64)
    n     = math.ceil(total / CHUNK)
    print(f"{src.name}: {len(data):,} bytes -> {n} chunk(s)")

    for i in range(n):
        chunk = b64[i*CHUNK:(i+1)*CHUNK]
        mode  = "wb" if i == 0 else "ab"
        script = (
            f'python3 -c "'
            f'import base64,pathlib,os;'
            f'os.makedirs(os.path.dirname(\\"{dest}\\"),exist_ok=True);'
            f'pathlib.Path(\\"{dest}\\").open(\\"{mode}\\").write(base64.b64decode(\\"{chunk}\\"))"'
        )
        out_file = DEPLOY / f"{prefix}_{i+1}.sh"
        out_file.write_text(script, encoding="utf-8")
        size = len(script.encode())
        print(f"  chunk {i+1}: {size:,} bytes -> {out_file.name}")

# HTML (likely 2 chunks)
write_chunks(
    OUT / "exec_dashboard.html",
    "/home/azureuser/zfp-advisor/static/exec_dashboard.html",
    "deploy_html"
)

# Action Register (likely 1 chunk)
write_chunks(
    OUT / "action_register.html",
    "/home/azureuser/zfp-advisor/static/action_register.html",
    "deploy_register"
)

# Routes (1 chunk)
write_chunks(
    OUT / "exec_routes.py",
    "/home/azureuser/zfp-advisor/backend/exec_routes.py",
    "deploy_routes"
)

# Actions JSON (1 chunk)
write_chunks(
    OUT / "action_register.json",
    "/home/azureuser/zfp-advisor/data/action_register.json",
    "deploy_actions"
)

print("\nAll chunks written to deploy_chunks/")
