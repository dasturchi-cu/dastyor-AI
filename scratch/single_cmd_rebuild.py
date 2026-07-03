import paramiko

def rebuild():
    host = "84.46.243.149"
    username = "root"
    pwd = "muhammad9085"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=username, password=pwd, timeout=60)
    
    combined_cmd = (
        "cd /opt/dastyor-ai && "
        "git -c http.sslVerify=false pull origin main && "
        "docker stop dastyor-ai-app-1 || true && "
        "docker rm dastyor-ai-app-1 || true && "
        "docker compose down && "
        "docker compose up -d --build"
    )
    
    print(f"Running combined command: {combined_cmd}")
    stdin, stdout, stderr = ssh.exec_command(combined_cmd)
    
    # Wait for execution to finish
    exit_status = stdout.channel.recv_exit_status()
    print("STDOUT:")
    print(stdout.read().decode('utf-8'))
    print("STDERR:")
    print(stderr.read().decode('utf-8'))
    print(f"Finished with exit status: {exit_status}")
    
    ssh.close()

if __name__ == '__main__':
    rebuild()
