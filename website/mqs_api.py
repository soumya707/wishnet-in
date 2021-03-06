# -*- coding: utf-8 -*-

"""Define helper functions for accessing MQS API."""

import random
import string
from datetime import datetime

from lxml import etree as et
from suds.client import Client


class MQSAPI():
    """Base class for accessing MQS SOAP API."""

    def __init__(self, app, **kwargs):
        super(MQSAPI, self).__init__(**kwargs)
        self.app = app
        self.ref_no = self._generate_reference_no()
        self.client = self._generate_mqs_username_token()

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__ = state

    def _generate_reference_no(self):
        """Generate Reference number for transactions."""

        return ''.join(
            random.choices(
                string.ascii_letters + string.digits,
                k=16
            )
        )

    def _generate_mqs_username_token(self):
        """Generate MQSUserNameToken for SOAP API access."""

        url = self.app.config['MQS_URL']
        client = Client(url, faults=False)
        username_token = client.factory.create('MQUserNameToken')
        username_token.User_id = self.app.config['MQS_USER']
        username_token.Password = self.app.config['MQS_PWD']
        username_token.ExternalPartyName = self.app.config['MQS_EXT']
        client.set_options(soapheaders=username_token)

        return client

    def request(self):
        """Prepare and send the request for the service.

        This is an abstract method which the subclass needs to extend."""

        raise NotImplementedError('Add functionality in your subclass.')

    def response(self):
        """Prepare and send the request for the service.

        This is an abstract method which the subclass needs to extend."""

        raise NotImplementedError('Add functionality in your subclass.')


class Recharge(MQSAPI):
    """Define TopUp API."""

    def __init__(self, app, **kwargs):
        super(Recharge, self).__init__(app, **kwargs)
        self.response_code = None
        self.response_msg = None
        self.txn_no = None
        self.txn_msg = None
        self.error_no = None

    def request(self, cust_id, plan_code):
        """Send request for TopUp."""

        topup_info_xml = '''
        <REQUESTINFO>
            <KEY_NAMEVALUE>
                <KEY_NAME>CUSTOMERNO</KEY_NAME>
                <KEY_VALUE>{}</KEY_VALUE>
            </KEY_NAMEVALUE>
            <TOPUPINFO>
                <PLANCODE>{}</PLANCODE>
            </TOPUPINFO>
        </REQUESTINFO>'''.format(cust_id, plan_code)

        res = self.client.service.TopUp(topup_info_xml, self.ref_no)

        self.response_code, self.response_msg = res[0], res[1]

    def response(self):
        """Parse response for TopUp."""

        if self.response_code == 200:
            res_tree = et.fromstring(self.response_msg)

            self.txn_no = res_tree.findtext('.//TRANSACTIONNO')
            self.txn_msg = res_tree.findtext('.//MESSAGE')
            self.error_no = res_tree.findtext('.//ERRORNO')


class AddPlan(MQSAPI):
    """Define AddContract API."""

    def __init__(self, app, **kwargs):
        super(AddPlan, self).__init__(app, **kwargs)
        self.response_code = None
        self.response_msg = None
        self.txn_no = None
        self.txn_msg = None
        self.error_no = None

    def request(self, cust_id, plan_code):
        """Send request for AddContract."""

        addplan_info_xml = '''
        <REQUESTINFO>
            <KEY_NAMEVALUE>
                <KEY_NAME>CUSTOMERNO</KEY_NAME>
                <KEY_VALUE>{}</KEY_VALUE>
            </KEY_NAMEVALUE>
            <CONTRACTINFO>
                <PLANINFO>
                    <PLANCODE>{}</PLANCODE>
                </PLANINFO>
            </CONTRACTINFO>
        </REQUESTINFO>'''.format(cust_id, plan_code)

        res = self.client.service.AddContract(addplan_info_xml, self.ref_no)

        self.response_code, self.response_msg = res[0], res[1]

    def response(self):
        """Parse response for AddContract."""

        if self.response_code == 200:
            res_tree = et.fromstring(self.response_msg)

            self.txn_no = res_tree.findtext('.//TRANSACTIONNO')
            self.txn_msg = res_tree.findtext('.//MESSAGE')
            self.error_no = res_tree.findtext('.//ERRORNO')


