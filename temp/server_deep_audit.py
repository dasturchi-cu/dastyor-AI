"""Production deep audit - ASCII only output for Windows console."""
from __future__ import annotations

import json
import sys
import io

# Force UTF-8 stdout on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import paramiko

HOST = "84.46.243.149"
USER = "root"
PASS = "muhammad9085"

REMOTE_PY = r'''
import json, sqlite3, os, traceback, time
from pathlib import Path

out = {"steps": []}
try:
    # locate db
    candidates = ["/data/app.db", "/app/data/app.db", "/app/app.db", "/data/bot.db"]
    db = None
    for c in candidates:
        if os.path.exists(c) and os.path.getsize(c) > 0:
            db = c
            break
    if not db:
        for p in Path("/data").rglob("*.db") if Path("/data").exists() else []:
            if p.stat().st_size > 1000:
                db = str(p); break
        if not db:
            for p in Path("/app").rglob("*.db"):
                if p.stat().st_size > 1000:
                    db = str(p); break
    out["db_path"] = db
    if db:
        out["db_size_mb"] = round(os.path.getsize(db)/1024/1024, 2)

        # time integrity check
        t0 = time.perf_counter()
        conn = sqlite3.connect(db, timeout=30)
        try:
            r = conn.execute("PRAGMA integrity_check").fetchone()
            out["integrity_check"] = r[0] if r else None
            out["integrity_ms"] = int((time.perf_counter()-t0)*1000)
        except Exception as e:
            out["integrity_error"] = str(e)
            out["integrity_ms"] = int((time.perf_counter()-t0)*1000)

        conn.row_factory = sqlite3.Row
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        out["tables"] = tables

        if "error_logs" in tables:
            cats = conn.execute(
                "SELECT category, COUNT(*) c FROM error_logs GROUP BY category ORDER BY c DESC LIMIT 25"
            ).fetchall()
            out["error_by_category"] = [dict(r) for r in cats]
            out["errors_last_24h"] = conn.execute(
                "SELECT COUNT(*) FROM error_logs WHERE created_at >= datetime('now','-1 day')"
            ).fetchone()[0]
            out["errors_last_7d"] = conn.execute(
                "SELECT COUNT(*) FROM error_logs WHERE created_at >= datetime('now','-7 day')"
            ).fetchone()[0]
            rows = conn.execute(
                "SELECT id, category, message, substr(coalesce(details,''),1,500) details, created_at "
                "FROM error_logs ORDER BY id DESC LIMIT 50"
            ).fetchall()
            out["error_logs"] = [dict(r) for r in rows]

        # AI related tables
        for t in tables:
            low = t.lower()
            if "ai" in low or "quota" in low or "cooldown" in low:
                try:
                    n = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
                    out[f"count_{t}"] = n
                    cols = [r[1] for r in conn.execute(f"PRAGMA table_info([{t}])").fetchall()]
                    sample = conn.execute(f"SELECT * FROM [{t}] ORDER BY rowid DESC LIMIT 8").fetchall()
                    out[f"sample_{t}"] = [dict(zip(cols, r)) for r in sample]
                except Exception as e:
                    out[f"err_{t}"] = str(e)

        for t in ("users", "payments", "sessions"):
            if t in tables:
                out[f"count_{t}"] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]

        # recent payments / activity
        if "payments" in tables:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(payments)").fetchall()]
            out["payment_cols"] = cols
            try:
                out["payments_by_status"] = [dict(r) for r in conn.execute(
                    "SELECT status, COUNT(*) c FROM payments GROUP BY status"
                ).fetchall()]
            except Exception as e:
                out["payments_status_err"] = str(e)

        conn.close()

    # quick health-like path timing inside process
    try:
        from database.verify import check_db_integrity, verify_schema
        t0 = time.perf_counter()
        ok, msg = check_db_integrity()
        t1 = time.perf_counter()
        schema = verify_schema() if ok else {}
        t2 = time.perf_counter()
        out["check_db_integrity_ms"] = int((t1-t0)*1000)
        out["verify_schema_ms"] = int((t2-t1)*1000)
        out["check_db_ok"] = ok
        out["check_db_msg"] = msg
        out["schema_ok"] = schema.get("ok") if isinstance(schema, dict) else None
    except Exception:
        out["verify_import_error"] = traceback.format_exc()

except Exception:
    out["fatal"] = traceback.format_exc()

print(json.dumps(out, ensure_ascii=True, default=str))
'''


