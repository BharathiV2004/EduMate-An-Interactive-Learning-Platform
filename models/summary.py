from db import db
from datetime import datetime

class Summary(db.Model):
    __tablename__ = 'summary'
    
    summary_id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey('extracted_content.content_id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    level = db.Column(db.String(20), default='detailed')  # concise, detailed, or comprehensive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to ExtractedContent
    extracted_content = db.relationship('ExtractedContent', backref='summary')

    def __repr__(self):
        return f"<Summary {self.summary_id} - {self.title} ({self.level})>"