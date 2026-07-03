import paramiko
import sys

def run_ssh():
    host = "84.46.243.149"
    username = "root"
    pwd = "muhammad9085"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=username, password=pwd, timeout=15)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # Check users table
    command = "docker exec -i dastyor-ai python -c \"import sqlite3; conn=sqlite3.connect('/data/app.db'); conn.row_factory=sqlite3.Row; [print(dict(r)) for r in conn.execute('SELECT * FROM users').fetchall()]\""
    print(f"Running command: {command}")
    stdin, stdout, stderr = ssh.exec_command(command)
    print("STDOUT:")
    print(stdout.read().decode('utf-8'))
    print("STDERR:")
    print(stderr.read().decode('utf-8'))
    ssh.close()

if __name__ == '__main__':
    run_ssh()
