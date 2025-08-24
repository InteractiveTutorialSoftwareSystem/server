from flask import Flask, request, jsonify, g, Response, redirect
import flask_sqlalchemy
import flask_cors
from werkzeug.serving import WSGIRequestHandler
import base64
import os
import time
import subprocess
import json
import uuid
import logging
import signal
import sys
import re
from decouple import config
from logging.handlers import RotatingFileHandler
import platform
from tutorial.schema import Tutorial, TutorialSection, User, UserTutorialState, db
from sqlalchemy import or_, and_
from collections import Counter
from datetime import datetime
import hashlib
import string

import nltk
nltk.download('stopwords')
nltk.download('punkt')
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Import hybrid storage system
from tutorial.utils.storage_backend import get_storage_manager
from tutorial.utils.file_server import register_file_routes, create_file_upload_handler

# Input validation helpers
def validate_string_input(value, max_length=320, allow_empty=False):
    """Basic string validation to prevent injection attacks"""
    if not allow_empty and (not value or not value.strip()):
        return False, "Field cannot be empty"
    
    if value and len(value) > max_length:
        return False, f"Field exceeds maximum length of {max_length}"
    
    # Basic XSS prevention - block common script tags and SQL injection patterns
    dangerous_patterns = ['<script', 'javascript:', 'onclick=', 'onerror=', 'onload=', 
                         'SELECT ', 'INSERT ', 'UPDATE ', 'DELETE ', 'DROP ', 'UNION ']
    
    value_upper = value.upper() if value else ""
    for pattern in dangerous_patterns:
        if pattern.upper() in value_upper:
            return False, "Invalid characters detected"
    
    return True, None

def validate_integer_input(value, min_val=None, max_val=None):
    """Validate integer input and convert from string if needed"""
    try:
        if isinstance(value, str):
            value = int(value)
        elif not isinstance(value, int):
            return False, None, "Invalid integer format"
        
        if min_val is not None and value < min_val:
            return False, None, f"Value must be at least {min_val}"
        
        if max_val is not None and value > max_val:
            return False, None, f"Value cannot exceed {max_val}"
            
        return True, value, None
    except (ValueError, TypeError):
        return False, None, "Invalid integer format"

def validate_uuid_input(value):
    """Validate UUID format"""
    if not value:
        return False, "UUID cannot be empty"
    
    if not isinstance(value, str):
        return False, "UUID must be a string"
    
    # Basic UUID format validation (alphanumeric and dashes, correct length)
    uuid_pattern = r'^[a-fA-F0-9]{8}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{12}$|^[a-fA-F0-9]{32}$'
    if not re.match(uuid_pattern, value):
        return False, "Invalid UUID format"
    
    if len(value) not in [32, 36]:  # 32 for hex string, 36 for UUID with dashes
        return False, "Invalid UUID length"
    
    return True, None


# Initialize flask app
application = app = Flask(__name__)
app.debug = config("DEBUG", default=False, cast=bool)
# Set very large MAX_CONTENT_LENGTH to override Werkzeug's default limit
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB - effectively unlimited
# Configure Werkzeug Request limits for large form uploads
from werkzeug.wrappers import Request
Request.max_form_parts = 10000  # Increase form parts limit
Request.max_form_memory_size = 1024 * 1024 * 1024  # 1GB form memory
# Additional upload configurations
app.config['UPLOAD_FOLDER'] = '/tmp'
# Initializes CORS with specific origins
cors = flask_cors.CORS()
allowed_origins = config("ALLOWED_ORIGINS", default="http://localhost:3000").split(",")
cors.init_app(app, origins=allowed_origins, supports_credentials=True)

