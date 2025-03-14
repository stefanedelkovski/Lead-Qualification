from app.database import db


class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    raw_input = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # "success", "fail", "edge case"
    file_id = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<Entry {self.id}, Status: {self.status}, 'File: {self.file_id}>"
