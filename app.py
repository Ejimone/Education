import os
import logging
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pathlib import Path
from logging.handlers import RotatingFileHandler
import json
import secrets

app = Flask(__name__)

# Add secret key for session management
app.secret_key = secrets.token_hex(16)

# Define the scopes required for Classroom and Drive APIs
SCOPES = [
    'https://www.googleapis.com/auth/classroom.coursework.me',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/classroom.courses.readonly' # Added missing scope
]

# Path configuration using pathlib
BASE_DIR = Path(__file__).parent
TOKEN_PATH = BASE_DIR / 'token.json'
CREDENTIALS_PATH = BASE_DIR / 'credentials.json'

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler('app.log', mode='a', maxBytes=10485760, backupCount=5)
    ]
)
logger = logging.getLogger(__name__)

def authenticate():
    """Get credentials for Google APIs with proper token management and logging."""
    creds = None
    logger.info(f"Checking if token file exists at: {TOKEN_PATH}")
    if TOKEN_PATH.exists():
        logger.info("Token file exists. Attempting to load credentials from token file.")
        try:
            with open(TOKEN_PATH, 'r', encoding='utf-8') as token:
                token_data = json.load(token)
                # Check if refresh_token exists in token_data
                if 'refresh_token' not in token_data:
                    logger.warning("Refresh token not found in token file. Deleting token file.")
                    try:
                        TOKEN_PATH.unlink()
                    except Exception as e:
                        logger.error(f"Error deleting token file: {e}")
                    creds = None  # Ensure creds is None to trigger re-authentication
                else:
                    creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            logger.warning(f"Error reading token file: {e}")
            try:
                TOKEN_PATH.unlink()
            except Exception as e:
                logger.error(f"Error deleting token file: {e}")
            creds = None # Ensure creds is None to trigger re-authentication
    else:
        logger.info("Token file does not exist.")

    if not creds or not creds.valid:
        logger.info("Credentials not found or invalid. Attempting to refresh or obtain new credentials.")
        if creds and creds.expired and creds.refresh_token:
            logger.info("Credentials expired and refresh token exists. Refreshing credentials.")
            creds.refresh(Request())
            logger.info("Credentials refreshed.")
        else:
            logger.info("No valid credentials or refresh token. Running installed app flow to obtain new credentials.")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH),
                SCOPES
            )
            # Explicitly request offline access to get a refresh token
            flow.oauth2session.redirect_uri = 'http://localhost:8080/'
            authorization_url, _ = flow.authorization_url(
                access_type='offline',
                prompt='consent'  # Force to show the consent screen
            )
            logger.info(f"Authorization URL: {authorization_url}")
            
            # Use a fixed port (e.g., 8080) to match Google Cloud Console redirect URI
            creds = flow.run_local_server(
                port=8080,
                authorization_prompt_message="Please authorize this application to access your Google account"
            )
            logger.info("New credentials obtained.")
            
            # Verify we got a refresh token
            if not creds.refresh_token:
                logger.warning("No refresh token obtained, this may cause issues later.")
        
        # Save the credentials
        if creds and creds.valid:
            with open(TOKEN_PATH, 'w', encoding='utf-8') as token:
                token.write(creds.to_json())
                logger.info("Credentials saved to token file.")
    else:
        logger.info("Valid credentials found.")

    return creds

def get_services(creds):
    """Return Classroom and Drive API services."""
    classroom_service = build('classroom', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    return classroom_service, drive_service

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/auth')
def auth():
    """Initiate OAuth flow."""
    if not CREDENTIALS_PATH.exists():
        return jsonify({'error': 'credentials.json not found'}), 500
    
    # Delete token file to force re-authentication
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
        logger.info("Deleted existing token.json to force re-authentication.")
    
    try:
        # Try using the InstalledAppFlow approach which is more reliable for local development
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_PATH),
            SCOPES
        )
        
        # Explicitly set the redirect URI
        flow.oauth2session.redirect_uri = 'http://localhost:8080/'
        
        # Run the local server directly
        creds = flow.run_local_server(port=8080)
        
        # Save the credentials
        with open(TOKEN_PATH, 'w', encoding='utf-8') as token:
            token.write(creds.to_json())
        logger.info("Credentials saved with refresh token.")
        
        return redirect(url_for('courses'))
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return jsonify({'error': f'Authentication failed: {str(e)}'}), 500


