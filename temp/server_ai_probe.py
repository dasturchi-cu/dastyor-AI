import asyncio
import json
import time

import paramiko

HOST = "84.46.243.149"
USER = "root"
PASS = "muhammad9085"
CMD = (
    "docker exec dastyor-ai python -c "
    "'import asyncio, json; "
    "from features.ai.routing.probe import probe_all_keys; "
    "print(json.dumps(asyncio.run(probe_all_keys(timeout_sec=15.0))))'"
)


def main() -> int:
    for attempt in range(1, 3):
        try:
            c = paramiko.SSHClient()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            c.connect(HOST, username=USER, password=PASS, timeout=30)
            print("Probing all keys on server (1-2 min)...")
            _, stdout, stderr = c.exec_command(CMD, timeout=180)
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            c.close()
            if err:
                print("stderr:", err[:500])
            if not out:
                raise RuntimeError("empty output")
            data = json.loads(out)
            print(f"TOTAL: {data.get('total_keys')} | OK: {data.get('ok_keys')} | FAIL: {data.get('fail_keys')}")
            print("\nBy provider:")
            for name, row in sorted((data.get("summary") or {}).items()):
                print(
                    f"  {name}: {row.get('ok', 0)}/{row.get('key_count', 0)} ok"
                    + (f" (model: {row.get('models', [''])[0]})" if row.get("models") else "")
                )
            fails = [r for r in data.get("results") or [] if not r.get("ok")]
            if fails:
                print("\nFailed keys:")
                for r in fails[:15]:
                    print(f"  {r.get('provider')} #{r.get('key_index')}: {r.get('error') or 'probe_failed'}")
            return 0
        except Exception as exc:
            print(f"attempt {attempt} failed: {exc}")
            time.sleep(5)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
