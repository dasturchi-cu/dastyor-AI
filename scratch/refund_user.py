import paramiko

def refund_user():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("84.46.243.149", username="root", password="muhammad9085")
    
    script = """
from database.connection import get_connection
with get_connection() as conn:
    conn.execute("UPDATE users SET credits = credits + 1 WHERE telegram_id = 7458702074")
    print("Credits refunded successfully!")
    user = conn.execute("SELECT credits FROM users WHERE telegram_id = 7458702074").fetchone()
    print("New balance:", dict(user))
"""
    
    stdin, stdout, stderr = ssh.exec_command("docker exec -i dastyor-ai-app-1 python")
    stdin.write(script)
    stdin.close()
    
    print("STDOUT:")
    print(stdout.read().decode("utf-8"))
    print("STDERR:")
    print(stderr.read().decode("utf-8"))
    ssh.close()

if __name__ == "__main__":
    refund_user()
