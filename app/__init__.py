from flask import Flask
from sqlalchemy import text

from app.config import config
from app.database import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    db.init_app(app)

    with app.app_context():
        db.session.execute(text("PRAGMA foreign_keys = ON;"))
        db.session.commit()

        with db.engine.connect() as conn:
            result = conn.execute(text("PRAGMA foreign_keys;")).fetchone()
            # print(f"Foreign Keys Enabled: {result[0]}")

    return app
