"""Recreate container with new env AND re-apply code hotfixes."""
from __future__ import annotations

import sys
import time

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOST = "84.46.243.149"
USER = "root"
PASS = "muhammad9085"
APP = "/opt/dastyor-ai"
CONTAINER = "dastyor-ai"

FILES = [
    "database/verify.py",
    "backend/routers/site.py",
    "backend/routers/tg_update.py",
    "features/ai/routing/adapters.py",
    "features/ai/routing/config.py",
    "features/ai/routing/quota.py",
    "features/ai/routing/health.py",
    "database/repositories/ai_quota.py",
    "shared/keyboards.py",
]

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASS, timeout=30)


def run(cmd: str, timeout: int = 300) -> tuple[str, str]:
    _, o, e = c.exec_command(cmd, timeout=timeout)
    return o.read().decode("utf-8", errors="replace"), e.read().decode("utf-8", errors="replace")


print("recreate container...")
script = r"""
set -e
IMG=$(docker inspect dastyor-ai --format '{{.Config.Image}}')
echo IMAGE=$IMG
docker stop dastyor-ai
docker rm dastyor-ai
docker run -d --name dastyor-ai --restart unless-stopped \
  -p 8000:8000 \
  --env-file /opt/dastyor-ai/.env \
  -e DATA_DIR=/data -e PORT=8000 -e PRODUCTION=1 \
  -v /opt/dastyor-ai/data:/data \
  "$IMG"
sleep 8
echo GITHUB_MODEL=$(docker exec dastyor-ai printenv GITHUB_MODEL || true)
"""
out, err = run(script, timeout=180)
print(out)
if err.strip():
    print("stderr:", err[:500])

print("re-apply hotfix files...")
sftp = c.open_sftp()
for rel in FILES:
    remote = f"{APP}/{rel}"
    sftp.put(rel, remote)
    o, e = run(f"docker cp {remote} {CONTAINER}:/app/{rel}")
    print(" ", rel, "ok" if not e.strip() else e[:120])
sftp.put("temp/probe_errors.py", f"{APP}/temp/probe_errors.py")
run(f"docker cp {APP}/temp/probe_errors.py {CONTAINER}:/app/temp_probe_errors.py")
sftp.close()

print("restart to load code...")
print(run(f"docker restart {CONTAINER}")[0])
time.sleep(12)

for i in range(10):
    out, _ = run("docker inspect dastyor-ai --format '{{.State.Health.Status}}'")
    status = (out or "").strip()
    print(f"health[{i}]: {status}")
    if status == "healthy":
        break
    time.sleep(8)

out, _ = run(
    "docker exec dastyor-ai python -c \""
    "import time,urllib.request\n"
    "for path in ['/ping','/health']:\n"
    " t=time.perf_counter(); r=urllib.request.urlopen('http://127.0.0.1:8000'+path, timeout=8); "
    "print(path, int((time.perf_counter()-t)*1000), 'ms', r.read()[:140])\n"
    "\""
)
print("TIMING:", out)

out, err = run("docker exec dastyor-ai python /app/temp_probe_errors.py", timeout=200)
print("PROBE:", out or err)
c.close()
