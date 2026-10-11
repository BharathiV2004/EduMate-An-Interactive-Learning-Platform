from db import db
from datetime import datetime

class Story(db.Model):
    __tablename__ = 'story'
    
    story_id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey('extracted_content.content_id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    topic = db.Column(db.String(255),nullable=False)
    file_path = db.Column(db.String(255),nullable=False)
    # Relationship to ExtractedContent (assuming this table exists)
    extracted_content = db.relationship('ExtractedContent', backref='story')