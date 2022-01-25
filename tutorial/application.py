from flask import Flask, request, jsonify, g
import flask_sqlalchemy
import flask_cors
import boto3
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
from schema import Tutorial, TutorialSection, User, UserTutorialState, db
from sqlalchemy import or_, and_
from collections import Counter
from datetime import datetime

import nltk
nltk.download('stopwords')
nltk.download('punkt')
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize


# Initialize flask app
application = app = Flask(__name__)
app.debug = True
# Initializes CORS
cors = flask_cors.CORS()
cors.init_app(app)

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

access_key_id = config("ACCESS_KEY_ID")
secret_access_key = config("SECRET_ACCESS_KEY")
s3_bucket_name = config("S3_BUCKET_NAME")
s3_learner_bucket_name = config("S3_LEARNER_BUCKET_NAME")

s3 = boto3.client(
  's3',
  aws_access_key_id = access_key_id,
  aws_secret_access_key = secret_access_key
)

s3_resource = boto3.resource(
  's3',
  aws_access_key_id = access_key_id,
  aws_secret_access_key = secret_access_key
)

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
@app.route("/tutorials/get_all/<UserId>")
def get_all_tutorials(UserId):
  """
    Gets all tutorials for the learner that are within the publish duration.
    Also gets the last assessed page by the learner for each tutorial.
  """
  date_time_now = datetime.utcnow()
  tutorials = db.session.query(Tutorial, User, UserTutorialState).join(User, Tutorial.userid == User.id) \
  .outerjoin(UserTutorialState, (Tutorial.id==UserTutorialState.tutorial_id) & (UserTutorialState.user_id==UserId)) \
  .filter(or_(and_(Tutorial.start_date < date_time_now, Tutorial.end_date > date_time_now), and_(Tutorial.start_date < date_time_now, Tutorial.end_date == None))).all()

  tutorialsJson = []
  for tutorial in tutorials:
    # print(tutorial)
    tutorialJson = {
      "id": tutorial[0].id,
      "name": tutorial[0].name,
      "language": tutorial[0].language,
      "startDatetime": tutorial[0].start_date,
      "endDatetime": tutorial[0].end_date,
      "sequence": len(tutorial[0].sequence[1:-1].split(",")),
      "user_name": tutorial[1].name,
      "user_picture": tutorial[1].picture,
      "last_page": tutorial[2] and tutorial[2].last_page or 0,
    }
    tutorialsJson.append(tutorialJson)
  
  log_data = {'userId': UserId, 'role': 'learner', 'action': 'Learner Homepage', 'uuid': g.uuid}
  app.logger.info(str(log_data))
  return jsonify({"tutorials": tutorialsJson}), 200

@app.route('/tutorial/get/<string:TutorialId>')
def get_tutorial_by_id(TutorialId):
  """
    Gets all tutorial details from Tutorial ID.
  """
  tutorial = Tutorial.query.filter_by(id=TutorialId).first()
  if tutorial:
    # log_data = {'tutorialId': TutorialId, 'action': 'get_tutorial_by_id', 'uuid': g.uuid}
    # app.logger.info(str(log_data))
    return jsonify(tutorial.json()), 200
  return jsonify({"message": "Tutorial not found"}), 200

@app.route('/tutorials/get/<string:UserId>')
def get_tutorial_by_user_id(UserId):
  """
    Gets all author's tutorials.
  """
  tutorials = db.session.query(Tutorial, User).join(User, Tutorial.userid == User.id).filter_by(id = UserId).all()
  tutorialsJson = []
  for tutorial in tutorials:
    tutorialJson = {
      "id": tutorial[0].id,
      "name": tutorial[0].name,
      "language": tutorial[0].language,
      "sequence": len(tutorial[0].sequence[1:-1].split(",")),
      "user_name": tutorial[1].name,
      "user_picture": tutorial[1].picture,
    }
    tutorialsJson.append(tutorialJson)
  
  log_data = {'userId': UserId, 'role': 'author', 'action': 'Author Homepage', 'uuid': g.uuid}
  app.logger.info(str(log_data))
  return jsonify({"tutorials": tutorialsJson}), 200

