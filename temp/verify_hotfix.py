import json
import time
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("84.46.243.149", username="root", password="muhammad9085", timeout=30)

def run(cmd, t=120):
    _, o, e = c.exec_command(cmd, timeout=t)
    return o.read().decode("utf-8", errors="replace"), e.read().decode("utf-8", errors="replace")

out, _ = run(
    "docker exec dastyor-ai python -c \""
    "import time,urllib.request,json\n"
    "for path in ['/ping','/health']:\n"
    " times=[]\n"
    " body=b''\n"
    " for i in range(3):\n"
    "  t=time.perf_counter()\n"
    "  r=urllib.request.urlopen('http://127.0.0.1:8000'+path, timeout=10)\n"
    "  body=r.read()\n"
    "  times.append(int((time.perf_counter()-t)*1000))\n"
    " print(path, 'ms=', times, 'body=', body[:180])\n"
    "\""
)
print("TIMING:\n", out)

out, err = run(
    "docker exec dastyor-ai python /app/temp_probe_errors.py",
    t=180,
)
print("AI PROBE:\n", out or err)

out, _ = run(
    "docker exec dastyor-ai python -c \""
    "import sqlite3,os\n"
    "db='/data/app.db'\n"
    "conn=sqlite3.connect(db)\n"
    "print('size_mb', round(os.path.getsize(db)/1024/1024,2))\n"
    "print('history', conn.execute('select count(*) from ai_quota_history').fetchone()[0])\n"
    "print('freelist', conn.execute('PRAGMA freelist_count').fetchone()[0])\n"
    "print('page_count', conn.execute('PRAGMA page_count').fetchone()[0])\n"
    "\""
)
print("DB:\n", out)

out, _ = run("docker inspect dastyor-ai --format '{{.State.Health.Status}} Restart={{.RestartCount}}'")
print("HEALTH:", out)
c.close()