class GetAllContracts(MQSAPI):
    """Define GetAllContracts API."""

    def __init__(self, app, **kwargs):
        super(GetAllContracts, self).__init__(app, **kwargs)
        self.response_code = None
        self.response_msg = None
        self.txn_no = None
        self.txn_msg = None
        self.all_plans = None
        self.inactive_plans = None
        self.active_plans = None

    def request(self, cust_id):
        """Send request for GetRecordsBySearch."""
        get_records_by_search_xml = '''
        <REQUESTINFO>
            <KEY_NAMEVALUE>
                <KEY_NAME>PROCESS</KEY_NAME>
                <KEY_VALUE>GETCUSTOMERCONTRACTDETAILS</KEY_VALUE>
            </KEY_NAMEVALUE>
            <ADDITIONAL_INFO>
                <CUSTOMERNO>{}</CUSTOMERNO>
            </ADDITIONAL_INFO>
        </REQUESTINFO>'''.format(cust_id)

        res = self.client.service.GetRecordsBySearch(
            get_records_by_search_xml, self.ref_no
        )

        self.response_code, self.response_msg = res[0], res[1]

    def response(self):
        """Parse response for GetRecordsBySearch."""
        if self.response_code == 200:
            # months = {
            #     'JAN': '01',
            #     'FEB': '02',
            #     'MAR': '03',
            #     'APR': '04',
            #     'MAY': '05',
            #     'JUN': '06',
            #     'JUL': '07',
            #     'AUG': '08',
            #     'SEP': '09',
            #     'OCT': '10',
            #     'NOV': '11',
            #     'DEC': '12',
            # }
            # def modify_date(date):
            #     """Modify the date to proper format."""
            #     splitted_date = date.split('-')
            #     splitted_date[1] = months.get(splitted_date[1])
            #     splitted_date[2] = '20' + splitted_date[2]
            #     return '-'.join(splitted_date)

            res_tree = et.fromstring(self.response_msg)

            self.txn_no = res_tree.findtext('.//TRANSACTIONNO')
            self.txn_msg = res_tree.findtext('.//MESSAGE')
            # Get a list of the contract status
            contract_status = [
                status.text for status in res_tree.iterfind('.//STATUS')
                if status.text
            ]
            # Get a list of plan codes
            self.all_plans = [
                plan_code.text for plan_code in res_tree.iterfind('.//PLANCODE')
            ]
            # Get a list of start dates
            start_dates = [
                plan_start.text
                # modify_date(plan_start.text)
                for plan_start in res_tree.iterfind('.//STARTDATE')
            ]
            # Get a list of end dates
            end_dates = [
                plan_end.text
                # modify_date(plan_end.text)
                for plan_end in res_tree.iterfind('.//ENDDATE')
            ]
            # Get a list of plan validity
            validities = [
                ' - '.join(period) for period in zip(start_dates, end_dates)
            ]
            # Get a consolidated plan list
            # [(contract_status, plan_code, validity)]
            plans_with_validity = \
                list(zip(contract_status, self.all_plans, validities))
            # filter active plans
            self.active_plans = [
                plan for plan in plans_with_validity if plan[0] == 'Active'
            ]
            # filter inactive plans
            self.inactive_plans = [
                plan for plan in plans_with_validity if plan[0] == 'Expired'
            ]

    def to_dict(self):
        """Define interface to dict."""
        return {
            'all_plans': self.all_plans,
            'inactive_plans': self.inactive_plans,
            'active_plans': self.active_plans,
        }


class ContractsByKey(MQSAPI):
    """Define GetContractsByKey API."""

    def __init__(self, app, **kwargs):
        super(ContractsByKey, self).__init__(app, **kwargs)
        self.response_code = None
        self.response_msg = None
        self.txn_no = None
        self.txn_msg = None
        self.error_no = None
        self.active_plans = None

    def _fix_date_fmt(self, date):
        """Fix the date formats to be readable."""
        date_split = date.split('/')
        return '-'.join([date_split[1], date_split[0], date_split[2]])

    def request(self, cust_id):
        """Send request for GetContractsByKey."""
        contracts_info_xml = '''
        <REQUESTINFO>
            <KEY_NAMEVALUE>
                <KEY_NAME>CUSTOMERNO</KEY_NAME>
                <KEY_VALUE>{}</KEY_VALUE>
            </KEY_NAMEVALUE>
        </REQUESTINFO>'''.format(cust_id)

        res = self.client.service.GetContractsByKey(
            contracts_info_xml, self.ref_no
        )

        self.response_code, self.response_msg = res[0], res[1]

    def response(self):
        """Parse response for GetContractsByKey."""
        if self.response_code == 200:
            res_tree = et.fromstring(self.response_msg)

            self.txn_no = res_tree.findtext('.//TRANSACTIONNO')
            self.txn_msg = res_tree.findtext('.//MESSAGE')
            self.error_no = res_tree.findtext('.//ERRORNO')
            # process data only if API call is successful
            if self.error_no == '0':
                plans = [plan.text for plan in res_tree.iterfind('.//PlanCode')]
                end_dates = list(
                    map(
                        self._fix_date_fmt,
                        [plan.text for plan in res_tree.iterfind('.//EndDate')]
                    )
                )
                self.active_plans = list(zip(plans, end_dates))


