import paramiko
import sys

def run_reset_credits():
    host = "84.46.243.149"
    username = "root"
    pwd = "muhammad9085"
    local_script = r"c:\Users\User\hujjatchi_ai_bot\scripts\reset_credits.py"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=username, password=pwd, timeout=15)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    print(f"Connected to {host}")
    encoding = sys.stdout.encoding or 'utf-8'
    
    # SFTP upload
    sftp = ssh.open_sftp()
    sftp.put(local_script, "/opt/dastyor-ai/scripts/reset_credits.py")
    sftp.close()
    print("Uploaded reset_credits.py")
    
    commands = [
        "docker cp /opt/dastyor-ai/scripts/reset_credits.py dastyor-ai:/app/reset_credits.py",
        "docker exec -w /app -i dastyor-ai python reset_credits.py",
        "docker exec -i dastyor-ai rm /app/reset_credits.py",
        "rm /opt/dastyor-ai/scripts/reset_credits.py"
    ]
    
    for cmd in commands:
        print(f"\nRunning: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        if out:
            print(out.encode(encoding, errors='replace').decode(encoding))
        if err:
            print("STDERR:", err.encode(encoding, errors='replace').decode(encoding))
    
    ssh.close()
    print("\nDone!")

if __name__ == '__main__':
    run_reset_credits()
