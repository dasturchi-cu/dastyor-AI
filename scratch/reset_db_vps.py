import paramiko

def reset_db():
    host = "84.46.243.149"
    username = "root"
    pwd = "muhammad9085"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=username, password=pwd, timeout=15)
    
    # We will connect and run sqlite reset commands on the app container
    cmd = (
        "docker exec dastyor-ai-app-1 python -c \""
        "import sqlite3; "
        "conn = sqlite3.connect('/data/app.db'); "
        "conn.execute('DELETE FROM payments'); "
        "conn.execute(\\\"UPDATE sqlite_sequence SET seq = 0 WHERE name = 'payments'\\\"); "
        "conn.commit(); "
        "conn.close(); "
        "print('Payments table reset successfully!')\""
    )
    
    print(f"Running command: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    
    print("STDOUT:")
    print(stdout.read().decode('utf-8'))
    print("STDERR:")
    print(stderr.read().decode('utf-8'))
    
    ssh.close()

if __name__ == '__main__':
    reset_db()