# Initialize a local database
# db = flask_sqlalchemy.SQLAlchemy()
app.config['SQLALCHEMY_DATABASE_URI'] = config("SQLALCHEMY_DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Setup Logger
logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s : %(message)s')
logger.setLevel(logging.DEBUG)
# handler = RotatingFileHandler('/opt/python/log/application.log')
handler = RotatingFileHandler('application.log')
handler.setFormatter(formatter)
application.logger.addHandler(handler)

# Initialize hybrid storage system
storage = get_storage_manager()

# Register file serving routes for local storage
register_file_routes(application)

# Create file upload handler with validation
upload_handler = create_file_upload_handler()

# Log storage backend information
backend_info = storage.get_backend_info()
logger.info(f"Storage backend initialized: {backend_info}")

# Legacy S3 configuration (for backward compatibility during transition)
# These will be automatically used by the storage backend if configured
# No need to create s3 client directly anymore

@app.before_request
def before_request_func():
  # list of flask.Request attributes can be found at https://tedboy.github.io/flask/generated/generated/flask.Request.html#attributes
  g.uuid = uuid.uuid4().hex
  user_ip = request.access_route[0] if request.access_route else request.remote_addr or '127.0.0.1'
  log_data = {'client address': user_ip, 'method': request.method, 'path': request.path , 'function': request.endpoint, 'browser': str(request.user_agent), 'uuid': g.uuid}
  app.logger.info(str(log_data))

@app.after_request
def after_request_func(response):
  # list of flask.Response attributes can be found at https://tedboy.github.io/flask/generated/generated/flask.Response.html#attributes
  log_data = {'status': response.status_code, 'uuid': g.uuid}
  app.logger.info(str(log_data))
  
  # Add security headers
  response.headers['X-Content-Type-Options'] = 'nosniff'
  response.headers['X-Frame-Options'] = 'DENY'
  response.headers['X-XSS-Protection'] = '1; mode=block'
  response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
  response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
  
  return response


'''
Testing
'''
@app.route("/")
def test():
  return jsonify({"message": "hello world"}), 200


'''
Tutorial
'''
@app.route("/tutorials/get_all/<int:UserId>")
def get_all_tutorials(UserId):
  """
    Gets all tutorials for the learner that are within the publish duration.
    Also gets the last assessed page by the learner for each tutorial.
  """
  try:
    # Validate UserId is a positive integer
    is_valid, user_id, error_msg = validate_integer_input(UserId, min_val=1)
    if not is_valid:
      return jsonify({"error": f"Invalid user ID: {error_msg}"}), 400
      
    date_time_now = datetime.utcnow()
    tutorials = db.session.query(Tutorial, User, UserTutorialState).join(User, Tutorial.userid == User.id) \
    .outerjoin(UserTutorialState, (Tutorial.id==UserTutorialState.tutorial_id) & (UserTutorialState.user_id==user_id)) \
    .filter(or_(and_(Tutorial.start_date < date_time_now, Tutorial.end_date > date_time_now), and_(Tutorial.start_date < date_time_now, Tutorial.end_date == None))).all()

    tutorialsJson = []
    for tutorial in tutorials:
      # Safely parse sequence length
      sequence_length = 0
      try:
        if tutorial[0].sequence:
          sequence_data = json.loads(tutorial[0].sequence)
          if isinstance(sequence_data, list):
            sequence_length = len(sequence_data)
      except (json.JSONDecodeError, TypeError):
        sequence_length = 0
        
      tutorialJson = {
        "id": tutorial[0].id,
        "name": tutorial[0].name,
        "language": tutorial[0].language,
        "startDatetime": tutorial[0].start_date,
        "endDatetime": tutorial[0].end_date,
        "sequence": sequence_length,
        "user_name": tutorial[1].name,
        "user_picture": tutorial[1].picture,
        "last_page": tutorial[2] and tutorial[2].last_page or 0,
      }
      tutorialsJson.append(tutorialJson)
    
    log_data = {'userId': user_id, 'role': 'learner', 'action': 'Learner Homepage', 'uuid': g.uuid}
    app.logger.info(str(log_data))
    return jsonify({"tutorials": tutorialsJson}), 200
    
  except Exception as e:
    app.logger.error(f"Error in get_all_tutorials: {str(e)}, uuid: {g.uuid}")
    return jsonify({"error": "Internal server error"}), 500

@app.route('/tutorial/get/<string:TutorialId>')
def get_tutorial_by_id(TutorialId):
  """
    Gets all tutorial details from Tutorial ID.
  """
  try:
    # Validate UUID format
    is_valid, error_msg = validate_uuid_input(TutorialId)
    if not is_valid:
      return jsonify({"error": f"Invalid tutorial ID: {error_msg}"}), 400
    
    tutorial = Tutorial.query.filter_by(id=TutorialId).first()
    if not tutorial:
      return jsonify({"error": "Tutorial not found"}), 404
      
    log_data = {'tutorialId': TutorialId, 'action': 'get_tutorial_by_id', 'uuid': g.uuid}
    app.logger.info(str(log_data))
    return jsonify(tutorial.json()), 200
    
  except Exception as e:
    app.logger.error(f"Error in get_tutorial_by_id: {str(e)}, uuid: {g.uuid}")
    return jsonify({"error": "Internal server error"}), 500

@app.route('/tutorials/get/<int:UserId>')
def get_tutorial_by_user_id(UserId):
  """
    Gets all author's tutorials.
  """
  try:
    # Validate UserId is a positive integer
    is_valid, user_id, error_msg = validate_integer_input(UserId, min_val=1)
    if not is_valid:
      return jsonify({"error": f"Invalid user ID: {error_msg}"}), 400
      
    tutorials = db.session.query(Tutorial, User).join(User, Tutorial.userid == User.id).filter_by(id=user_id).all()
    tutorialsJson = []
    for tutorial in tutorials:
      # Safely parse sequence length
      sequence_length = 0
      try:
        if tutorial[0].sequence:
          sequence_data = json.loads(tutorial[0].sequence)
          if isinstance(sequence_data, list):
            sequence_length = len(sequence_data)
      except (json.JSONDecodeError, TypeError):
        sequence_length = 0
        
      tutorialJson = {
        "id": tutorial[0].id,
        "name": tutorial[0].name,
        "language": tutorial[0].language,
        "sequence": sequence_length,
        "user_name": tutorial[1].name,
        "user_picture": tutorial[1].picture,
      }
      tutorialsJson.append(tutorialJson)
    
    log_data = {'userId': user_id, 'role': 'author', 'action': 'Author Homepage', 'uuid': g.uuid}
    app.logger.info(str(log_data))
    return jsonify({"tutorials": tutorialsJson}), 200
    
  except Exception as e:
    app.logger.error(f"Error in get_tutorial_by_user_id: {str(e)}, uuid: {g.uuid}")
    return jsonify({"error": "Internal server error"}), 500

@app.route('/tutorial/create', methods=['POST'])
def create_tutorial():
  """
    Create a new tutorial
  """
  try:
    data = request.get_json(force=True)
    if not data:
      return jsonify({"error": "No data provided"}), 400
      
    # Validate required fields
    required_fields = ['name', 'language', 'userid']
    for field in required_fields:
      if field not in data or not data[field]:
        return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Validate inputs
    is_valid, error_msg = validate_string_input(data['name'], max_length=320)
    if not is_valid:
      return jsonify({"error": f"Invalid name: {error_msg}"}), 400
      
    is_valid, error_msg = validate_string_input(data['language'], max_length=100)
    if not is_valid:
      return jsonify({"error": f"Invalid language: {error_msg}"}), 400
    
    is_valid, user_id, error_msg = validate_integer_input(data['userid'], min_val=1)
    if not is_valid:
      return jsonify({"error": f"Invalid user ID: {error_msg}"}), 400
    
    name = data['name'].strip()
    language = data['language'].strip()
    unique_index = uuid.uuid4().hex
    
    statement = Tutorial(id=unique_index, name=name, language=language, sequence="[]", userid=user_id, start_date=None, end_date=None)

    db.session.add(statement)
    db.session.commit()
    
    log_data = {'userId': user_id, 'role': 'author', 'tutorialId': unique_index, 'action': 'Create Tutorial', 'uuid': g.uuid}
    app.logger.info(str(log_data))
    return jsonify({"id": unique_index}), 200
    
  except Exception as e:
    db.session.rollback()
    app.logger.error(f"Error creating tutorial: {str(e)}, uuid: {g.uuid}")
    return jsonify({"error": "Internal server error"}), 500

@app.route('/tutorial/createsample', methods=['POST'])
def create_tutorial_sample():
  """
    Duplicates a tutorial for a given User ID for a given SAMPLE_TUTORIAL_ID.
  """
  data = request.get_json(force=True)
  userid = data['userid']
  tutorial_id = uuid.uuid4().hex
  tutorial_page_ids = [uuid.uuid4().hex, uuid.uuid4().hex, uuid.uuid4().hex, uuid.uuid4().hex, uuid.uuid4().hex]

  sample_tutorial_id = config("SAMPLE_TUTORIAL_ID")
  sample_tutorial_details = Tutorial.query.filter_by(id=sample_tutorial_id).first()
  try:
    sample_tutorial_page_ids = json.loads(sample_tutorial_details.sequence)
  except (json.JSONDecodeError, TypeError) as e:
    app.logger.error(f"Failed to parse tutorial sequence: {e}")
    sample_tutorial_page_ids = []

  statements = []
  tutorial_statement = Tutorial(
    id=tutorial_id, 
    name=sample_tutorial_details.name, 
    language=sample_tutorial_details.language, 
    sequence=str(tutorial_page_ids), 
    userid=userid, 
    start_date=None, 
    end_date=None)
  statements.append(tutorial_statement)

  for i in range(len(sample_tutorial_page_ids)):
    # Copy tutorial section files using hybrid storage
    success = storage.copy_recording_section(sample_tutorial_page_ids[i], tutorial_page_ids[i])
    if not success:
      logger.warning(f"Failed to copy tutorial section {sample_tutorial_page_ids[i]} to {tutorial_page_ids[i]}")
      # Continue anyway as this might be a new section with no files yet
    sample_tutorial_page_details = TutorialSection.query.filter_by(id=sample_tutorial_page_ids[i]).first()
    tutorial_page_statement = TutorialSection(
      id=tutorial_page_ids[i], 
      name=sample_tutorial_page_details.name, 
      code_input=sample_tutorial_page_details.code_input,
      language=sample_tutorial_page_details.language,
      tutorial_id=tutorial_id,
      frequent_word=sample_tutorial_page_details.frequent_word,
      tutorial_type=sample_tutorial_page_details.tutorial_type,
      duration=sample_tutorial_page_details.duration)
    statements.append(tutorial_page_statement)

  db.session.add_all(statements)
  db.session.commit()

  return jsonify({"id": tutorial_id}), 200


@app.route("/tutorial/get/<string:TutorialId>/<int:PageId>/<int:UserId>")
def getTutorialPageDetails(TutorialId, PageId, UserId):
  """
    Gets Tutorial Section details of the Page accessed. 
    Also save the last assessed details for the user.
  """
  # Validate inputs
  if not TutorialId or len(TutorialId) != 32:  # UUID hex length
    return jsonify({"message": "Invalid tutorial ID"}), 400
  if PageId <= 0:
    return jsonify({"message": "Invalid page ID"}), 400
  if UserId <= 0:
    return jsonify({"message": "Invalid user ID"}), 400
    
  tutorial_details = Tutorial.query.filter_by(id=TutorialId).first()

  tutorial_page_names = []
  tutorial_pages_sequence = []
  for element in tutorial_details.sequence[1:-1].strip().split(','):
    tutorial_section_id = element.strip()[1:-1]
    tutorial_pages_sequence.append(tutorial_section_id)
    tutorial_page_names.append(TutorialSection.query.filter_by(id=tutorial_section_id).first().name)

  tutorial_pages = TutorialSection.query.filter_by(tutorial_id=TutorialId).all()

  if (int(PageId) > len(tutorial_pages)):
    return jsonify({"message": "Invalid Page."}), 404

  tutorial_page_details = TutorialSection.query.filter_by(id=tutorial_pages_sequence[int(PageId) - 1]).first()
  user = User.query.filter_by(id=UserId).first()

  tutorial_page_type = tutorial_page_details.tutorial_type

  if tutorial_page_type == "Code":
    try:
      description_content = storage.get_recording_file(tutorial_page_details.id, 'description.md')
      description = description_content.decode('utf-8') if description_content else None
    except Exception as e:
      app.logger.warning(f"Failed to load description: {e}")
      description = None

    try:
      keystroke_content = storage.get_recording_file(tutorial_page_details.id, 'keystroke.json')
      keystroke = keystroke_content.decode('utf-8') if keystroke_content else None
    except Exception as e:
      app.logger.warning(f"Failed to load keystroke: {e}")
      keystroke = None

    try:
      console_action_content = storage.get_recording_file(tutorial_page_details.id, 'consoleAction.json')
      consoleAction = console_action_content.decode('utf-8') if console_action_content else None
    except:
      consoleAction = None

    try:
      console_scroll_content = storage.get_recording_file(tutorial_page_details.id, 'consoleScrollAction.json')
      consoleScrollAction = console_scroll_content.decode('utf-8') if console_scroll_content else "\"[{\\\"timestamp\\\":0,\\\"scroll\\\":0}]\""
    except:
      consoleScrollAction = "\"[{\\\"timestamp\\\":0,\\\"scroll\\\":0}]\""

    try:
      input_keystrokes_content = storage.get_recording_file(tutorial_page_details.id, 'inputKeystrokes.json')
      inputKeystrokes = input_keystrokes_content.decode('utf-8') if input_keystrokes_content else None
    except:
      inputKeystrokes = None

    try:
      input_scroll_content = storage.get_recording_file(tutorial_page_details.id, 'inputScrollAction.json')
      inputScrollAction = input_scroll_content.decode('utf-8') if input_scroll_content else "\"[{\\\"timestamp\\\":0,\\\"scroll\\\":0}]\""
    except:
      inputScrollAction = "\"[{\\\"timestamp\\\":0,\\\"scroll\\\":0}]\""

    try:
      layout_action_content = storage.get_recording_file(tutorial_page_details.id, 'layoutAction.json')
      layoutAction = layout_action_content.decode('utf-8') if layout_action_content else None
    except:
      layoutAction = None

    try:
      select_action_content = storage.get_recording_file(tutorial_page_details.id, 'selectAction.json')
      selectAction = select_action_content.decode('utf-8') if select_action_content else None
    except:
      selectAction = None

    try:
      scroll_action_content = storage.get_recording_file(tutorial_page_details.id, 'scrollAction.json')
      scrollAction = scroll_action_content.decode('utf-8') if scroll_action_content else None
    except:
      scrollAction = None

    try:
      editor_scroll_content = storage.get_recording_file(tutorial_page_details.id, 'editorScrollAction.json')
      editorScrollAction = editor_scroll_content.decode('utf-8') if editor_scroll_content else "\"[{\\\"timestamp\\\":0,\\\"scroll\\\":0}]\""
    except:
      editorScrollAction = "\"[{\\\"timestamp\\\":0,\\\"scroll\\\":0}]\""


    try:
      transcript_content = storage.get_recording_file(tutorial_page_details.id, 'transcript.json')
      transcript = transcript_content.decode('utf-8') if transcript_content else None
    except Exception as e:
      app.logger.error(f"Transcript retrieval error for {tutorial_page_details.id}: {str(e)}")
      transcript = None

    try:
      # Generate URL for recording file (works for both S3 and local)
      recordingResponse = storage.get_file_url(tutorial_page_details.id, 'recording.wav', expires_in=21600)
      # For local storage, prepend base URL
      if storage.get_backend_type() == 'local' and recordingResponse:
        base_url = config("REACT_APP_TUTORIAL_URL", default="http://localhost:5002")
        recordingResponse = f"{base_url}{recordingResponse}"
    except:
      recordingResponse = None

    version = None
    try:
      if (tutorial_details.language == 'python'):
        version = 'python ' + str(sys.version_info[0])+'.'+str(sys.version_info[1])+'.'+str(sys.version_info[2])
      if (tutorial_details.language == 'java'):
        java_version = subprocess.check_output(['java', '-version'], stderr=subprocess.STDOUT).decode('utf-8')
        version = 'java ' + re.search('"([^"]*)"', java_version).group()[1:-1]
      if (tutorial_details.language == 'javascript'):
        javascript_version = subprocess.check_output(['node', '--version'], stderr=subprocess.STDOUT).decode('utf-8')
        version = 'nodejs ' + javascript_version[1:-1]
    except:
      version = None

    result = {
      "tutorial_name": tutorial_details.name,
      "tutorial_pages": tutorial_page_names,
      "tutorial_page": int(PageId) - 1,
      "tutorial_type": tutorial_page_details.tutorial_type,
      "language": tutorial_details.language,
      "version": version,
      "duration": tutorial_page_details.duration,
      "description": description,
      "keystroke": keystroke,
      "consoleAction": consoleAction,
      "consoleScrollAction": consoleScrollAction,
      "layoutAction": layoutAction,
      "selectAction": selectAction,
      "scrollAction": scrollAction,
      "editorScrollAction": editorScrollAction,
      "recording": recordingResponse,
      "transcript": transcript,
      "frequent_word": tutorial_page_details.frequent_word,
      "tutorial_section_id": tutorial_page_details.id,
      "input_ide": tutorial_page_details.code_input,
      "inputKeystrokes": inputKeystrokes,
      "inputScrollAction": inputScrollAction
    }

    if tutorial_page_details:
      if user.current_role == 'learner':
        userTutorialState = db.session.query(UserTutorialState).filter_by(user_id=UserId, tutorial_id=TutorialId).first()
        if (userTutorialState):
          userTutorialState.last_page = PageId
        else:
          db.session.add(UserTutorialState(user_id=UserId, tutorial_id=TutorialId, last_page=PageId))
        db.session.commit()

      log_data = {'userId': UserId, 'role': user.current_role, 'tutorialId': TutorialId, 'tutorialSectionId': tutorial_page_details.id, 'tutorialSectionType': tutorial_page_type, 'action': 'Open Tutorial', 'uuid': g.uuid}
      app.logger.info(str(log_data))
      return jsonify(result), 200

  if tutorial_page_type == "Question":
    try:
      question_data = storage.get_recording_file(tutorial_page_details.id, 'question.json')
      question = question_data.decode('utf-8') if question_data else None
    except:
      question = None
    
    result = {
      "tutorial_name": tutorial_details.name,
      "tutorial_pages": tutorial_page_names,
      "tutorial_page": int(PageId) - 1,
      "tutorial_type": tutorial_page_details.tutorial_type,
      "question": question,
      "tutorial_section_id": tutorial_page_details.id
    }

    if tutorial_page_details:
      if user.current_role == 'learner':
        userTutorialState = db.session.query(UserTutorialState).filter_by(user_id=UserId, tutorial_id=TutorialId).first()
        if (userTutorialState):
          userTutorialState.last_page = PageId
        else:
          db.session.add(UserTutorialState(user_id=UserId, tutorial_id=TutorialId, last_page=PageId))
        db.session.commit()
      
      log_data = {'userId': UserId, 'role': user.current_role, 'tutorialId': TutorialId, 'tutorialSectionId': tutorial_page_details.id, 'tutorialSectionType': tutorial_page_type, 'action': 'Open Tutorial', 'uuid': g.uuid}
      app.logger.info(str(log_data))
      return jsonify(result), 200

  return jsonify({"message": "Tutorial Section not found."}), 404

@app.route('/tutorial/update/<string:TutorialId>', methods=['POST'])
def update_tutorial(TutorialId):
  """
    Update a tutorial. Currently only able to update sequence startDatetime and endDatetime
  """
  tutorial = Tutorial.query.filter_by(id=TutorialId).first()
  data = request.get_json(force=True)

  if "sequence" in data:
    tutorial.sequence = str(data['sequence'])
  
  if "startDatetime" in data:
    tutorial.start_date = data['startDatetime']

  if "endDatetime" in data:
    tutorial.end_date = data['endDatetime']

  try:
    db.session.merge(tutorial)
    db.session.commit()
  except Exception as e:
    db.session.rollback()
    app.logger.error(f"Database error updating tutorial: {str(e)}, uuid: {g.uuid}")
    return jsonify({"message": "An error occurred updating the tutorial"}), 500
  log_data = {'tutorialId': TutorialId, 'action': 'Update Tutorial Sequence', 'uuid': g.uuid}
  app.logger.info(str(log_data))
  return jsonify({"message": "success"}), 200

@app.route('/tutorial/delete/<string:TutorialId>')
def delete_tutorial_by_id(TutorialId):
  """
    Delete a tutorial. It will also delete the tutorial sections which belong to this tutorial
  """
  try:
    tutorial_sections = TutorialSection.query.filter_by(tutorial_id=TutorialId).all()
    try:
      for tutorial_section in tutorial_sections:
        storage.delete_recording_section(tutorial_section.id)
    except:
      print('no file in storage')
    tutorial_section = TutorialSection.query.filter_by(tutorial_id=TutorialId).delete()
    user_tutorial_state = UserTutorialState.query.filter_by(tutorial_id=TutorialId).delete()
    tutorial = Tutorial.query.filter_by(id=TutorialId).delete()
    db.session.commit()
  except:
    return jsonify({"message": "Failed to delete tutorial"}), 400
  
  log_data = {'tutorialId': TutorialId, 'action': 'Delete Tutorial', 'uuid': g.uuid}
  app.logger.info(str(log_data))
  return jsonify({"message": "success"}), 200

'''
Tutorial Section
'''
def get_frequent_word(sentence):
  """
    Get 5 most frequent word from string
  """
  stop_words = set(stopwords.words('english'))
  sentence = sentence.lower()
  tokenized_sentence = word_tokenize(sentence)
  filtered_sentence = [w for w in tokenized_sentence if not w in stop_words]
  counter = Counter(filtered_sentence)
  most_occured = [key for key, _ in counter.most_common()]
  if (len(most_occured) > 5):
    most_occured = most_occured[0:5]
  return most_occured

def remove_markdown_symbol(sentence):
  """
    Remove markdown tags and syntax
  """
  stripped_description = re.sub(r"\[(.+)\]\(.+\)", r"\1", sentence)
  stripped_description = re.sub(r"^```[^\S\r\n]*[a-z]*(?:\n(?!```$).*)*\n```", '', stripped_description, 0, re.MULTILINE)
  stripped_description = re.sub('[^A-Za-z0-9 ]+', ' ', stripped_description)
  return stripped_description

def validate_filename(filename):
  """
    Validate filename to prevent path traversal attacks
  """
  # Remove any path separators and check for valid characters
  basename = os.path.basename(filename)
  if not basename or basename in ('.', '..'):
    return False
  # Only allow alphanumeric, dash, underscore, and dot
  allowed_chars = string.ascii_letters + string.digits + '-_.'
  return all(c in allowed_chars for c in basename)

def sanitize_script_content(content, language):
  """
    Basic content sanitization for script execution
  """
  if not content or len(content) > 50000:  # Limit script size
    return False
  
  # Block potentially dangerous imports/commands
  dangerous_patterns = [
    r'import\s+os', r'import\s+sys', r'import\s+subprocess',
    r'__import__', r'eval\s*\(', r'exec\s*\(',
    r'open\s*\(', r'file\s*\(', r'input\s*\(',
    r'raw_input\s*\(', r'execfile\s*\(',
  ]
  
  content_lower = content.lower()
  for pattern in dangerous_patterns:
    if re.search(pattern, content_lower):
      return False
  
  return True

@app.route("/upload_recording", methods=["POST"])
def upload_recording():
  """
    This will trigger when author save the recording. It will save the keystroke, console action, layout action, select and scroll action, description.
  """
  # Validate required tutorial_section_id
  if 'tutorial_section_id' not in request.form:
    return jsonify({"error": "Missing tutorial_section_id"}), 400
    
  tutorial_section_id = request.form['tutorial_section_id']
  is_valid, error_msg = validate_uuid_input(tutorial_section_id)
  if not is_valid:
    return jsonify({"error": f"Invalid tutorial section ID: {error_msg}"}), 400
    
  keystroke = request.form['keystroke']
  consoleAction = request.form['consoleAction']
  consoleScrollAction = request.form['consoleScrollAction']
  layoutAction = request.form['layoutAction']
  selectAction = request.form['selectAction']
  scrollAction = request.form['scrollAction']
  editorScrollAction = request.form['editorScrollAction']
  inputKeystrokes = request.form['inputKeystrokes']
  inputScrollAction = request.form['inputScrollAction']
  full_transcript = ""
  tutorial_section_detail = TutorialSection.query.filter_by(id=tutorial_section_id).first()


  if "name" in request.form:
    tutorial_section_detail.name = request.form["name"]

  if "tutorial_type" in request.form:
    tutorial_section_detail.tutorial_type = request.form["tutorial_type"]

  if "language" in request.form:
    tutorial_section_detail.language = request.form["language"]

  if "code_input" in request.form:
    tutorial_section_detail.code_input = request.form["code_input"]

  if "duration" in request.form:
    tutorial_section_detail.duration = request.form["duration"]

  try:
    storage.delete_recording_section(tutorial_section_id)
  except:
    pass

  if "description" in request.form:
    full_transcript = full_transcript + remove_markdown_symbol(request.form['description'])
    filename = "description.md"

    with open("./" + filename, "wb") as f:
      f.write(request.form["description"].encode())

    with open("./" + filename, "rb") as readfile:
      content = readfile.read()
      storage.save_recording_file(tutorial_section_id, filename, content)
    
    os.remove("./" + filename)
  
  if "code_content" in request.form:
    filename = "code_content.txt"

    with open("./" + filename, "wb") as f:
      f.write(request.form["code_content"].encode())

    with open("./" + filename, "rb") as readfile:
      content = readfile.read()
      storage.save_recording_file(tutorial_section_id, filename, content)
    
    os.remove("./" + filename)

  # Recording upload
  if "file" in request.form:
    recording = request.form['file']
    recording_data = base64.b64decode(recording)
    recording_filename = "recording.wav"
    with open("./" + recording_filename, "wb") as f:
      f.write(recording_data)

    with open("./" + recording_filename, "rb") as readfile:
      content = readfile.read()
      storage.save_recording_file(tutorial_section_id, recording_filename, content)

    os.remove("./" + recording_filename)

  # Keystroke upload
  keystroke_filename = "keystroke.json"
  with open("./" + keystroke_filename, "wb") as f:
    f.write(json.dumps(keystroke).encode())

  with open("./" + keystroke_filename, "rb") as readfile:
    content = readfile.read()
    storage.save_recording_file(tutorial_section_id, keystroke_filename, content)
  
  os.remove("./" + keystroke_filename)

  # inputKeystrokes upload
  inputKeystroke_filename = 'inputKeystrokes.json'
  with open("./" + inputKeystroke_filename, 'wb') as f:
    f.write(json.dumps(inputKeystrokes).encode())

  with open("./"+ inputKeystroke_filename, 'rb') as readfile:
    content = readfile.read()
    storage.save_recording_file(tutorial_section_id, inputKeystroke_filename, content)

  os.remove('./'+inputKeystroke_filename)

  # inputScrollAction upload
  inputScrollAction_filename = 'inputScrollAction.json'
  with open('./' + inputScrollAction_filename, 'wb') as f:
    f.write(json.dumps(inputScrollAction).encode())
  
  with open('./' + inputScrollAction_filename, 'rb') as readfile:
    content = readfile.read()
    storage.save_recording_file(tutorial_section_id, inputScrollAction_filename, content)

  os.remove('./'+inputScrollAction_filename)

  # Console action upload
  consoleAction_filename = "consoleAction.json"
  with open("./" + consoleAction_filename, "wb") as f:
    f.write(json.dumps(consoleAction).encode())

  with open("./" + consoleAction_filename, "rb") as readfile:
    content = readfile.read()
    storage.save_recording_file(tutorial_section_id, consoleAction_filename, content)
  
  os.remove("./" + consoleAction_filename)

  # Console Scroll action upload
  consoleScrollAction_filename = 'consoleScrollAction.json'
  with open('./' + consoleScrollAction_filename, 'wb') as f:
    f.write(json.dumps(consoleScrollAction).encode())
  
  with open('./'+ consoleScrollAction_filename, 'rb') as readfile:
    content = readfile.read()
    storage.save_recording_file(tutorial_section_id, consoleScrollAction_filename, content)
  
  os.remove('./' + consoleScrollAction_filename)

  # Layout action upload
  layoutAction_filename = "layoutAction.json"
  with open("./" + layoutAction_filename, "wb") as f:
    f.write(json.dumps(layoutAction).encode())

  with open("./" + layoutAction_filename, "rb") as readfile:
    content = readfile.read()
    storage.save_recording_file(tutorial_section_id, layoutAction_filename, content)
  
  os.remove("./" + layoutAction_filename)

  # Scroll action upload
  scrollAction_filename = "scrollAction.json"
  with open("./" + scrollAction_filename, "wb") as f:
    f.write(json.dumps(scrollAction).encode())

  with open("./" + scrollAction_filename, "rb") as readfile:
    content = readfile.read()
    storage.save_recording_file(tutorial_section_id, scrollAction_filename, content)
  
  os.remove("./" + scrollAction_filename)

  # Editor scroll action upload
  editorScrollAction_filename = "editorScrollAction.json"
  with open("./"+editorScrollAction_filename, "wb") as f:
    f.write(json.dumps(editorScrollAction).encode())
  
  with open("./" + editorScrollAction_filename, "rb") as readfile:
    content = readfile.read()
    storage.save_recording_file(tutorial_section_id, editorScrollAction_filename, content)

  os.remove("./"+editorScrollAction_filename)

  # Scroll select upload
  selectAction_filename = "selectAction.json"
  with open("./" + selectAction_filename, "wb") as f:
    f.write(json.dumps(selectAction).encode())

  with open("./" + selectAction_filename, "rb") as readfile:
    content = readfile.read()
    storage.save_recording_file(tutorial_section_id, selectAction_filename, content)
  
  os.remove("./" + selectAction_filename)

  # Transcript upload
  if "transcript" in request.form:
    transcript = request.form['transcript']

    transcript_array = json.loads(transcript)
    for sentence in transcript_array:
      full_transcript = full_transcript + sentence['text'] + " "

    transcript_filename = "transcript.json"
    with open("./" + transcript_filename, "wb") as f:
      f.write(json.dumps(transcript).encode())

    with open("./" + transcript_filename, "rb") as readfile:
      content = readfile.read()
      storage.save_recording_file(tutorial_section_id, transcript_filename, content)
    
    os.remove("./" + transcript_filename)
  
  frequent_word = get_frequent_word(full_transcript)
  tutorial_section_detail.frequent_word = str(frequent_word)

  try:
    db.session.merge(tutorial_section_detail)
    db.session.commit()
  except Exception as e:
    db.session.rollback()
    app.logger.error(f"Database error saving recording: {str(e)}, uuid: {g.uuid}")
    return jsonify({"message": "An error occurred saving the recording"}), 500

  log_data = {'tutorialId': tutorial_section_detail.tutorial_id, 'tutorialSectionId': tutorial_section_detail.id, 'tutorialSectionType': tutorial_section_detail.tutorial_type, 'action': 'Upload Tutorial Section', 'uuid': g.uuid}
  app.logger.info(str(log_data))
  return jsonify({"message": "success", "frequent_word": tutorial_section_detail.frequent_word}), 200

@app.route("/run_script/<string:language>", methods=["POST"])
def run_script(language):
  """
    Runs provided script with input. 
    Currently supports python, java and javascript.
    Timeouts after 10 seconds.
  """
  data = request.get_data()

  script = json.loads(data)

  # Validate language
  allowed_languages = ["python", "java", "javascript"]
  if language not in allowed_languages:
    return {"output": "Unsupported language"}, 400

  # Validate script content
  if not sanitize_script_content(script['data'], language):
    return {"output": "Script content not allowed for security reasons"}, 400

  # Validate filename if provided
  if 'filename' in script and not validate_filename(script['filename']):
    return {"output": "Invalid filename"}, 400

  id = uuid.uuid4().hex

  if language == "python":
    pathName = "./script/" + id + ".py"
  elif language == "java":
    pathName = "./script/" + id + ".java"
  elif language == "javascript":
    pathName = "./script/" + id + ".js"

  # Ensure script directory exists and is secure
  script_dir = "./script/"
  if not os.path.exists(script_dir):
    os.makedirs(script_dir, mode=0o755)

  # Write file securely
  try:
    with open(pathName, 'wb') as f:
      f.write(script['data'].encode())
    # Set restrictive permissions
    os.chmod(pathName, 0o644)
  except (OSError, IOError) as e:
    app.logger.error(f"File write error: {str(e)}, uuid: {g.uuid}")
    return {"output": "Failed to create script file"}, 500

  if language == "python":
    cmd = "python " + id + ".py"
  elif language == "java":
    cmd = "java " + id + ".java"
  elif language == "javascript":
    cmd = "node " + id + ".js"

  scriptInput = script['input'].encode()
  if (platform.system() == "Windows"):
    p1 = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, cwd="script", creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
  else:
    p1 = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, cwd="script", preexec_fn=os.setsid)
  
  try:
    timeStarted = time.time()
    output, errors = p1.communicate(scriptInput, timeout=10)
    timeDelta = time.time() - timeStarted
    p1.wait()
  except subprocess.TimeoutExpired as e:
    if (platform.system() == "Windows"):
      p1.send_signal(signal.CTRL_BREAK_EVENT)
    else:
      os.killpg(p1.pid, signal.SIGTERM)

    # Clean up file securely
    try:
      os.remove(pathName)
    except OSError:
      pass
    filename_display = script.get('filename', 'script')
    return {"output": f"Script execution timeout after 10 seconds"}, 200

  # Clean up file securely
  try:
    os.remove(pathName)
  except OSError:
    pass

  if p1.returncode == 0:
    result = output.decode()
    if language == "java":
      result += "\r\n"
    return {"output": result, "time": timeDelta}, 200
  
  filename_display = script.get('filename', 'script')
  error_output = errors.decode().replace(id, filename_display)
  return {"output": error_output}, 200


