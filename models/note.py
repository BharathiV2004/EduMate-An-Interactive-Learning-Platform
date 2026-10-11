from db import db
from datetime import datetime

class Note(db.Model):
    __tablename__ = 'note'
    
    note_id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey('extracted_content.content_id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)  # Changed from 'topic' to 'title'
    file_path = db.Column(db.String(255), nullable=False)
    # Relationship to ExtractedContent (maintaining same pattern)
    extracted_content = db.relationship('ExtractedContent', backref='notes')

    def __repr__(self):
        return f"<Note {self.note_id} - {self.title}>"