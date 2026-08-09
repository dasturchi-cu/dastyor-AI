import os
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("84.46.243.149", username="root", password=os.environ["CONTABO_SSH_PASS"], timeout=30)
cmds = [
    "docker inspect dastyor-ai --format 'health={{.State.Health.Status}} status={{.State.Status}}'",
    "docker exec dastyor-ai python -c \"import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=8).read()[:280])\"",
    "cd /opt/dastyor-ai && git log -1 --oneline",
]
for cmd in cmds:
    print(">>>", cmd)
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace"))
    err = e.read().decode("utf-8", "replace")
    if err:
        print("ERR", err)
c.close()