@app.route("/compile_script/<string:language>", methods=["POST"])
def compile_script(language):
  """
    Compiles provided script code. 
    Currently supports java and similar compiled languages.
    Returns compilation results/errors.
  """
  data = request.get_data()
  script = json.loads(data)

  # Validate language
  allowed_languages = ["java", "javascript", "python"]
  if language not in allowed_languages:
    return {"output": "Unsupported language"}, 400

  # Validate script content
  if not sanitize_script_content(script['data'], language):
    return {"output": "Script content not allowed for security reasons"}, 400

  # Validate filename if provided
  if 'filename' in script and not validate_filename(script['filename']):
    return {"output": "Invalid filename"}, 400

  id = uuid.uuid4().hex

  # For languages that don't need compilation, return success
  if language == "python":
    return {"output": "Python is an interpreted language - no compilation needed", "success": True}, 200
  elif language == "javascript":
    return {"output": "JavaScript is an interpreted language - no compilation needed", "success": True}, 200
  elif language == "java":
    pathName = "./script/" + id + ".java"
    
    # Ensure script directory exists and is secure
    script_dir = "./script/"
    if not os.path.exists(script_dir):
      os.makedirs(script_dir, mode=0o755)

    # Write file securely
    try:
      with open(pathName, 'wb') as f:
        f.write(script['data'].encode())
      # Set restrictive permissions
      os.chmod(pathName, 0o644)
    except (OSError, IOError) as e:
      app.logger.error(f"File write error: {str(e)}, uuid: {g.uuid}")
      return {"output": "Failed to create script file"}, 500

    # Compile Java code
    cmd = "javac " + id + ".java"
    
    if (platform.system() == "Windows"):
      p1 = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, cwd="script", creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
      p1 = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, cwd="script", preexec_fn=os.setsid)
    
    try:
      timeStarted = time.time()
      output, errors = p1.communicate(timeout=10)
      timeDelta = time.time() - timeStarted
      p1.wait()
    except subprocess.TimeoutExpired as e:
      if (platform.system() == "Windows"):
        p1.send_signal(signal.CTRL_BREAK_EVENT)
      else:
        os.killpg(p1.pid, signal.SIGTERM)
      # Clean up files securely
      try:
        os.remove(pathName)
        class_file = "./script/" + id + ".class"
        if os.path.exists(class_file):
          os.remove(class_file)
      except OSError:
        pass
      return {"output": "Compilation timeout after 10 seconds"}, 200

    # Clean up source file securely
    try:
      os.remove(pathName)
    except OSError:
      pass

    if p1.returncode == 0:
      # Clean up compiled class file
      try:
        class_file = "./script/" + id + ".class"
        if os.path.exists(class_file):
          os.remove(class_file)
      except OSError:
        pass
      return {"output": "Compilation successful", "success": True, "time": timeDelta}, 200
    else:
      filename_display = script.get('filename', 'script')
      error_output = errors.decode().replace(id, filename_display)
      return {"output": error_output, "success": False}, 200

  return {"output": "Language not supported for compilation"}, 400


