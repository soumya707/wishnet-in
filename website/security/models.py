# -*- coding: utf-8 -*-

""" Define models for Flask-Security."""

from datetime import datetime

from flask_admin.contrib.fileadmin import FileAdmin
from flask_admin.contrib.sqla import ModelView
from flask_security import RoleMixin, UserMixin, current_user

from website import db


# Flask-Security User and Role models
roles_users = db.Table(
    'roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id')),
    info={'bind_key': 'users'}
)


class Role(db.Model, RoleMixin):
    """Define the role for users."""

    __bind_key__ = 'users'

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __str__(self):
        return self.name


class User(db.Model, UserMixin):
    """Define the user."""

    __bind_key__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime(),
                             default=datetime.now().astimezone())
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    def __str__(self):
        return self.email


# Flask-Admin access-based views
class SuperuserModelView(ModelView):

    # export models
    can_export = True
    export_types = ['csv', 'xlsx']

    # use modals for adding and editing
    create_modal = True
    edit_modal = True

    # allow setting page size
    can_set_page_size = True

    def is_accessible(self):
        return (
            current_user.is_active and
            current_user.is_authenticated and
            current_user.has_role('superuser')
        )


class EditorModelView(ModelView):
    def is_accessible(self):
        return (
            current_user.is_active and
            current_user.is_authenticated and
            (current_user.has_role('editor') or
             current_user.has_role('superuser'))
        )


class NOCModelView(ModelView):

    # export models
    can_export = True
    export_types = ['csv', 'xlsx']

    # use modals for adding and editing
    create_modal = True
    edit_modal = True

    # allow setting page size
    can_set_page_size = True

    def is_accessible(self):
        return (
            current_user.is_active and
            current_user.is_authenticated and
            (current_user.has_role('noc') or
             current_user.has_role('editor') or
             current_user.has_role('superuser'))
        )


class HRModelView(ModelView):
    def is_accessible(self):
        return (
            current_user.is_active and
            current_user.is_authenticated and
            (current_user.has_role('hr') or
             current_user.has_role('noc') or
             current_user.has_role('editor') or
             current_user.has_role('superuser'))
        )


class DeskModelView(ModelView):

    # export models
    can_export = True
    export_types = ['csv', 'xlsx']

    # use modals for adding and editing
    create_modal = True
    edit_modal = True

    # allow setting page size
    can_set_page_size = True

    def is_accessible(self):
        return (
            current_user.is_active and
            current_user.is_authenticated and
            (current_user.has_role('desk') or
             current_user.has_role('noc') or
             current_user.has_role('editor') or
             current_user.has_role('superuser'))
        )


class CustomFileView(FileAdmin):

    allowed_extensions = (
        'svg',
        'jpg',
        'png'
    )

    # editable_extensions = ('md','html','js','css','txt')

    def is_accessible(self):
        return (
            current_user.is_active and
            current_user.is_authenticated and
            (current_user.has_role('editor') or
             current_user.has_role('superuser'))
        )


class CustomerInfoModelView(ModelView):

    # export models
    can_export = True
    export_types = ['csv', 'xlsx']

    # use modals for adding and editing
    create_modal = True
    edit_modal = True

    # allow setting page size
    can_set_page_size = True

    # allow searching
    column_searchable_list = ['customer_no']

    # allow filtering
    column_filters = ['zone_id']

    def is_accessible(self):
        return (
            current_user.is_active and
            current_user.is_authenticated and
            (current_user.has_role('noc') or
             current_user.has_role('editor') or
             current_user.has_role('superuser'))
        )


class RechargeEntryModelView(ModelView):

    # export models
    can_export = True
    export_types = ['csv', 'xlsx']

    # use modals for adding and editing
    create_modal = True
    edit_modal = True

    # allow setting page size
    can_set_page_size = True

    # allow searching
    column_searchable_list = ['customer_no']

    # allow filtering
    column_filters = ['payment_gateway']

    def is_accessible(self):
        return (
            current_user.is_active and
            current_user.is_authenticated and
            (current_user.has_role('desk') or
             current_user.has_role('noc') or
             current_user.has_role('editor') or
             current_user.has_role('superuser'))
        )
