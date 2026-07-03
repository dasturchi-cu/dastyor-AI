import paramiko
import sys

def run_ssh(host, username, password, command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=username, password=password, timeout=15)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return False

    print(f"Connected to {host}")
    encoding = sys.stdout.encoding or 'utf-8'
    print(f"Running command: {command}")
    try:
        stdin, stdout, stderr = ssh.exec_command(command)
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        if out:
            print("STDOUT:")
            print(out.encode(encoding, errors='replace').decode(encoding))
        if err:
            print("STDERR:")
            print(err.encode(encoding, errors='replace').decode(encoding))
    except Exception as e:
        print(f"Error executing command: {e}")
    finally:
        ssh.close()
    return True

if __name__ == '__main__':
    host = "84.46.243.149"
    username = "root"
    pwd = "muhammad9085"
    
    # Run a Python one-liner in the container to check sqlite database
    command = "docker exec -i dastyor-ai python -c \"import sqlite3; conn=sqlite3.connect('/data/app.db'); print('PAYMENTS COUNT:', conn.execute('SELECT COUNT(*) FROM payments').fetchone()[0]); seq = conn.execute('SELECT seq FROM sqlite_sequence WHERE name=\'payments\'').fetchone(); print('SEQUENCE:', seq[0] if seq else 'None')\""
    
    run_ssh(host, username, pwd, command)
