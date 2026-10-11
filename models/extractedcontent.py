from db import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import ARRAY

class ExtractedContent(db.Model):
    __tablename__ = 'extracted_content'
    
    content_id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('inputfile.file_id'), nullable=False)
    raw_text = db.Column(db.Text)
    # topics_detected = db.Column(ARRAY(db.String(50)))  # PostgreSQL array of strings
    extraction_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    input_file = db.relationship('InputFile', backref=db.backref('extracted_contents', lazy=True))