@app.route("/tutorial_section/get/<string:TutorialSectionId>")
def find_tutorial_section_by_id(TutorialSectionId):
  """
    Returns Tutorial Section details with ID.
  """
  tutorial_section_detail = TutorialSection.query.filter_by(id=TutorialSectionId).first()

  try:
    description_data = storage.get_recording_file(TutorialSectionId, 'description.md')
    description = description_data.decode('utf-8') if description_data else None
  except:
    description = None

  try:
    code_content_data = storage.get_recording_file(TutorialSectionId, 'code_content.txt')
    code_content = code_content_data.decode('utf-8') if code_content_data else None
  except:
    code_content = None

  try:
    question_data = storage.get_recording_file(TutorialSectionId, 'question.json')
    question = question_data.decode('utf-8') if question_data else None
  except:
    question = None

  tutorial_detail = Tutorial.query.filter_by(id=tutorial_section_detail.tutorial_id).first()

  version = None
  try:
    if (tutorial_detail.language == 'python'):
      version = 'python ' + str(sys.version_info[0])+'.'+str(sys.version_info[1])+'.'+str(sys.version_info[2])
    if (tutorial_detail.language == 'java'):
      java_version = subprocess.check_output(['java', '-version'], stderr=subprocess.STDOUT).decode('utf-8')
      version = 'java ' + re.search('"([^"]*)"', java_version).group()[1:-1]
    if (tutorial_detail.language == 'javascript'):
      javascript_version = subprocess.check_output(['node', '--version'], stderr=subprocess.STDOUT).decode('utf-8')
      version = 'nodejs ' + javascript_version[1:-1]
  except:
    version = None

  try:
    recordingResponse = storage.get_file_url(tutorial_section_detail.id, 'recording.wav', expires_in=21600)
  except:
    recordingResponse = None

  result = {
    "id": tutorial_section_detail.id,
    "name": tutorial_section_detail.name,
    "tutorial_type": tutorial_section_detail.tutorial_type,
    "description": description,
    "code_content": code_content,
    "question": question,
    "code_input": tutorial_section_detail.code_input,
    "language": tutorial_detail.language,
    "version": version,
    "tutorial_id": tutorial_section_detail.tutorial_id,
    "frequent_word": tutorial_section_detail.frequent_word,
    "sequence": json.loads(tutorial_detail.sequence).index(tutorial_section_detail.id) + 1 if tutorial_detail.sequence else 1,
    "recording" : recordingResponse
  }

  if tutorial_section_detail:
      log_data = {'tutorialId': tutorial_section_detail.tutorial_id, 'tutorialSectionId': TutorialSectionId, 'tutorialSectionType': tutorial_section_detail.tutorial_type, 'action': 'Open Tutorial Section', 'uuid': g.uuid}
      app.logger.info(str(log_data))
      return jsonify(result), 200
  return jsonify({"message": "Tutorial Section not found."}), 404

