import sqlite3
from pathlib import Path
import sys

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from config.settings import settings

db_path = settings.db_path.resolve()
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row

print("=== Tables and Counts ===")
tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
for table in tables:
    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"Table: {table} | Rows: {count}")

print("\n=== All CV Data ===")
for r in conn.execute("SELECT * FROM cv_data").fetchall():
    print(dict(r))

print("\n=== All Obyektivka Data (if exists) ===")
# Let's see if there is an obyektivka_data or similar table
if "obyektivka_data" in tables:
    for r in conn.execute("SELECT * FROM obyektivka_data").fetchall():
        print(dict(r))
elif "pending_obyektivka" in tables:
    for r in conn.execute("SELECT * FROM pending_obyektivka").fetchall():
        print(dict(r))

conn.close()
