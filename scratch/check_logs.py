import paramiko
import sys

def check_logs():
    host = "84.46.243.149"
    username = "root"
    pwd = "muhammad9085"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=username, password=pwd, timeout=15)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return False

    print(f"Connected to {host}")
    encoding = sys.stdout.encoding or 'utf-8'
    
    commands = [
        "docker ps -a",
        "docker logs --tail 100 dastyor-ai-app-1"
    ]
    
    for cmd in commands:
        print(f"\nRunning command: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        if out:
            print(out.encode(encoding, errors='replace').decode(encoding))
        if err:
            print("STDERR:", err.encode(encoding, errors='replace').decode(encoding))
        
    ssh.close()
    return True

if __name__ == '__main__':
    check_logs()
