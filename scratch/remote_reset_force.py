import paramiko
import sys
import os

def run_reset():
    host = "84.46.243.149"
    username = "root"
    pwd = "muhammad9085"
    
    local_script = r"c:\Users\User\hujjatchi_ai_bot\scripts\reset_payments_force.py"
    remote_path = "/opt/dastyor-ai/scripts/reset_payments_force.py"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=username, password=pwd, timeout=15)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return False

    print(f"Connected to {host}")
    
    # SFTP upload
    try:
        sftp = ssh.open_sftp()
        print(f"SFTP Upload: {local_script} -> {remote_path}")
        sftp.put(local_script, remote_path)
        sftp.close()
    except Exception as e:
        print(f"SFTP failed: {e}")
        ssh.close()
        return False
        
    commands = [
        "docker cp /opt/dastyor-ai/scripts/reset_payments_force.py dastyor-ai:/app/reset_payments_force.py",
        "docker exec -w /app -i dastyor-ai python reset_payments_force.py",
        "docker exec -i dastyor-ai rm /app/reset_payments_force.py",
        "rm /opt/dastyor-ai/scripts/reset_payments_force.py"
    ]
    
    encoding = sys.stdout.encoding or 'utf-8'
    for cmd in commands:
        print(f"Running command: {cmd}")
        try:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            out = stdout.read().decode('utf-8')
            err = stderr.read().decode('utf-8')
            if out:
                print("STDOUT:")
                print(out.encode(encoding, errors='replace').decode(encoding))
            if err:
                print("STDERR:")
                print(err.encode(encoding, errors='replace').decode(encoding))
        except Exception as e:
            print(f"Error executing: {e}")
            
    ssh.close()
    return True

if __name__ == '__main__':
    run_reset()
