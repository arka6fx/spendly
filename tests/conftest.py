import pytest
import database.db as db_module
from app import app as flask_app
from database.db import init_db, seed_db


@pytest.fixture
def app(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_file)
    flask_app.config.update(TESTING=True, SECRET_KEY="test")
    with flask_app.app_context():
        init_db()
        seed_db()
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()