def run(c, cmd, timeout=180):
    _, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    return stdout.read().decode("utf-8", errors="replace"), stderr.read().decode("utf-8", errors="replace")


def main():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PASS, timeout=30)
    print("connected")

    # workers / processes inside container
    out, err = run(c, "docker exec dastyor-ai sh -c 'ps aux | head -30; echo ---; ls -lah /data 2>/dev/null | head -20; ls -lah /data/*.db 2>/dev/null; ls -lah /app/*.db 2>/dev/null'")
    print("=== PROCESSES / DB FILES ===")
    print(out)

    # curl health vs ping timing
    out, _ = run(c, "docker exec dastyor-ai sh -c 'python -c \"import time,urllib.request;\\n"
                 "for path in [\\\"/ping\\\",\\\"/health\\\"]:\\n"
                 " t=time.perf_counter();\\n"
                 " try:\\n"
                 "  r=urllib.request.urlopen(\\\"http://127.0.0.1:8000\\\"+path, timeout=30);\\n"
                 "  body=r.read()[:200];\\n"
                 "  print(path, int((time.perf_counter()-t)*1000), \\\"ms\\\", r.status, body)\\n"
                 " except Exception as e:\\n"
                 "  print(path, int((time.perf_counter()-t)*1000), \\\"ms FAIL\\\", e)\\n\"'")
    print("=== PING vs HEALTH ===")
    print(out)

    # write and run db audit
    sftp = c.open_sftp()
    try:
        sftp.mkdir("/opt/dastyor-ai/temp")
    except OSError:
        pass
    with sftp.file("/opt/dastyor-ai/temp/db_audit2.py", "w") as f:
        f.write(REMOTE_PY)
    sftp.close()

    out, err = run(
        c,
        "docker cp /opt/dastyor-ai/temp/db_audit2.py dastyor-ai:/app/temp_db_audit2.py && "
        "docker exec dastyor-ai python /app/temp_db_audit2.py",
        timeout=180,
    )
    print("=== DB AUDIT ===")
    print(out)
    if err.strip():
        print("stderr:", err[:1000])

    try:
        data = json.loads(out.strip().splitlines()[-1])
        with open("temp/prod_audit_db.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=True)
        print("saved temp/prod_audit_db.json")
        print("db=", data.get("db_path"), "size_mb=", data.get("db_size_mb"))
        print("integrity_ms=", data.get("integrity_ms"), "check_db_ms=", data.get("check_db_integrity_ms"), "schema_ms=", data.get("verify_schema_ms"))
        print("errors_24h=", data.get("errors_last_24h"), "7d=", data.get("errors_last_7d"))
        print("categories:")
        for row in (data.get("error_by_category") or [])[:15]:
            print(" ", row)
        print("last 20 errors:")
        for row in (data.get("error_logs") or [])[:20]:
            print(" ", row.get("created_at"), row.get("category"), "|", (row.get("message") or "")[:120])
    except Exception as e:
        print("parse err", e)

    # AI probe one key each
    sftp = c.open_sftp()
    sftp.put("temp/probe_errors.py", "/opt/dastyor-ai/temp/probe_errors.py")
    sftp.close()
    out, err = run(
        c,
        "docker cp /opt/dastyor-ai/temp/probe_errors.py dastyor-ai:/app/temp_probe_errors.py && "
        "docker exec dastyor-ai python /app/temp_probe_errors.py",
        timeout=200,
    )
    print("=== AI PROBE ===")
    print(out or err)
    try:
        with open("temp/prod_ai_probe.json", "w", encoding="utf-8") as f:
            f.write(out.strip())
    except Exception:
        pass

    # more docker logs: webhook / telegram / exception
    out, _ = run(
        c,
        "docker logs --since 48h dastyor-ai 2>&1 | grep -iE 'Traceback|Exception|ERROR|Webhook|update failed|AiQuota|failover|all providers|Timeout|blocked' | tail -n 80",
    )
    print("=== ERROR LOG LINES 48h ===")
    print(out or "(none)")

    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
