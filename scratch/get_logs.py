import paramiko

def get_logs():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("84.46.243.149", username="root", password="muhammad9085")
    # Let's get the tail of standard error and output fully
    stdin, stdout, stderr = ssh.exec_command("docker logs dastyor-ai-app-1 --tail 500")
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    ssh.close()
    
    with open("scratch/logs.txt", "w", encoding="utf-8") as f:
        f.write("=== STDOUT ===\n")
        f.write(out)
        f.write("\n=== STDERR ===\n")
        f.write(err)
    print("Logs written to scratch/logs.txt successfully!")

if __name__ == "__main__":
    get_logs()
