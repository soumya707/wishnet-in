# -*- coding: utf-8 -*-

"""Initiate the application."""

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


# initiate app
app = Flask(__name__, instance_relative_config=True)


# load config
app.config.from_object('config')
app.config.from_pyfile('config.py')


# Custom access-based Admin Index
# class AdminHomeView(AdminIndexView):
#     @expose('/')
#     def index(self):
#         if not current_user.is_authenticated:
#             return redirect(url_for('index'))

#         return self.render('admin/index.html')


# initiate required objects
# setup DB
db = SQLAlchemy(app, query_class=CachingQuery)

# setup cache
cache = Cache(app)

# setup admin portal
admin = Admin(
    app,
    name='Admin',
    url='/admin',
    endpoint='admin',
    base_template='admin/master.html',
    template_mode='bootstrap3',
)

# setup DB migrate
migrate = Migrate(app, db)

# setup session storage
Session(app)


# import here to avoid cyclic import
from website import views
from website.models import BestPlans, Downloads, JobVacancy, FAQ, \
    RegionalOffices, Services, Ventures
from website.models import  BizPlan, FUPPlan, FTTHPlan, UnlimitedPlan
from website.security.models import Role, User
from website.security.models import CustomFileView, EditorModelView, \
    SuperuserModelView, UserModelView
from website.security.models import PortalView


# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)


path = op.join(op.dirname(__file__), 'static')


# add defined models as views to admin portal
admin.add_view(CustomFileView(path, '/static/', name='Static Files'))
admin.add_view(SuperuserModelView(User, db.session, category='Access'))
admin.add_view(SuperuserModelView(Role, db.session, category='Access'))
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
    return dict(
        admin_base_template=admin.base_template,
        admin_view=admin.index_view,
        h=admin_helpers,
        get_url=url_for
    )
