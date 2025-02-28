from flask import Blueprint, render_template, request, jsonify, session, send_file
from extensions import db
from models.user import User
from models.file import File
import os
from werkzeug.utils import secure_filename
import datetime
import uuid
import magic
from PIL import Image

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'} 
UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

files_bp = Blueprint('files', __name__, url_prefix='/apps/files')

def validate_user():
    """Validate user session"""
    if 'user' not in session:
        print("User not logged in")
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
        
    current_user = User.query.filter_by(username=session['user']).first()
    if not current_user:
        print(f"User {session['user']} not found in database")
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    return current_user

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_secure_filepath(filename):
    safe_path = os.path.abspath(os.path.join(UPLOAD_FOLDER, filename))
    if not safe_path.startswith(os.path.abspath(UPLOAD_FOLDER)):
        return None
    return os.path.join(UPLOAD_FOLDER, filename)

def get_unique_filename(original_filename, user_id):
    """Generate a unique filename using a UUID to prevent overwriting"""
    extension = os.path.splitext(original_filename)[1] if '.' in original_filename else ''
    unique_filename = f"{datetime.datetime.now(datetime.UTC).strftime('%Y%m%d%H%M%S')}_{user_id}_{uuid.uuid4().hex[:8]}{extension}"
    return unique_filename

def validate_file_content(file_path, claimed_extension):
    """Verify file content matches its extension"""
    try:
        mime_type = magic.from_file(file_path, mime=True)
    
        mime_map = {
            'pdf': 'application/pdf',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif'
        }
        
        expected_mime = mime_map.get(claimed_extension.lower())
        if not expected_mime:
            return False
        
        return mime_type == expected_mime
    except Exception as e:
        print(f"Error validating file content: {str(e)}")
        return False

def sanitize_image(input_path, output_path, format):
    """Process image to strip any embedded code"""
    
    try:
        with Image.open(input_path) as img:
            if img.mode != 'RGB' and format.lower() != 'gif':
                img = img.convert('RGB')
            img.save(output_path, format=format)
        return True
    except Exception as e:
        print(f"Error sanitizing image: {str(e)}")
        return False

@files_bp.route('/')
def files():
    """Render files page with all files uploaded by the current user"""
    print("=== FILES LISTING ROUTE ACCESSED ===")
    current_user = validate_user()
    if isinstance(current_user, tuple):
        return current_user

    print(f"Loading files for user: {current_user.username} (ID: {current_user.id})")
    
    all_files = File.query.filter_by(user_id=current_user.id).order_by(File.uploaded_at.desc()).all()
    print(f"Found {len(all_files)} files")
    
    for file in all_files:
        print(f"  - ID: {file.id}, Filename: {file.filename}, Uploaded: {file.uploaded_at}")
    
    return render_template('files.html', files=all_files, current_user_id=current_user.id)

def validate_file(file):
    if not file:
        print("No file part in request")
        return jsonify({'success': False, 'error': 'No file part'}), 400
    
    if file.content_length > MAX_CONTENT_LENGTH:
        print("File too large")
        return jsonify({'success': False, 'error': 'File too large'}), 413
    
    if not allowed_file(file.filename):
        print("File type not allowed")
        return jsonify({'success': False, 'error': 'File type not allowed'}), 400
    
    return None

def use_content_validation(filename, file_path, extension):
    if not validate_file_content(file_path, extension):
        print(f"Error: File content does not match extension: {filename}")
        os.remove(file_path)
        return jsonify({'success': False, 'error': 'File content validation failed'}), 403
    
    return None

def use_image_sanitization(extension, filename, file_path):
    print(f"Sanitizing image file: {filename}")
    
    # Temporary sanitized file path
    sanitized_path = file_path.replace(f".{extension}", f"_sanitized.{extension}")
    # Determine image format
    image_format = 'JPEG' if extension.lower() in {'jpg', 'jpeg'} else extension.upper()
    
    # Sanitize the image
    if not sanitize_image(file_path, sanitized_path, image_format):
        print(f"Error sanitizing image: {filename}")
        os.remove(file_path)
        if os.path.exists(sanitized_path):
            os.remove(sanitized_path)
        return jsonify({'success': False, 'error': 'Image sanitization failed'}), 500
    
    # Replace the original file with the sanitized version
    os.remove(file_path)
    os.rename(sanitized_path, file_path)
    print(f"Image sanitized successfully: {filename}")
    
    return None

