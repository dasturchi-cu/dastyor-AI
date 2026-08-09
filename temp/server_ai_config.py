import json
import time

import paramiko

HOST = "84.46.243.149"
USER = "root"
PASS = "muhammad9085"
CMD = (
    "docker exec dastyor-ai python -c "
    "'from features.ai.routing.probe import build_config_summary; "
    "import json; print(json.dumps(build_config_summary()))'"
)


def main() -> int:
    last_err = None
    for attempt in range(1, 4):
        try:
            c = paramiko.SSHClient()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            c.connect(HOST, username=USER, password=PASS, timeout=30)
            _, stdout, stderr = c.exec_command(CMD, timeout=90)
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            c.close()
            if err:
                print("stderr:", err)
            if out:
                data = json.loads(out)
                print(json.dumps(data, indent=2))
                print(f"\nTOTAL_KEYS={data.get('total_keys')}")
                return 0
            last_err = "empty output"
        except Exception as exc:
            last_err = str(exc)
            print(f"attempt {attempt} failed: {exc}")
            time.sleep(4)
    print("FAILED:", last_err)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
