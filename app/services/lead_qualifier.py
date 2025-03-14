import sys
import os
import json
from openai import OpenAI
from app import create_app
from app.database import db
from models.entry_model import Entry
from models.lead_model import Lead
from app.config import config

app = create_app()
client = OpenAI(api_key=config.OPENAI_API_KEY)


def get_success_entries(file_id=None):
    with app.app_context():
        query = db.session.query(Entry).filter_by(status="success")
        if file_id:
            query = query.filter_by(file_id=file_id)
        return query.all()


def qualify_leads(entries):
    input_data = [{"id": entry.id, "text": entry.raw_input} for entry in entries]

    prompt = (
        "You are an AI responsible for structuring business inquiries."
        "Extract the following details while maintaining structure:"
        "Company Name: If mentioned, otherwise null."
        "Industry: The industry type (e.g., SaaS, Retail, Marketing, etc.)."
        "Business Model: One of ['B2B', 'B2C', 'DTC', 'Unknown']." 
        "Budget: The amount the user is willing to spend (e.g., marketing, services, investment)."
        "Revenue (Monthly): ONLY if the user explicitly states it. Do NOT confuse with budget. Convert to monthly."
        "Growth Goal (Monthly): If the user mentions growth objective. Do NOT confuse with budget. Convert to monthly."
        "Urgency: ['Urgent', 'High', 'Medium', 'Low'] based on how soon they need help."
        "Lead Sentiment: ['Hot', 'Neutral', 'Cold'] based on interest level."
        "Additional Notes: ONLY extract specific user requests, not the entire inquiry."
        "Ensure every extracted entry corresponds 1:1 with input."
        "Return JSON with 'entries': [{id: int, Company Name: str, Industry: str, Business Model: str, Budget: str, "
        "Revenue: str, Growth Goal: str, Urgency: str, Lead Sentiment: str, Additional Notes: str}]"
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps({"entries": input_data})},
    ]

    response = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=messages,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "lead_data",
                "schema": {
                    "type": "object",
                    "properties": {
                        "entries": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "integer"},
                                    "Company Name": {"type": ["string", "null"]},
                                    "Industry": {"type": ["string", "null"]},
                                    "Business Model": {"type": ["string", "null"], "enum": ["B2B", "B2C", "DTC", "Unknown"]},
                                    "Budget": {"type": ["string", "null"]},
                                    "Revenue (Monthly)": {"type": ["string", "null"]},
                                    "Growth Goal (Monthly)": {"type": ["string", "null"]},
                                    "Urgency": {"type": ["string", "null"], "enum": ["Urgent", "High", "Medium", "Low"]},
                                    "Lead Sentiment": {"type": ["string", "null"], "enum": ["Hot", "Neutral", "Cold"]},
                                    "Additional Notes": {"type": ["string", "null"]}
                                },
                                "required": [
                                    "id", "Company Name", "Industry", "Business Model", "Budget", "Revenue (Monthly)",
                                    "Growth Goal (Monthly)", "Urgency", "Lead Sentiment", "Additional Notes"
                                ],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["entries"],
                    "additionalProperties": False
                },
                "strict": True
            }
        },
        temperature=0.2
    )

    structured_data = json.loads(response.choices[0].message.content)

    if len(structured_data["entries"]) != len(entries):
        raise ValueError(f"Expected {len(entries)} responses, but got {len(structured_data['entries'])}")

    return structured_data


def store_leads(entries, structured_data):
    with app.app_context():
        structured_data_dict = {entry["id"]: entry for entry in structured_data["entries"]}

        for entry in entries:
            if entry.id not in structured_data_dict:
                raise ValueError(f"❌ ERROR: No structured data found for Entry ID {entry.id}")

            structured_entry = structured_data_dict[entry.id]

            lead = Lead(
                file_id=entry.file_id,
                entry_id=entry.id,
                company_name=structured_entry["Company Name"],
                industry=structured_entry["Industry"],
                business_model=structured_entry["Business Model"],
                budget=structured_entry["Budget"],
                revenue=structured_entry["Revenue (Monthly)"],
                growth_goal=structured_entry["Growth Goal (Monthly)"],
                urgency=structured_entry["Urgency"],
                lead_sentiment=structured_entry["Lead Sentiment"],
                additional_notes=structured_entry["Additional Notes"],
                leads_AI_priority_level=None,
                audit_AI_priority_level=None,
                audit_AI_notes=None,
                audit_accuracy_score=None,
            )

            db.session.add(lead)

        db.session.commit()
        print("✅ Structured leads stored successfully.")


def process_lead_qualification(file_id=None):
    entries = get_success_entries(file_id)
    if not entries:
        print(f"⚠️ No entries found with status 'success' for file_id: {file_id or 'ALL'}")
        return False

    try:
        structured_data = qualify_leads(entries)
        store_leads(entries, structured_data)
        print("✅ Lead qualification process completed.")
        return True
    except Exception as e:
        print(f"❌ Lead qualification failed: {e}")
        return False


if __name__ == "__main__":
    file_id = sys.argv[1] if len(sys.argv) > 1 else None
    file_id = 'demo_data2'
    process_lead_qualification(file_id)
