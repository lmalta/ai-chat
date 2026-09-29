import sqlite3
from contextlib import contextmanager

DB_PATH = "ai_chat.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                model TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(id)
                    ON DELETE CASCADE
            )
        """)

def create_conversation(title="Nouvelle conversation"):

    with get_db() as conn:

        cursor = conn.execute(
            """
            INSERT INTO conversations (title)
            VALUES (?)
            """,
            (title,)
        )

        return cursor.lastrowid

def update_conversation_title(conversation_id, title):

    with get_db() as conn:

        cursor = conn.execute(
            """
            UPDATE conversations
            SET title = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (title, conversation_id)
        )

        return cursor.rowcount > 0
        
def conversation_exists(conversation_id):

    with get_db() as conn:

        row = conn.execute(
            """
            SELECT 1
            FROM conversations
            WHERE id = ?
            """,
            (conversation_id,)
        ).fetchone()

        return row is not None

def get_conversation(conversation_id):

    with get_db() as conn:

        row = conn.execute(
            """
            SELECT
                id,
                title,
                created_at,
                updated_at
            FROM conversations
            WHERE id = ?
            """,
            (conversation_id,)
        ).fetchone()

        if row is None:
            return None

        return dict(row)
        
def add_message(conversation_id, role, content, model=None):
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO messages (
                conversation_id,
                role,
                content,
                model
            )
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, role, content, model)
        )

        conn.execute(
            """
            UPDATE conversations
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (conversation_id,)
        )

        return cursor.lastrowid


def get_conversations():
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                title,
                created_at,
                updated_at
            FROM conversations
            ORDER BY updated_at DESC
            """
        ).fetchall()

        return [dict(row) for row in rows]


def get_messages(conversation_id):
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                conversation_id,
                role,
                content,
                model,
                created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversation_id,)
        ).fetchall()

        return [dict(row) for row in rows]

def delete_conversation(conversation_id):
    with get_db() as conn:
        cursor = conn.execute(
            """
            DELETE FROM conversations
            WHERE id = ?
            """,
            (conversation_id,)
        )

        return cursor.rowcount > 0