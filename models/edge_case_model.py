from app.database import db


class EdgeCase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    entry_id = db.Column(db.Integer, db.ForeignKey('entry.id'), nullable=False)
    file_id = db.Column(db.String(100), nullable=False)
    raw_input = db.Column(db.Text, nullable=False)
    reason = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<EdgeCase {self.id}, File ID: {self.file_id}>"
