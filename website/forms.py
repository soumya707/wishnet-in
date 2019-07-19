# -*- coding: utf-8 -*-


from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class ContactForm(FlaskForm):
    """Class for contact form."""
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired()])
    message = TextAreaField('Message', validators=[DataRequired(),
                                                   Length(max=200)])
    submit = SubmitField('Submit')


class RechargeForm(FlaskForm):
    """Class for recharge form."""
    user_id = StringField('User ID', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class NewConnectionForm(FlaskForm):
    """Class for new connection form."""
    pass
