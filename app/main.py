import csv
import sys
import os
import json
import logging
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, request, jsonify
from app import create_app
from app.database import db
from models.entry_model import Entry
from models.lead_model import Lead
from models.edge_case_model import EdgeCase

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_filename = f"../logs/run_{timestamp}.log"
logging.basicConfig(filename=log_filename, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = create_app()

ALLOWED_EXTENSIONS = {'json', 'txt'}
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
OUTPUT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output"))

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def convert_txt_to_json(txt_filepath):
    json_filename = txt_filepath.replace('.txt', '.json')
    json_filepath = os.path.join(UPLOAD_FOLDER, json_filename)

    with open(txt_filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    json_data = [{"text": line.strip()} for line in lines if line.strip()]

    with open(json_filepath, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=4)

    return json_filename


@app.route('/process-file', methods=['POST'])
def process_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Only .json and .txt allowed."}), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    if file.filename.endswith(".txt"):
        file.filename = convert_txt_to_json(file_path)
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    file_id = os.path.splitext(file.filename)[0]

    with app.app_context():
        if db.session.query(Entry).filter_by(file_id=file_id).first():
            return jsonify({"error": f"file_id '{file_id}' already exists. Delete first if you want to reuse."}), 400

    logging.info(f"Processing file: {file.filename} (file_id: {file_id})")

    # Step 1
    from scripts.populate_db import populate_db
    if not populate_db(file.filename):
        logging.error(f"Failed to populate DB for file_id: {file_id}")
        return jsonify({"error": f"Database population failed for file_id: {file_id}"}), 400
    print(f"✅ Data stored successfully for file_id: {file_id}.\n")

    # Step 2
    from services.flag_entries import flag_entries
    if not flag_entries(file_id):
        logging.error(f"Flagging process failed for file_id: {file_id}")
        return jsonify({"error": f"Flagging process failed for file_id: {file_id}"}), 400
    print(f"✅ Entries flagged successfully.\n")

    # Step 3
    from services.lead_qualifier import process_lead_qualification
    if not process_lead_qualification(file_id):
        logging.error(f"Lead qualification failed for file_id: {file_id}")
        return jsonify({"error": f"Lead qualification failed for file_id: {file_id}"}), 400
    print(f"✅ Leads categorized successfully.\n")

    # Step 4
    from services.assign_priority_lead import process_priority_assignment
    if not process_priority_assignment(file_id):
        logging.error(f"GPT priority assignment failed for file_id: {file_id}")
        return jsonify({"error": f"GPT priority assignment failed for file_id: {file_id}"}), 400
    print(f"✅ Priority levels assigned successfully (Leads AI).\n")

    # Step 5
    from services.assign_priority_audit import process_deepseek_audit
    if not process_deepseek_audit(file_id):
        logging.error(f"DeepSeek audit failed for file_id: {file_id}")
        return jsonify({"error": f"DeepSeek audit failed for file_id: {file_id}"}), 400
    print(f"✅ Priority levels assigned and evaluated Leads AI successfully (Audit AI).\n")

    save_leads_to_output(file_id)

    print(f"\nAll processes completed successfully for file_id: {file_id}\n")
    logging.info(f"All processes completed successfully for file_id: {file_id}")

    return jsonify({"message": f"File '{file.filename}' processed successfully.", "file_id": file_id}), 200


def save_leads_to_output(file_id):
    with app.app_context():
        leads = db.session.query(Lead).filter_by(file_id=file_id).order_by(
            Lead.audit_AI_priority_level.desc()).all()

        json_path = os.path.join(OUTPUT_FOLDER, f"{file_id}.json")
        csv_path = os.path.join(OUTPUT_FOLDER, f"{file_id}.csv")

        leads_data = [{
            "Company Name": lead.company_name,
            "Industry": lead.industry,
            "Business Model": lead.business_model,
            "Budget": lead.budget,
            "Revenue": lead.revenue,
            "Growth Goal": lead.growth_goal,
            "Urgency": lead.urgency,
            "Lead Sentiment": lead.lead_sentiment,
            "Additional Notes": lead.additional_notes,
            "DeepSeek Priority Level": lead.audit_AI_priority_level
        } for lead in leads]

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(leads_data, f, indent=4)

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=leads_data[0].keys())
            writer.writeheader()
            writer.writerows(leads_data)

        print(f"✅ Leads saved to: {json_path} and {csv_path}")


@app.route('/get_leads', methods=['GET'])
def get_leads():
    file_id = request.args.get('file_id')
    with app.app_context():
        leads = db.session.query(Lead).filter_by(file_id=file_id).order_by(
            Lead.audit_AI_priority_level.desc()).all()
    return jsonify([lead.__dict__ for lead in leads]), 200


@app.route('/get_entries', methods=['GET'])
def get_entries():
    file_id = request.args.get('file_id')
    with app.app_context():
        entries = db.session.query(Entry).filter_by(file_id=file_id).all()
    return jsonify([entry.__dict__ for entry in entries]), 200


@app.route('/get_edge_cases', methods=['GET'])
def get_edge_cases():
    file_id = request.args.get('file_id')
    with app.app_context():
        edge_cases = db.session.query(EdgeCase).filter_by(file_id=file_id).all()
    return jsonify([edge_case.__dict__ for edge_case in edge_cases]), 200


if __name__ == '__main__':
    app.run(debug=True)
