# Wish Net Pvt. Ltd. website

This repository contains the code and resources for the website.

## Repository organization

```
.
+-- Pipfile
+-- config.py
+-- README.md
+-- tox.ini
+-- celeryconfig.py (contains configurations for Celery)
+-- instance/
|   +-- config.py (contains instance specific config)
+-- migrations/ (contains files for database migrations)
+-- website/
|   +-- __init__.py
|   +-- forms.py (contains class definitions for forms)
|   +-- models.py (contains class definitions used for database)
|   +-- views.py (conatins routes)
|   +-- utils.py (contains helper class definitions)
|   +-- tasks.py (contains task definitions for Celery)
|   +-- mqs_api.py (contains class definitions for MQ Sure API)
|   +-- location_for_new_connection.csv (contains available locations for new connection)
|   +-- plans_with_tariff.csv (contains all the plans including metadata and tariff)
|   +-- security/
|   |   +-- __init__.py
|   |   +-- models.py (contains class definitions for Flask-Security)
|   +-- static
|   |   +-- css/
|   |   |   +-- style.css (custom CSS)
|   |   +-- img/ (contains images)
|   |   +-- assets/ (contains downloadable material)
|   +-- templates/ (contains HTML templates)
|   |   +-- admin/ (templates used for admin)
|   |   +-- security/ (templates used for security)

```

## Initiating the application

### Basic setup

You need a fresh Python virtualenv before starting out. To ease the process, `pipenv` is used and hence the `Pipfile` in the project. Install `pipenv` for your platform if not installed. Once done, run the following in the project root:

``` shell
$ pipenv --python <path/to/python/binary> install
```

This will create a new virtualenv and also install the packages specified in `Pipfile`. Make sure you are able to run the following:

``` shell
$ pipenv shell
```

### Configurations

To do a fresh start of the application, set the `FLASK_APP` environment variable to `website/__init__.py`. This will let you use the `flask` command line command later on. Then create a directory called `instance` in the root of the project. Once inside the `instance` directory, create a file called `config.py` and put specific configurations. The following might serve as an example:

``` python

# Flask
ENV = 'development'
DEBUG = True
SECRET_KEY = '...'
TEMPLATES_AUTO_RELOAD = True

# SQLAlchemy
SQLALCHEMY_DATABASE_URI = '...'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Flask-Admin
FLASK_ADMIN_SWATCH = 'flatly'

# Flask-Security
SECURITY_URL_PREFIX = '/admin'
SECURITY_PASSWORD_HASH = '...'
SECURITY_PASSWORD_SALT = '...'

# Flask-Security URLs and Views
SECURITY_LOGIN_URL = '/login/'
SECURITY_LOGOUT_URL = '/logout/'
SECURITY_REGISTER_URL = '/register/'
SECURITY_POST_LOGIN_VIEW = '/admin/'
SECURITY_POST_LOGOUT_VIEW = '/admin/'
SECURITY_POST_REGISTER_VIEW = '/admin/'

# Flask-Security Feature Flags
SECURITY_REGISTERABLE = True
SECURITY_CONFIRMABLE = False

# Flask-Security Miscellaneous
SECURITY_SEND_REGISTER_EMAIL = False

# Flask-Mail
MAIL_DEBUG = False
MAIL_SUPPRESS_SEND = False
MAIL_SERVER = '...'
MAIL_PORT = 465
MAIL_USE_TLS = False
MAIL_USE_SSL = True
MAIL_USERNAME = '...'
MAIL_PASSWORD = '...'
MAIL_DEFAULT_SENDER = '...'

# Flask-Session
SESSION_TYPE = '...'
SESSION_FILE_DIR = '...'

# Flask-Caching
CACHE_TYPE = '...'
CACHE_DIR = '...'

# reCAPTCHA support
RECAPTCHA_PUBLIC_KEY = '...'
RECAPTCHA_PRIVATE_KEY = '...'

# MQS SOAP API credentials
MQS_URL = '...'
MQS_USER = '...'
MQS_PWD = '...'
MQS_EXT = '...'

# Paytm credentials
PAYTM_MID = '...'
PAYTM_WEBSITE = '...'
PAYTM_MKEY = '...'
PAYTM_WEBNAME = '...'
PAYTM_INDUSTRYTYPE = '...'
PAYTM_CHANNELID = '..'
PAYTM_CALLBACKURL = '...'
PAYTM_TXNURL = '...'

# Razorpay credentials
RAZORPAY_KEY = "..."
RAZORPAY_SECRET = "..."

```

Now, create a `celeryconfig.py` module which would hold the configurations for Celery. An example configuration can be like so:

``` python

# Broker URL
broker_url = '...'

# Modules to import when Celery worker starts
imports = ('website.tasks', )

# Result backend
result_backend = '...'

```

### Database setup

After plugging the proper configurations, you need to connect to the database. You can either create a new database or connect to an existing database. To create a new database with clean tables, you need to start the Python interpreter in the project root and execute the following commands:

``` python-console
>>> from website import db
>>> db.create_all()
```

This will create all the necessary tables.

### Creating admin access

Before you do anything else, it is necessary to generate a `admin` superuser so that you can create and update contents of the website. To generate the same head over to the webserver in the browser and append `/admin` to the end of the URL. This will open the admin portal and is customizable via the configurations.

#### Default admin credentials

By default, the application has the following admin credentials you can use to log in the admin portal:

1. Superuser:

``` text
Username: websiteadmin@wnpl.co.in
Password: w3bs1te@dm1n
```

2. Editor:

``` text
Username: websiteeditor@wnpl.co.in
Password: w3bs1teed1t0r
```

These credentials won't work if you are setting up the database from scratch.

### Setting up the system for deployment

To successfully run the application, make sure to install, configure and daemonize the following:

1. Nginx (works as reverse proxy)
2. SQL database server of your choice
3. Redis (recommended for cache and session storage)
4. RabbitMQ (recommended for use as Message Queue for running asynchronous operations)
5. Terminal multiplexer (tmux, GNU screen)

Also, install other packages as required by the system's OS.

#### Running in test mode

To check if the test server works, run:

``` shell
(virtualenv) $ flask db run
```

#### Running in production mode

After getting the test server running, when you are ready for deployment, be sure to use gunicorn as the server for the application. Gunicorn is production-ready HTTP WSGI server and plays really well with Nginx. You should have gunicorn installed in your virtualenv and you can initiate the server using the following command:

``` shell
(virtualenv) $ gunicorn website:app
```

Also, make sure to configure gunicorn as per your needs.

## Maintenance

### Database migrations

Before performing any migrations, run the following command to generate a `migrations` folder and keep that in version control:

``` shell
flask db init --multidb
```

You don't need to run the above if you have existing databases.

To perform database migrations, run the following command in the project root:

``` shell
flask db migrate
```

If new changes are detected, it will generate a new Python script for upgrade/downgrade using `alembic`. Open the latest generated script to check if everything is in order. Once done, run:

``` shell
flask db upgrade
```

### Content

To add/remove content on the website, head over to the admin portal and sign in either as `superuser` or `editor` (recommended). Once in the portal, you'll find the necessary options to change the contents.
