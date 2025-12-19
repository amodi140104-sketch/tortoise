import sqlite3
from pathlib import Path


class Storage:
    def __init__(self, db_path="flipkart.db", commit_every=10):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        # Allow cross-thread access and apply PRAGMA settings for faster inserts
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        cur = self.conn.cursor()
        # WAL + NORMAL synchronous tends to be much faster for many small transactions
        try:
            cur.execute('PRAGMA journal_mode=WAL')
            cur.execute('PRAGMA synchronous = NORMAL')
        except Exception:
            pass

        self._commit_every = int(commit_every) if commit_every else 1
        self._pending = 0
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            title TEXT,
            category TEXT,
            product_url TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS price_snapshots (
            product_id TEXT,
            scraped_at TEXT,
            price INTEGER,
            rating REAL
        )
        """)

        self.conn.commit()

    def save_item(self, item):
        cur = self.conn.cursor()

        cur.execute("""
        INSERT OR IGNORE INTO products
        VALUES (?, ?, ?, ?)
        """, (
            item["product_id"],
            item["title"],
            item["category"],
            item["product_url"],
        ))

        cur.execute("""
        INSERT INTO price_snapshots
        VALUES (?, ?, ?, ?)
        """, (
            item["product_id"],
            item["scraped_at"],
            item["price"],
            item["rating"],
        ))

        # Batch commits to reduce disk I/O
        self._pending += 1
        if self._pending >= self._commit_every:
            self.conn.commit()
            self._pending = 0

    def commit_pending(self):
        if self._pending > 0:
            self.conn.commit()
            self._pending = 0

    def close(self):
        try:
            self.commit_pending()
        finally:
            try:
                self.conn.close()
            except Exception:
                pass
