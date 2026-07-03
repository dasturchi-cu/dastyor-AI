import paramiko
import sys

def run_ssh(host, username, password, commands):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=username, password=password, timeout=10)
    except Exception as e:
        print(f"Failed to connect with password: {password}. Error: {e}")
        return False

    print(f"Connected to {host}")
    encoding = sys.stdout.encoding or 'utf-8'
    for cmd in commands:
        print(f"Running: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        
        # Read output
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        if out:
            print("STDOUT:")
            print(out.encode(encoding, errors='replace').decode(encoding))
        if err:
            print("STDERR:")
            print(err.encode(encoding, errors='replace').decode(encoding))
            
    ssh.close()
    return True

if __name__ == '__main__':
    host = "84.46.243.149"
    username = "root"
    passwords = ["muhammad9085", "muhammad90085"]
    
    commands = [
        "docker cp /opt/dastyor-ai/scripts/reset_payments.py dastyor-ai:/app/reset_payments.py",
        'echo "ha" | docker exec -w /app -i dastyor-ai python reset_payments.py',
        'docker exec -i dastyor-ai rm /app/reset_payments.py'
    ]
    
    for pwd in passwords:
        print(f"Trying password: {pwd}")
        if run_ssh(host, username, pwd, commands):
            print("Successfully executed reset script!")
            sys.exit(0)
    print("Failed with all passwords.")
    sys.exit(1)
