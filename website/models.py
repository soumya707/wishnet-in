# -*- coding: utf-8 -*-

"""Contains the models for the application."""

from datetime import datetime
import random
import string

from website import db


# Job Vacancies
class JobVacancy(db.Model):
    """Class for representing job vacancies."""

    __bind_key__ = 'assets'

    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(200), nullable=False)
    salary = db.Column(db.Integer, nullable=True)
    experience = db.Column(db.String(200), nullable=True)
    required = db.Column(db.String(10), nullable=True)
    opening = db.Column(db.Integer, nullable=False)
    posted_on = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=False)
    education = db.Column(db.String(50), nullable=False)
    education_requirements = db.Column(db.Text, nullable=False)
    dept_email = db.Column(db.String(50), nullable=False)


# Tariff Plans
class DataPlan(db.Model):
    """Base class for representing basic data plan."""

    __abstract__ = True
    __bind_key__ = 'assets'

    id = db.Column(db.Integer, primary_key=True)
    plan_name = db.Column(db.String(50), nullable=False)
    bandwidth = db.Column(db.Integer, nullable=False)
    validity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    # terms = db.Column(db.Text, nullable=True)

    def __str__(self):
        return self.plan_name


class UnlimitedPlan(DataPlan):
    """Class for representing Unlimited Plan."""

    __bind_key__ = 'assets'


class FTTHPlan(DataPlan):
    """Class for representing FTTH Plan."""

    __bind_key__ = 'assets'


class BizPlan(DataPlan):
    """Class for representing Biz Plan."""

    __bind_key__ = 'assets'


class LimitedPlan(DataPlan):
    """Base class for representing Limited Plans."""

    __abstract__ = True
    __bind_key__ = 'assets'

    data_limit = db.Column(db.Integer, nullable=False)
    speed_after_limit = db.Column(db.Integer, nullable=False)


class FUPPlan(LimitedPlan):
    """Class for representing FUP Plan."""

    __bind_key__ = 'assets'


# FAQ
class FAQ(db.Model):
    """Class for representing FAQs."""

    __bind_key__ = 'assets'

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.Text, nullable=False)


# Best plans
class BestPlans(db.Model):
    """Class for representing the best plans displayed on homepage."""

    __bind_key__ = 'assets'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    speed = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    validity = db.Column(db.Integer, nullable=False)
    logo_id = db.Column(db.String(20), nullable=False)


# Services
class Services(db.Model):
    """Class for representing the services offered."""

    __bind_key__ = 'assets'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    features = db.Column(db.Text, nullable=False)
    logo_id = db.Column(db.String(20), nullable=False)


# Downloads
class Downloads(db.Model):
    """Class for representing the downloads."""

    __bind_key__ = 'assets'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    img = db.Column(db.String(20), nullable=False)
    link = db.Column(db.String(100), nullable=False)


# Ventures
class Ventures(db.Model):
    """Class for representing the ventures."""

    __bind_key__ = 'assets'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    pic = db.Column(db.String(20), nullable=False)


# New Connection form model
class NewConnection(db.Model):
    """Class for representing the already existing new connection info."""

    __bind_key__ = 'connection'

    def random_query_no_gen():
        """Generate random query number."""
        return ''.join(
            random.choices(
                string.ascii_letters + string.digits, k=8
            )
        )

    id = db.Column(db.Integer, primary_key=True)
    query_no = db.Column(db.String(8), unique=True,
                         default=random_query_no_gen())
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(500), nullable=False)
    location = db.Column(db.String(20), nullable=False)
    postal_code = db.Column(db.String(6), nullable=False)
    phone_no = db.Column(db.String(10), nullable=False)
    remark = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(10), nullable=False, default='website')
    cust_add = db.Column(db.String(20), nullable=False, default='ADD_CUST')
    date = db.Column(db.Date(), nullable=False,
                     default=datetime.now().astimezone().date())
    time = db.Column(db.Time(), nullable=False,
                     default=datetime.now().astimezone().time())
