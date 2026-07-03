"""Contabo serverga SSH orqali deploy qiluvchi skript."""
import sys
import time
import paramiko

HOST = "84.46.243.149"
USER = "root"
PASS = "muhammad9085"
APP_DIR = "/opt/dastyor-ai"

def run(client, cmd, timeout=300):
    print(f"\n► {cmd[:80]}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout, get_pty=True)
    out = ""
    for line in iter(stdout.readline, ""):
        print(f"  {line}", end="")
        out += line
    err = stderr.read().decode(errors="ignore")
    if err.strip():
        print(f"  [stderr] {err.strip()[:200]}")
    rc = stdout.channel.recv_exit_status()
    return rc, out

def main():
    print("=" * 60)
    print("  DASTYOR AI — Contabo Deploy")
    print(f"  Server: {HOST}")
    print("=" * 60)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print(f"\n🔗 SSH ulanmoqda {HOST}...")
    try:
        client.connect(HOST, username=USER, password=PASS, timeout=20)
        print("✅ SSH ulandi!\n")
    except Exception as e:
        print(f"❌ SSH ulanmadi: {e}")
        sys.exit(1)

    # 1. App papkasi borligini tekshirish
    rc, out = run(client, f"test -d {APP_DIR}/.git && echo EXISTS || echo MISSING")
    first_deploy = "MISSING" in out

    if first_deploy:
        print("\n⚠️  Birinchi deploy — to'liq setup boshlanyapti...")
        # .env faylini yuklash kerak — avval papka yaratamiz
        run(client, f"mkdir -p {APP_DIR}")
        print("\n📤 .env faylini serverga ko'chirmoqda...")
        sftp = client.open_sftp()
        try:
            sftp.put("c:/Users/User/hujjatchi_ai_bot/.env", f"{APP_DIR}/.env")
            print("✅ .env ko'chirildi")
        except Exception as e:
            print(f"❌ .env ko'chirishda xato: {e}")
            sys.exit(1)
        finally:
            sftp.close()

        # Keyin assets/samples ni ham ko'chirish kerak
        print("\n📤 Assets/samples papkasini ko'chirmoqda...")
        import os
        samples_dir = "c:/Users/User/hujjatchi_ai_bot/assets/samples"
        sftp = client.open_sftp()
        try:
            run(client, f"mkdir -p {APP_DIR}/assets/samples")
            for fname in os.listdir(samples_dir):
                local = os.path.join(samples_dir, fname)
                remote = f"{APP_DIR}/assets/samples/{fname}"
                sftp.put(local, remote)
                print(f"  ✅ {fname}")
        except Exception as e:
            print(f"  ⚠️ Samples ko'chirishda xato: {e}")
        finally:
            sftp.close()

        # Setup skriptni clone qilmasdan yuklab ishlatish
        run(client, "apt-get update -y -q 2>/dev/null | tail -2")
        run(client, "apt-get install -y -q git curl wget nginx certbot python3-certbot-nginx 2>/dev/null | tail -2")
        run(client, "curl -fsSL https://get.docker.com | sh -s -- -y 2>&1 | tail -5")
        run(client, "systemctl enable docker && systemctl start docker")
        run(client, f"git clone https://github.com/dasturchi-cu/dastyor-AI.git {APP_DIR} 2>&1 || true")
        # Copy .env again after clone (clone may have overwritten)
        sftp = client.open_sftp()
        try:
            sftp.put("c:/Users/User/hujjatchi_ai_bot/.env", f"{APP_DIR}/.env")
        except:
            pass
        finally:
            sftp.close()
    else:
        print(f"\n📦 Mavjud deploy yangilanmoqda...")
        # Git pull
        rc, out = run(client, f"cd {APP_DIR} && git pull origin main 2>&1")
        if rc != 0:
            print("  ⚠️ git pull xato, SSL bypass bilan urinamiz...")
            run(client, f"cd {APP_DIR} && git -c http.sslVerify=false pull origin main 2>&1")

    # Data papkalar
    run(client, "mkdir -p /opt/dastyor-ai/data/uploads/receipts /opt/dastyor-ai/data/uploads/generated /opt/dastyor-ai/data/tmp")

    # Docker build
    print("\n🐳 Docker image build qilinmoqda (5-15 daqiqa)...")
    rc, out = run(client, f"cd {APP_DIR} && docker build -t dastyor-ai . 2>&1 | tail -20", timeout=900)
    if rc != 0:
        print("❌ Docker build xato!")
        sys.exit(1)
    print("✅ Docker build tayyor!")

    # Container restart
    run(client, "docker stop dastyor-ai 2>/dev/null || true")
    run(client, "docker rm dastyor-ai 2>/dev/null || true")
    rc, _ = run(client, (
        "docker run -d "
        "--name dastyor-ai "
        "--restart unless-stopped "
        "-p 8000:8000 "
        "-v /opt/dastyor-ai/data:/data "
        f"--env-file {APP_DIR}/.env "
        "dastyor-ai"
    ))
    if rc != 0:
        print("❌ Container ishga tushmadi!")
        sys.exit(1)

    print("\n⏳ Container tekshirilmoqda (15s)...")
    time.sleep(15)
    run(client, "docker ps | grep dastyor-ai || echo 'CONTAINER YOQ!'")
    run(client, "docker logs dastyor-ai --tail=20 2>&1")

    # Health check
    run(client, "curl -s http://127.0.0.1:8000/health || echo 'health endpoint javob bermadi'")

    client.close()
    print("\n" + "=" * 60)
    print("  ✅ DEPLOY TUGADI!")
    print(f"  🌐 https://dastyorai.duckdns.org")
    print("=" * 60)

if __name__ == "__main__":
    main()
