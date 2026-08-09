import json
import time

import paramiko

HOST = "84.46.243.149"
USER = "root"
PASS = "muhammad9085"


def main() -> int:
    for attempt in range(1, 4):
        try:
            c = paramiko.SSHClient()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            c.connect(HOST, username=USER, password=PASS, timeout=30)
            sftp = c.open_sftp()
            sftp.put("temp/list_sambanova_models.py", "/opt/dastyor-ai/temp/list_sambanova_models.py")
            sftp.close()
            cmd = (
                "docker cp /opt/dastyor-ai/temp/list_sambanova_models.py dastyor-ai:/app/list_sn.py && "
                "docker exec dastyor-ai python /app/list_sn.py"
            )
            _, stdout, stderr = c.exec_command(cmd, timeout=60)
            print(stdout.read().decode())
            err = stderr.read().decode().strip()
            if err:
                print("stderr:", err[:300])
            c.close()
            return 0
        except Exception as exc:
            print(f"attempt {attempt}: {exc}")
            time.sleep(4)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
