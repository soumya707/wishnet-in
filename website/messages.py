# -*- coding: utf-8 -*-

"""Messages displayed in the website."""


# DISPLAYED IN INSTA-RECHARGE FOR USER HAVING NO ACTIVE PLANS
NO_ACTIVE_PLANS = (
    'There are no active plans for your account. '
    'Please use self-care or call us.'
)

# USER DATA NOT FOUND IN DATABASE; POSSIBLY NEW USER
USER_NOT_FOUND_IN_DB = (
    'Invalid customer number. If you are a new customer, your profile data '
    'is being updated. Please try later.'
)

# SUCCESSFUL SENDING OF CUSTOMER NUMBER TO MOBILE
CUSTOMER_NO_SENT = (
    'Customer number has been sent to your registered mobile number.'
)

# SMS MESSAGE FOR SUCCESSFUL SENDING OF CUSTOMER NUMBER
SMS_CUSTOMER_NO = '{} is your customer number. Team Wishnet.'

# UNSUCCESSFUL SENDING OF CUSTOMER NUMBER TO MOBILE
CUSTOMER_NO_NOT_SENT = 'There was some problem, please try again.'

# CUSTOMER MOBILE NUMBER NOT FOUND IN DATABASE
NO_MOBILE_NO = (
    'No registered mobile number found. '
    'Please get your mobile number registered with us.'
)

# INVALID CREDENTIALS FOR USER
INVALID_CUSTOMER = (
    'Could not retrieve details with the provided credentials. '
    'Try again with valid credentials or contact us.'
)

# SUCCESSFUL RECHARGE
SUCCESSFUL_RECHARGE = (
    'Payment received and recharge successful. '
    'Kindly await for plan activation.'
)

# UNSUCCESSFUL RECHARGE
UNSUCCESSFUL_RECHARGE = (
    'Payment received but recharge failed. '
    'We will revert within 24 hours.'
)

# SUCCESSFUL ADD PLAN
SUCCESSFUL_ADDPLAN = (
    'Payment received and plan added. '
    'Kindly await for plan activation.'
)

# UNSUCCESSFUL ADD PLAN
UNSUCCESSFUL_ADDPLAN = (
    'Payment received but plan addition failed.'
    'We will revert within 24 hours.'
)

# SUCCESSFUL PROFILE UPDATE
SUCCESSFUL_PROFILE_UPDATE = (
    'Profile updated successfully! The changes will take effect the '
    'next time you log in.'
)

# UNSUCCESSFUL PROFILE UPDATE
UNSUCCESSFUL_PROFILE_UPDATE = (
    'There was an error while updating your profile. '
    'Please open a ticket or contact us.'
)

# INCOMPLETE PAYMENT
INCOMPLETE_PAYMENT = 'Payment incomplete! Please try again.'

# UNSUCCESSFUL PAYMENT
UNSUCCESSFUL_PAYMENT = 'Payment failed! Please try again.'

# NEW CONNECTION REQUEST SUCCESSFUL
SUCCESSFUL_NEW_CONN_REQUEST = 'Request sent successfully!'

# INCORRECT PASSWORD FOR SELF-CARE LOGIN
INCORRECT_PWD = (
    'Incorrect password for the given customer number. '
    'Please try again.'
)

# NON-REGISTERED SELF-CARE ENTRY TRIAL
NON_REGISTERED_USER = (
    'You have not registered for the self-care portal. '
    'Please register before proceeding.'
)

# SUCCESSFUL LOGOUT
SUCCESSFUL_LOGOUT = 'You have been successfully logged out.'

# ACCESSING SELF-CARE WHILE NOT LOGGED IN
LOG_IN_FIRST = 'Please log in.'

# REGISTERING FOR SELF-CARE WHILE ALREADY REGISTERED
ALREADY_REGISTERED = 'You are already registered. Try logging in.'

# SMS MESSAGE FOR OTP FOR SELF-CARE REGISTRATION
SMS_REG_OTP = '{} is your OTP for self-care registration. Team Wishnet.'

