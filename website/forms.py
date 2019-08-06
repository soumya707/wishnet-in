# -*- coding: utf-8 -*-

"""Define the forms to be used."""

import re

from flask_wtf import FlaskForm
from wtforms import (
    IntegerField, PasswordField, SelectField, StringField, SubmitField,
    TextAreaField)
from wtforms.validators import DataRequired, Length, Regexp


class ContactForm(FlaskForm):
    """Class for contact form."""
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired()])
    message = TextAreaField('Message', validators=[DataRequired(),
                                                   Length(max=200)])
    submit = SubmitField('Submit')


class RechargeForm(FlaskForm):
    """Class for recharge form."""
    user_id = StringField(
        'User ID',
        validators=[DataRequired()],
        render_kw={'placeholder': 'User ID'})
    submit = SubmitField('Pay')


class NewConnectionForm(FlaskForm):
    """Class for new connection form."""
    pin_code_msg = 'Invalid postal code'
    phone_no_msg = 'Invalid mobile no.'

    first_name = StringField('First Name', validators=[DataRequired()])
    middle_name = StringField('Middle Name')
    last_name = StringField('Last Name', validators=[DataRequired()])
    address = StringField('Address', validators=[DataRequired()])
    location = SelectField('Location', choices=[('kol', 'Kolkata'),
                                                ('rob', 'Rest of WB')],
                           validators=[DataRequired()])
    postal_code = StringField('Pin code',
                               validators=[
                                   DataRequired(),
                                   Regexp('^[7]+\d{1,6}$',
                                          message=pin_code_msg)
                               ])
    phone_no = StringField('Mobile no.',
                           validators=[
                               DataRequired(),
                               Regexp('^\d{1,10}$',
                                      message=phone_no_msg)
                            ])
    remark = TextAreaField('Remarks', validators=[Length(max=200)])
    submit = SubmitField('Submit')
