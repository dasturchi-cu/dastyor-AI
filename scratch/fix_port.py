"""Port 8000 ni tozalab, containerni qayta ishga tushirish."""
import sys
import time
import paramiko

HOST = "84.46.243.149"
USER = "root"
PASS = "muhammad9085"

def run(client, cmd, timeout=60):
    print(f"  $ {cmd[:90]}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout, get_pty=True)
    out = ""
    for line in iter(stdout.readline, ""):
        print(f"    {line}", end="")
        out += line
    rc = stdout.channel.recv_exit_status()
    return rc, out

def main():
    print("=" * 55)
    print("  Port xatosini tuzatish va container restart")
    print("=" * 55)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=20)
    print("SSH ulandi!\n")

    # Port 8000 ni kim ishlatayotganini toping
    print("[1] Port 8000 ni ishlatayotgan jarayonlar:")
    run(client, "ss -tlnp | grep 8000 || echo 'hech narsa yoq'")

    # Barcha docker containerlarni ko'ring
    print("\n[2] Barcha containerlar:")
    run(client, "docker ps -a")

    # Barcha ishlab turgan containerlarni to'xtatish
    print("\n[3] Barcha containerlar to'xtatilmoqda...")
    run(client, "docker stop $(docker ps -q) 2>/dev/null || echo 'toxtatiladigan container yoq'")
    run(client, "docker rm $(docker ps -aq) 2>/dev/null || echo 'ochiriladigan container yoq'")

    # Bir oz kuting
    time.sleep(3)

    print("\n[4] Container qayta ishga tushirilmoqda...")
    rc, out = run(client, (
        "docker run -d "
        "--name dastyor-ai "
        "--restart unless-stopped "
        "-p 8000:8000 "
        "-v /opt/dastyor-ai/data:/data "
        "--env-file /opt/dastyor-ai/.env "
        "dastyor-ai"
    ))

    if rc != 0:
        print("\n[!] Hali ham xato. Port 8000 ni force kill qilamiz...")
        run(client, "fuser -k 8000/tcp 2>/dev/null || true")
        time.sleep(2)
        run(client, (
            "docker run -d "
            "--name dastyor-ai "
            "--restart unless-stopped "
            "-p 8000:8000 "
            "-v /opt/dastyor-ai/data:/data "
            "--env-file /opt/dastyor-ai/.env "
            "dastyor-ai"
        ))

    print("\n[5] 15 soniya kutilmoqda...")
    time.sleep(15)

    print("\n[6] Container holati:")
    run(client, "docker ps | grep dastyor-ai || echo 'CONTAINER ISHLAMAYAPTI!'")

    print("\n[7] Oxirgi loglar:")
    run(client, "docker logs dastyor-ai --tail=25 2>&1")

    print("\n[8] Health check:")
    run(client, "curl -s http://127.0.0.1:8000/health || echo 'health endpoint javob bermadi'")

    client.close()
    print("\n" + "=" * 55)
    print("  Tayyor!")
    print("=" * 55)

if __name__ == "__main__":
    main()
