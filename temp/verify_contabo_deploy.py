"""Verify Contabo after deploy. Pass via CONTABO_SSH_PASS."""
from __future__ import annotations

import os
import sys
import time

import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("84.46.243.149", username="root", password=os.environ["CONTABO_SSH_PASS"], timeout=30)


def run(cmd: str, t: int = 60) -> str:
    _, o, e = c.exec_command(cmd, timeout=t)
    out = o.read().decode("utf-8", errors="replace")
    err = e.read().decode("utf-8", errors="replace")
    code = o.channel.recv_exit_status()
    return f"exit={code}\n{out}{err}"


print("WAIT 20s for startup...")
time.sleep(20)
print(run("docker inspect dastyor-ai --format 'health={{.State.Health.Status}} status={{.State.Status}} restart={{.RestartCount}}'"))
print(run(
    "docker exec dastyor-ai python -c \""
    "import time,urllib.request;"
    "t=time.perf_counter();"
    "b=urllib.request.urlopen('http://127.0.0.1:8000/ping',timeout=5).read();"
    "print('ping_ms',int((time.perf_counter()-t)*1000),b[:80]);"
    "t=time.perf_counter();"
    "b=urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=5).read();"
    "print('health_ms',int((time.perf_counter()-t)*1000),b[:240])"
    "\""
))
print(run("cd /opt/dastyor-ai && git log -1 --oneline && git status -sb"))
print(run("docker logs --tail 20 dastyor-ai"))
c.close()
