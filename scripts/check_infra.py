"""Verify infrastructure dependencies: PostgreSQL, Redis, ChromaDB, Celery."""
import subprocess, sys, os, socket

print("=" * 60)
print("INFRASTRUCTURE CHECK")
print("=" * 60)

# 1. PostgreSQL
print("\n[1] PostgreSQL")
try:
    import psycopg2
    # Try connecting to default PostgreSQL port
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            dbname="postgres",
            connect_timeout=3
        )
        cur = conn.cursor()
        cur.execute("SELECT 1 AS ok")
        print("  PostgreSQL: RUNNING (localhost:5432)")
        
        # Check if code_reviewer database exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname='code_reviewer'")
        exists = cur.fetchone()
        if exists:
            print("  code_reviewer DB: EXISTS")
        else:
            print("  code_reviewer DB: NOT FOUND — will be created at startup")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"  PostgreSQL: NOT REACHABLE — {e}")
except ImportError:
    print("  psycopg2 not installed — checking port only...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(("localhost", 5432))
    sock.close()
    if result == 0:
        print("  PostgreSQL: PORT OPEN (localhost:5432)")
    else:
        print("  PostgreSQL: NOT RUNNING (port 5432 closed)")

# 2. Redis
print("\n[2] Redis")
try:
    import redis
    r = redis.Redis(host="localhost", port=6379, socket_connect_timeout=2)
    r.ping()
    print("  Redis: RUNNING (localhost:6379)")
except ImportError:
    print("  redis-py not installed — checking port only...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(("localhost", 6379))
    sock.close()
    if result == 0:
        print("  Redis: PORT OPEN (localhost:6379)")
    else:
        print("  Redis: NOT RUNNING (port 6379 closed)")
except Exception as e:
    print(f"  Redis: NOT REACHABLE — {e}")

# 3. ChromaDB
print("\n[3] ChromaDB")
persist_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "chroma_db")
print(f"  ChromaDB persist dir: {persist_dir}")
if os.path.isdir(persist_dir):
    files = len([f for f in os.listdir(persist_dir) if not f.startswith(".")])
    print(f"  ChromaDB embedded: READY ({files} items in persist dir)")
else:
    print("  ChromaDB embedded: no persist dir (will be created on first use)")
try:
    import chromadb
    print(f"  chromadb package: INSTALLED (v{chromadb.__version__})")
except ImportError:
    print("  chromadb package: NOT INSTALLED")

# 4. Celery app
print("\n[4] Celery")
celery_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "backend", "app", "infrastructure", "queue", "celery_tasks.py"
)
print(f"  Celery module: {celery_path}")
if os.path.isfile(celery_path):
    print("  Celery module: EXISTS")
    print("  Celery app instance: celery_app (in celery_tasks.py)")
    print("  Worker command: celery -A app.infrastructure.queue.celery_tasks.celery_app worker --loglevel=info")
else:
    print("  Celery module: MISSING")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print("Application uses SQLite by default (see DATABASE_URL in config.py).")
print("PostgreSQL is only needed if DATABASE_URL is changed to postgresql://.")
print("Redis is needed for Celery. If Redis is unavailable, set APP_ENV=test")
print("to enable eager (synchronous) task execution.")
print("ChromaDB runs embedded by default (PersistentClient, no separate server).")
print("Celery module exists at app.infrastructure.queue.celery_tasks:celery_app.")
