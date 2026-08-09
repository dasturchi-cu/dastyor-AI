import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("84.46.243.149", username="root", password="muhammad9085", timeout=30)
_, stdout, _ = c.exec_command(
    "grep -E '^(SAMBANOVA|GITHUB)_' /opt/dastyor-ai/.env | cut -d= -f1 | sort || true"
)
print(stdout.read().decode() or "(server .env da SAMBANOVA/GITHUB yo'q)")
c.close()