@app.route("/tutorial_section/get/tutorial_id/<string:TutorialId>")
def find_tutorial_section_by_tutorial_id(TutorialId):
  """
    Get tutorial section by tutorial id
  """
  tutorial_sections = TutorialSection.query.filter_by(tutorial_id=TutorialId).all()
  if tutorial_sections:
      log_data = {'tutorialId': TutorialId, 'action': 'Tutorial Overview', 'uuid': g.uuid}
      app.logger.info(str(log_data))
      return jsonify({"tutorial_section": [tutorial_section.json() for tutorial_section in tutorial_sections]}), 200
  log_data = {'tutorialId': TutorialId, 'action': 'Tutorial Overview', 'uuid': g.uuid}
  app.logger.info(str(log_data))
  return jsonify({"message": "Tutorial Section not found."}), 200

@app.route('/tutorial_section/create', methods=['POST'])
def create_tutorial_section():
  """
    Create a tutorial section. This API will return the tutorial section ID
  """
  data = request.get_json(force=True)
  unique_index = uuid.uuid4().hex
  name = data['name']
  tutorial_id = data['tutorial_id']
  tutorial_type = data['tutorial_type']

  tutorial_detail = Tutorial.query.filter_by(id=tutorial_id).first()

  statement = TutorialSection(
    id=unique_index,
    name=name,
    tutorial_type=tutorial_type,
    code_input=None,
    language=tutorial_detail.language,
    tutorial_id=tutorial_id,
    frequent_word=None,
    duration=0,
  )
  
  try:
    sequence = json.loads(tutorial_detail.sequence) if tutorial_detail.sequence else []
  except (json.JSONDecodeError, TypeError):
    sequence = []
  sequence.append(unique_index)
  tutorial_detail.sequence = json.dumps(sequence)

  try:
    db.session.add(statement)
    db.session.merge(tutorial_detail)
    db.session.commit()
  except Exception as e:
    db.session.rollback()
    app.logger.error(f"Database error creating tutorial section: {str(e)}, uuid: {g.uuid}")
    return jsonify({"message": "An error occurred creating the tutorial section"}), 500

  log_data = {'tutorialId': tutorial_id, 'tutorialSectionId': unique_index, 'tutorialSectionType': tutorial_type, 'action': 'Create Tutorial Section', 'uuid': g.uuid}
  app.logger.info(str(log_data))
  return jsonify({"id": unique_index}), 200

