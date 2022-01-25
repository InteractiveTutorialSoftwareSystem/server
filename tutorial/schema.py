from flask import Flask
import flask_sqlalchemy
from decouple import config
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config("SQLALCHEMY_DATABASE_URI")
app.config['SECRET_KEY'] = config("APP_SECRET_KEY")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = flask_sqlalchemy.SQLAlchemy(app)

class Tutorial(db.Model):
  id = db.Column(db.String(length=36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True)
  name = db.Column(db.String(320), nullable=False)
  language = db.Column(db.String(100), nullable=False)
  tutorial_tutorialsection = db.relationship('TutorialSection')
  sequence = db.Column(db.String(10000))
  userid = db.Column(db.Integer)
  start_date = db.Column(db.DateTime, default=None)
  end_date = db.Column(db.DateTime, default=None)

  def __init__(self, id, name, language, sequence, userid, start_date, end_date):
      self.id = id
      self.name = name
      self.language = language
      self.sequence = sequence
      self.userid = userid
      self.start_date = start_date
      self.end_date = end_date

  def json(self):
      return {"id": self.id, "name": self.name, "language": self.language, "sequence": self.sequence, "userid": self.userid, "start_date": self.start_date, "end_date": self.end_date}

class TutorialSection(db.Model):
  id = db.Column(db.String(length=36), primary_key=True, default=lambda: str(uuid.uuid4().hex))
  name = db.Column(db.String(320), nullable=False)
  tutorial_type = db.Column(db.String(320), nullable=False)
  code_input = db.Column(db.String(10000))
  language = db.Column(db.String(100))
  frequent_word = db.Column(db.String(1000))
  duration = db.Column(db.Integer)
  tutorial_id = db.Column(db.String(length=36), db.ForeignKey('tutorial.id'), nullable=False)

  def __init__(self, id, name, tutorial_type, code_input, language, frequent_word, duration, tutorial_id):
    self.id = id
    self.name = name
    self.tutorial_type = tutorial_type
    self.code_input = code_input
    self.language = language
    self.frequent_word = frequent_word
    self.duration = duration
    self.tutorial_id = tutorial_id

  def json(self):
    return {"id": self.id, "name": self.name, "tutorial_type": self.tutorial_type, "code_input": self.code_input, "language": self.language, "frequent_word": self.frequent_word, "duration": self.duration, "tutorial_id": self.tutorial_id}

class UserTutorialState(db.Model):
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
  tutorial_id = db.Column(db.String(length=36), db.ForeignKey('tutorial.id'), primary_key=True)
  last_page = db.Column(db.Integer, default=1)

class User(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(320), nullable=False)
  picture = db.Column(db.String(320))
  roles = db.Column(db.String(15), nullable=False)
  current_role = db.Column(db.String(7))