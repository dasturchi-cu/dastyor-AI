import sys
import paramiko
import time

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def main():
    host = "84.46.243.149"
    password = "muhammad9085"

    script = """#!/bin/bash
echo "=== Wait 5 seconds for safety ==="
sleep 5
echo "=== Setting Webhook Manually ==="
docker exec dastyor-ai python -c "
import asyncio
from main import create_bot
from config.settings import settings
async def main():
    bot = create_bot()
    print('Setting webhook to:', settings.webhook_url)
    res = await bot.set_webhook(url=settings.webhook_url, secret_token=settings.webhook_secret or None, drop_pending_updates=True)
    print('Webhook result:', res)
    info = await bot.get_webhook_info()
    print('Webhook Info:', info)
asyncio.run(main())
" 2>&1
"""

    print("Connecting...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, 22, "root", password, timeout=30)
        print("Connected.")
        
        chan = ssh.get_transport().open_session()
        chan.exec_command("bash -s")
        chan.sendall(script.encode('utf-8'))
        chan.shutdown_write()
        
        while True:
            if chan.recv_ready():
                chunk = chan.recv(8192).decode('utf-8', errors='replace')
                print(chunk, end='')
            if chan.recv_stderr_ready():
                data = chan.recv_stderr(4096).decode('utf-8', errors='replace')
                if data.strip():
                    print("[ERR]", data, end='')
            if chan.exit_status_ready():
                while chan.recv_ready():
                    chunk = chan.recv(8192).decode('utf-8', errors='replace')
                    print(chunk, end='')
                break
            time.sleep(0.3)

    finally:
        ssh.close()

if __name__ == "__main__":
    main()
