from app.database import db
from models.entry_model import Entry


class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.String(255), nullable=False)
    entry_id = db.Column(db.Integer, db.ForeignKey(Entry.id, ondelete="CASCADE"), nullable=False)
    company_name = db.Column(db.String(255), nullable=True)
    industry = db.Column(db.String(255), nullable=True)
    business_model = db.Column(db.String(50), nullable=True)
    budget = db.Column(db.String(50), nullable=True)
    revenue = db.Column(db.String(50), nullable=True)
    growth_goal = db.Column(db.String(50), nullable=True)
    urgency = db.Column(db.String(50), nullable=True)
    lead_sentiment = db.Column(db.String(50), nullable=True)
    additional_notes = db.Column(db.Text, nullable=True)
    leads_AI_priority_level = db.Column(db.String(50), nullable=True)
    audit_AI_priority_level = db.Column(db.String(50), nullable=True)
    audit_AI_notes = db.Column(db.Text, nullable=True)
    audit_accuracy_score = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f"<Lead {self.id}, File ID: {self.file_id}>"
