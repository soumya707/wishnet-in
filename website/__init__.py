# -*- coding: utf-8 -*-

"""Initiate the application."""

import csv
import os.path as op

from flask import Flask, url_for, redirect
from flask_admin import Admin
from flask_admin import helpers as admin_helpers
from flask_migrate import Migrate
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy_caching import CachingQuery
from flask_caching import Cache
from flask_security import Security, SQLAlchemyUserDatastore
from passlib.totp import TOTP

from website.utils import AvailablePlans, retrieve_otp_secret


# initiate Flask application
app = Flask(__name__, instance_relative_config=True)

# load config
app.config.from_object('config')
app.config.from_pyfile('config.py')

# initiate required objects

# setup Flask-SQLAlchemy
db = SQLAlchemy(app, query_class=CachingQuery)

# setup Flask-Caching
cache = Cache(app)

# setup Flask-Admin
admin = Admin(
    app,
    name='Admin',
    url='/admin',
    endpoint='admin',
    base_template='admin/master.html',
    template_mode='bootstrap3',
)

# setup Flask-Migrate
migrate = Migrate(app, db)

# Setup Passlib TOTP
TotpFactory = TOTP.using(
    period=270,
    secrets=retrieve_otp_secret('website/otp_secrets.csv')
)

# setup Flask-Session
Session(app)

# get available plans
plans = AvailablePlans('website/plans_with_tariff.csv')

from website import views
from website.models import (
    BestPlans, CarouselImages, Downloads, JobVacancy, FAQ, RegionalOffices,
    Services, Ventures, BizPlan, FUPPlan, FTTHPlan, UnlimitedPlan)
from website.security.models import Role, User
from website.security.models import (
    CustomFileView, EditorModelView, SuperuserModelView)


# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)


path = op.join(op.dirname(__file__), 'static')


# add defined models as views to admin portal
admin.add_view(CustomFileView(path, '/static/', name='Static Files'))
admin.add_view(SuperuserModelView(User, db.session, category='Access'))
admin.add_view(SuperuserModelView(Role, db.session, category='Access'))
admin.add_view(EditorModelView(CarouselImages, db.session, category='Index'))
admin.add_view(EditorModelView(Services, db.session, category='Index'))
admin.add_view(EditorModelView(BestPlans, db.session, category='Index'))
admin.add_view(EditorModelView(Downloads, db.session, category='Index'))
admin.add_view(EditorModelView(Ventures, db.session, category='Index'))
admin.add_view(EditorModelView(UnlimitedPlan, db.session, category='Plans'))
admin.add_view(EditorModelView(FTTHPlan, db.session, category='Plans'))
admin.add_view(EditorModelView(BizPlan, db.session, category='Plans'))
admin.add_view(EditorModelView(FUPPlan, db.session, category='Plans'))
admin.add_view(EditorModelView(RegionalOffices, db.session, category='Info'))
admin.add_view(EditorModelView(FAQ, db.session, category='Info'))
admin.add_view(EditorModelView(JobVacancy, db.session, category='Info'))


# define a context processor for merging flask-admin's template context into the
# flask-security views.
@security.context_processor
def security_context_processor():
    """Use Flask-Admin's template."""
    return dict(
        admin_base_template=admin.base_template,
        admin_view=admin.index_view,
        h=admin_helpers,
        get_url=url_for
    )
