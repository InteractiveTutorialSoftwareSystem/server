# Interactive Tutorial System (Backend)

[![Security Hardened](https://img.shields.io/badge/Security-Hardened-green.svg)](https://github.com/InteractiveTutorialSoftwareSystem/server)
[![SQL Injection Protected](https://img.shields.io/badge/SQL%20Injection-Protected-blue.svg)](https://github.com/InteractiveTutorialSoftwareSystem/server)
[![Flask](https://img.shields.io/badge/Flask-2.3.x-red.svg)](https://flask.palletsprojects.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)

## Table of Contents
1. [Introduction](#introduction)
2. [Latest Security Updates](#latest-security-updates)
3. [Technologies Required](#technologies-required)
4. [Fresh Installation](#fresh-installation)
5. [Development Setup](#development-setup)
6. [Running the Application](#running-the-application)
7. [Security Features](#security-features)
8. [Database Schema](#database-schema)
9. [AWS S3 Configuration](#aws-s3-configuration)
10. [API Documentation](#api-documentation)
11. [Troubleshooting](#troubleshooting)
12. [References](#references)

## Introduction
This repository contains the backend Flask application for the Interactive Tutorial System (ITSS) project. The system provides secure REST APIs for authentication, tutorial management, and interactive programming environments.

**Frontend Repository:** [InteractiveTutorialSoftwareSystem/client](https://github.com/InteractiveTutorialSoftwareSystem/client)

## Latest Security Updates

### 🛡️ Security Hardening (August 2024)
- ✅ **SQL Injection Protection**: All database queries now use parameterized statements
- ✅ **Input Validation**: Comprehensive validation for all user inputs
- ✅ **Code Injection Prevention**: Replaced all dangerous `eval()` calls with secure JSON parsing
- ✅ **Parameter Sanitization**: Strict type checking and bounds validation
- ✅ **Error Handling**: Secure error responses without information disclosure

### 🔧 Security Improvements
- **Input Validation Functions**: `validate_integer_input()`, `validate_uuid_input()`, `validate_string_input()`
- **Safe JSON Parsing**: Replaced `eval()` with `json.loads()` and proper error handling
- **SQL Parameterization**: All queries use SQLAlchemy ORM or parameterized statements
- **Bounds Checking**: Integer inputs validated with min/max ranges
- **UUID Validation**: Proper format validation for all UUID parameters
- **String Sanitization**: Length limits and content validation for text inputs

## Technologies Required

### Core Requirements
- **Python**: >= 3.8.4 (3.9+ recommended for better security)
- **MySQL**: >= 8.0 (5.7+ supported but 8.0+ recommended)
- **Java**: >= 11 (for code execution sandbox)
- **Node.js**: >= 16.0.0 (for JavaScript execution)

### Additional Dependencies
- **Git**: Latest version
- **pip**: Latest version (comes with Python)
- **Virtual Environment**: `venv` or `virtualenv`

### Optional Tools
- **MySQL Workbench**: For database management
- **Postman**: For API testing
- **Docker**: For containerized deployment

### Version Check
```bash
python --version    # Should be >= 3.8.4
mysql --version     # Should be >= 8.0
java -version       # Should be >= 11
node --version      # Should be >= 16.0.0
```

## Fresh Installation

### 1. Clone Repository
```bash
git clone https://github.com/InteractiveTutorialSoftwareSystem/server.git
cd server
```

### 2. Create Virtual Environment
```bash
# Create virtual environment
python -m venv itss_env

# Activate virtual environment
# On Windows:
itss_env\Scripts\activate
# On macOS/Linux:
source itss_env/bin/activate
```

### 3. Install Dependencies
```bash
# Install all Python dependencies
pip install -r requirements.txt

# Install service-specific dependencies
pip install -r auth/requirements.txt
pip install -r tutorial/requirements.txt
```

### 4. Database Setup

#### MySQL Installation and Configuration
```bash
# Install MySQL 8.0+ 
# Follow installation guide: https://dev.mysql.com/doc/mysql-installation-excerpt/

# Create database
mysql -u root -p
CREATE DATABASE interactive_tutorial_system;
CREATE USER 'itss_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON interactive_tutorial_system.* TO 'itss_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 5. Environment Configuration

The system supports three storage configuration modes. Choose the `.env` file that matches your deployment needs:

#### Option A: Local Storage Only (Recommended for Development)
Create `.env` file based on `.env.local.example`:
```env
# Database Configuration
SQLALCHEMY_DATABASE_URI=mysql+mysqlconnector://itss_user:secure_password@localhost:3306/interactive_tutorial_system

# Security Configuration
APP_SECRET_KEY=your-super-secure-secret-key-min-32-characters

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Storage Configuration - Local Only
STORAGE_TYPE=local

# Service URLs
REACT_APP_TUTORIAL_URL=http://localhost:5002
REACT_APP_AUTH_URL=http://localhost:5001
```

#### Option B: AWS S3 Storage Only (Production)
Create `.env` file based on `.env.s3.example`:
```env
# Database Configuration
SQLALCHEMY_DATABASE_URI=mysql+mysqlconnector://itss_user:secure_password@localhost:3306/interactive_tutorial_system

# Security Configuration
APP_SECRET_KEY=your-super-secure-secret-key-min-32-characters

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Storage Configuration - S3 Only
STORAGE_TYPE=s3
ACCESS_KEY_ID=your-aws-access-key-id
SECRET_ACCESS_KEY=your-aws-secret-access-key
S3_BUCKET_NAME=itss-recordings-bucket
S3_LEARNER_BUCKET_NAME=itss-layouts-bucket

# Service URLs
REACT_APP_TUTORIAL_URL=http://localhost:5002
REACT_APP_AUTH_URL=http://localhost:5001
```

#### Option C: Hybrid Storage (S3 with Local Fallback)
Create `.env` file based on `.env.hybrid.example`:
```env
# Database Configuration
SQLALCHEMY_DATABASE_URI=mysql+mysqlconnector://itss_user:secure_password@localhost:3306/interactive_tutorial_system

# Security Configuration
APP_SECRET_KEY=your-super-secure-secret-key-min-32-characters

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Storage Configuration - Hybrid Mode
STORAGE_TYPE=auto
ACCESS_KEY_ID=your-aws-access-key-id
SECRET_ACCESS_KEY=your-aws-secret-access-key
S3_BUCKET_NAME=itss-recordings-bucket
S3_LEARNER_BUCKET_NAME=itss-layouts-bucket

# Service URLs
REACT_APP_TUTORIAL_URL=http://localhost:5002
REACT_APP_AUTH_URL=http://localhost:5001
```

### 6. Initialize Database Schema
```bash
python reset_schema.py
```

### 7. AWS S3 Setup (Optional but recommended)

#### Create S3 Buckets
```bash
# Using AWS CLI (install with: pip install awscli)
aws s3 mb s3://itss-recordings-bucket
aws s3 mb s3://itss-layouts-bucket

# Configure CORS for web access
aws s3api put-bucket-cors --bucket itss-recordings-bucket --cors-configuration file://cors-config.json
```

Example `cors-config.json`:
```json
{
    "CORSRules": [
        {
            "AllowedHeaders": ["*"],
            "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
            "AllowedOrigins": ["http://localhost:3000", "https://yourdomain.com"],
            "MaxAgeSeconds": 3000
        }
    ]
}
```

## Development Setup

### Project Structure
```
server/
├── auth/                 # Authentication service
│   ├── application.py    # Flask app for auth
│   ├── schema.py         # Auth database models
│   └── requirements.txt  # Auth-specific dependencies
├── tutorial/             # Tutorial service
│   ├── application.py    # Flask app for tutorials
│   ├── schema.py         # Tutorial database models
│   ├── requirements.txt  # Tutorial-specific dependencies
│   └── utils/            # Tutorial utilities & storage backends
│       ├── storage_backend.py # Hybrid storage system (S3 + Local)
│       ├── file_server.py    # Local file serving routes
│       └── local_storage.py  # Local storage utilities
├── storage/              # Local file storage (NEW)
│   ├── recordings/       # Audio & tutorial files
│   └── layouts/          # User layout preferences
├── start_servers.sh      # Quick start script (NEW)
├── stop_servers.sh       # Stop all servers script (NEW)
├── SERVER_COMMANDS.md    # Standardized commands guide (NEW)
├── reset_schema.py       # Database schema setup
├── requirements.txt      # Global dependencies
└── .env                  # Environment variables
```

### API Services
The backend consists of two microservices:

1. **Authentication Service** (Port 5001)
   - User registration and login
   - JWT token management
   - Google OAuth integration

2. **Tutorial Service** (Port 5002)
   - Tutorial CRUD operations
   - Code execution sandbox
   - File upload/download
   - Progress tracking

## Running the Application

### 🚀 Quick Start (Recommended)
```bash
# Start all backend servers with one command
cd /path/to/server
./start_servers.sh

# Stop all servers
./stop_servers.sh
```

### 📋 Manual Development Mode
All commands run from the server root directory:
```bash
cd /path/to/server

# Terminal 1: Start authentication service
PYTHONPATH=. python3 auth/application.py
# Runs on http://localhost:5001

# Terminal 2: Start tutorial service (with local storage)
PYTHONPATH=. STORAGE_TYPE=local python3 tutorial/application.py
# Runs on http://localhost:5002
```

### 🗂️ Storage Configuration
The system supports **three storage backends** for maximum flexibility:

#### 1. Local Storage (`STORAGE_TYPE=local`)
- **Best for**: Development, small deployments, cost optimization
- **Files stored in**: `storage/recordings/` and `storage/layouts/`
- **Advantages**: No AWS costs, faster access, simple setup
- **Use when**: Developing locally or want to avoid cloud costs

#### 2. AWS S3 Storage (`STORAGE_TYPE=s3`)
- **Best for**: Production, distributed teams, scalability
- **Files stored in**: AWS S3 buckets configured in `.env`
- **Advantages**: Scalable, distributed access, cloud backup
- **Use when**: Production deployment or distributed development

#### 3. Hybrid Mode (`STORAGE_TYPE=auto`)
- **Best for**: Migration scenarios, high availability
- **Behavior**: Tries S3 first, automatically falls back to local storage
- **Advantages**: Seamless migration, fault tolerance
- **Use when**: Migrating from S3 to local or want redundancy

#### Configuration Examples:
```bash
# Local only (development)
STORAGE_TYPE=local

# S3 only (production)  
STORAGE_TYPE=s3
ACCESS_KEY_ID=your-aws-access-key
SECRET_ACCESS_KEY=your-aws-secret-key
S3_BUCKET_NAME=itss-recordings-bucket
S3_LEARNER_BUCKET_NAME=itss-layouts-bucket

# Hybrid (migration/fallback)
STORAGE_TYPE=auto
# Include both local and S3 config above
```

### 🏭 Production Mode
```bash
# Using gunicorn for production
pip install gunicorn

# Start from server root directory
cd /path/to/server

# Start auth service
PYTHONPATH=. gunicorn --bind 0.0.0.0:5001 auth.application:app

# Start tutorial service  
PYTHONPATH=. STORAGE_TYPE=local gunicorn --bind 0.0.0.0:5002 tutorial.application:app
```

### Docker Deployment
```dockerfile
# Example Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5001 5002

CMD ["python", "auth/application.py"]
```

## Security Features

### Implemented Security Measures

#### Input Validation
```python
# Example validation functions
def validate_integer_input(value, min_val=None, max_val=None):
    """Validate integer input with bounds checking"""
    
def validate_uuid_input(uuid_string):
    """Validate UUID format and structure"""
    
def validate_string_input(text, max_length=None, allowed_chars=None):
    """Validate string input with length and content restrictions"""
```

#### SQL Injection Prevention
- ✅ **Parameterized Queries**: All database operations use SQLAlchemy ORM
- ✅ **Input Sanitization**: User inputs validated before database operations
- ✅ **Type Checking**: Strict parameter type validation
- ✅ **Bounds Validation**: Numeric inputs checked against min/max values

#### Code Injection Prevention
- ✅ **JSON Parsing**: Replaced `eval()` with secure `json.loads()`
- ✅ **Sandboxed Execution**: Code execution in controlled environment
- ✅ **Input Validation**: All code inputs sanitized and validated
- ✅ **Error Handling**: Secure error responses without system information

#### Authentication Security
- ✅ **JWT Tokens**: Secure token-based authentication
- ✅ **Password Hashing**: Argon2 password hashing
- ✅ **OAuth Integration**: Google OAuth 2.0 support
- ✅ **Session Management**: Secure session handling

### Security Best Practices
- Environment variables for sensitive configuration
- Secure HTTP headers in production
- Regular dependency updates
- Input validation at API boundaries
- Proper error handling without information disclosure

## Database Schema

The Entity Relationship diagram shows the interactions between database tables:

![Interactive Tutorial System ER Diagram](https://mermaid.ink/img/eyJjb2RlIjoiZXJEaWFncmFtXG5cblVTRVIgfHwtLW98IFVTRVItQVVUSCA6IGhhc1xuVVNFUiB8fC0tb3wgVVNFUi1PQVVUSCA6IGhhc1xuXG5VU0VSIHx8LS1veyBUVVRPUklBTCA6IGNyZWF0ZXNcblxuVFVUT1JJQUwgfHwtLW97IFRVVE9SSUFMLVNFQ1RJT04gOiBoYXNcblxuVVNFUiB8fC0tb3sgVVNFUi1UVVRPUklBTC1TVEFURSA6IGNyZWF0ZXNcblRVVE9SSUFMIHx8LS1veyBVU0VSLVRVVE9SSUFMLVNUQVRFIDogaGFzIiwibWVybWFpZCI6IntcbiAgXCJ0aGVtZVwiOiBcImRlZmF1bHRcIlxufSIsInVwZGF0ZUVkaXRvciI6dHJ1ZSwiYXV0b1N5bmMiOnRydWUsInVwZGF0ZURpYWdyYW0iOnRydWV9)

### Core Tables

#### User Table
Stores user account information and roles.

|Column Name|Data Type|Constraints|Description|
|-----------|---------|-----------|-----------|
|id|Integer|PRIMARY KEY|Unique user identifier|
|name|String(320)|NOT NULL|User's display name|
|picture|String(320)|NULL|Profile picture URL|
|roles|String(15)|NOT NULL|User permissions (author/learner)|
|current_role|String(7)|NULL|Active role session|

#### Tutorial Table
Stores tutorial metadata and structure.

|Column Name|Data Type|Constraints|Description|
|-----------|---------|-----------|-----------|
|id|String(36)|PRIMARY KEY|UUID identifier|
|name|String(320)|NOT NULL|Tutorial title|
|language|String(100)|NOT NULL|Programming language|
|sequence|TEXT|NULL|Section ordering (JSON)|
|userid|Integer|FOREIGN KEY|Author's user ID|
|start_date|DateTime|NULL|Publication date|
|end_date|DateTime|NULL|Expiration date|

#### TutorialSection Table
Stores individual tutorial section content.

|Column Name|Data Type|Constraints|Description|
|-----------|---------|-----------|-----------|
|id|String(36)|PRIMARY KEY|UUID identifier|
|name|String(320)|NOT NULL|Section title|
|code_content|TEXT|NULL|Code content|
|code_input|TEXT|NULL|Input examples|
|description|TEXT|NULL|Section description|
|tutorial_id|String(36)|FOREIGN KEY|Parent tutorial ID|
|tutorial_type|String(20)|NULL|'Code' or 'Question'|
|recording|TEXT|NULL|Audio recording data|
|question|TEXT|NULL|Quiz questions (JSON)|

## 🗄️ Hybrid Storage System

### Overview
The system now supports both **AWS S3** and **Local File Storage** with automatic migration capabilities:

- **Hybrid Backend**: Seamlessly switch between S3 and local storage
- **Migration Tools**: One-click migration from S3 to local storage
- **Cost Optimization**: Reduce AWS costs by using local storage
- **Performance**: Faster file access with local storage
- **Reliability**: Local backup of all S3 data

### Storage Types
```bash
# Environment variable options
STORAGE_TYPE=local    # Use local file storage only
STORAGE_TYPE=s3       # Use AWS S3 storage only  
STORAGE_TYPE=auto     # Auto-detect (tries S3 first, falls back to local)
```

### Migration Commands
The migration tools are located in the `docs/` folder:

```bash
# Migrate all S3 files to local storage
python3 docs/migrate_s3_to_local_full.py

# Migrate specific tutorials listed in target_tutorials.json
python3 docs/migrate_specific_tutorials.py

# Test local storage backend health
python3 docs/test_local_storage.py

# View migration reports
cat docs/migration_report_*.json
```

#### Migration Process:
1. **Backup**: Always backup your database before migration
2. **Test**: Run `docs/test_local_storage.py` to verify local storage works
3. **Migrate**: Use appropriate migration script for your needs
4. **Verify**: Check migration reports for any failed transfers
5. **Switch**: Update `STORAGE_TYPE` in `.env` after successful migration

### Local Storage Structure
```
storage/
├── recordings/                    # Tutorial recordings and files
│   └── [tutorial-section-uuid]/
│       ├── recording.wav          # Audio recording
│       ├── description.md         # Section description  
│       ├── keystroke.json         # Keystroke data
│       ├── consoleAction.json     # Console interactions
│       ├── layoutAction.json      # Layout changes
│       └── transcript.json        # Audio transcript
└── layouts/                       # User layout preferences
    └── [user-id]/
        └── [tutorial-id]/
            ├── author/
            └── learner/
```

## AWS S3 Configuration

### Bucket Structure

#### Recording Bucket (`S3_BUCKET_NAME`)
Stores tutorial section recordings and metadata:

```
tutorial-section-uuid/
├── code_content.txt      # Code content
├── description.md        # Section description
├── recording.wav         # Audio recording
├── keystroke.json        # Keystroke data
├── consoleAction.json    # Console interactions
├── layoutAction.json     # Layout changes
├── scrollAction.json     # Scroll events
├── selectAction.json     # Text selections
└── transcript.json       # Audio transcript
```

#### Layout Bucket (`S3_LEARNER_BUCKET_NAME`)
Stores user-customized layouts:

```
user-id/
└── tutorial-id/
    ├── author/
    │   └── layout.json   # Author's layout
    └── learner/
        └── layout.json   # Learner's layout
```

### S3 Security Configuration
- **Bucket Policies**: Restrict access to authenticated users
- **CORS Configuration**: Allow frontend domain access
- **Encryption**: Enable server-side encryption
- **Versioning**: Enable for data protection

## API Documentation

### Authentication Endpoints (Port 5001)

#### POST `/auth/register`
Register a new user account.
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "secure_password",
  "roles": "author,learner"
}
```

#### POST `/auth/login`
Authenticate user and return JWT token.
```json
{
  "email": "john@example.com",
  "password": "secure_password"
}
```

#### GET `/auth/protected`
Validate JWT token and return user information.
```bash
Authorization: Bearer <jwt_token>
```

### Tutorial Endpoints (Port 5002)

#### GET `/tutorials`
Retrieve all tutorials for the authenticated user.

#### POST `/tutorial/create`
Create a new tutorial.
```json
{
  "name": "Python Basics",
  "language": "python",
  "description": "Learn Python fundamentals"
}
```

#### GET `/tutorial/<tutorial_id>`
Retrieve specific tutorial details.

#### POST `/tutorial_section/create`
Create a new tutorial section.

#### POST `/code/execute`
Execute code in sandboxed environment.
```json
{
  "language": "python",
  "code": "print('Hello, World!')",
  "input": ""
}
```

### Error Handling
All endpoints return consistent error responses:
```json
{
  "error": "Error description",
  "status": "error",
  "code": 400
}
```

## Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Check MySQL service status
sudo systemctl status mysql

# Test database connection
mysql -u itss_user -p -h localhost interactive_tutorial_system
```

#### Import Errors
```bash
# Ensure you're running from server root directory
cd /path/to/server

# Check current directory structure
ls -la

# Reinstall dependencies
pip install --upgrade -r requirements.txt
pip install --upgrade -r auth/requirements.txt
pip install --upgrade -r tutorial/requirements.txt

# Run with explicit PYTHONPATH
PYTHONPATH=. python3 auth/application.py
```

#### Port Conflicts
```bash
# Check which ports are in use
netstat -tlnp | grep :5001
netstat -tlnp | grep :5002

# Change ports in application.py files if needed
```

#### JWT Token Issues
```bash
# Verify secret key configuration
python -c "from auth.application import app; print(app.config['JWT_SECRET_KEY'])"
```

#### S3 Access Issues
```bash
# Test AWS credentials
aws sts get-caller-identity

# Check bucket permissions
aws s3api get-bucket-policy --bucket your-bucket-name
```

### Performance Optimization

#### Database Optimization
- **Indexing**: Ensure proper indexes on frequently queried columns
- **Connection Pooling**: Configure SQLAlchemy connection pool
- **Query Optimization**: Use SQLAlchemy's query optimization features

#### Code Execution Performance
- **Sandboxing**: Implement Docker-based code execution for better isolation
- **Resource Limits**: Set memory and CPU limits for code execution
- **Caching**: Implement caching for frequently executed code

## Development Guidelines

### Code Quality Standards
- **PEP 8**: Follow Python style guidelines
- **Type Hints**: Use type annotations for better code documentation
- **Error Handling**: Implement comprehensive error handling
- **Logging**: Use structured logging for debugging and monitoring
- **Testing**: Write unit tests for all new functionality

### Security Guidelines
- **Input Validation**: Validate all user inputs at API boundaries
- **SQL Injection**: Always use parameterized queries
- **Authentication**: Implement proper authentication for all endpoints
- **Authorization**: Check user permissions for resource access
- **Sensitive Data**: Never log sensitive information

### Contributing Workflow
1. Create feature branch from `main`
2. Implement changes with proper tests
3. Run security checks and validate inputs
4. Submit pull request with detailed description
5. Code review and security audit
6. Merge after approval

## Deployment

### Production Checklist
1. **Environment Variables**: Set all production values
2. **Database**: Configure production MySQL instance
3. **SSL/TLS**: Enable HTTPS for all API endpoints
4. **Monitoring**: Set up application monitoring
5. **Logging**: Configure centralized logging
6. **Backups**: Set up automated database backups
7. **Security**: Review and test all security measures

### Docker Deployment
```yaml
# docker-compose.yml
version: '3.8'
services:
  auth:
    build: .
    command: gunicorn --bind 0.0.0.0:5001 auth.application:app
    ports:
      - "5001:5001"
    environment:
      - FLASK_ENV=production
    
  tutorial:
    build: .
    command: gunicorn --bind 0.0.0.0:5002 tutorial.application:app
    ports:
      - "5002:5002"
    environment:
      - FLASK_ENV=production
```

## Monitoring and Maintenance

### Health Checks
Implement health check endpoints for monitoring:
```python
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': datetime.utcnow()}
```

### Performance Monitoring
- **Application Metrics**: Response time, error rate, throughput
- **Database Metrics**: Connection pool, query performance
- **System Metrics**: CPU, memory, disk usage
- **Security Metrics**: Failed login attempts, suspicious requests

## References
Ouh, Eng Lieh, Benjamin Kok Siew Gan, and David Lo. "ITSS: Interactive Web-Based Authoring and Playback Integrated Environment for Programming Tutorials." Proceedings of the 2022 ACM Conference on International Computing Education Research-Volume 1. 2022.
[📄 Research Paper](https://dl.acm.org/doi/10.1145/3510456.3514142)

---

**Repository**: [InteractiveTutorialSoftwareSystem/server](https://github.com/InteractiveTutorialSoftwareSystem/server)  
**License**: [MIT](LICENSE)  
**Maintained by**: Interactive Tutorial Software System Team