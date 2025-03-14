import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.database import db
from models.entry_model import Entry
from models.lead_model import Lead
from models.edge_case_model import EdgeCase

app = create_app()


def delete_entries(file_id):
    with app.app_context():
        db.session.query(Lead).filter_by(file_id=file_id).delete()
        db.session.query(EdgeCase).filter_by(file_id=file_id).delete()
        db.session.query(Entry).filter_by(file_id=file_id).delete()

        db.session.commit()
        print(f"✅ Deleted all records for file_id '{file_id}' from entries, leads, and edge_cases.")


if __name__ == "__main__":
    file_id = sys.argv[1] if len(sys.argv) > 1 else None
    file_id = 'demo_data2'
    if not file_id:
        print("❌ Error: Please provide a file_id.")
    else:
        delete_entries(file_id)
