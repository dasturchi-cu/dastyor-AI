"""Finish Contabo container recreate after image build. Pass via CONTABO_SSH_PASS."""
from __future__ import annotations

import os
import sys
import time

import paramiko

HOST = "84.46.243.149"
USER = "root"
APP = "/opt/dastyor-ai"
CONTAINER = "dastyor-ai"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    password = os.environ.get("CONTABO_SSH_PASS", "").strip()
    if not password:
        return 2

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=password, timeout=30)

    def run(cmd: str, timeout: int = 600) -> int:
        print(f"\n>>> {cmd[:160]}", flush=True)
        transport = client.get_transport()
        assert transport is not None
        chan = transport.open_session()
        chan.settimeout(timeout)
        chan.get_pty()
        chan.exec_command(cmd)
        deadline = time.time() + timeout
        while True:
            if chan.recv_ready():
                print(chan.recv(4096).decode("utf-8", errors="replace"), end="", flush=True)
            if chan.recv_stderr_ready():
                print(chan.recv_stderr(4096).decode("utf-8", errors="replace"), end="", flush=True)
            if chan.exit_status_ready() and not chan.recv_ready() and not chan.recv_stderr_ready():
                break
            if time.time() > deadline:
                print("TIMEOUT", flush=True)
                return 124
            time.sleep(0.15)
        code = chan.recv_exit_status()
        print(f"\nexit={code}", flush=True)
        return code

    # If previous build unfinished, finish it; else image already exists
    code = run(
        f"cd {APP} && docker images {CONTAINER}:latest --format '{{{{.ID}}}} {{{{.CreatedSince}}}}' && "
        f"docker build -t {CONTAINER} .",
        timeout=900,
    )
    if code != 0:
        client.close()
        return code

    code = run(
        f"docker stop {CONTAINER} || true; docker rm {CONTAINER} || true; "
        f"docker run -d --name {CONTAINER} --restart unless-stopped -p 8000:8000 "
        f"-v {APP}/data:/data --env-file {APP}/.env {CONTAINER}; "
        f"sleep 12; docker ps --filter name={CONTAINER}; "
        f"docker inspect {CONTAINER} --format 'health={{{{.State.Health.Status}}}} status={{{{.State.Status}}}}'",
        timeout=180,
    )
    if code != 0:
        client.close()
        return code

    run(
        f"docker exec {CONTAINER} python -c "
        "\"import time,urllib.request;"
        "t=time.perf_counter();"
        "b=urllib.request.urlopen('http://127.0.0.1:8000/ping',timeout=5).read();"
        "print('ping_ms',int((time.perf_counter()-t)*1000),b[:80]);"
        "t=time.perf_counter();"
        "b=urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=5).read();"
        "print('health_ms',int((time.perf_counter()-t)*1000),b[:220])\"",
        timeout=60,
    )
    run(f"cd {APP} && git log -1 --oneline && docker logs --tail 25 {CONTAINER}", timeout=60)
    client.close()
    print("\nDEPLOY OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
