import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.database import db
from models.entry_model import Entry

app = create_app()

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


def get_file_id(filename):
    return os.path.splitext(filename)[0]


def file_exists(file_id):
    with app.app_context():
        return db.session.query(Entry).filter_by(file_id=file_id).first() is not None


def populate_db(file_name="demo_data.json"):
    file_path = os.path.join(DATA_DIR, file_name)
    file_id = get_file_id(file_name)

    with app.app_context():
        if file_exists(file_id):
            print(f"❌ Error: file_id '{file_id}' already exists in the database.")
            return False

        if not os.path.exists(file_path):
            print(f"❌ Error: {file_name} not found!")
            return False

        with open(file_path, "r", encoding="utf-8") as f:
            test_data = json.load(f)

        for item in test_data:
            entry = Entry(raw_input=item["text"], status="pending", file_id=file_id)
            db.session.add(entry)

        db.session.commit()
        print(f"✅ Data from {file_name} inserted successfully with file_id '{file_id}'.")
        return True


if __name__ == "__main__":
    file_to_use = sys.argv[1] if len(sys.argv) > 1 else "demo_data2.json"
    populate_db(file_to_use)