@app.route('/courses')
def courses():
    """List all enrolled courses."""
    creds = authenticate()
    classroom_service, _ = get_services(creds)
    results = classroom_service.courses().list(studentId='me').execute()
    courses = results.get('courses', [])
    return jsonify({'courses': [{'id': course['id'], 'name': course['name']} for course in courses]})

@app.route('/assignments/<course_id>')
def assignments(course_id):
    """List assignments for a course."""
    creds = authenticate()
    classroom_service, _ = get_services(creds)
    coursework = classroom_service.courses().courseWork().list(courseId=course_id).execute()
    assignments = coursework.get('courseWork', [])
    assignment_list = []
    for work in assignments:
        submissions = classroom_service.courses().courseWork().studentSubmissions().list(
            courseId=course_id, courseWorkId=work['id'], userId='me'
        ).execute()
        status = submissions['studentSubmissions'][0]['state'] if submissions.get('studentSubmissions') else 'NOT_SUBMITTED'
        due_date = work.get('dueDate', {})
        due = f"{due_date.get('year', 'N/A')}-{due_date.get('month', 'N/A')}-{due_date.get('day', 'N/A')}" if due_date else 'No due date'
        assignment_list.append({'id': work['id'], 'title': work['title'], 'due': due, 'status': status})
    return jsonify({'assignments': assignment_list})

@app.route('/submit', methods=['POST'])
def submit():
    """Submit an assignment."""
    creds = authenticate()
    classroom_service, drive_service = get_services(creds)
    course_id = request.form['course_id']
    coursework_id = request.form['assignment_id']
    file = request.files['file']
    file_path = os.path.join('uploads', file.filename)
    os.makedirs('uploads', exist_ok=True)
    file.save(file_path)

    try:
        # Upload file to Drive
        file_id = upload_file_to_drive(drive_service, file_path)
        # Submit assignment
        submit_assignment(classroom_service, course_id, coursework_id, file_id, file.filename)
        os.remove(file_path)  # Clean up
        return jsonify({'message': f'Assignment {coursework_id} submitted successfully.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def upload_file_to_drive(drive_service, file_path):
    """Upload a file to Google Drive."""
    file_metadata = {'name': os.path.basename(file_path)}
    media = MediaFileUpload(file_path, resumable=True)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

def submit_assignment(classroom_service, course_id, coursework_id, file_id, filename):
    """Submit an assignment to Classroom."""
    submissions = classroom_service.courses().courseWork().studentSubmissions().list(
        courseId=course_id, courseWorkId=coursework_id, userId='me'
    ).execute()
    
    if submissions.get('studentSubmissions'):
        submission = submissions['studentSubmissions'][0]
        if submission['state'] == 'TURNED_IN':
            raise Exception("Assignment already turned in.")
    else:
        submission = classroom_service.courses().courseWork().studentSubmissions().create(
            courseId=course_id, courseWorkId=coursework_id, body={'state': 'DRAFT'}
        ).execute()
    
    attachment = {'driveFile': {'id': file_id, 'title': filename}}
    classroom_service.courses().courseWork().studentSubmissions().patch(
        courseId=course_id, courseWorkId=coursework_id, id=submission['id'],
        updateMask='addAttachments', body={'addAttachments': [attachment]}
    ).execute()
    
    classroom_service.courses().courseWork().studentSubmissions().turnIn(
        courseId=coursework_id, id=submission['id']
    ).execute()

@app.route('/check_redirect_uri')
def check_redirect_uri():
    """Debug endpoint to check the redirect URI configuration."""
    if CREDENTIALS_PATH.exists():
        try:
            with open(CREDENTIALS_PATH, 'r') as f:
                creds_data = json.load(f)
                redirect_uris = creds_data.get('web', {}).get('redirect_uris', [])
                return jsonify({
                    'configured_redirect_uris': redirect_uris,
                    'app_redirect_uri': 'http://localhost:5000/oauth2callback'
                })
        except Exception as e:
            return jsonify({'error': f'Error reading credentials file: {str(e)}'})
    return jsonify({'error': 'credentials.json not found'})

if __name__ == '__main__':
    app.run(debug=True)
