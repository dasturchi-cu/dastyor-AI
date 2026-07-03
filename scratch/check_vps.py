import paramiko

def check():
    host = "84.46.243.149"
    username = "root"
    pwd = "muhammad9085"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=username, password=pwd, timeout=15)
    
    stdin, stdout, stderr = ssh.exec_command("docker ps")
    print(stdout.read().decode('utf-8'))
    ssh.close()

if __name__ == '__main__':
    check()
