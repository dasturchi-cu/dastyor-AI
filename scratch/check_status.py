"""Container loglarini va health statusini tekshirish."""
import time
import paramiko

HOST = "84.46.243.149"
USER = "root"
PASS = "muhammad9085"

def run(client, cmd, timeout=30):
    print(f"  $ {cmd[:90]}")
    _, stdout, _ = client.exec_command(cmd, timeout=timeout, get_pty=True)
    out = ""
    for line in iter(stdout.readline, ""):
        print(f"    {line}", end="")
        out += line
    stdout.channel.recv_exit_status()
    return out

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=20)
print("SSH ulandi!\n")

print("[1] Container holati:")
run(client, "docker ps | grep dastyor-ai")

print("\n[2] Loglar (oxirgi 40 qator):")
run(client, "docker logs dastyor-ai --tail=40 2>&1")

print("\n[3] Health check:")
run(client, "curl -s http://127.0.0.1:8000/health")

print("\n[4] Webhook holati:")
run(client, "curl -s https://dastyorai.duckdns.org/health || echo 'HTTPS javob bermadi'")

client.close()
print("\nDone.")