@app.route('/tutorial/create', methods=['POST'])
def create_tutorial():
  """
    Create a new tutorial
  """
  data = request.get_json(force=True)
  name = data['name']
  language = data['language']
  unique_index = uuid.uuid4().hex
  userid = data['userid']
  
  statement = Tutorial(id=unique_index, name=name, language=language, sequence="[]", userid=userid, start_date=None, end_date=None)

  try:
    db.session.add(statement)
    db.session.commit()
  except:
    return jsonify({"message": "An error occurred creating the tutorial"}), 500

  log_data = {'userId': userid, 'role': 'author', 'tutorialId': unique_index, 'action': 'Create Tutorial', 'uuid': g.uuid}
  app.logger.info(str(log_data))
  return jsonify({"id": unique_index}), 200

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
  sample_tutorial_page_ids = eval(sample_tutorial_details.sequence)

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
    response = s3.list_objects_v2(Bucket=s3_bucket_name, Prefix=sample_tutorial_page_ids[i] + "/")
    for object in response['Contents']:
      s3_resource.meta.client.copy({'Bucket': s3_bucket_name, 'Key': object['Key']}, s3_bucket_name, tutorial_page_ids[i]+'/'+object["Key"].split("/")[-1])
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


@app.route("/tutorial/get/<TutorialId>/<PageId>/<string:UserId>")
def getTutorialPageDetails(TutorialId, PageId, UserId):
  """
    Gets Tutorial Section details of the Page accessed. 
    Also save the last assessed details for the user.
  """
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
      descriptionResponse = s3.get_object(Bucket=s3_bucket_name, Key=tutorial_page_details.id + '/description.md')
      description = descriptionResponse['Body'].read().decode('utf-8')
    except:
      description = None

    try:
      keystrokeResponse = s3.get_object(Bucket=s3_bucket_name, Key=tutorial_page_details.id + '/keystroke.json')
      keystroke = keystrokeResponse['Body'].read().decode('utf-8')
    except:
      keystroke = None

    try:
      consoleActionResponse = s3.get_object(Bucket=s3_bucket_name, Key=tutorial_page_details.id + '/consoleAction.json')
      consoleAction = consoleActionResponse['Body'].read().decode('utf-8')
    except:
      consoleAction = None

    try:
      consoleScrollActionResponse = s3.get_object(Bucket=s3_bucket_name, Key=tutorial_page_details.id +'/consoleScrollAction.json')
      consoleScrollAction = consoleScrollActionResponse['Body'].read().decode('utf-8')
    except:
      consoleScrollAction = "\"[{\\\"timestamp\\\":0,\\\"scroll\\\":0}]\""

    try:
      inputKeystrokesResponse = s3.get_object(Bucket=s3_bucket_name, Key=tutorial_page_details.id + '/inputKeystrokes.json')
      inputKeystrokes = inputKeystrokesResponse['Body'].read().decode('utf-8')
    except:
      inputKeystrokes = None

    try:
      inputScrollActionResponse = s3.get_object(Bucket=s3_bucket_name, Key=tutorial_page_details.id +'/inputScrollAction.json')
      inputScrollAction = inputScrollActionResponse['Body'].read().decode('utf-8')
    except:
      inputScrollAction = "\"[{\\\"timestamp\\\":0,\\\"scroll\\\":0}]\""

    try:
      layoutActionResponse = s3.get_object(Bucket=s3_bucket_name, Key=tutorial_page_details.id + '/layoutAction.json')
      layoutAction = layoutActionResponse['Body'].read().decode('utf-8')
    except:
      layoutAction = None

    try:
      selectActionResponse = s3.get_object(Bucket=s3_bucket_name, Key=tutorial_page_details.id + '/selectAction.json')
      selectAction = selectActionResponse['Body'].read().decode('utf-8')
    except:
      selectAction = None

    try:
      scrollActionResponse = s3.get_object(Bucket=s3_bucket_name, Key=tutorial_page_details.id + '/scrollAction.json')
      scrollAction = scrollActionResponse['Body'].read().decode('utf-8')
    except:
      scrollAction = None

    try:
      editorScrollActionResponse = s3.get_object(Bucket=s3_bucket_name, Key=tutorial_page_details.id +'/editorScrollAction.json')
      editorScrollAction = editorScrollActionResponse['Body'].read().decode('utf-8')
    except:
      editorScrollAction = "\"[{\\\"timestamp\\\":0,\\\"scroll\\\":0}]\""


    try:
      transcriptResponse = s3.get_object(Bucket=s3_bucket_name, Key=tutorial_page_details.id + '/transcript.json')
      transcript = transcriptResponse['Body'].read().decode('utf-8')
    except:
      transcript = None

    try:
      recordingResponse = s3.get_object(Bucket=s3_bucket_name, Key=tutorial_page_details.id + '/recording.wav')
      recordingResponse = s3.generate_presigned_url('get_object',
        Params={
            'Bucket': s3_bucket_name,
            'Key': tutorial_page_details.id + '/recording.wav'
        },
        ExpiresIn=21600)
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
      questionResponse = s3.get_object(Bucket=s3_bucket_name, Key=tutorial_page_details.id + '/question.json')
      question = questionResponse['Body'].read().decode('utf-8')
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
  except:
    return jsonify({"message": "An error occurred creating the tutorial section"}), 500
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
        response = s3.list_objects_v2(Bucket=s3_bucket_name, Prefix=tutorial_section.id + "/")
        for object in response['Contents']:
          s3.delete_object(Bucket=s3_bucket_name, Key=object['Key'])
    except:
      print('no file in s3')
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

