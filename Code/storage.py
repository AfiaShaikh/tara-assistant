"""Same record contract for SQLite and optional PostgreSQL/pgvector."""
import json, os, sqlite3, threading
from pathlib import Path
from engine import vector
class Store:
    def __init__(self,path):
        self.lock=threading.RLock();self.pg=bool(os.getenv('DATABASE_URL'))
        if self.pg:
            import psycopg
            self.db=psycopg.connect(os.environ['DATABASE_URL'],autocommit=True)
        else:
            Path(path).parent.mkdir(parents=True,exist_ok=True)
            self.db=sqlite3.connect(path,check_same_thread=False,isolation_level=None)
        self.execute('CREATE TABLE IF NOT EXISTS records (kind TEXT NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(kind,id))')
        self.execute('CREATE TABLE IF NOT EXISTS ai_assessments (id TEXT PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, payload TEXT NOT NULL)')
        if self.pg:
            self.execute('CREATE EXTENSION IF NOT EXISTS vector')
            self.execute('CREATE TABLE IF NOT EXISTS chunk_vectors (id TEXT PRIMARY KEY, embedding vector(384))')
    def execute(self,sql,args=()):return self.db.execute(sql.replace('?', '%s') if self.pg else sql,args)
    def get(self,kind,id):
        with self.lock:
            row=self.execute('SELECT payload FROM records WHERE kind=? AND id=?',(kind,id)).fetchone()
            return json.loads(row[0]) if row else None
    def all(self,kind):
        with self.lock:return [json.loads(r[0]) for r in self.execute('SELECT payload FROM records WHERE kind=? ORDER BY id',(kind,)).fetchall()]
    def put(self,kind,id,payload):
        with self.lock:
            self.execute('INSERT INTO records(kind,id,payload) VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET payload=excluded.payload',(kind,id,json.dumps(payload)))
            if kind=='chunk' and self.pg:
                self.execute('INSERT INTO chunk_vectors(id,embedding) VALUES(?,?::vector) ON CONFLICT(id) DO UPDATE SET embedding=excluded.embedding',(id,json.dumps(vector(payload['title']+' '+payload['text']))))
    def candidates(self,question,k=30):
        if not self.pg:return self.all('chunk')
        with self.lock:
            rows=self.execute('SELECT id FROM chunk_vectors ORDER BY embedding <=> ?::vector LIMIT ?',(json.dumps(vector(question)),k)).fetchall()
            return [self.get('chunk',r[0]) for r in rows]
    def save_assessment(self,record):
        with self.lock:
            self.execute('INSERT INTO ai_assessments(id,title,status,created_at,updated_at,payload) VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,status=excluded.status,updated_at=excluded.updated_at,payload=excluded.payload',(record['id'],record['title'],record['status'],record['created_at'],record['updated_at'],json.dumps(record)))
    def get_assessment(self,id):
        with self.lock:
            row=self.execute('SELECT payload FROM ai_assessments WHERE id=?',(id,)).fetchone()
            return json.loads(row[0]) if row else None
    def list_assessments(self):
        with self.lock:return [json.loads(r[0]) for r in self.execute('SELECT payload FROM ai_assessments ORDER BY created_at DESC').fetchall()]
    def close(self):self.db.close()
