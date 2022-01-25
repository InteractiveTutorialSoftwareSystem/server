# Interactive Tutorial System (Backend)


# Table of contents
1. [Introduction](#introduction)
2. [Technologies Required](#technologies_required)
    1. [Installation](#installation)
        1. [Python](#install_python)
        2. [MySQL](#install_mysql)
        3. [Java](#install_java)
        4. [Node.js](#install_node)
    2. [Version Check](#version_check)
        1. [Python](#version_check_python)
        2. [MySQL](#version_check_mysql)
        3. [Java](#version_check_java)
        4. [Node.js](#version_check_node)
3. [Configuration & Setting Up](#setup)
    1. [Cloning Repository](#cloning_repository)
    2. [Virtual Environment](#virtual_environment)
    3. [Installing Dependencies](#install_dependencies)
    4. [Environment File](#environment_file)
    5. [Database Setup](#database_setup)
4. [Running the Application](#run_app)
5. [Database Schema](#database_schema)
    1. [User](#db_user)
    2. [UserAuth](#db_userauth)
    3. [UserOauth](#db_useroauth)
    4. [Tutorial](#db_tutorial)
    5. [TutorialSection](#db_tutorialsection)
    6. [UserTutorialState](#db_usertutorialstate)
6. [S3 Configurations](#s3_configurations)
    1. [Recording Bucket](#recording_bucket)
    2. [Layout Bucket](#layout_bucket)

## Introduction <a name="introduction"></a>
This repository contains the backend development of the Interactive Tutorial System project.

Please note that the backend should be run concurrently with the frontend of the project, which can be found [here](https://github.com/InteractiveTutorialSystem/client). Do ensure that you have all the [required technologies](#technologies_required) installed on your machine before proceeding with the [setup](#setup).


## Technologies Required <a name="technologies_required"></a>
This project is created with the following technologies and versions.
- [Python] : >= 3.8.4
- [MySQL] : >= 5.7.31
- [Java] : >= 11
- [Node.js] : >= 10.16

If you already have these technologies installed in your machine, follow the steps in the [Version Check](#version_check) segment to check the version installed in your machine. If you have yet to install any, please refer to the [Installation](#installation) segment.


### Installation <a name="installation"></a>
The following are methods to install the required technologies, namely Python.


#### Python <a name="install_python"></a>
Refer to this [link](https://realpython.com/installing-python/?__cf_chl_captcha_tk__=8549f8a6c2021f8fe00b6b4260fbcc48801159ad-1590127799-0-AbUuziuPCvsluadKh82TqHEZw0FoJX7V6KaEyYAz8sgLXaH4Ih75Oj8PV-ZocYrH-hN-t7ikn8xZ2pCtblsIpEnwwmO-mN_VVFOe4FMz4cXWf55qVJdPOl87FQiyTqJT7V-HLyF4HvevxDcGGqmGnQBFTsRMm8vBH2-4Zu8Nm1mC8XRpBEhdaGfZbXwwAhH0mrNfd_kutl-_PXR7-uX8ZDz9it6wf-issUUWZpU9A99n1V7U7qZtF-ySMN_zAMjQbEHeBOOTzmRZUFD51OMF5Ly8ZAZwlIv0Nr8ifwVAr_B1clVGm6TqlmBPJwYSImEOk-mAF0TWMhMqsiGLU-XyiqbPpXri_R1XgslIx1s1iQ3qcP7QfM2qOxeQURTw3fH3XDguT5tYsFkq5eO6kOKEC7p_P3GDg-B8VKvMdj3fcFaoGr1zbBlnWTpZBDZCqWNVJAwlWwqNwA20nG-U2MzPFX7uMGUM8BPhuGmi-8hbUyIoYLv60poBK14C0RCrZo6gjpDSjDDKRjgps6B7rFb1XnE) for instructions on how to install the latest version of Python.


#### MySQL <a name="install_mysql"></a>
Refer to this [link](https://dev.mysql.com/doc/mysql-getting-started/en/) for instructions on how to install the latest version of MySQL. Do install the MySQL server as well.

Alternatively, you can install a solution stack that includes MySQL, such as WampServer.


#### Java <a name="install_java"></a>
Refer to this [link](https://docs.oracle.com/en/java/javase/16/install/overview-jdk-installation.html) for instructions on how to install Oracle JDK 16. 


#### Node.js <a name="install_node"></a>
Download the installation file from [link](https://nodejs.org/en/) and install Node.js. To avoid any errors, installing the latest Long Term Support version is recommended. Ensure that npm is installed as well.


### Version Check <a name="version_check"></a>
The following are methods you can use to check the version of your current technologies.


#### Python <a name="version_check_python"></a>
Open a command-line application and type in **either one** of the following commands:
```
python --version OR
python -V
```
If your current version of Python is older than **3.8.4**, [download](https://www.python.org/downloads/) and [install](#install_python) the latest version.  


#### MySQL <a name="version_check_mysql"></a>
There are several ways to check your MySQL version, including using the MySQL Command-Line Client, MySQL Workbench and phpMyAdmin.

Open a MySQL Client and type in **either one** of the following commands:
```
SELECT version(); OR
SELECT @@version;
```
If your current version of MySQL is older than **5.7.31**, [install](#install_mysql) the latest version.


#### Java <a name="version_check_java"></a>
Open a command-line application and type in the following command:
```
java -version
```
If your current version of Java is older than **11**, [install](#install_java) the latest version.  


#### Node.js <a name="version_check_node"></a>
Open a command-line application and type in **either one** of the following commands:
```
node --version OR
node -v
```
If your current version of Node.js is older than **10.16.0**, [install](#install_node) the latest Long Term Support version.


## Configuration & Setup <a name="setup"></a>
After you have installed the required technologies, you can proceed to setup the project. If you have yet to install/update the required technologies, please proceed the [Technologies Required](#technologies_required) section to do so.


### Cloning Repository <a name="cloning_repository"></a>
Refer to this [link](https://docs.github.com/en/github/creating-cloning-and-archiving-repositories/cloning-a-repository-from-github/cloning-a-repository) for instructions on how to clone this repository. You can clone the repository using a command-line application or GitHub Desktop.

Alternatively, you can [download](https://github.com/InteractiveTutorialSystem/server/archive/refs/heads/main.zip) the repository.


### Virtual Environment <a name="virtual_environment"></a>
A virtual environment may be created to keep dependencies required by different projects separate. Refer to this [link](https://flask.palletsprojects.com/en/2.0.x/installation/#virtual-environments) for instructions on how to create and activate a virtual environment. 


### Installing Dependencies <a name="install_dependencies"></a>
To install the dependencies, run the following command from the root folder.
```
pip install -r requirements.txt
```


### Environment File <a name="environment_file"></a>
Create a `.env` file with the following fields in the root folder:
```
SQLALCHEMY_DATABASE_URI=''

APP_SECRET_KEY=''

GOOGLE_CLIENT_ID=''
GOOGLE_CLIENT_SECRET=''

ACCESS_KEY_ID=''
SECRET_ACCESS_KEY=''

S3_BUCKET_NAME=''
S3_LEARNER_BUCKET_NAME=''

REACT_APP_TUTORIAL_URL=''
```
Enter the database URI that should be used for the MySQL connection. An example could be `"mysql+mysqlconnector://root@localhost:3306/interactive_tutorial_system"` where a database named `'interactive_tutorial_system'` is created.

Enter a secret key for authentication. This can be any string and it will be used in the encryption and decyption of passwords.

Obtain the Google OAuth 2.0 Credentials from the [Google API Console](https://console.developers.google.com/). For the Authorised JavaScript origins, enter the domain of the application. This could be `http://localhost:3000`. For the Authorised redirect URIs, enter the URIs for OAuth registration and login. These could be `http://localhost:5001/oauth/register` and `http://127.0.0.1:5001/oauth/login`.

Obtain the AWS Credentials from the [AWS Management Console](https://aws.amazon.com/console/). Setup two S3 Buckets. More details on the file structure in the S3 Buckets can be found in the [S3 Configurations](#s3_configurations) section.

Enter the URLs of the backend Flask applications. An example could be `"http://localhost:5002"` for the `REACT_APP_TUTORIAL_URL`.


### Database Setup <a name="database_setup"></a>
To setup the database, run the following command from the root folder.
```
python reset_schema.py
```


## Running the Application <a name="run_app"></a>
Your setup is now configured and ready to run. Start your flask applications by running the following code in the respective folders:
```
python application.py
```

The backend has now been successfully setup and ready to be used concurrently with the frontend.

Once you are done, press ```Ctrl``` + ```C``` to **deactivate** the application servers. 


## Database Schema <a name="database_schema"></a>
The Entity Relationship diagram below shows the interactions between the database tables utilised in this project.

![Interactive Tutorial System ER Diagram](https://mermaid.ink/img/eyJjb2RlIjoiZXJEaWFncmFtXG5cblVTRVIgfHwtLW98IFVTRVItQVVUSCA6IGhhc1xuVVNFUiB8fC0tb3wgVVNFUi1PQVVUSCA6IGhhc1xuXG5VU0VSIHx8LS1veyBUVVRPUklBTCA6IGNyZWF0ZXNcblxuVFVUT1JJQUwgfHwtLW97IFRVVE9SSUFMLVNFQ1RJT04gOiBoYXNcblxuVVNFUiB8fC0tb3sgVVNFUi1UVVRPUklBTC1TVEFURSA6IGNyZWF0ZXNcblRVVE9SSUFMIHx8LS1veyBVU0VSLVRVVE9SSUFMLVNUQVRFIDogaGFzIiwibWVybWFpZCI6IntcbiAgXCJ0aGVtZVwiOiBcImRlZmF1bHRcIlxufSIsInVwZGF0ZUVkaXRvciI6dHJ1ZSwiYXV0b1N5bmMiOnRydWUsInVwZGF0ZURpYWdyYW0iOnRydWV9)

The remainder of this section will detail the tables and fields used.


### User <a name="db_user"></a>
The User table stores the details of users that will use the application.

|Column Name|Data Type|Null Value|Description|
|-|-|-|-|
|id|Integer|Not Null|PK|
|name|String(320)|Not Null|User's name|
|picture|String(320)|Null|User's profile picture URL|
|roles|String(15)|Not Null|User's registered roles|
|current_role|String(7)|Null|User's current role<ol><li>author</li><li>learner</li></ol>|


### UserAuth <a name="db_userauth"></a>
The UserAuth table stores the authentication details of a user utilizing the form method of registering and logging in.

Note: A UserAuth can have one User only.

|Column Name|Data Type|Null Value|Description|
|-|-|-|-|
|id|Integer|Not Null|PK|
|email|String(320)|Not Null|User's email address|
|password|String(131)|Not Null|User's encrypted password|
|user_id|Integer|Not Null|FK to [user](#db_user).id


### UserOauth <a name="db_useroauth"></a>
The UserOauth table stores the authentication details of a user utilizing the Google OAuth method of registering and logging in.

Note: A UserOauth can have one User only.

|Column Name|Data Type|Null Value|Description|
|-|-|-|-|
|google_id|String(21)|Not Null|PK|
|email|String(320)|Not Null|User's email address|
|user_id|Integer|Not Null|FK to [user](#db_user).id


### Tutorial <a name="db_tutorial"></a>
The Tutorial table stores the tutorial details.

Note: A Tutorial can have one User only.

|Column Name|Data Type|Null Value|Description|
|-|-|-|-|
|id|String(36)|Not Null|PK|
|name|String(320)|Not Null|Tutorial's name|
|language|String(100)|Not Null|Tutorial's programming language|
|sequence|String(10000)|Null|Tutorial's TutorialSection order|
|userid|Integer|Null|Tutorial author's user id|
|start_date|DateTime|Null|Tutorial start date|
|end_date|DateTime|Null|Tutorial end date|


### TutorialSection <a name="db_tutorialsection"></a>
The TutorialSection table stores the details of each TutorialSection.

Note: A TutorialSection can have one Tutorial only.

|Column Name|Data Type|Null Value|Description|
|-|-|-|-|
|id|String(36)|Not Null|PK|
|name|String(320)|Not Null|TutorialSection's name|
|code_input|String(10000)|Null|TutorialSection's last code input|
|language|String(100)|Null|TutorialSection's programming language|
|tutorial_id|String(36)|Not Null|FK to [tutorial](#db_tutorial).id|
|frequent_word|String(1000)|Null|Tutorial Section's frequent words from audio transcript|
|tutorial_type|String(320)|Null|Tutorial Type<ol><li>Code</li><li>Question</li></ol>|
|duration|Integer|Null|TutorialSection Duration|


### UserTutorialState <a name="db_usertutorialstate"></a>
The UserTutorialState table stores the User's last accessed TutorialSection for each Tutorial.

|Column Name|Data Type|Null Value|Description|
|-|-|-|-|
|user_id|Integer|Not Null|PK, FK to [user](#db_user).id|
|tutorial_id|String(36)|Not Null|PK, FK to [tutorial](#db_tutorial).id|
|last_page|Integer|Null|User's last accessed page number for that Tutorial|


## S3 Configurations <a name="s3_configurations"></a>

### Recording Bucket <a name="recording_bucket"></a>
When an author saves a [TutorialSection](#db_tutorialsection), a universally unique identifier is generated and this id will be the TutorialSection's id. A folder of this id is created in the S3 Recording Bucket for storage and retrieval.

A TutorialSection of id `02fe5f9241da4f35ad25549c422da874` could have a directory tree as follows:

    02fe5f9241da4f35ad25549c422da874
    ├── code_content.txt
    ├── consoleAction.json
    ├── description.md
    ├── keystroke.json
    ├── layoutAction.json
    ├── recording.wav
    ├── scrollAction.json
    ├── selectAction.json
    └── transcript.json

### Layout Bucket <a name="layout_bucket"></a>
When an [User](#db_user) saves a [Tutorial](#db_tutorial) layout, the layout will be saved in the S3 Layout Bucket for storage and retrieval.

User `8191` saving a customsied layout of Tutorial id `78064898e50b45a48c8ed51cf9153986` as both an `author` and a `learner` will have a directory tree as follows:

    8191
    └── 78064898e50b45a48c8ed51cf9153986
        ├── author
        │   └── layout.json
        └── learner
            └── layout.json