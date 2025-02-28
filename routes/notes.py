from flask import Blueprint, render_template, request, jsonify, session
from markupsafe import escape
from extensions import db
from models.user import User
from models.note import Note
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

notes_bp = Blueprint('notes', __name__, url_prefix='/apps/notes')

@notes_bp.route('/')
def notes():
    """Render notes page with all notes"""
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
        
    current_user = User.query.filter_by(username=session['user']).first()
    if not current_user:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    user_id = request.args.get('user_id', current_user.id)
    
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        user_id = current_user.id

    all_notes = Note.query.filter_by(user_id=user_id).order_by(Note.created_at.desc()).all()
    print(f"Loading notes page - Found {len(all_notes)} notes for user {user_id}")
    
    return render_template('notes.html', notes=all_notes, current_user_id=current_user.id)

@notes_bp.route('/create', methods=['POST'])
def create_note():
    """Create a new note - Fixed XSS vulnerability"""
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
        
    current_user = User.query.filter_by(username=session['user']).first()
    if not current_user:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    title = request.form.get('title')
    content = request.form.get('content')
    
    if not title or not content:
        return jsonify({'success': False, 'error': 'Title and content are required'}), 400
    
    # Escape user input to prevent XSS
    safe_title = escape(title)
    safe_content = escape(content)
    
    try:
        print(f"Creating note - Title: {safe_title}, Content: {safe_content}")
        
        note = Note(
            title=safe_title,
            content=safe_content,
            created_at=datetime.now(),
            user_id=current_user.id
        )
        
        db.session.add(note)
        db.session.commit()
        
        print(f"Note created with ID: {note.id}")
        
        return jsonify({
            'success': True,
            'message': 'Note created successfully',
            'note': {
                'id': note.id,
                'title': note.title,
                'content': note.content,
                'created_at': note.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': note.user_id
            }
        })
    except Exception as e:
        print(f"Error creating note: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
