"""Hotfix critical files on production + prune quota history + restart."""
from __future__ import annotations

import io
import sys
import time

import paramiko

HOST = "84.46.243.149"
USER = "root"
PASS = "muhammad9085"
CONTAINER = "dastyor-ai"
APP = "/opt/dastyor-ai"

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
    "Dockerfile",
    "docker-compose.yml",
]

PRUNE_PY = r"""
from database.repositories.ai_quota import prune_history
import os, sqlite3
n = prune_history(keep_days=14)
print('pruned', n)
db = '/data/app.db'
conn = sqlite3.connect(db)
before = os.path.getsize(db)
conn.execute('VACUUM')
conn.close()
after = os.path.getsize(db)
print('db_mb_before', round(before/1024/1024,2), 'after', round(after/1024/1024,2))
print('history_left', sqlite3.connect(db).execute('SELECT COUNT(*) FROM ai_quota_history').fetchone()[0])
"""


def run(c, cmd, timeout=600):
    _, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return out, err


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("connect...")
    c.connect(HOST, username=USER, password=PASS, timeout=30)
    sftp = c.open_sftp()
    try:
        sftp.mkdir(f"{APP}/temp")
    except OSError:
        pass

    for rel in FILES:
        local = rel.replace("/", "\\") if False else rel
        remote = f"{APP}/{rel}"
        # ensure remote dir
        parts = rel.split("/")[:-1]
        cur = APP
        for p in parts:
            cur = f"{cur}/{p}"
            try:
                sftp.mkdir(cur)
            except OSError:
                pass
        print(f"upload {rel}")
        sftp.put(rel, remote)
        # copy into running container filesystem (bind may or may not exist)
        out, err = run(c, f"docker cp {remote} {CONTAINER}:/app/{rel}")
        if err.strip():
            print("  docker cp warn:", err[:200])

    with sftp.file(f"{APP}/temp/prune_now.py", "w") as f:
        f.write(PRUNE_PY)
    sftp.close()

    print("prune + vacuum...")
    out, err = run(
        c,
        f"docker cp {APP}/temp/prune_now.py {CONTAINER}:/app/temp_prune_now.py && "
        f"docker exec {CONTAINER} python /app/temp_prune_now.py",
        timeout=600,
    )
    print(out or err)

    print("restart container...")
    out, err = run(c, f"docker restart {CONTAINER}", timeout=120)
    print(out or err)
    time.sleep(8)

    print("health/ping after restart...")
    out, err = run(
        c,
        "docker exec dastyor-ai python -c \""
        "import time,urllib.request\n"
        "for path in ['/ping','/health']:\n"
        " t=time.perf_counter()\n"
        " try:\n"
        "  r=urllib.request.urlopen('http://127.0.0.1:8000'+path, timeout=10)\n"
        "  print(path, int((time.perf_counter()-t)*1000), 'ms', r.status, r.read()[:120])\n"
        " except Exception as e:\n"
        "  print(path, int((time.perf_counter()-t)*1000), 'ms FAIL', e)\n"
        "\"",
        timeout=60,
    )
    print(out or err)

    out, _ = run(
        c,
        "docker inspect dastyor-ai --format '{{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}'",
    )
    print("inspect:", out)
    # wait for healthy
    for i in range(6):
        time.sleep(10)
        out, _ = run(
            c,
            "docker inspect dastyor-ai --format '{{.State.Health.Status}}'",
        )
        print(f"health[{i}]:", out.strip())
        if out.strip() == "healthy":
            break

    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
