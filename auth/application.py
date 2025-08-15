from flask import Flask, request, jsonify, g
import flask_sqlalchemy
import flask_praetorian
import flask_cors
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import re
import jwt
import uuid
import requests
import logging
from decouple import config
from google.oauth2 import id_token
from google.auth.transport import requests as googleRequests
from logging.handlers import RotatingFileHandler
from auth.schema import User, UserAuth, UserOauth, db

# db = flask_sqlalchemy.SQLAlchemy()
guard = flask_praetorian.Praetorian()
cors = flask_cors.CORS()

# Initialize flask app
application = app = Flask(__name__)
app.debug = config("DEBUG", default=False, cast=bool)
app.config['SECRET_KEY'] = config("APP_SECRET_KEY")
app.config['JWT_ACCESS_LIFESPAN'] = {'hours': 24}
app.config['JWT_REFRESH_LIFESPAN'] = {'days': 30}

# Initialize a local database
app.config['SQLALCHEMY_DATABASE_URI'] = config("SQLALCHEMY_DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Initializes CORS with specific origins
allowed_origins = config("ALLOWED_ORIGINS", default="http://localhost:3000").split(",")
cors.init_app(app, origins=allowed_origins, supports_credentials=True)

# Initialize the flask-praetorian instance for the app
guard.init_app(app, UserAuth)

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=config("LIMITER_STORAGE_URI", default="memory://")
)
limiter.init_app(app)

# Setup Logger
logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s : %(message)s')
logger.setLevel(logging.DEBUG)
# handler = RotatingFileHandler('/opt/python/log/application.log')
handler = RotatingFileHandler('application.log')
handler.setFormatter(formatter)
application.logger.addHandler(handler)

# Input validation helper
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
    import re
    uuid_pattern = r'^[a-fA-F0-9]{8}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{12}$|^[a-fA-F0-9]{32}$'
    if not re.match(uuid_pattern, value):
        return False, "Invalid UUID format"
    
    if len(value) not in [32, 36]:  # 32 for hex string, 36 for UUID with dashes
        return False, "Invalid UUID length"
    
    return True, None

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


@app.route("/")
def test():
  return jsonify({"message": "auth"}), 200

@app.route('/auth/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    """
    Creates an entry in the UserAuth table if the input is valid
    Takes in name, email, password, the repassword, and the role
    """
    req = request.get_json(force=True)
    name = req.get('name', None)
    email = req.get('email', None)
    password = req.get('password', None)
    repassword = req.get('repassword', None)
    role = req.get('role', None)

    if not (name and email and password and repassword and role):
        return {'message':'All fields are required.'}, 400

    # Validate inputs
    is_valid, error_msg = validate_string_input(name, max_length=100)
    if not is_valid:
        return {'message': f'Invalid name: {error_msg}'}, 400
    
    is_valid, error_msg = validate_string_input(email, max_length=254)
    if not is_valid:
        return {'message': f'Invalid email: {error_msg}'}, 400
    
    email = email.lower().strip()

    # More robust email validation
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email) or len(email) > 254:
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

    try:
        db.session.add_all([newUser,
            UserAuth(email=email, password=guard.hash_password(password), user=newUser),
        ])

        db.session.commit()
        
        log_data = {'userId': newUser.id, 'role': role, 'action': 'Form Registration', 'uuid': g.uuid}
        app.logger.info(str(log_data))
        return {'message':'Registration successful. Redirecting to Login.'}, 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Database error during registration: {str(e)}, uuid: {g.uuid}")
        return {'message':'Registration failed. Please try again.'}, 500

@app.route('/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
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

    # More robust email validation
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email) or len(email) > 254:
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
@limiter.limit("20 per minute")
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

    try:
        db.session.add_all([newGuest,
            UserAuth(email=guestEmail, password=guard.hash_password(guestPassword), user=newGuest),
        ])

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Database error during guest login: {str(e)}, uuid: {g.uuid}")
        return {'message':'Guest login failed. Please try again.'}, 500

    user_auth = guard.authenticate(guestEmail, guestPassword)

    if (guestRole == 'author'):
        requests.post(config("REACT_APP_TUTORIAL_URL") + '/tutorial/createsample', json={'userid':newGuest.id})
    
    log_data = {'userId': newGuest.id, 'role': guestRole, 'action': 'Guest Login', 'uuid': g.uuid}
    app.logger.info(str(log_data))
    return {'access_token': guard.encode_jwt_token(user_auth), 'role': guestRole}, 200

@app.route('/oauth/register', methods=['POST'])
@limiter.limit("5 per minute")
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

    try:
        db.session.add_all([newUser,
            UserOauth(google_id=google_id, email=email, user=newUser)
        ])

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Database error during OAuth registration: {str(e)}, uuid: {g.uuid}")
        return {'message':'Registration failed. Please try again.'}, 500

    log_data = {'userId': newUser.id, 'role': role, 'action': 'Google Registration', 'uuid': g.uuid}
    app.logger.info(str(log_data))
    return {'message':'Registration successful. Redirecting to Login.'}, 200

@app.route('/oauth/login', methods=['POST'])
@limiter.limit("10 per minute")
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

        try:
            db.session.commit()
            log_data = {'userId': currentUserOauth.user_id, 'role': role, 'action': 'Google Login', 'uuid': g.uuid}
            app.logger.info(str(log_data))
            return {'access_token': token, 'role': role}, 200
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Database error during OAuth login: {str(e)}, uuid: {g.uuid}")
            return {'message':'Login failed. Please try again.'}, 500

    return {'message':'Account not permitted'}, 400
  
@app.route('/auth/refresh', methods=['POST'])
@limiter.limit("30 per minute")
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
    try:
        data = request.get_json(force=True)
        if not data or 'id' not in data:
            return {'message': 'User ID is required'}, 400
        
        # Validate integer input
        is_valid, user_id, error_msg = validate_integer_input(data['id'], min_val=1)
        if not is_valid:
            return {'message': f'Invalid user ID: {error_msg}'}, 400
        
        userDetails = db.session.query(User).filter_by(id=user_id).first()
        if not userDetails:
            return {'message': 'User not found'}, 404
            
        rolesArray = userDetails.roles.split(",")

        if "guest" in rolesArray:
            rolesArray.remove('guest')
            return {'name': userDetails.name, 'roles': "".join(rolesArray).title(), 'loginType': 'guest'}, 200
            
        if userDetails.user_auth:
            email = userDetails.user_auth.email
            loginType = 'form'
        elif userDetails.user_oauth:
            email = userDetails.user_oauth.email
            loginType = 'google'
        else:
            return {'message': 'User authentication data not found'}, 404

        roles = []
        for role in rolesArray:
            roles.append(role.title())

        return {'name': userDetails.name, 'email': email, 'roles': ", ".join(roles), 'picture': userDetails.picture, 'loginType': loginType}, 200
        
    except Exception as e:
        app.logger.error(f"Error in getUserDetails: {str(e)}, uuid: {g.uuid}")
        return {'message': 'Internal server error'}, 500


# Run the example
if __name__ == '__main__':
    app.run(port=5001, debug=False)