@app.route('/tutorial_section/update/<string:TutorialSectionId>', methods=['POST'])
def update_tutorial_section(TutorialSectionId):
  """
    Update tutorial section. This function will update the name, tutorial type, language, code input in RDS.
    It will upload the description, code content, question, transcript into S3
  """
  tutorial_section_detail = TutorialSection.query.filter_by(id=TutorialSectionId).first()
  data = request.get_json(force=True)
  full_transcript = ""

  if "name" in data:
    tutorial_section_detail.name = data["name"]

  if "tutorial_type" in data:
    tutorial_section_detail.tutorial_type = data["tutorial_type"]

  if "language" in data:
    tutorial_section_detail.language = data["language"]

  if "code_input" in data:
    tutorial_section_detail.code_input = data["code_input"]

  if "description" in data:
    full_transcript = full_transcript + remove_markdown_symbol(data['description'])
    filename = "description.md"

    with open("./" + filename, "wb") as f:
      f.write(data["description"].encode())

    with open("./" + filename, "rb") as readfile:
      content = readfile.read()
      storage.save_recording_file(TutorialSectionId, filename, content)
    
    os.remove("./" + filename)
  
  if "code_content" in data:
    filename = "code_content.txt"

    with open("./" + filename, "wb") as f:
      f.write(data["code_content"].encode())

    with open("./" + filename, "rb") as readfile:
      content = readfile.read()
      storage.save_recording_file(TutorialSectionId, filename, content)
    
    os.remove("./" + filename)

  if "question" in data and data["question"] != None:
    filename = "question.json"

    with open("./" + filename, "wb") as f:
      f.write(json.dumps(data["question"]).encode())

    with open("./" + filename, "rb") as readfile:
      content = readfile.read()
      storage.save_recording_file(TutorialSectionId, filename, content)
    
    os.remove("./" + filename)

  # TO:DO handle transcript
  try:
    transcript_data = storage.get_recording_file(TutorialSectionId, 'transcript.json')
    transcript = transcript_data.decode('utf-8') if transcript_data else None
    try:
      transcript_json = json.loads(transcript)
      transcript_array = transcript_json if isinstance(transcript_json, list) else []
    except (json.JSONDecodeError, TypeError) as e:
      app.logger.error(f"Failed to parse transcript: {e}")
      transcript_array = []
    for sentence in transcript_array:
      full_transcript = full_transcript + sentence['text'] + " "
  except:
    transcript = []
  
  frequent_word = get_frequent_word(full_transcript)
  tutorial_section_detail.frequent_word = str(frequent_word)

  try:
    db.session.merge(tutorial_section_detail)
    db.session.commit()
  except Exception as e:
    db.session.rollback()
    app.logger.error(f"Database error updating tutorial section: {str(e)}, uuid: {g.uuid}")
    return jsonify({"message": "An error occurred updating the tutorial section"}), 500

  log_data = {'tutorialId': tutorial_section_detail.tutorial_id, 'tutorialSectionId': TutorialSectionId, 'tutorialSectionType': tutorial_section_detail.tutorial_type, 'action': 'Save Tutorial Section', 'uuid': g.uuid}
  app.logger.info(str(log_data))
  return jsonify({"tutorial_id": tutorial_section_detail.tutorial_id}), 200

