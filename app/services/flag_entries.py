import sys
import os
import json
from pydantic import BaseModel
from typing import List, Dict
from openai import OpenAI

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.database import db
from models.entry_model import Entry
from models.edge_case_model import EdgeCase
from app.config import config

app = create_app()
client = OpenAI(api_key=config.OPENAI_API_KEY)


class EntryFlags(BaseModel):
    flags: List[str]
    reasons: List[str]


def get_entries_by_file(file_id):
    with app.app_context():
        return db.session.query(Entry).filter_by(file_id=file_id).all()


def call_openai_flagging(entries):
    BATCH_SIZE = 20
    total_entries = len(entries)
    all_flagged_entries = []

    for i in range(0, total_entries, BATCH_SIZE):
        batch_entries = entries[i:i + BATCH_SIZE]
        input_texts = [entry.raw_input for entry in batch_entries]

        prompt = (
            "You are an AI that categorizes business inquiries, a company that helps digital marketing agencies scale."
            "Your task is to classify each inquiry into one of the following categories:\n\n"
    
            "'success': The inquiry is a legitimate business request related to scaling, "
            "operations, team expansion, fulfillment, consulting, or process optimization. "
            "It should mention relevant details such as business type, revenue, growth goals, "
            "challenges, or a direct question about services.\n\n"
    
            "'fail': The inquiry is irrelevant, incoherent, or lacks meaningful context. "
            "This includes random text, gibberish, spam, or messages that provide no actionable "
            "business information (e.g., 'hello', 'I need help', 'can you do marketing?'). "
            "Fail inquiries do not give any specifics about their business, problems, or needs.\n\n"
    
            "'edge case': The inquiry contains elements that require human review. "
            "These include:\n"
            "  - Requests for a direct **video call or in-person meeting** before sharing details.\n"
            "  - Inquiries that are **vague but show potential business intent**, yet lack "
            "    enough information to determine if they are a serious lead.\n"
            "    If the inquiry seems too vague or lacks business context, it should be a fail."
            "  - Messages related to **something other than a standard business inquiry**, "
            "    such as partnerships, job applications, or media opportunities.\n\n"
    
            "For any entry marked as 'edge case', briefly provide a reason. "
            "Return a structured JSON list where each entry has:\n"
            "  - 'flag': The classification (success, fail, edge case).\n"
            "  - 'reason': If it's an edge case, give a VERY BRIEF reason (e.g., 'Requested call before details'). "
            "For success or fail, set reason as null.\n\n"
            "Ensure precise classification and preserve order in the response."
            "**IMPORTANT:** Return exactly **one classification per input**. "
            "Ensure the response contains **EXACTLY the same number of items** as the input."
        )

        # input_texts = [entry.raw_input for entry in batch_entries]

        try:
            response = client.chat.completions.create(
                model="gpt-4o-2024-08-06",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": json.dumps(input_texts)}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "entry_flags",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "entries": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "flag": {
                                                "type": "string",
                                                "enum": ["success", "fail", "edge case"]
                                            },
                                            "reason": {
                                                "type": ["string", "null"]
                                            }
                                        },
                                        "required": ["flag", "reason"],
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

            raw_response = response.choices[0].message.content

            try:
                structured_output = json.loads(raw_response)
                batch_results = structured_output["entries"]

                if len(batch_results) != len(batch_entries):
                    print(f"❌ Mismatch in batch {i // BATCH_SIZE + 1} response length!")
                    print(f"Expected: {len(batch_entries)}, Got: {len(batch_results)}")
                    raise ValueError("Mismatch between input and output size in batch.")

                all_flagged_entries.extend(batch_results)

            except json.JSONDecodeError as e:
                print(f"❌ Error parsing AI response: {e}")
                return None

        except Exception as e:
            print(f"❌ OpenAI API Error: {e}")
            return None

    return all_flagged_entries


def flag_entries(file_id):
    entries = get_entries_by_file(file_id)

    if not entries:
        print(f"⚠️ No entries found for file_id '{file_id}'.")
        return False

    print(f"Flagging {len(entries)} entries for file_id '{file_id}'..")

    flagged_entries = call_openai_flagging(entries)

    if not flagged_entries or len(flagged_entries) != len(entries):
        print("❌ Error: Mismatch in response length or invalid response format.")
        return False

    total_edgecase = 0
    total_success = 0
    total_fail = 0

    with app.app_context():
        for entry, flagged_entry in zip(entries, flagged_entries):
            flag = flagged_entry["flag"]
            reason = flagged_entry["reason"]

            entry.status = flag
            db.session.add(entry)

            if flag == "edge case":
                edge_case = EdgeCase(entry_id=entry.id, file_id=file_id, raw_input=entry.raw_input, reason=reason)
                total_edgecase += 1
                db.session.add(edge_case)
            elif flag == "success":
                total_success += 1
            elif flag == "fail":
                total_fail += 1

        db.session.commit()
        print(f"Flagging completed. Entries updated:")
        print(f"✅ Success flags: {total_success}")
        print(f"❌ Fail flags: {total_fail}")
        print(f"⚠️ Edge case flags: {total_edgecase}")

    return True


if __name__ == "__main__":
    file_id = sys.argv[1] if len(sys.argv) > 1 else None
    file_id = 'demo_data2'
    if not file_id:
        print("❌ Error: Please provide a file_id.")
    else:
        flag_entries(file_id)
