"""Local donation API with SQLite search and a real-time SSE feed."""
import json
import queue
import sqlite3
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).parent
DB_PATH = ROOT / "donations.sqlite3"
CLIENTS = []
CLIENTS_LOCK = threading.Lock()


def database():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def setup_database():
    with database() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS people (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT, phone TEXT);
            CREATE TABLE IF NOT EXISTS donations (id INTEGER PRIMARY KEY, person_id INTEGER NOT NULL, cause TEXT NOT NULL, amount INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, FOREIGN KEY(person_id) REFERENCES people(id));
        """)
        if connection.execute("SELECT COUNT(*) FROM people").fetchone()[0] == 0:
            connection.executemany("INSERT INTO people(name, email, phone) VALUES (?, ?, ?)", [
                ("Ama Mensah", "ama@example.org", "0240000000"),
                ("Kwame Asare", "kwame@example.org", "0550000000"),
                ("Akosua Boateng", "akosua@example.org", "0200000000"),
            ])


def stats(connection):
    supporters = connection.execute("SELECT COUNT(DISTINCT person_id) FROM donations").fetchone()[0]
    communities = connection.execute("SELECT COUNT(DISTINCT cause) FROM donations").fetchone()[0]
    return {"supporters": supporters, "communities": communities}


def broadcast(donation):
    with CLIENTS_LOCK:
        for client in list(CLIENTS):
            client.put(donation)


class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload, status=200):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/people":
            query = parse_qs(parsed.query).get("q", [""])[0].strip()
            with database() as connection:
                rows = connection.execute("SELECT id, name, email, phone FROM people WHERE name LIKE ? OR email LIKE ? OR phone LIKE ? ORDER BY name LIMIT 20", tuple("%" + query + "%" for _ in range(3))).fetchall()
            return self.send_json([dict(row) for row in rows])
        if parsed.path == "/api/donations":
            with database() as connection:
                rows = connection.execute("SELECT donations.id, person_id, people.name, cause, 0 AS amount, created_at FROM donations JOIN people ON people.id = donations.person_id ORDER BY donations.id DESC LIMIT 100").fetchall()
                return self.send_json({"donations": [dict(row) for row in rows], "stats": stats(connection)})
        if parsed.path == "/api/stream":
            client = queue.Queue()
            with CLIENTS_LOCK:
                CLIENTS.append(client)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            try:
                while True:
                    donation = client.get()
                    self.wfile.write(("data: " + json.dumps(donation) + "\n\n").encode())
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                with CLIENTS_LOCK:
                    if client in CLIENTS:
                        CLIENTS.remove(client)
            return
        if parsed.path in ("/", "/donations.html"):
            return self.serve_file("donations.html", "text/html")
        return self.serve_file(parsed.path.lstrip("/"), None)

    def do_POST(self):
        if urlparse(self.path).path != "/api/donations":
            return self.send_json({"error": "Not found"}, 404)
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")
        person_id = int(payload.get("person_id", 0))
        cause = str(payload.get("cause", "General fund")).strip() or "General fund"
        created_at = datetime.now(timezone.utc).isoformat()
        with database() as connection:
            person = connection.execute("SELECT id, name FROM people WHERE id = ?", (person_id,)).fetchone()
            if not person:
                return self.send_json({"error": "Unknown person"}, 400)
            cursor = connection.execute("INSERT INTO donations(person_id, cause, amount, created_at) VALUES (?, ?, 0, ?)", (person_id, cause, created_at))
            donation = {"id": cursor.lastrowid, "person_id": person_id, "name": person["name"], "cause": cause, "amount": 0, "created_at": created_at}
        broadcast(donation)
        return self.send_json(donation, 201)

    def serve_file(self, relative_path, content_type):
        path = (ROOT / relative_path).resolve()
        if ROOT not in path.parents or not path.is_file():
            return self.send_json({"error": "Not found"}, 404)
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    setup_database()
    print("Donation monitor: http://127.0.0.1:8000/donations.html")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
