import sys
import os
import json
from openai import OpenAI
from sqlalchemy import text

from app import create_app
from app.database import db
from models.lead_model import Lead
from app.config import config
from sqlalchemy.orm.attributes import flag_modified

app = create_app()
client = OpenAI(api_key=config.OPENAI_API_KEY)


def get_leads_by_file(file_id):
    with app.app_context():
        return db.session.query(Lead).filter_by(file_id=file_id).all()


def assign_priorities(leads):
    if not leads:
        return []

    prompt = (
        "You are an AI responsible for determining lead priority levels. "
        "Each lead has structured data, including company name, industry, budget, revenue, "
        "growth goals, urgency, and lead sentiment. "
        "Assign a priority level based on overall lead potential:\n\n"
        "- 'Urgent': Critical business need, high budget, immediate action required.\n"
        "- 'High': Strong growth potential, clear budget, and serious interest.\n"
        "- 'Medium': Business shows interest but lacks strong urgency or budget.\n"
        "- 'Low': Weak interest, unclear goals, or very low budget.\n\n"
        "Ensure each lead gets exactly one of these four priority levels."
    )

    input_data = [
        {"entry_id": lead.entry_id, "industry": lead.industry, "model": lead.business_model, "budget": lead.budget,
         "revenue": lead.revenue, "growth_goal": lead.growth_goal,
         "urgency": lead.urgency, "lead_sentiment": lead.lead_sentiment}
        for lead in leads]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(input_data)}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "priority_assignment",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "priorities": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "entry_id": {"type": "integer"},
                                        "priority_level": {
                                            "type": "string",
                                            "enum": ["Urgent", "High", "Medium", "Low"]
                                        }
                                    },
                                    "required": ["entry_id", "priority_level"],
                                    "additionalProperties": False
                                }
                            }
                        },
                        "required": ["priorities"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            },
            temperature=0.0
        )

        structured_output = json.loads(response.choices[0].message.content)

        if "priorities" not in structured_output:
            raise ValueError("❌ OpenAI Response Missing 'priorities' Key!")

        return structured_output["priorities"]

    except Exception as e:
        print(f"❌ OpenAI API Error: {e}")
        return []


def process_priority_assignment(file_id):
    with app.app_context():
        leads = get_leads_by_file(file_id)

        if not leads:
            print(f"⚠️ No leads found for file_id '{file_id}'. Skipping priority assignment.")
            return False

        print(f"Assigning priorities for {len(leads)} success-flagged leads from file_id '{file_id}'...")

        priorities = assign_priorities(leads)

        if not priorities or len(priorities) != len(leads):
            print(
                f"❌ Error: Mismatch in response length for file_id '{file_id}'! Expected {len(leads)}, got {len(priorities)}")
            return False

        try:
            for lead, priority in zip(leads, priorities):
                priority_level = priority["priority_level"]

                lead.leads_AI_priority_level = priority_level
                db.session.add(lead)

            db.session.commit()
            print("✅ Priorities updated in the database! (Leads AI)")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Commit failed: {e}")

    return True


if __name__ == "__main__":
    file_id = sys.argv[1] if len(sys.argv) > 1 else None
    file_id = 'demo_data2'
    if not file_id:
        print("❌ Error: Please provide a file_id.")
    else:
        process_priority_assignment(file_id)
