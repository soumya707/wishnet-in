# -*- coding: utf-8 -*-

"""Contains the models for the application."""

import random
import string
from datetime import datetime

from website import db


# Job Vacancies
class JobVacancy(db.Model):
    """Class for representing job vacancies."""

    __bind_key__ = 'assets'

    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(50), nullable=False)
    salary_range = db.Column(db.String(50), nullable=False)
    job_type = db.Column(db.String(50), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    job_summary = db.Column(db.Text, nullable=False)
    key_skills = db.Column(db.Text, nullable=False)
    experience = db.Column(db.String(200), nullable=False)
    education = db.Column(db.String(50), nullable=False)
    preferable = db.Column(db.String(20), nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    posted_on = db.Column(db.Date, nullable=False)
    dept_email = db.Column(db.String(50), nullable=False)
    no_of_opening = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(10), nullable=False)

    def __str__(self):
        return self.job_title


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
    contention_ratio = db.Column(db.String(5), nullable=False)
    plan_type = db.Column(db.String(20), nullable=False)

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

    static_ip = db.Column(db.Integer, nullable=False)


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
    category = db.Column(db.String(20), nullable=False)


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
    link = db.Column(db.String(100), nullable=False)
    text = db.Column(db.String(200), nullable=False)
    img_id = db.Column(db.String(50), nullable=False)

    def __str__(self):
        return self.name


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
    email = db.Column(db.String(50), nullable=False)
    remark = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(10), nullable=False, default='website')
    cust_add = db.Column(db.String(20), nullable=False, default='ADD_CUST')
    date = db.Column(db.Date(), nullable=False,
                     default=datetime.now().astimezone().date())
    time = db.Column(db.Time(), nullable=False,
                     default=datetime.now().astimezone().time())

    def __str__(self):
        return self.query_no


# Regional offices
class RegionalOffices(db.Model):
    """Class for representing regional offices."""

    __bind_key__ = 'assets'

    id = db.Column(db.Integer, primary_key=True)
    place = db.Column(db.String(15), nullable=False)
    address = db.Column(db.Text, nullable=False)

    def __str__(self):
        return self.place


# Carousel
class CarouselImages(db.Model):
    """Class for representing carousel images."""

    __bind_key__ = 'assets'

    id = db.Column(db.Integer, primary_key=True)
    image_name = db.Column(db.String(20), nullable=False)

    def __str__(self):
        return self.image_name


# Recharge
class RechargeEntry(db.Model):
    """Class for representing recharge data."""

    __bind_key__ = 'recharge'

    id = db.Column(db.Integer, primary_key=True)
    wishnet_payment_order_id = db.Column(db.String(20), nullable=False)
    payment_gateway = db.Column(db.String(10), nullable=False)
    payment_gateway_order_id = db.Column(db.String(20), nullable=False)
    payment_status = db.Column(db.String(10), nullable=False)
    mq_topup_reference_id = db.Column(db.String(20), nullable=True)
    mq_topup_status = db.Column(db.String(10), nullable=True)

    def __str__(self):
        return self.wishnet_payment_order_id


# Retrieve customer number
class CustomerInfo(db.Model):
    """Class for representing customer basic info."""

    __bind_key__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    customer_no = db.Column(db.String(20), nullable=False)
    user_name = db.Column(db.String(20), nullable=False)
    mobile_no = db.Column(db.String(15), nullable=False)

    def __str__(self):
        return self.customer_no
