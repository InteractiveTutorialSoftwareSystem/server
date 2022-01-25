from flask import Flask, request, jsonify, g
import flask_sqlalchemy
import flask_praetorian
import flask_cors
import re
import jwt
import uuid
import requests
import logging
from decouple import config
from google.oauth2 import id_token
from google.auth.transport import requests as googleRequests
from logging.handlers import RotatingFileHandler
from schema import User, UserAuth, UserOauth, db

# db = flask_sqlalchemy.SQLAlchemy()
guard = flask_praetorian.Praetorian()
cors = flask_cors.CORS()

# Initialize flask app
application = app = Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = config("APP_SECRET_KEY")
app.config['JWT_ACCESS_LIFESPAN'] = {'hours': 24}
app.config['JWT_REFRESH_LIFESPAN'] = {'days': 30}

# Initialize a local database
app.config['SQLALCHEMY_DATABASE_URI'] = config("SQLALCHEMY_DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Initializes CORS
cors.init_app(app)

# Initialize the flask-praetorian instance for the app
guard.init_app(app, UserAuth)

# Setup Logger
logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s : %(message)s')
logger.setLevel(logging.DEBUG)
# handler = RotatingFileHandler('/opt/python/log/application.log')
handler = RotatingFileHandler('application.log')
handler.setFormatter(formatter)
application.logger.addHandler(handler)

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


@app.route("/")
def test():
  return jsonify({"message": "auth"}), 200

@app.route('/auth/register', methods=['POST'])
def register():
    """
    Creates an entry in the UserAuth table if the input is valid
    Takes in name, email, password, the repassword, and the role
    """
    req = request.get_json(force=True)
    name = req.get('name', None)
    email = req.get('email', None).lower()
    password = req.get('password', None)
    repassword = req.get('repassword', None)
    role = req.get('role', None)

    if not (name and email and password and repassword and role):
        return {'message':'All fields are required.'}, 400

    regex = '^(\w|\.|\_|\-)+[@](\w|\_|\-|\.)+[.]\w{2,3}$'
    if re.search(regex, email) == None:
        return {'message':'Invalid Email.'}, 400

    if (len(password) < 8):
        return {'message':'Invalid Password.'}, 400

    if not re.search("[a-z]", password):
        return {'message':'Invalid Password.'}, 400

    if not re.search("[A-Z]", password):
        return {'message':'Invalid Password.'}, 400

    if not re.search("[0-9]", password):
        return {'message':'Invalid Password.'}, 400

    if not re.search("[#?!@$%^&*-]", password):
        return {'message':'Invalid Password.'}, 400

    if (password != repassword):
        return {'message':'Password mismatch.'}, 400

    roleOptions = ['author', 'learner', 'both']
    if (role not in roleOptions): 
        return {'message':'Please select a different role.'}, 400

    if UserAuth.lookup(email) != None:
        return {'message':'Account already registered. Please Login.'}, 400

    if role == "both":
        role = "author,learner"
    
    newUser = User(name=name, roles=role)

    db.session.add_all([newUser,
        UserAuth(email=email, password=guard.hash_password(password), user=newUser),
    ])

    db.session.commit()
    
    log_data = {'userId': newUser.id, 'role': role, 'action': 'Form Registration', 'uuid': g.uuid}
    app.logger.info(str(log_data))
    return {'message':'Registration successful. Redirecting to Login.'}, 200

@app.route('/auth/login', methods=['POST'])
def login():
    """
    Logs a user in by parsing a POST request containing user credentials and issuing a JWT token.
    """
    req = request.get_json(force=True)
    email = req.get('email', None).lower()
    password = req.get('password', None)
    role = req.get('role', None)

    if not (email and password and role):
        return {'message':'All fields are required.'}, 400

    regex = '^(\w|\.|\_|\-)+[@](\w|\_|\-|\.)+[.]\w{2,3}$'
    if re.search(regex, email) == None:
        return {'message':'Invalid Email.'}, 400

    roleOptions = ['author', 'learner']
    if (role not in roleOptions): 
        return {'message':'Incorrect email and/or password for the selected role.'}, 400

    user_auth = guard.authenticate(email, password)

    if role not in user_auth.user.roles:
        return {'message':'Incorrect email and/or password for the selected role.'}, 400
        
    current_user_id = user_auth.user_id
    currentUser = db.session.query(User).filter_by(id=current_user_id).first()
    currentUser.current_role = role

    db.session.commit()
    
    log_data = {'userId': currentUser.id, 'role': role, 'action': 'Form Login', 'uuid': g.uuid}
    app.logger.info(str(log_data))
    return {'access_token': guard.encode_jwt_token(user_auth), 'role': role}, 200

@app.route('/guest/login', methods=['POST'])
def guest_login():
    """
    Creates a randomly generated user account and logins the user in via token
    """
    data = request.get_json(force=True)
    guestRole = data['role']

    roleOptions = ['author', 'learner']
    if (guestRole not in roleOptions): 
        return {'message':'Incorrect role.'}, 400

    newGuest = User(name="Guest", roles="guest,"+guestRole, current_role=guestRole)
    guestEmail = uuid.uuid4().hex
    guestPassword = uuid.uuid4().hex

    db.session.add_all([newGuest,
        UserAuth(email=guestEmail, password=guard.hash_password(guestPassword), user=newGuest),
    ])

    db.session.commit()

    user_auth = guard.authenticate(guestEmail, guestPassword)

    if (guestRole == 'author'):
        requests.post(config("REACT_APP_TUTORIAL_URL") + '/tutorial/createsample', json={'userid':newGuest.id})
    
    log_data = {'userId': newGuest.id, 'role': guestRole, 'action': 'Guest Login', 'uuid': g.uuid}
    app.logger.info(str(log_data))
    return {'access_token': guard.encode_jwt_token(user_auth), 'role': guestRole}, 200

@app.route('/oauth/register', methods=['POST'])
def gRegister():
    """
    Creates an entry in the UserOauth table if the input is valid
    """
    token = request.get_json(force=True)["token"]
    role = request.get_json(force=True)["role"]

    roleOptions = ['author', 'learner', 'both']
    if (role not in roleOptions): 
        return {'message':'Please select a different role.'}, 400

    userinfo = id_token.verify_oauth2_token(token, googleRequests.Request(), config("GOOGLE_CLIENT_ID"))
    google_id = userinfo['sub']

    if db.session.query(UserOauth).filter_by(google_id=google_id).first() != None:
        return {'message':'Account already registered. Please Login.'}, 400

    email = userinfo['email']
    name = userinfo['name']
    picture = userinfo['picture']

    if role == "both":
        role = "author,learner"
    
    newUser = User(name=name, picture=picture, roles=role)

    db.session.add_all([newUser,
        UserOauth(google_id=google_id, email=email, user=newUser)
    ])

    db.session.commit()

    log_data = {'userId': newUser.id, 'role': role, 'action': 'Google Registration', 'uuid': g.uuid}
    app.logger.info(str(log_data))
    return {'message':'Registration successful. Redirecting to Login.'}, 200

@app.route('/oauth/login', methods=['POST'])
def gLogin():
    """
    Verifies the token passed from frontend and saves the user details in DB
    """
    token = request.get_json(force=True)["token"]
    role = request.get_json(force=True)["role"]
    userinfo = id_token.verify_oauth2_token(token, googleRequests.Request(), config("GOOGLE_CLIENT_ID"))
    google_id = userinfo['sub']
    email = userinfo['email']
    name = userinfo['name']
    picture = userinfo['picture']

    if db.session.query(UserOauth).filter_by(google_id=google_id).count() == 1:
        currentUserOauth = db.session.query(UserOauth).filter_by(google_id=google_id).first()
        if role not in currentUserOauth.user.roles:
            return {'message':'Account not permitted'}, 400

        currentUserOauth.email = email
        currentUserOauth.user.name = name
        currentUserOauth.user.picture = picture
        currentUserOauth.user.current_role = role

        db.session.commit()
        log_data = {'userId': currentUserOauth.user_id, 'role': role, 'action': 'Google Login', 'uuid': g.uuid}
        app.logger.info(str(log_data))
        return {'access_token': token, 'role': role}, 200

    return {'message':'Account not permitted'}, 400
  
@app.route('/auth/refresh', methods=['POST'])
def refresh():
    """
    Refreshes an existing JWT by creating a new one that is a copy of the old
    except that it has a refreshed access expiration.
    """
    try:
        old_token = request.get_data().decode(('utf-8'))
        new_token = guard.refresh_jwt_token(old_token)
        ret = {'access_token': new_token}
        return ret, 200
    except:
        return {'message':'Token Expired'}, 400
  
  
@app.route('/auth/protected')
def protected():
    """
    A protected endpoint. The auth_required decorator will require a header
    containing a valid JWT
    """
    try:
        bearer, _, token = request.headers.get('Authorization').partition(' ')
        if bearer != 'Bearer':
            raise ValueError('Invalid token')
        userinfo = jwt.decode(token, config("APP_SECRET_KEY"), algorithms=["HS256"])
        userid = userinfo["id"]
        currentUserAuth = db.session.query(UserAuth).filter_by(id=userid).first()
        return {'id': currentUserAuth.user.id, 'role': currentUserAuth.user.current_role}
    except:
        try:
            bearer, _, token = request.headers.get('Authorization').partition(' ')
            if bearer != 'Bearer':
                raise ValueError('Invalid token')
            userinfo = id_token.verify_oauth2_token(token, googleRequests.Request(), config("GOOGLE_CLIENT_ID"))
            google_id = userinfo['sub']
            currentUserOauth = db.session.query(UserOauth).filter_by(google_id=google_id).first()
            return {'id': currentUserOauth.user.id, 'role': currentUserOauth.user.current_role}
        except:
            return {'message':'Token Expired'}, 400


@app.route('/getUserDetails', methods=['POST'])
def getUserDetails():
    """
    Gets user details from User ID. Also gets the login type.
    """
    data = request.get_json(force=True)
    id = data['id']
    userDetails = db.session.query(User).filter_by(id=id).first()
    rolesArray = userDetails.roles.split(",")

    if "guest" in rolesArray:
        rolesArray.remove('guest')
        return {'name': userDetails.name, 'roles': "".join(rolesArray).title(), 'loginType': 'guest'}
    if userDetails.user_auth:
        email = userDetails.user_auth.email
        loginType = 'form'
    else:
        email = userDetails.user_oauth.email
        loginType = 'google'

    roles = []
    for role in rolesArray:
        roles.append(role.title())

    return {'name': userDetails.name, 'email': email, 'roles': ", ".join(roles), 'picture': userDetails.picture, 'loginType': loginType}, 200


# Run the example
if __name__ == '__main__':
    app.run(port=5001, debug=False)