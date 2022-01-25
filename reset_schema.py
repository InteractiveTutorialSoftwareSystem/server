from flask import Flask
import flask_sqlalchemy
import flask_praetorian
from decouple import config
import uuid
from tutorial import Tutorial, TutorialSection, db as tutorial_db
from auth import User, UserAuth, UserOauth, db as auth_db


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config("SQLALCHEMY_DATABASE_URI")
app.config['SECRET_KEY'] = config("APP_SECRET_KEY")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
guard = flask_praetorian.Praetorian()

guard.init_app(app, UserAuth)
auth_db.drop_all()
auth_db.create_all()
tutorial_db.drop_all()
tutorial_db.create_all()

both_test = User(name='Both Test', roles='author,learner')
author_test = User(name='Author Test', roles='author')
learner_test = User(name='Learner Test', roles='learner')
google_test = User(name='EMMANUEL TAN SHENG WEI _', picture='https://lh3.googleusercontent.com/a/AATXAJy73s3vTNy75_LQpyRIhLdhLf_IHk0BpnF1iU4N=s96-c', roles='author,learner')
auth_db.session.add_all([both_test, author_test, learner_test, google_test,
    UserAuth(email='test@its.com', password=guard.hash_password('password'), user=both_test),
    UserAuth(email='testa@its.com', password=guard.hash_password('passworda'), user=author_test),
    UserAuth(email='testl@its.com', password=guard.hash_password('passwordl'), user=learner_test),
    UserOauth(google_id='114755667002473147207', email='emmanueltan.2018@smu.edu.sg', user=google_test)
])

auth_db.session.commit()
tutorial_db.session.commit()