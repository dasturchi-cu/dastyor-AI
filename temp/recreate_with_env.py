"""Recreate dastyor-ai with updated .env (GitHub model) and verify."""
from __future__ import annotations

import sys
import time

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("84.46.243.149", username="root", password="muhammad9085", timeout=30)


def run(cmd: str, timeout: int = 300) -> tuple[str, str]:
    _, o, e = c.exec_command(cmd, timeout=timeout)
    return o.read().decode("utf-8", errors="replace"), e.read().decode("utf-8", errors="replace")


out, _ = run("docker inspect dastyor-ai --format '{{.Config.Image}} {{.HostConfig.RestartPolicy.Name}}'")
print("image/policy:", out.strip())

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
sleep 12
echo GITHUB_MODEL=$(docker exec dastyor-ai printenv GITHUB_MODEL)
docker inspect dastyor-ai --format 'status={{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}'
"""
out, err = run(script, timeout=180)
print(out)
if err.strip():
    print("stderr:", err[:800])

for i in range(10):
    time.sleep(8)
    out, _ = run("docker inspect dastyor-ai --format '{{.State.Health.Status}}'")
    status = out.strip()
    print(f"health[{i}]: {status}")
    if status == "healthy":
        break

# Re-copy probe if missing after recreate (same image should still have /app)
out, err = run(
    "docker exec dastyor-ai test -f /app/temp_probe_errors.py || "
    "(docker cp /opt/dastyor-ai/temp/probe_errors.py dastyor-ai:/app/temp_probe_errors.py); "
    "docker exec dastyor-ai python /app/temp_probe_errors.py",
    timeout=200,
)
print("PROBE:", out or err)

out, _ = run(
    "docker exec dastyor-ai python -c \""
    "import time,urllib.request\n"
    "t=time.perf_counter()\n"
    "r=urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)\n"
    "print('health', int((time.perf_counter()-t)*1000), 'ms', r.read()[:120])\n"
    "\""
)
print("HEALTH BODY:", out)
c.close()