@app.route('/tutorial_section/delete/<string:TutorialSectionId>')
def delete_tutorial_section_by_id(TutorialSectionId):
  """
    Delete tutorial section by tutorial section ID
  """
  try:
    tutorial_section = TutorialSection.query.filter_by(id=TutorialSectionId).first()
    tutorial = Tutorial.query.filter_by(id=tutorial_section.tutorial_id).first()
    try:
      sequence = json.loads(tutorial.sequence) if tutorial.sequence else []
    except (json.JSONDecodeError, TypeError):
      sequence = []
    if TutorialSectionId in sequence:
      sequence.remove(TutorialSectionId)
    tutorial.sequence = json.dumps(sequence)

    try:
      storage.delete_recording_section(TutorialSectionId)
    except:
      print("No file in storage/Failed to delete in storage")

    tutorial_section = TutorialSection.query.filter_by(id=TutorialSectionId).delete()

    db.session.merge(tutorial)
    db.session.commit()
  except:
    return jsonify({"message": "Failed to delete tutorial section"}), 400

  log_data = {'tutorialId': tutorial.id, 'tutorialSectionId': TutorialSectionId, 'action': 'Delete Tutorial Section', 'uuid': g.uuid}
  app.logger.info(str(log_data))
  return jsonify({"message": "success"}), 200

