from flask import Flask
import flask_sqlalchemy
import flask_praetorian
from decouple import config
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config("SQLALCHEMY_DATABASE_URI")
app.config['SECRET_KEY'] = config("APP_SECRET_KEY")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = flask_sqlalchemy.SQLAlchemy(app)

class User(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(320), nullable=False)
  picture = db.Column(db.String(320))
  roles = db.Column(db.String(15), nullable=False)
  current_role = db.Column(db.String(7))
  user_auth = db.relationship('UserAuth', uselist=False, backref='user')
  user_oauth = db.relationship('UserOauth', uselist=False, backref='user')

class UserAuth(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  email = db.Column(db.String(320), unique=True, nullable=False)
  password = db.Column(db.String(131), nullable=False)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)

  @property
  def rolenames(self):
    try:
        return self.current_role.split(',')
    except Exception:
        return []

  @classmethod
  def lookup(cls, email):
    return cls.query.filter_by(email=email).one_or_none()

  @classmethod
  def identify(cls, id):
    return cls.query.get(id)

  @property
  def identity(self):
    return self.id

class UserOauth(db.Model):
  google_id = db.Column(db.String(21), primary_key=True)
  email = db.Column(db.String(320), unique=True, nullable=False)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)