import sys
import os

from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.database import db
from models.entry_model import Entry
from models.lead_model import Lead
from models.audit_model import Audit
from models.edge_case_model import EdgeCase

app = create_app()


def init_database():
    with app.app_context():
        print("Checking database URI:", app.config["SQLALCHEMY_DATABASE_URI"])
        db.session.execute(text("PRAGMA foreign_keys = ON;"))
        db.drop_all()
        db.create_all()
        db.session.commit()

        print("✅ Database initialized successfully.")


if __name__ == "__main__":
    init_database()