@app.route('/save_learner_layout', methods=['POST'])
def save_learner_layout():
  """
    Save Learner Layout to S3 bucket
  """
  data = request.get_json(force=True)
  userid = str(data['userid'])
  tutorialid = data['tutorialid']
  role = data['role']
  layout = data['layout']

  # Layout upload
  layout_filename = "layout.json"
  with open("./" + layout_filename, "wb") as f:
    f.write(json.dumps(layout).encode())

  with open("./" + layout_filename, "rb") as readfile:
    content = readfile.read()
    storage.save_user_layout(userid, tutorialid, role, content)

  os.remove("./" + layout_filename)

  log_data = {'userId': userid, 'role': role, 'tutorialId': tutorialid, 'action': 'Save Tutorial Layout', 'uuid': g.uuid}
  app.logger.info(str(log_data))
  return jsonify({"message": "success"}), 200

@app.route('/get_learner_layout', methods=['POST'])
def get_learner_layout():
  """
    Retrieve Learner Layout from S3 bucket
  """
  data = request.get_json(force=True)
  userid = str(data['userid'])
  tutorialid = data['tutorialid']
  role = data['role']

  # Layout upload
  try:
    layout_data = storage.get_user_layout(userid, tutorialid, role)
    layout = layout_data.decode('utf-8') if layout_data else None
  except:
    layout = None

  # log_data = {'userId': userid, 'role': role, 'tutorialId': tutorialid, 'action': 'Load Tutorial Layout', 'uuid': g.uuid}
  # app.logger.info(str(log_data))
  return jsonify({"layout": layout}), 200

@app.route('/tutorial_section/search/keyword/<string:Keyword>/<string:TutorialSectionID>')
def search_keyword(Keyword, TutorialSectionID):
  """
    Search keyword based on transcript
  """
  result = []
  try:
    transcript_data = storage.get_recording_file(TutorialSectionID, 'transcript.json')
    transcript = transcript_data.decode('utf-8') if transcript_data else None
    try:
      transcript_json = json.loads(transcript)
      transcript_array = transcript_json if isinstance(transcript_json, list) else []
    except (json.JSONDecodeError, TypeError) as e:
      app.logger.error(f"Failed to parse transcript: {e}")
      transcript_array = []
    print(transcript_array)
    for sentence in transcript_array:
      if (Keyword.lower() in sentence['text'].lower()):
        result.append(sentence)
  except:
    transcript = []

  return jsonify({"result": result}), 200

if __name__ == '__main__':
    app.run(port=5002, debug=False)