# Wish Net Pvt. Ltd. website

This repository contains the code and resources for the website.

## Repository organization

```
.
+-- config.py
+-- README.md
+-- run.py
+-- tox.ini
+-- instance
|   +-- config.py (contains instance specific config)
+-- website
|   +-- __init__.py
|   +-- forms.py (contains class definitions for forms)
|   +-- models.py (contains class definitions used in db)
|   +-- views.py (conatins routes)
|   +-- helpers.py (contains class definitions for MQ Sure API)
|   +-- static
|   |   +-- css
|   |   |   +-- style.css (custom CSS)
|   |   +-- img
|   |   |   +-- (contains images)
|   |   +-- js
|   +-- templates
|   |   +-- (contains HTML templates)
|   |   +-- admin
|   |   |   +-- (templates used for admin)
|   |   +-- security
|   |   |   +-- (templates used for security)
|   +-- security
|   |   +-- __init__.py
|   |   +-- models.py (contains models for Flask-Security)
```

## Initiating the application

### Basic setup

You need a fresh Python virtualenv before starting out. To ease the process, `pipenv` is used and hence the `Pipfile` in the project. Install `pipenv` for your platform if not installed. Once done, run the following in the project root:

``` shell
pipenv --python <path/to/python/binary> install
```

This will create a new virtualenv and also install the packages specified in `Pipfile`. Make sure you are able to run the following:

``` powershell
pipenv shell
```

### Configurations

To do a fresh start of the application, set the `FLASK_APP` environment variable to `website/__init__.py`. This will let you use the `flask` command line command later on. Then create a directory called `instance` in the root of the project. Once inside the `instance` directory, create a file called `config.py` and put specific configurations. The following might serve as an example:

``` python

# Flask
ENV = 'development'
DEBUG = True
SECRET_KEY = '782f8d8084fdc57c85140853f6e52e78'
TEMPLATES_AUTO_RELOAD = True

# SQLAlchemy
SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/website.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Flask-Admin
FLASK_ADMIN_SWATCH = 'flatly'

# Flask-Security
SECURITY_URL_PREFIX = '/admin'
SECURITY_PASSWORD_HASH = 'pbkdf2_sha512'
SECURITY_PASSWORD_SALT = 'ATGUOHAELKiubahiughaerGOJAEGj'

# Flask-Security URLs and Views
SECURITY_LOGIN_URL = '/login/'
SECURITY_LOGOUT_URL = '/logout/'
SECURITY_REGISTER_URL = '/register/'
SECURITY_POST_LOGIN_VIEW = '/admin/'
SECURITY_POST_LOGOUT_VIEW = '/admin/'
SECURITY_POST_REGISTER_VIEW = '/admin/'

# Flask-Security Feature Flags
SECURITY_REGISTERABLE = True

```

### Database setup

After plugging the proper configurations, you need to connect to the database. You can either create a new database or connect to an existing database. To create a new database with clean tables, you need to start the Python interpreter in the project root and execute the following commands:

``` python-console
from website import db
db.create_all()
```

This will create all the necessary tables.

### Creating admin access

Before you do anything else, it is necessary to generate a `admin` superuser so that you can create and update contents of the website. To generate the same head over to the webserver in the browser and append `/admin` to the end of the URL. This will open the admin portal and is customizable via the configurations.

## Maintenance

### Database migrations

Before performing any migrations, run the following command to generate a `migrations` folder and keep that in version control:

``` shell
flask db init --multidb
```

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
