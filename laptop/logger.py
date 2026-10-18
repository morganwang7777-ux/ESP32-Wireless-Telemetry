import json
import socket
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

RESULTS = Path(__file__).resolve().parent.parent / "results"

# database
db = sqlite3.connect(RESULTS / "telemetry.db")   # creates the file the first time
db.execute("""CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT,
    note TEXT)""")
db.execute("""CREATE TABLE IF NOT EXISTS samples (
    run_id INTEGER,
    received_at REAL,
    seq INTEGER,
    t_ms INTEGER,
    throttle INTEGER,
    rssi INTEGER)""")

note = " ".join(sys.argv[1:])   # label for the run, e.g. python logger.py 10m
cur = db.execute("INSERT INTO runs (started_at, note) VALUES (?, ?)",
                 (datetime.now().isoformat(timespec="seconds"), note))
run_id = cur.lastrowid
db.commit()

# listen for packets from the ESP32 (port has to match the .ino)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", 5005))
sock.settimeout(1.0)   # so the status line still prints when nothing is arriving
print(f"Run {run_id} started ({note}). Listening... Ctrl+C to stop.")

received = 0
first_seq = None
last_seq = None
last_print = time.time()

try:
    while True:
        try:
            data, _ = sock.recvfrom(1024)
            msg = json.loads(data.decode())
            db.execute("INSERT INTO samples VALUES (?, ?, ?, ?, ?, ?)",
                       (run_id, time.time(), msg["seq"], msg["t_ms"],
                        msg["throttle"], msg["rssi"]))
            received += 1
            if first_seq is None:
                first_seq = msg["seq"]
            last_seq = msg["seq"]
            rssi = msg["rssi"]
        except socket.timeout:
            pass

        # commit + print status once a second
        if time.time() - last_print >= 1:
            db.commit()
            if first_seq is not None:
                expected = last_seq - first_seq + 1
                lost = expected - received
                loss_pct = 100 * lost / expected
                print(f"received {received} | lost {lost} ({loss_pct:.1f}%) | RSSI {rssi} dBm")
            last_print = time.time()
except KeyboardInterrupt:
    db.commit()
    print(f"\nRun {run_id} saved with {received} samples.")
    db.close()