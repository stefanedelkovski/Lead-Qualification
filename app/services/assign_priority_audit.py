import os
import sys
import json
import requests
from app import create_app
from app.database import db
from models.lead_model import Lead
from models.entry_model import Entry


app = create_app()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")


def get_leads_for_deepseek(file_id):
    with app.app_context():
        return (
            db.session.query(Lead, Entry)
            .join(Entry, Entry.id == Lead.entry_id)
            .filter(Lead.file_id == file_id)
            .all()
        )


def call_deepseek_audit(leads):
    MAX_BATCH_SIZE = 40
    total_leads = len(leads)
    all_audit_results = []

    for i in range(0, total_leads, MAX_BATCH_SIZE):
        batch_leads = leads[i:i + MAX_BATCH_SIZE]

        input_data = [
            {
                "id": lead.entry_id,
                "raw_inquiry": entry.raw_input,
                "structured_data": {
                    "Company Name": lead.company_name,
                    "Industry": lead.industry,
                    "Business Model": lead.business_model,
                    "Budget": lead.budget,
                    "Revenue (Monthly)": lead.revenue,
                    "Growth Goal (Monthly)": lead.growth_goal,
                    "Urgency": lead.urgency,
                    "Lead Sentiment": lead.lead_sentiment,
                    "Additional Notes": lead.additional_notes,
                },
                "leads_ai_priority_level": lead.leads_AI_priority_level,
            }
            for lead, entry in batch_leads
        ]

        prompt = (
            "You are an independent AI auditor. Your task is to evaluate the accuracy of lead classifications made by "
            "another AI. Each lead consists of:\n"
            "- Raw Inquiry: The original text the user provided.\n"
            "- Structured Data: AI-extracted details such as company name, industry, budget, urgency, and sentiment.\n"
            "- Priority Level assigned by GPT: The AI's classification of the lead.\n\n"

            "Your job is to verify if the classification is correct. Assign a corrected priority level based on all "
            "available data.\n"
            "- 'Urgent': Needs immediate action.\n"
            "- 'High': Strong growth potential but not immediate.\n"
            "- 'Medium': Moderate relevance but not urgent.\n"
            "- 'Low': Weak intent or unclear need.\n\n"

            "Return the following for each lead:\n"
            "1. 'deepseek_priority_level': Your own classification of priority level from the input data.\n"
            "2. 'deepseek_notes': If the GPT AI made a mistake, explain briefly why - comparison between your own "
            "classification and the other AI's. If the priority level is matched, this value can be empty.\n"
            "3. 'deepseek_accuracy_score': A score from 1-100 number - percentage on how accurate GPT AI's "
            "classification was. 1 represents strong misclassification and 100 is an exact match in the priority level."
            "It can be any number in the range, depending on the misclassification level. If GPT said 'High' but you "
            "consider it 'Urgent', the accuracy score can be 70-90 for example, depending on the input data. If GPT "
            "said 'Low', but you consider it 'High', it can be 20-50% accurate for example, and so on.\n\n"

            "The order of the inputs and outputs is important, pay attention to it. Below is the required output, it "
            "should be a LIST of dictionaries, each entry line should have a corresponding output dictionary in the "
            "list. The output length is not important - it can be as long as needed to get the full output.  If the "
            "input data has 20 entries, the output should be a list of 20 dictionaries.\n\n"

            "Expected format:\n"
            "[\n"
            "{'id': 'value', 'deepseek_priority_level' : 'value', 'deepseek_notes' : 'value', 'deepseek_accuracy_score': 'value' },\n"
            "{'id': 'value', 'deepseek_priority_level' : 'value', 'deepseek_notes' : 'value', 'deepseek_accuracy_score': 'value' },\n"
            "{'id': 'value', 'deepseek_priority_level' : 'value', 'deepseek_notes' : 'value', 'deepseek_accuracy_score': 'value' },\n"
            "... \n"
            "]"
        )

        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(input_data)},
            ],
            "temperature": 0.2,
            "max_tokens": 8192,
        }

        response = requests.post("https://api.deepseek.com/v1/chat/completions", json=payload, headers=headers)

        if response.status_code != 200:
            print(f"❌ DeepSeek API Error: {response.status_code}, {response.text}")
            return None

        try:
            raw_response = response.json()
            deepseek_text_output = raw_response["choices"][0]["message"]["content"]
            batch_results = parse_deepseek_output(deepseek_text_output, batch_leads)

            if batch_results:
                all_audit_results.extend(batch_results)
            else:
                print("⚠️ Skipping this batch due to failed parsing.")

        except Exception as e:
            print(f"❌ Failed to parse DeepSeek response: {e}")
            return None

    return all_audit_results


def parse_deepseek_output(response_text, leads):

    try:
        structured_data = json.loads(response_text)
    except json.JSONDecodeError:
        print("❌ Failed to parse DeepSeek response.")
        return None

    results = []

    for entry in structured_data:
        try:
            lead_id = int(entry["id"])
            priority = entry["deepseek_priority_level"]
            notes = entry["deepseek_notes"] if entry["deepseek_notes"] else None
            accuracy = float(entry["deepseek_accuracy_score"])

            if isinstance(accuracy, str):
                accuracy = float(accuracy.replace("%", ""))

            results.append({
                "id": lead_id,
                "deepseek_priority_level": priority,
                "deepseek_notes": notes,
                "deepseek_accuracy_score": accuracy,
            })

        except (KeyError, ValueError):
            print(f"⚠️ Skipping malformed entry: {entry}")
            continue

    return results


def process_deepseek_audit(file_id):
    leads = get_leads_for_deepseek(file_id)

    if not leads:
        print(f"⚠️ No leads found for audit with file_id '{file_id}'.")
        return False

    audit_results = call_deepseek_audit(leads)

    if not audit_results or len(audit_results) != len(leads):
        print("❌ Error: Mismatch in response length or invalid response format.")
        return False

    total_score = sum(entry["deepseek_accuracy_score"] for entry in audit_results)
    overall_accuracy = total_score / len(leads) if leads else 0

    with app.app_context():
        for lead, entry in leads:
            for audit_entry in audit_results:
                if audit_entry["id"] == lead.entry_id:
                    lead.audit_AI_priority_level = audit_entry["deepseek_priority_level"]
                    lead.audit_AI_notes = audit_entry["deepseek_notes"]
                    lead.audit_accuracy_score = audit_entry["deepseek_accuracy_score"]
                    db.session.add(lead)

        db.session.commit()

    print(f"\n✅ DeepSeek audit completed for file_id '{file_id}' with {overall_accuracy:.2f}% model accuracy.")
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_id = sys.argv[1]
    else:
        file_id = "demo_data2"

    success = process_deepseek_audit(file_id)

    if success:
        print(f"✅ DeepSeek audit completed successfully for file_id: {file_id}")
    else:
        print(f"❌ DeepSeek audit failed for file_id: {file_id}")