class RegisterTicket(MQSAPI):
    """Define RegisterTicket API."""

    def __init__(self, app, **kwargs):
        super(RegisterTicket, self).__init__(app, **kwargs)
        self.response_code = None
        self.response_msg = None
        self.txn_no = None
        self.txn_msg = None
        self.error_no = None
        self.ticket_no = None

    def request(self, cust_id, category, description, nature):
        """Send request for RegisterTicket."""

        register_ticket_xml = '''
        <REQUESTINFO>
            <KEY_NAMEVALUE>
                <KEY_NAME>CUSTOMERNO</KEY_NAME>
                <KEY_VALUE>{0}</KEY_VALUE>
            </KEY_NAMEVALUE>
            <REGISTERTICKET>
                <TICKETNO></TICKETNO>
                <TICKETCATEGORY>{3}</TICKETCATEGORY>
                <TICKETDESCRIPTION>{1}</TICKETDESCRIPTION>
                <TICKETNATURE>{2}</TICKETNATURE>
                <TICKETSTATUS>ACTIVE</TICKETSTATUS>
                <TICKETPRIORITY>HIGH</TICKETPRIORITY>
                <SERVICETEAM>CUSTOMERDESK</SERVICETEAM>
                <ASSIGNEDTO>CUSDESK</ASSIGNEDTO>
            </REGISTERTICKET>
            <PROBLEM-INFO>
                <PROBLEM>
                    <PROBLEMCODE></PROBLEMCODE>
                </PROBLEM>
            </PROBLEM-INFO>
        </REQUESTINFO>'''.format(cust_id, description, nature, category.strip())

        res = self.client.service.RegisterTicket(
            register_ticket_xml, self.ref_no
        )

        self.response_code, self.response_msg = res[0], res[1]

    def response(self):
        """Parse response for RegisterTicket."""

        if self.response_code == 200:
            res_tree = et.fromstring(self.response_msg)

            self.txn_no = res_tree.findtext('.//TRANSACTIONNO')
            self.txn_msg = res_tree.findtext('.//MESSAGE')
            self.error_no = res_tree.findtext('.//ERRORNO')
            self.ticket_no = res_tree.findtext('.//SERVICEREQUESTNO')


class CloseTicket(MQSAPI):
    """Define CloseTicket API."""

    def __init__(self, app, **kwargs):
        super(CloseTicket, self).__init__(app, **kwargs)
        self.response_code = None
        self.response_msg = None
        self.txn_no = None
        self.txn_msg = None
        self.error_no = None

    def request(self, ticket_no):
        """Send request for CloseTicket."""

        close_ticket_xml = '''
        <REQUESTINFO>
            <CLOSETICKET>
                <TICKETNO>{}</TICKETNO>
                <TICKETRESCODE>RESOLVED</TICKETRESCODE>
                <TICKETRESNOTES>Closed</TICKETRESNOTES>
            </CLOSETICKET>
         </REQUESTINFO>'''.format(ticket_no)

        res = self.client.service.CloseTicket(
            close_ticket_xml, self.ref_no
        )

        self.response_code, self.response_msg = res[0], res[1]

    def response(self):
        """Parse response for CloseTicket."""

        if self.response_code == 200:
            res_tree = et.fromstring(self.response_msg)

            self.txn_no = res_tree.findtext('.//TRANSACTIONNO')
            self.txn_msg = res_tree.findtext('.//MESSAGE')
            self.error_no = res_tree.findtext('.//ERRORNO')


