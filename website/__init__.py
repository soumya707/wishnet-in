# -*- coding: utf-8 -*-

"""Initiate the application."""

import os.path as op

from flask import Flask, url_for, redirect
from flask_admin import Admin, AdminIndexView, expose
from flask_admin import helpers as admin_helpers
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore


# initiate app
app = Flask(__name__, instance_relative_config=True)


# load config
app.config.from_object('config')
app.config.from_pyfile('config.py')


# Custom access-based Admin Index
class AdminHomeView(AdminIndexView):
    @expose('/')
    def index(self):
        if not current_user.is_authenticated:
            return redirect(url_for('index'))

        return self.render('admin/index.html')


# initiate required objects
db = SQLAlchemy(app)
admin = Admin(
    app,
    name='Admin',
    base_template='admin/master.html',
    # index_view=AdminHomeView(),
    template_mode='bootstrap3'
)
migrate = Migrate(app, db)


# import here to avoid cyclic import
from website import views
from website.models import BestPlans, Downloads, JobVacancy, FAQ, Services, \
    Ventures
from website.models import  BizPlan, FUPPlan, FTTHPlan, UnlimitedPlan
from website.security.models import Role, User
from website.security.models import CustomFileView, EditorModelView, \
    SuperuserModelView, UserModelView


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
admin.add_view(EditorModelView(FAQ, db.session))
admin.add_view(EditorModelView(JobVacancy, db.session))


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
