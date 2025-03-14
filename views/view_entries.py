import sys
import os
import pandas as pd
from tabulate import tabulate

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.database import db
from models.entry_model import Entry

app = create_app()


def view_entries():
    with app.app_context():
        entries = db.session.query(Entry).all()

        if not entries:
            print("⚠️ No entries found in the database.")
            return

        data = []
        for entry in entries:
            data.append([
                entry.id, entry.file_id, entry.status,
                (entry.raw_input[:250] + "...") if entry.raw_input else "N/A"
            ])

        columns = ["ID", "File ID", "Status", "Input (truncated)"]
        df = pd.DataFrame(data, columns=columns)

        print("\n" + tabulate(df, headers='keys', tablefmt='grid'))


if __name__ == "__main__":
    view_entries()
