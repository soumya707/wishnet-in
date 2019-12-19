# -*- coding: utf-8 -*-

"""Define the forms to be used."""


from flask_wtf import FlaskForm
from wtforms import (
    PasswordField, SelectField, StringField, SubmitField, TextAreaField)
from wtforms.validators import (
    Email, EqualTo, InputRequired, IPAddress, Length, Optional, Regexp)


class RechargeForm(FlaskForm):
    """Class for recharge form."""
    user_id = StringField(
        'User ID',
        validators=[InputRequired()],
        render_kw={'placeholder': 'Customer ID'})
    submit = SubmitField('Insta-Recharge')


class NewConnectionForm(FlaskForm):
    """Class for new connection form."""
    pin_code_msg = 'Invalid postal code'
    phone_no_msg = 'Invalid mobile no.'
    email_msg = 'Invalid e-mail address'

    first_name = StringField('First Name', validators=[InputRequired()])
    middle_name = StringField('Middle Name')
    last_name = StringField('Last Name', validators=[InputRequired()])
    address = StringField('Address', validators=[InputRequired()])
    location = SelectField('Location', validators=[InputRequired()])
    postal_code = StringField(
        'Pin code',
        validators=[
            InputRequired(),
            Regexp(r'^[7]+\d{1,6}$', message=pin_code_msg)
        ]
    )
    phone_no = StringField(
        'Mobile no.',
        validators=[
            InputRequired(),
            Regexp(r'^\d{1,10}$', message=phone_no_msg)
        ]
    )
    email_address = StringField(
        'E-mail',
        validators=[
            InputRequired(),
            Email(message=email_msg)
        ]
    )
    submit = SubmitField('Submit')


class GetCustomerNumberForm(FlaskForm):
    """Class for getting customer number."""
    username = StringField(
        'Username',
        render_kw={'placeholder': 'Username'},
        validators=[Optional()]
    )
    ip_address = StringField(
        'IP Address',
        render_kw={'placeholder': 'IP Address'},
        validators=[
            Optional(),
            IPAddress(message='Invalid IP address'),
        ]
    )

    submit = SubmitField('Get')


class LoginForm(FlaskForm):
    """Class for authentication form."""
    customer_no = StringField('Customer ID', validators=[InputRequired()])
    password = PasswordField('Password', validators=[InputRequired()])
    submit = SubmitField('Sign in')


class RegistrationForm(FlaskForm):
    """Class for registration form."""
    customer_no = StringField('Customer ID', validators=[InputRequired()])
    submit = SubmitField('Get OTP')


class ForgotPasswordForm(FlaskForm):
    """Class for forgot password form."""
    customer_no = StringField('Customer ID', validators=[InputRequired()])
    submit = SubmitField('Get OTP')


class OTPVerificationForm(FlaskForm):
    """Class for verifying OTP form."""
    otp = StringField('Enter OTP', validators=[InputRequired()])
    submit = SubmitField('Verify')


class SetPasswordForm(FlaskForm):
    """Class for setting new password form."""
    password = PasswordField('New Password', validators=[
        InputRequired(),
        EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')
    submit = SubmitField('Set New Password')


class ChangePasswordForm(FlaskForm):
    """Class for changing password form."""
    old_password = PasswordField('Old Password', validators=[
        InputRequired(),
    ])
    new_password = PasswordField('New Password', validators=[
        InputRequired(),
        EqualTo('confirm', message='New passwords must match')
    ])
    confirm = PasswordField('Repeat Password', validators=[
        InputRequired(),
    ])
    submit = SubmitField('Set Password')


class UpdateProfileForm(FlaskForm):
    """Class for updating profile form."""
    new_phone_no = StringField(
        'New mobile no.',
        validators=[
            Optional(),
            Regexp(r'^\d{1,10}$', message='Invalid mobile no.')
        ]
    )
    new_email_address = StringField(
        'New e-mail address',
        validators=[
            Optional(),
            Email(message='Invalid e-mail address')
        ]
    )
    submit = SubmitField('Update')


class NewTicketForm(FlaskForm):
    """Class for submitting a ticket form."""
    nature = SelectField('Ticket Nature', validators=[InputRequired()])
    remarks = TextAreaField(
        'Remarks',
        validators=[
            Optional(),
            Length(max=200)
        ]
    )
    submit = SubmitField('Submit')


class MobileNumberUpdateRequestForm(FlaskForm):
    """Class for requesting mobile number update form (outside portal)."""
    phone_no_msg = 'Invalid mobile no.'
    pin_code_msg = 'Invalid postal code'

    old_phone_no = StringField(
        'Old mobile no.',
        validators=[
            Optional(),
            Regexp(r'^\d{1,10}$', message=phone_no_msg)
        ]
    )

    new_phone_no = StringField(
        'New mobile no.',
        validators=[
            Optional(),
            Regexp(r'^\d{1,10}$', message=phone_no_msg)
        ]
    )

    username_or_ip_address = StringField(
        'Username / IP Address',
        validators=[InputRequired()]
    )

    postal_code = StringField(
        'Pin code',
        validators=[
            InputRequired(),
            Regexp(r'^[7]+\d{1,6}$', message=pin_code_msg)
        ]
    )

    submit = SubmitField('Submit Request')


class UpdateGSTForm(FlaskForm):
    """Class for updating GST information form."""
    gst_msg = 'Invalid GST number'
    gst_no = StringField(
        'GST Number',
        validators=[
            InputRequired(),
            Regexp(r'^[A-Z0-9]{15}$', message=gst_msg)
        ]
    )
    submit = SubmitField('Submit Request')


class AddSoftphoneForm(FlaskForm):
    """Class for adding softphone number form."""
    name = StringField(
        'Name of User',
        validators=[InputRequired()],
    )
    mobile_number = StringField(
        'Mobile Number of User',
        validators=[
            Optional(),
            Regexp(r'^\d{1,10}$', message='Invalid mobile no.')
        ]
    )
    softphone_platform = SelectField(
        'Softphone Platform',
        validators=[InputRequired()],
        choices=[
            ('Android', 'Android'),
            ('iOS', 'iOS'),
            ('Fixed Line', 'Fixed Line')
        ]
    )
    password = PasswordField(
        'Password',
        validators=[
            InputRequired(),
            EqualTo('confirm_password', message='Passwords must match.'),
            Regexp(
                r'^[a-zA-Z0-9_\-]{1,8}$',
                message='Alphabets, numbers, - and _ are only used.'
            ),
            Length(max=8, message='Exceeding maximum length.')
        ],
        render_kw={'placeholder': 'Max. 8 characters'}
    )
    confirm_password = PasswordField(
        'Repeat Password',
        validators=[
            InputRequired(),
        ]
    )
    submit = SubmitField('Add Softphone')