# SMS MESSAGE FOR OTP FOR SELF-CARE PASSWORD RESET
SMS_PWD_RESET_OTP = '{} is your OTP for resetting password. Team Wishnet.'

# OTP FOR SELF-CARE REGISTRATION/PASSWORD RESET SENT
OTP_SENT = 'OTP has been sent to your registered mobile number.'

# OTP FOR SELF-CARE REGISTRATION/PASSWORD RESET NOT SENT
OTP_NOT_SENT = 'There was some problem, please try again.'

# OTP VERIFICATION FAILED
OTP_VERIFY_FAILED = 'OTP verification failed. Please try again.'

# SUCCESSFUL PASSWORD SAVE
SUCCESSFUL_PWD_SAVE = 'Password saved successfully!'

# SUCCESSFUL MOBILE NO REQUEST
SUCCESSFUL_MOBILE_NO_UPDATE_REQUEST = (
    'Update request sent successfully! We will confirm you once '
    'the procedure is complete.'
)

# SUCCESSFUL DOCKET GENERATE
SUCCESSFUL_DOCKET_GEN = 'Docket generated successfully.'

# UNSUCCESSFUL DOCKET GENERATE
UNSUCCESSFUL_DOCKET_GEN = 'Docket could not be generated. Please try again.'

# SUCCESSFUL DOCKET CLOSE
SUCCESSFUL_DOCKET_CLOSE = 'Docket: {} closed successfully.'

# UNSUCCESSFUL DOCKET CLOSE
UNSUCCESSFUL_DOCKET_CLOSE = (
    'Docket: {} could not be closed successfully, please try again.'
)

# NO EXISTING DOCKETS
NO_DOCKETS = 'No open ticket exists.'

# SETTING NEW PASSWORD TO OLD ONE
SET_NEW_PWD = 'You cannot use your old password as the new one.'

# NEW PASSWORD SAVED SUCCESSFULLY
NEW_PWD_SET = 'Password saved successfully!'

# INCORRECT OLD PASSWORD
INCORRECT_OLD_PWD = 'Old password entered is incorrect, please try again.'

# GST UPDATE REQUEST SENT SUCCESSFULLY
SUCCESSFUL_GST_UPDATE_REQUEST = (
    'GST information update request sent successfully! '
    'We will notify you when the procedure is complete.'
)

# SUCCESSFUL SOFTPHONE NUMBER ALLOCATION
SUCCESSFUL_SOFTPHONE_ALLOTMENT = 'Your softphone number has been successfully created.'

# UNSUCCESSFUL SOFTPHONE NUMBER ALLOCATION
UNSUCCESSFUL_SOFTPHONE_ALLOTMENT = 'There was some problem. Please try again.'

# UNSUCCESSFUL SMS FOR SOFTPHONE ALLOCATION
UNSUCCESSFUL_SOFTPHONE_SMS = (
    'Your softphone number has been successfully created. '
    'Please contact us for further support.'
)

# SUCCESSFUL SMS FOR SOFTPHONE CREATION (ANDROID)
SUCCESSFUL_SOFTPHONE_SMS_ANDROID = (
    'Download WishTalk app from Google Play Store. '
    'Your username is {0} and password is {1}. For instructions, visit '
    'https://wishnet.in/wishtalk.'
)

# SUCCESSFUL SMS FOR SOFTPHONE CREATION (iOS)
SUCCESSFUL_SOFTPHONE_SMS_IOS = (
    'Download Bria Mobile or any other softphone app from App Store. '
    'Your username is {0} and password is {1}. For instructions, visit '
    'https://wishnet.in/wishtalk.'
)

# SUCCESSFUL SMS FOR SOFTPHONE CREATION (FIXED LINE)
SUCCESSFUL_SOFTPHONE_SMS_FIXED_LINE = (
    'Dear customer, please contact us for further configuration. '
    'Your username is {0} and password is {1}. For instructions, visit '
    'https://wishnet.in/wishtalk.'
)
