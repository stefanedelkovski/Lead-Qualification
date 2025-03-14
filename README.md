# Lead Qualification Project

## Overview

This **AI Lead Qualification system** transforms raw lead inquiries into structured data, assigns priority levels using **GPT**, and independently classifies and audits classifications with **DeepSeek**.
Unlike conventional lead scoring systems, this approach uses **multiple LLMs for validation**, where GPT structures and classifies leads, while DeepSeek audits its accuracy by analyzing both the **structured data** and the **original unstructured input**. This reduces misclassification risks and enhances prioritization accuracy.

## Pipeline Breakdown

The system processes leads in **five key steps**:

### 1. Populate Database
- Loads and stores raw lead inquiries from a **JSON** or **TXT** file.
- Supports multiple input formats:

  **JSON format**:
  ```json
  [
    {"text": "We're a fintech startup looking to optimize our sales funnel. Budget: $15K/month. Need automation solutions."},
    {"text": "E-commerce business seeking better ad targeting strategies. Budget: $10K/month. Looking for expert insights."},
    {"text": "B2B SaaS platform aiming to expand in the US market. Budget: $20K/month. Need help with outreach and partnerships."}
  ]
  ```
  
  **TXT format**:
  ```
  We're a fintech startup looking to optimize our sales funnel. Budget: $15K/month. Need automation solutions.
  E-commerce business seeking better ad targeting strategies. Budget: $10K/month. Looking for expert insights.
  B2B SaaS platform aiming to expand in the US market. Budget: $20K/month. Need help with outreach and partnerships.
  ```

### 2. Flagging Entries
- Detects and marks incomplete, irrelevant, or **edge-case** inquiries.
- Entries flagged as **failures** are excluded from processing.
- **Edge cases** are stored separately for manual review.

### 3. Structuring the Data
- Extracts essential fields from valid inquiries:
  - **Company Name**
  - **Industry**
  - **Business Model**
  - **Budget**
  - **Revenue**
  - **Growth Goal**
  - **Urgency**
  - **Lead Sentiment**
  - **Additional Notes**

### 4. GPT Classification
- Assigns a **priority level** based on structured data only:
  - **Urgent**: Requires immediate action.
  - **High**: Strong growth potential.
  - **Medium**: Moderate relevance.
  - **Low**: Weak intent or unclear need.

### 5. DeepSeek Classification & GPT Evaluation
- Re-evaluates **GPT's classification** using both:
  - **Raw inquiry** (unstructured or raw input data)
  - **Structured data**
- Compares its own priority level against GPT’s classification.
- Provides an **accuracy score (1-100%)** measuring GPT’s correctness.

## Project Structure
```
lead_qualification_project/
│── app/
│   ├── services/
│   │   ├── assign_priority_lead.py       # Assigns lead priority using GPT
│   │   ├── assign_priority_audit.py      # Audits lead priority using DeepSeek
│   │   ├── flag_entries.py               # Flags entries (success, fail, edge case)
│   │   ├── lead_qualifier.py             # Core lead qualification logic
│   │   ├── __init__.py
│   ├── config.py                         # Application configuration
│   ├── database.py                       # Database setup and connections
│   ├── logging_config.py                 # Logging setup
│   ├── main.py                           # API entry point
│
├── data/
│
├── logs/
│
├── models/
│   ├── __init__.py
│   ├── entry_model.py                    # Database model for raw lead entries
│   ├── lead_model.py                     # Database model for structured lead storage
│   ├── edge_case_model.py                # Database model for flagged edge cases
│
├── scripts/
│   ├── __init__.py
│   ├── delete_entry.py                   # Deletes all data for a single file_id
│   ├── init_db.py                        # Initializes database
│   ├── populate_db.py                    # Populates database from file
│
├── views/
│   ├── view_edge_cases.py                # View edge case table
│   ├── view_entries.py                   # View raw entries table
│   ├── view_leads.py                     # View structured leads table
│
├── .env                                  # Environment variables
├── leads.db                              # SQLite database
├── README.md                             
├── requirements.txt                      
```

## Installation

1. **Clone the repository**:

   ```sh
   git clone https://github.com/your-repo/lead_qualification_project.git
   cd lead_qualification_project
   ```

2. **Create a virtual environment**:

   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies**:

   ```sh
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:

   - Create a `.env` file and configure API keys and database settings.


5. **Initialize the database**:

   ```sh
   python scripts/init_db.py
   ```

6. **Run the application**:

   ```sh
   python app/main.py
   ```

## Usage

- **Process new leads**:
  ```sh
  python scripts/populate_db.py --file data/sample_leads.json   # or sample_leads.txt
  ```
- **Audit lead classification**:
  ```sh
  python app/services/assign_priority_audit.py sample_leads
  ```
- **View leads**:
  ```sh
  python views/view_leads.py
  ```

