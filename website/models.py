# -*- coding: utf-8 -*-


from datetime import datetime

from website import db


class JobVacancy(db.Model):
    """Class for representing job vacancies."""
    id = db.Column(db.String(10), primary_key=True)
    job_title = db.Column(db.String(200), nullable=False)
    salary = db.Column(db.Integer, nullable=True)
    experience = db.Column(db.String(200), nullable=True)
    required = db.Column(db.String(10), nullable=True)
    opening = db.Column(db.Integer, nullable=False)
    posted_on = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text, nullable=False)
    education = db.Column(db.String(50), nullable=False)
    education_requirements = db.Column(db.Text, nullable=False)
    dept_email = db.Column(db.String(50), nullable=False)


class DataPlan(db.Model):
    """Class for representing basic data plan."""
    id = db.Column(db.Integer, primary_key=True)
    plan_name = db.Column(db.String(50), nullable=False)
    bandwidth = db.Column(db.Integer, nullable=False)
    validity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    terms = db.Column(db.Text, nullable=True)


class UnlimitedPlan(DataPlan):
    """Class for representing Unlimited Plan."""
    pass


class FTTHPlan(DataPlan):
    """Class for representing FTTH Plan."""
    pass


class BizPlan(DataPlan):
    """Class for representing Biz Plan."""
    pass


class FUPPlan(DataPlan):
    """Class for representing FUP Plan."""
    speed_after_limit = db.Column(db.Integer, nullable=False)
