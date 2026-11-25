"""PostgreSQL connection for the hosted FastAPI application."""

import os
import sqlite3

import psycopg
from psycopg.rows import dict_row


class AppCursor(psycopg.Cursor):
    def execute(self, query, params=None, **kwargs):
        # Shared application queries use SQLite-style positional placeholders.
        try:
            return super().execute(query.replace("?", "%s"), params, **kwargs)
        except psycopg.IntegrityError as exc:
            raise sqlite3.IntegrityError(str(exc)) from exc


def connect():
    conn = psycopg.connect(
        os.environ["DATABASE_URL"],
        sslmode="require",
        connect_timeout=5,
        prepare_threshold=None,
        cursor_factory=AppCursor,
        row_factory=dict_row,
    )
    try:
        conn.execute("SET LOCAL search_path TO gestao_produtos, pg_catalog")
        return conn
    except Exception:
        conn.close()
        raise
