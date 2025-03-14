import sys
import os
import pandas as pd
from tabulate import tabulate

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.database import db
from models.edge_case_model import EdgeCase

app = create_app()


def view_edge_cases(file_id=None):
    with app.app_context():
        query = db.session.query(EdgeCase)

        if file_id:
            query = query.filter_by(file_id=file_id)

        edge_cases = query.all()

        if not edge_cases:
            print(f"⚠️ No edge cases found{' for file_id: ' + file_id if file_id else ''}.")
            return

        data = []
        for case in edge_cases:
            data.append([
                case.id, case.file_id, case.reason,
                (case.raw_input[:250] + "...") if case.raw_input else "N/A"
            ])

        columns = ["ID", "File ID", "Reason", "Text (truncated)"]
        df = pd.DataFrame(data, columns=columns)

        print("\n" + tabulate(df, headers='keys', tablefmt='grid'))


if __name__ == "__main__":
    file_id = sys.argv[1] if len(sys.argv) > 1 else None
    view_edge_cases(file_id)