class UpdateProfile(MQSAPI):
    """Define ModifyCustomer API."""

    def __init__(self, app, **kwargs):
        super(UpdateProfile, self).__init__(app, **kwargs)
        self.response_code = None
        self.response_msg = None
        self.txn_no = None
        self.txn_msg = None
        self.error_no = None

    def request(self, cust_id, email, mobile_no):
        """Send request for UpdateProfile."""

        # only email needs to be changed
        if email and not mobile_no:
            update_profile_info_xml = '''
            <REQUESTINFO>
                <KEY_NAMEVALUE>
                    <KEY_NAME>CUSTOMERNO</KEY_NAME>
                    <KEY_VALUE>{customer_no}</KEY_VALUE>
                </KEY_NAMEVALUE>
                <CUSTOMERINFO>
                    <CONTACTINFO>
                        <EMAIL>{email}</EMAIL>
                    </CONTACTINFO>
                </CUSTOMERINFO>
            </REQUESTINFO>'''.format(customer_no=cust_id, email=email)

        # only mobile no. needs to be changed
        elif not email and mobile_no:
            update_profile_info_xml = '''
            <REQUESTINFO>
                <KEY_NAMEVALUE>
                    <KEY_NAME>CUSTOMERNO</KEY_NAME>
                    <KEY_VALUE>{customer_no}</KEY_VALUE>
                </KEY_NAMEVALUE>
                <CUSTOMERINFO>
                    <CONTACTINFO>
                        <MOBILEPHONE>{mobile_no}</MOBILEPHONE>
                    </CONTACTINFO>
                </CUSTOMERINFO>
            </REQUESTINFO>'''.format(customer_no=cust_id, mobile_no=mobile_no)

        # both email and mobile no. needs to be changed
        elif email and mobile_no:
            update_profile_info_xml = '''
            <REQUESTINFO>
                <KEY_NAMEVALUE>
                    <KEY_NAME>CUSTOMERNO</KEY_NAME>
                    <KEY_VALUE>{customer_no}</KEY_VALUE>
                </KEY_NAMEVALUE>
                <CUSTOMERINFO>
                    <CONTACTINFO>
                        <EMAIL>{email}</EMAIL>
                        <MOBILEPHONE>{mobile_no}</MOBILEPHONE>
                    </CONTACTINFO>
                </CUSTOMERINFO>
            </REQUESTINFO>'''.format(
                customer_no=cust_id,
                email=email,
                mobile_no=mobile_no
            )

        res = self.client.service.ModifyCustomer(
            update_profile_info_xml, self.ref_no
        )

        self.response_code, self.response_msg = res[0], res[1]

    def response(self):
        """Parse response for UpdateProfile."""

        if self.response_code == 200:
            res_tree = et.fromstring(self.response_msg)

            self.txn_no = res_tree.findtext('.//TRANSACTIONNO')
            self.txn_msg = res_tree.findtext('.//MESSAGE')
            self.error_no = res_tree.findtext('.//ERRORNO')


class GetUsageDetails():
    """Class for accessing AAA GetUsageDetails API."""

    def __init__(self, **kwargs):
        super(GetUsageDetails, self).__init__(**kwargs)
        self.response_code = None
        self.response_msg = None
        self.error_no = None
        self.usage = None

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__ = state

    def request(self, user_name, start_date, end_date):
        """Prepare and send the request for the service."""

        url = (
            'http://110.172.52.234:8080/MQNsureWebService/services/RadUser?wsdl'
        )
        client = Client(url, faults=False)

        username_token = client.factory.create('ns0:UserInfo')
        username_token.userName = 'webadmin'
        username_token.password = 'webadmin'

        get_usage_xml = '''
        <request name="UserSessionDetails">
            <UserDetails>
                <user_name>{0}</user_name>
                <from_date>{1}</from_date>
                <to_date>{2}</to_date>
                <group></group>
            </UserDetails>
        </request>'''.format(user_name, start_date, end_date)

        res = client.service.UserSessionDetails(
            get_usage_xml, username_token
        )

        self.response_code, self.response_msg = res[0], res[1]

    def response(self):
        """Prepare and send the request for the service."""

        if self.response_code == 200:
            res_tree = et.XML(bytes(self.response_msg, encoding='utf8'))

            self.error_no = res_tree.findtext('.//status')
            plans = [plan.text for plan in res_tree.iterfind('.//group')]
            # parse into datetime
            login_time = [
                datetime.strptime(time.text, '%d%m%Y%H%M%S')
                for time in res_tree.iterfind('.//login_time')
            ]
            # convert into hours
            usage_time = [
                round(float(time.text) / 3600, 1)
                for time in res_tree.iterfind('.//session_free_time')
            ]
            # consistent parsing
            download = [
                round(float(download.text) / 1024, 2)
                for download in res_tree.iterfind('.//free_download')
            ]
            upload = [
                round(float(upload.text) / 1024, 2)
                for upload in res_tree.iterfind('.//free_upload')
            ]
            ip_addr = [ip.text for ip in res_tree.iterfind('.//user_ip')]

            self.usage = list(
                zip(
                    plans, login_time, usage_time, download, upload, ip_addr
                )
            )
