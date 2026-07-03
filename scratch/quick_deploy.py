"""Quick deploy: git pull + docker restart on Contabo."""
import time
import paramiko

HOST = "84.46.243.149"
USER = "root"
PASS = "muhammad9085"
APP_DIR = "/opt/dastyor-ai"

def run(client, cmd, timeout=300):
    print(f"  $ {cmd[:80]}")
    _, stdout, _ = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="ignore")
    err = stdout.channel.recv_exit_status()
    if out.strip():
        for line in out.strip().splitlines()[-15:]:
            print(f"    {line}")
    return err, out

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=20)
print("SSH ulandi!\n")

print("[1] Git pull...")
run(client, f"cd {APP_DIR} && git pull origin main 2>&1 | tail -5")

print("\n[2] Docker build...")
rc, _ = run(client, f"cd {APP_DIR} && docker build -t dastyor-ai . 2>&1 | tail -10", timeout=900)

print("\n[3] Container restart...")
run(client, "docker stop dastyor-ai 2>/dev/null || true")
run(client, "docker rm dastyor-ai 2>/dev/null || true")
run(client, (
    "docker run -d --name dastyor-ai --restart unless-stopped "
    "-p 8000:8000 -v /opt/dastyor-ai/data:/data "
    f"--env-file {APP_DIR}/.env dastyor-ai"
))

print("\n[4] 20s kutilmoqda...")
time.sleep(20)

print("\n[5] Holat:")
run(client, "docker ps | grep dastyor-ai")
print("\n[6] Loglar:")
run(client, "docker logs dastyor-ai --tail=20 2>&1")

client.close()
print("\nDeploy tugadi!")
