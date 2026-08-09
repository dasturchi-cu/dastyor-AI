import json
import time

import paramiko

HOST = "84.46.243.149"
USER = "root"
PASS = "muhammad9085"
LOCAL = "temp/probe_errors.py"
REMOTE = "/opt/dastyor-ai/temp/probe_errors.py"
OUT = "/opt/dastyor-ai/temp/probe_out.json"


def main() -> int:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PASS, timeout=30)
    sftp = c.open_sftp()
    try:
        sftp.mkdir("/opt/dastyor-ai/temp")
    except OSError:
        pass
    sftp.put(LOCAL, REMOTE)
    sftp.close()

    cmd = (
        f"docker cp {REMOTE} dastyor-ai:/app/temp_probe_errors.py && "
        f"docker exec dastyor-ai python /app/temp_probe_errors.py > {OUT} 2>/dev/null; "
        f"cat {OUT}"
    )
    for attempt in range(1, 4):
        try:
            _, stdout, _ = c.exec_command(cmd, timeout=180)
            out = stdout.read().decode().strip()
            if not out:
                time.sleep(5)
                continue
            data = json.loads(out)
            for row in data:
                status = "OK" if row["ok"] else "FAIL"
                print(f"{row['provider']:12} {status:4} model={row['model']}")
                if row.get("text"):
                    print(f"             text={row['text']!r}")
                if row.get("error"):
                    print(f"             error={row['error']}")
            c.close()
            return 0
        except Exception as exc:
            print(f"attempt {attempt}: {exc}")
            time.sleep(5)
    c.close()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
