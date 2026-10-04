import logging
from pathlib import Path
import sqlite3
import sys
import types
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'discord-bot'))
# Avoid loading production configuration or touching a real database during tests.
sys.modules['settings'] = types.SimpleNamespace(logging=logging)
import db_utils as db


@pytest.fixture
def database():
    db.conn = sqlite3.connect(':memory:')
    db.initialize_database()
    for guild in (1, 2):
        for uid in (10, 20, 30, 40, 50):
            db.create_player_data(uid, guild)
    yield db.conn
    db.close_db_connection()
