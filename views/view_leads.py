import sys
import os
import pandas as pd
from tabulate import tabulate

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.database import db
from models.lead_model import Lead

app = create_app()


def view_leads(file_id=None):
    with app.app_context():
        query = db.session.query(Lead)

        if file_id:
            query = query.filter_by(file_id=file_id)

        leads = query.all()

        if not leads:
            print(f"⚠️ No leads found{' for file_id: ' + file_id if file_id else ''}.")
            return

        data = []
        for lead in leads:
            data.append([
                lead.id,
                lead.entry_id,
                lead.file_id,
                lead.company_name if lead.company_name else "N/A",
                lead.industry if lead.industry else "N/A",
                lead.business_model if lead.business_model else "N/A",
                lead.budget if lead.budget else "N/A",
                lead.revenue if lead.revenue else "N/A",
                lead.growth_goal if lead.growth_goal else "N/A",
                lead.urgency if lead.urgency else "N/A",
                lead.lead_sentiment if lead.lead_sentiment else "N/A",
                lead.additional_notes if lead.additional_notes else "N/A",
                lead.leads_AI_priority_level if lead.leads_AI_priority_level else "N/A",
                lead.audit_AI_priority_level if lead.audit_AI_priority_level else "N/A",
                lead.audit_AI_notes if lead.audit_AI_notes else "N/A",
                lead.audit_accuracy_score if lead.audit_accuracy_score is not None else "N/A"
            ])

        columns = [
            "ID", "Entry ID", "File ID", "Company", "Industry", "Model", "Budget", "Revenue", "Growth",
            "Urgency", "Sentiment", "Notes", "Priority Level (Leads AI)",
            "Priority Level (Audit AI)", "Notes (Audit AI)", "Accuracy Score % (Audit AI)"
        ]

        df = pd.DataFrame(data, columns=columns)
        print("\n" + tabulate(df, headers='keys', tablefmt='grid'))


if __name__ == "__main__":
    file_id = sys.argv[1] if len(sys.argv) > 1 else None
    file_id = 'demo_data2'
    view_leads(file_id)