@app.route("/upload_recording", methods=["POST"])
def upload_recording():
  """
    This will trigger when author save the recording. It will save the keystroke, console action, layout action, select and scroll action, description.
  """
  tutorial_section_id = request.form['tutorial_section_id']
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
    response = s3.list_objects_v2(Bucket=s3_bucket_name, Prefix=tutorial_section_id + "/")
    for object in response['Contents']:
      s3.delete_object(Bucket=s3_bucket_name, Key=object['Key'])
  except:
    pass

  if "description" in request.form:
    full_transcript = full_transcript + remove_markdown_symbol(request.form['description'])
    filename = "description.md"

    with open("./" + filename, "wb") as f:
      f.write(request.form["description"].encode())

    with open("./" + filename, "rb") as readfile:
      upload_path = tutorial_section_id + "/" + filename
      s3.upload_fileobj(readfile, s3_bucket_name, upload_path)
    
    os.remove("./" + filename)
  
  if "code_content" in request.form:
    filename = "code_content.txt"

    with open("./" + filename, "wb") as f:
      f.write(request.form["code_content"].encode())

    with open("./" + filename, "rb") as readfile:
      upload_path = tutorial_section_id + "/" + filename
      s3.upload_fileobj(readfile, s3_bucket_name, upload_path)
    
    os.remove("./" + filename)

  # Recording upload
  if "file" in request.form:
    recording = request.form['file']
    recording_data = base64.b64decode(recording)
    recording_filename = "recording.wav"
    with open("./" + recording_filename, "wb") as f:
      f.write(recording_data)

    with open("./" + recording_filename, "rb") as readfile:
      upload_path = tutorial_section_id + "/" + recording_filename
      s3.upload_fileobj(readfile, s3_bucket_name, upload_path)

    os.remove("./" + recording_filename)

  # Keystroke upload
  keystroke_filename = "keystroke.json"
  with open("./" + keystroke_filename, "wb") as f:
    f.write(json.dumps(keystroke).encode())

  with open("./" + keystroke_filename, "rb") as readfile:
    upload_path = tutorial_section_id + "/" + keystroke_filename
    s3.upload_fileobj(readfile, s3_bucket_name, upload_path)
  
  os.remove("./" + keystroke_filename)

  # inputKeystrokes upload
  inputKeystroke_filename = 'inputKeystrokes.json'
  with open("./" + inputKeystroke_filename, 'wb') as f:
    f.write(json.dumps(inputKeystrokes).encode())

  with open("./"+ inputKeystroke_filename, 'rb') as readfile:
    upload_path = tutorial_section_id+"/"+inputKeystroke_filename
    s3.upload_fileobj(readfile, s3_bucket_name, upload_path)

  os.remove('./'+inputKeystroke_filename)

  # inputScrollAction upload
  inputScrollAction_filename = 'inputScrollAction.json'
  with open('./' + inputScrollAction_filename, 'wb') as f:
    f.write(json.dumps(inputScrollAction).encode())
  
  with open('./' + inputScrollAction_filename, 'rb') as readfile:
    upload_path = tutorial_section_id+'/'+inputScrollAction_filename
    s3.upload_fileobj(readfile,s3_bucket_name,upload_path)

  os.remove('./'+inputScrollAction_filename)

  # Console action upload
  consoleAction_filename = "consoleAction.json"
  with open("./" + consoleAction_filename, "wb") as f:
    f.write(json.dumps(consoleAction).encode())

  with open("./" + consoleAction_filename, "rb") as readfile:
    upload_path = tutorial_section_id + "/" + consoleAction_filename
    s3.upload_fileobj(readfile, s3_bucket_name, upload_path)
  
  os.remove("./" + consoleAction_filename)

  # Console Scroll action upload
  consoleScrollAction_filename = 'consoleScrollAction.json'
  with open('./' + consoleScrollAction_filename, 'wb') as f:
    f.write(json.dumps(consoleScrollAction).encode())
  
  with open('./'+ consoleScrollAction_filename, 'rb') as readfile:
    upload_path = tutorial_section_id+"/" +consoleScrollAction_filename
    s3.upload_fileobj(readfile, s3_bucket_name, upload_path)
  
  os.remove('./' + consoleScrollAction_filename)

  # Layout action upload
  layoutAction_filename = "layoutAction.json"
  with open("./" + layoutAction_filename, "wb") as f:
    f.write(json.dumps(layoutAction).encode())

  with open("./" + layoutAction_filename, "rb") as readfile:
    upload_path = tutorial_section_id + "/" + layoutAction_filename
    s3.upload_fileobj(readfile, s3_bucket_name, upload_path)
  
  os.remove("./" + layoutAction_filename)

  # Scroll action upload
  scrollAction_filename = "scrollAction.json"
  with open("./" + scrollAction_filename, "wb") as f:
    f.write(json.dumps(scrollAction).encode())

  with open("./" + scrollAction_filename, "rb") as readfile:
    upload_path = tutorial_section_id + "/" + scrollAction_filename
    s3.upload_fileobj(readfile, s3_bucket_name, upload_path)
  
  os.remove("./" + scrollAction_filename)

  # Editor scroll action upload
  editorScrollAction_filename = "editorScrollAction.json"
  with open("./"+editorScrollAction_filename, "wb") as f:
    f.write(json.dumps(editorScrollAction).encode())
  
  with open("./" + editorScrollAction_filename, "rb") as readfile:
    upload_path = tutorial_section_id + "/" + editorScrollAction_filename
    s3.upload_fileobj(readfile, s3_bucket_name, upload_path)

  os.remove("./"+editorScrollAction_filename)

  # Scroll select upload
  selectAction_filename = "selectAction.json"
  with open("./" + selectAction_filename, "wb") as f:
    f.write(json.dumps(selectAction).encode())

  with open("./" + selectAction_filename, "rb") as readfile:
    upload_path = tutorial_section_id + "/" + selectAction_filename
    s3.upload_fileobj(readfile, s3_bucket_name, upload_path)
  
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
      upload_path = tutorial_section_id + "/" + transcript_filename
      s3.upload_fileobj(readfile, s3_bucket_name, upload_path)
    
    os.remove("./" + transcript_filename)
  
  frequent_word = get_frequent_word(full_transcript)
  tutorial_section_detail.frequent_word = str(frequent_word)

  try:
    db.session.merge(tutorial_section_detail)
    db.session.commit()
  except:
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

  id = uuid.uuid4().hex

  if language == "python":
    pathName = "./script/" + id + ".py"
  elif language == "java":
    pathName = "./script/" + id + ".java"
  elif language == "javascript":
    pathName = "./script/" + id + ".js"

  with open(pathName, 'wb') as f:
    f.write(script['data'].encode())

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

    os.remove(pathName)
    return {"output": format(e).replace(id, script['filename'])+"\r\n"}, 200

  os.remove(pathName)

  if p1.returncode == 0:
    result = output.decode()
    if language == "java":
      result += "\r\n"
    return {"output": result, "time": timeDelta}, 200
  return {"output": errors.decode().replace(id, script['filename'])}, 200


