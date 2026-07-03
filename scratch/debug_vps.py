import paramiko

def debug():
    host = "84.46.243.149"
    username = "root"
    pwd = "muhammad9085"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=username, password=pwd, timeout=15)
    
    stdin, stdout, stderr = ssh.exec_command("cd /opt/dastyor-ai && docker compose ps -a")
    print("DOCKER COMPOSE PS:")
    print(stdout.read().decode('utf-8'))
    
    stdin, stdout, stderr = ssh.exec_command("cd /opt/dastyor-ai && docker compose logs --tail=150")
    print("DOCKER COMPOSE LOGS:")
    print(stdout.read().decode('utf-8'))
    
    ssh.close()

if __name__ == '__main__':
    debug()
