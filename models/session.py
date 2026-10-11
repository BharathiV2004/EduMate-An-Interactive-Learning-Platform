from db import db
from datetime import datetime

class Session(db.Model):
    __tablename__ = 'sessions'
    
    session_id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    user = db.relationship('User', backref='sessions')
    
    def __init__(self, session_id, user_id, expires_at):
        self.session_id = session_id
        self.user_id = user_id
        self.expires_at = expires_at