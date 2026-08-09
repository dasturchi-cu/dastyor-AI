"""Sync Contabo to origin/main, rebuild, verify. Pass CONTABO_SSH_PASS."""
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
        print("CONTABO_SSH_PASS missing", file=sys.stderr)
        return 2

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("connecting...", flush=True)
    client.connect(HOST, username=USER, password=password, timeout=30)
    print("connected", flush=True)

    def run(cmd: str, timeout: int = 1200) -> int:
        print(f"\n>>> {cmd[:200]}", flush=True)
        transport = client.get_transport()
        assert transport is not None
        chan = transport.open_session()
        chan.settimeout(timeout)
        chan.get_pty()
        chan.exec_command(cmd)
        deadline = time.time() + timeout
        while True:
            if chan.recv_ready():
                print(chan.recv(8192).decode("utf-8", errors="replace"), end="", flush=True)
            if chan.recv_stderr_ready():
                print(chan.recv_stderr(8192).decode("utf-8", errors="replace"), end="", flush=True)
            if chan.exit_status_ready() and not chan.recv_ready() and not chan.recv_stderr_ready():
                break
            if time.time() > deadline:
                print("TIMEOUT", flush=True)
                return 124
            time.sleep(0.2)
        code = chan.recv_exit_status()
        print(f"\nexit={code}", flush=True)
        return code

    sync = f"""
set -e
cd {APP}
cp -a .env /tmp/dastyor.env.bak 2>/dev/null || true
git fetch origin
git reset --hard HEAD
git clean -fd -e .env -e data -e uploads
git checkout -B main origin/main
git reset --hard origin/main
git clean -fd -e .env -e data -e uploads
test -f .env || cp /tmp/dastyor.env.bak .env
git status -sb
git log -1 --oneline
"""
    if run(sync, 180) != 0:
        client.close()
        return 1

    # Quiet build — log to file to avoid SSH tty flood
    build = f"""
set -e
cd {APP}
DOCKER_BUILDKIT=1 docker build -t {CONTAINER} . > /tmp/dastyor-build.log 2>&1
tail -n 30 /tmp/dastyor-build.log
docker stop {CONTAINER} || true
docker rm {CONTAINER} || true
docker run -d --name {CONTAINER} --restart unless-stopped -p 8000:8000 \
  -v {APP}/data:/data --env-file {APP}/.env {CONTAINER}
sleep 15
docker ps --filter name={CONTAINER}
docker inspect {CONTAINER} --format 'health={{{{.State.Health.Status}}}} status={{{{.State.Status}}}}'
"""
    if run(build, 1200) != 0:
        run("tail -n 80 /tmp/dastyor-build.log", 60)
        client.close()
        return 1

    run(
        f"docker exec {CONTAINER} python -c \""
        "import time,urllib.request;"
        "t=time.perf_counter();"
        "b=urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=8).read();"
        "print('health_ms',int((time.perf_counter()-t)*1000),b[:260])"
        "\"",
        60,
    )
    run(
        "docker exec dastyor-ai python - <<'PY'\n"
        "from database.connection import get_connection\n"
        "with get_connection() as c:\n"
        "    cols={r[1] for r in c.execute('PRAGMA table_info(payments)')}\n"
        "    ucols={r[1] for r in c.execute('PRAGMA table_info(users)')}\n"
        "    print('payments', sorted(cols & {'package_id','credits_granted','promo_bonus_granted'}))\n"
        "    print('promo_col', 'pay_promo_expires_at' in ucols)\n"
        "    print('mig15', c.execute('select version,name from schema_migrations where version=15').fetchone())\n"
        "PY",
        60,
    )
    run(f"cd {APP} && git log -1 --oneline && docker logs --tail 20 {CONTAINER}", 60)
    client.close()
    print("\nDEPLOY OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
