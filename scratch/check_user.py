import paramiko

def check_user():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("84.46.243.149", username="root", password="muhammad9085")
    
    script = """
from database.connection import get_connection
with get_connection() as conn:
    cv_docs = conn.execute("SELECT * FROM cv_documents WHERE user_id = 317").fetchall()
    print("CV_DOCS:", [dict(d) for d in cv_docs])
    oby_docs = conn.execute("SELECT * FROM obyektivka_documents WHERE user_id = 317").fetchall()
    print("OBY_DOCS:", [dict(d) for d in oby_docs])
    docs = conn.execute("SELECT * FROM documents WHERE user_id = 317").fetchall()
    print("DOCS:", [dict(d) for d in docs])
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
    check_user()