@app.route("/tutorial_section/get/<string:TutorialSectionId>")
def find_tutorial_section_by_id(TutorialSectionId):
  """
    Returns Tutorial Section details with ID.
  """
  tutorial_section_detail = TutorialSection.query.filter_by(id=TutorialSectionId).first()

  try:
    descriptionResponse = s3.get_object(Bucket=s3_bucket_name, Key=TutorialSectionId + '/description.md')
    description = descriptionResponse['Body'].read().decode('utf-8')
  except:
    description = None

  try:
    codeContentResponse = s3.get_object(Bucket=s3_bucket_name, Key=TutorialSectionId + '/code_content.txt')
    code_content = codeContentResponse['Body'].read().decode('utf-8')
  except:
    code_content = None

  try:
    questionResponse = s3.get_object(Bucket=s3_bucket_name, Key=TutorialSectionId + '/question.json')
    question = questionResponse['Body'].read().decode('utf-8')
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
    recordingResponse = s3.get_object(Bucket=s3_bucket_name, Key=tutorial_section_detail.id + '/recording.wav')
    recordingResponse = s3.generate_presigned_url('get_object',
      Params={
          'Bucket': s3_bucket_name,
          'Key': tutorial_section_detail.id + '/recording.wav'
      },
      ExpiresIn=21600)
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
    "sequence": eval(tutorial_detail.sequence).index(tutorial_section_detail.id) + 1,
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
  
  sequence = eval(tutorial_detail.sequence)
  sequence.append(unique_index)
  tutorial_detail.sequence = str(sequence)

  try:
    db.session.add(statement)
    db.session.merge(tutorial_detail)
    db.session.commit()
  except:
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
      upload_path = TutorialSectionId + "/" + filename
      s3.upload_fileobj(readfile, s3_bucket_name, upload_path)
    
    os.remove("./" + filename)
  
  if "code_content" in data:
    filename = "code_content.txt"

    with open("./" + filename, "wb") as f:
      f.write(data["code_content"].encode())

    with open("./" + filename, "rb") as readfile:
      upload_path = TutorialSectionId + "/" + filename
      s3.upload_fileobj(readfile, s3_bucket_name, upload_path)
    
    os.remove("./" + filename)

  if "question" in data and data["question"] != None:
    filename = "question.json"

    with open("./" + filename, "wb") as f:
      f.write(json.dumps(data["question"]).encode())

    with open("./" + filename, "rb") as readfile:
      upload_path = TutorialSectionId + "/" + filename
      s3.upload_fileobj(readfile, s3_bucket_name, upload_path)
    
    os.remove("./" + filename)

  # TO:DO handle transcript
  try:
    transcriptResponse = s3.get_object(Bucket=s3_bucket_name, Key=TutorialSectionId + '/transcript.json')
    transcript = transcriptResponse['Body'].read().decode('utf-8')
    transcript_array = eval(json.loads(transcript))
    for sentence in transcript_array:
      full_transcript = full_transcript + sentence['text'] + " "
  except:
    transcript = []
  
  frequent_word = get_frequent_word(full_transcript)
  tutorial_section_detail.frequent_word = str(frequent_word)

  try:
    db.session.merge(tutorial_section_detail)
    db.session.commit()
  except:
    return jsonify({"message": "An error occurred creating the tutorial"}), 500

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
    sequence = eval(tutorial.sequence)
    sequence.remove(TutorialSectionId)
    tutorial.sequence = str(sequence)

    try:
      response = s3.list_objects_v2(Bucket=s3_bucket_name, Prefix=TutorialSectionId + "/")
      for object in response['Contents']:
        s3.delete_object(Bucket=s3_bucket_name, Key=object['Key'])
    except:
      print("No file in S3/Failed to delete in S3")

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
    upload_path = userid + "/" + tutorialid + "/" + role + "/" + layout_filename
    s3.upload_fileobj(readfile, s3_learner_bucket_name, upload_path)

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
    LayoutResponse = s3.get_object(Bucket=s3_learner_bucket_name, Key=userid + "/" + tutorialid + "/" + role + '/layout.json')
    layout = LayoutResponse['Body'].read().decode('utf-8')
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
    transcriptResponse = s3.get_object(Bucket=s3_bucket_name, Key=TutorialSectionID + '/transcript.json')
    transcript = transcriptResponse['Body'].read().decode('utf-8')
    transcript_array = eval(json.loads(transcript))
    print(transcript_array)
    for sentence in transcript_array:
      if (Keyword.lower() in sentence['text'].lower()):
        result.append(sentence)
  except:
    transcript = []

  return jsonify({"result": result}), 200

if __name__ == '__main__':
    app.run(port=5002, debug=False)