@files_bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload with intentional vulnerability"""
    print("\n=== FILE UPLOAD ATTEMPT ===")
    print(f"Request method: {request.method}")
    print(f"Form data: {request.form}")
    print(f"Files: {request.files}")
    
    current_user = validate_user()
    if isinstance(current_user, tuple):
        return current_user

    file = request.files.get('file')
    print(f"Received file: {file}")
    
    file_validation = validate_file(file)
    if file_validation is not None:
        return file_validation
    
    filename = secure_filename(file.filename)
    unique_filename = get_unique_filename(filename, current_user.id)
    
    file_path = get_secure_filepath(unique_filename)
    if not file_path:
        print(f"Error: Unsafe file path: {unique_filename}")
        return jsonify({'success': False, 'error': 'Unsafe file path'}), 403
    
    print(f"File path: {file_path}")
    
    try:
        file.save(file_path)
        print(f"File saved successfully at {file_path}")
        
        # Validate file content
        extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        content_validation = use_content_validation(filename, file_path, extension)
        if content_validation is not None:
            return content_validation
        
        # Sanitize image files
        image_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        if extension in image_extensions:
            image_sanitization = use_image_sanitization(extension, filename, file_path)
            if image_sanitization is not None:
                return image_sanitization

        new_file = File(
            filename=filename,
            file_path=file_path,
            user_id=current_user.id
        )
        db.session.add(new_file)
        db.session.commit()
        print(f"File record saved to database with ID: {new_file.id}")

        return jsonify({
            'success': True,
            'message': 'File uploaded successfully!',
            'file': new_file.to_dict()
        })
    except Exception as e:
        print(f"Error saving file: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@files_bp.route('/delete/<int:file_id>', methods=['DELETE'])
def delete_file(file_id):
    """Delete a file"""
    print(f"\n=== FILE DELETE ATTEMPT: ID {file_id} ===")
    
    current_user = validate_user()
    if isinstance(current_user, tuple):
        return current_user

    try:
        file = File.query.get_or_404(file_id)
        print(f"Found file {file_id}: {file.filename}")
        
        if file.user_id != current_user.id:
            print(f"Access denied: File {file_id} belongs to user {file.user_id}, not {current_user.id}")
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        file_path = file.file_path
        if not os.path.abspath(file_path).startswith(os.path.abspath(UPLOAD_FOLDER)):
            print(f"Error: Unsafe file path: {file.filename}")
            return jsonify({'success': False, 'error': 'Unsafe file path'}), 403
        
        db.session.delete(file)
        db.session.commit()
        print(f"File record deleted from database")
        
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"File deleted from filesystem: {file_path}")
        else:
            print(f"Warning: File not found on filesystem: {file_path}")
            
        return jsonify({'success': True, 'message': 'File deleted successfully'})
    except Exception as e:
        print(f"Error deleting file: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

from flask import send_from_directory

@files_bp.route('/download/<int:file_id>')
def download_file(file_id):
    """Download a file using send_from_directory for maximum compatibility"""
    print(f"\n=== FILE DOWNLOAD ATTEMPT: ID {file_id} ===")
    
    current_user = validate_user()
    if isinstance(current_user, tuple):
        return current_user

    try:
        file = File.query.get_or_404(file_id)
        
        if file.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        print(f"Found file {file_id}: {file.filename}")
        
        
        # Get the directory and filename
        file_path = file.file_path
        if not os.path.abspath(file_path).startswith(os.path.abspath(UPLOAD_FOLDER)):
            print(f"Error: Unsafe file path: {file.filename}")
            return jsonify({'success': False, 'error': 'Unsafe file path'}), 403
        
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        
        if os.path.exists(file_path):
            print(f"Sending file: {file_path}")
            
            return send_from_directory(
                directory,
                filename,
                download_name=file.filename,
                as_attachment=True
            )
        else:
            print(f"Error: File not found on filesystem: {file_path}")
            return jsonify({'success': False, 'error': 'File not found on server'}), 404
    except Exception as e:
        print(f"Error sending file: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500