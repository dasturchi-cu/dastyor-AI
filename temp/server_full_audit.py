"""Production audit: docker health, recent logs, error_logs, AI probe summary."""
from __future__ import annotations

import json
import sys
import time

import paramiko

HOST = "84.46.243.149"
USER = "root"
PASS = "muhammad9085"


REMOTE_AUDIT_PY = r'''
import json, sqlite3, os, traceback
from pathlib import Path

out = {}
try:
    # find db
    candidates = [
        "/app/data/app.db",
        "/app/app.db",
        "/app/data/bot.db",
        "/data/app.db",
    ]
    db = None
    for c in candidates:
        if os.path.exists(c):
            db = c
            break
    if not db:
        # search
        for p in Path("/app").rglob("*.db"):
            if p.stat().st_size > 0:
                db = str(p)
                break
    out["db_path"] = db

    if db:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        out["tables"] = tables

        if "error_logs" in tables:
            rows = conn.execute(
                "SELECT id, category, message, substr(details,1,400) as details, created_at "
                "FROM error_logs ORDER BY id DESC LIMIT 40"
            ).fetchall()
            out["error_logs"] = [dict(r) for r in rows]
            cats = conn.execute(
                "SELECT category, COUNT(*) c FROM error_logs GROUP BY category ORDER BY c DESC LIMIT 20"
            ).fetchall()
            out["error_by_category"] = [dict(r) for r in cats]
            recent = conn.execute(
                "SELECT COUNT(*) FROM error_logs WHERE created_at >= datetime('now','-1 day')"
            ).fetchone()[0]
            out["errors_last_24h"] = recent

        if "ai_routing_events" in tables or "ai_attempts" in tables:
            for t in ("ai_routing_events", "ai_attempts", "ai_provider_health", "ai_quota"):
                if t in tables:
                    try:
                        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                        out[f"count_{t}"] = n
                    except Exception as e:
                        out[f"count_{t}"] = str(e)

        # recent AI failures if table exists
        for t in tables:
            if "ai" in t.lower() and "log" in t.lower() or t in ("ai_routing_logs", "ai_call_logs", "ai_events"):
                try:
                    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({t})").fetchall()]
                    out[f"cols_{t}"] = cols
                    rows = conn.execute(f"SELECT * FROM {t} ORDER BY rowid DESC LIMIT 15").fetchall()
                    out[f"sample_{t}"] = [dict(zip(cols, r)) for r in rows]
                except Exception as e:
                    out[f"err_{t}"] = str(e)

        # activity / users
        for t in ("users", "payments", "activity_events", "user_activity"):
            if t in tables:
                out[f"count_{t}"] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]

        conn.close()
except Exception:
    out["audit_error"] = traceback.format_exc()

print(json.dumps(out, ensure_ascii=False, default=str))
'''


def run(c: paramiko.SSHClient, cmd: str, timeout: int = 120) -> tuple[str, str]:
    _, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    return stdout.read().decode(errors="replace"), stderr.read().decode(errors="replace")


def main() -> int:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("Connecting...")
    c.connect(HOST, username=USER, password=PASS, timeout=30)

    print("\n=== DOCKER PS ===")
    out, err = run(c, "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
    print(out or err)

    print("\n=== CONTAINER LOGS (last 200 lines, errors/warnings) ===")
    out, err = run(
        c,
        "docker logs --tail 400 dastyor-ai 2>&1 | grep -iE 'error|exception|traceback|fail|timeout|quota|429|500|webhook|ai_|obyektivka|cv_|handler' | tail -n 120",
    )
    print(out or "(no matching log lines)")
    if err.strip():
        print("stderr:", err[:300])

    print("\n=== RECENT RAW LOGS (last 80) ===")
    out, _ = run(c, "docker logs --tail 80 dastyor-ai 2>&1")
    print(out)

    print("\n=== SYSTEMCTL / PROCESS ===")
    out, _ = run(c, "docker inspect dastyor-ai --format '{{.State.Status}} {{.State.Health.Status}} RestartCount={{.RestartCount}} StartedAt={{.State.StartedAt}}' 2>&1")
    print(out)

    print("\n=== WRITE DB AUDIT INTO CONTAINER ===")
    sftp = c.open_sftp()
    try:
        sftp.mkdir("/opt/dastyor-ai/temp")
    except OSError:
        pass
    with sftp.file("/opt/dastyor-ai/temp/db_audit.py", "w") as f:
        f.write(REMOTE_AUDIT_PY)
    sftp.close()

    out, err = run(
        c,
        "docker cp /opt/dastyor-ai/temp/db_audit.py dastyor-ai:/app/temp_db_audit.py && "
        "docker exec dastyor-ai python /app/temp_db_audit.py",
        timeout=60,
    )
    print(out or err)
    try:
        data = json.loads(out.strip().split("\n")[-1])
        print("\n=== ERROR CATEGORIES ===")
        for row in data.get("error_by_category") or []:
            print(f"  {row.get('category')}: {row.get('c')}")
        print(f"errors_last_24h: {data.get('errors_last_24h')}")
        print(f"db: {data.get('db_path')}")
        print("\n=== LAST ERRORS ===")
        for row in (data.get("error_logs") or [])[:25]:
            print(f"[{row.get('created_at')}] {row.get('category')}: {row.get('message')}")
            if row.get("details"):
                print(f"    details: {str(row.get('details'))[:220]}")
    except Exception as e:
        print("parse failed:", e)

    print("\n=== AI ONE-KEY PROBE ===")
    out, err = run(
        c,
        "docker exec dastyor-ai python -c \""
        "import asyncio,json; "
        "from features.ai.routing.adapters import generate_with_endpoint; "
        "from features.ai.routing.config import load_routing_config; "
        "from features.ai.routing.types import Endpoint; "
        "cfg=load_routing_config(); "
        "rows=[]; "
        "\n"
        "\" 2>&1 | head -5",
        timeout=30,
    )
    # Simpler: copy probe_errors
    sftp = c.open_sftp()
    sftp.put("temp/probe_errors.py", "/opt/dastyor-ai/temp/probe_errors.py")
    sftp.close()
    out, err = run(
        c,
        "docker cp /opt/dastyor-ai/temp/probe_errors.py dastyor-ai:/app/temp_probe_errors.py && "
        "docker exec dastyor-ai python /app/temp_probe_errors.py",
        timeout=180,
    )
    print(out or err)

    print("\n=== ENV AI KEYS (names only) ===")
    out, _ = run(
        c,
        "docker exec dastyor-ai sh -c \"env | grep -E '^(AI_|GEMINI|GROQ|OPENAI|OPENROUTER|CLOUDFLARE|SAMBANOVA|GITHUB|GOOGLE_API)' | cut -d= -f1 | sort\"",
    )
    print(out)

    c.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print("FATAL:", e, file=sys.stderr)
        raise SystemExit(1)
