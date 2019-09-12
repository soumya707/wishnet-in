# -*- coding: utf-8 -*-

"""Define helper functions for accessing MQS API."""

import random
import string

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

        return ''.join(random.choices(string.ascii_letters + string.digits,
                                      k=16))

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


class GetCustomerInfo(MQSAPI):
    """Define GetCustomerInfo API."""

    def __init__(self, app, **kwargs):
        super(GetCustomerInfo, self).__init__(app, **kwargs)
        self.response_code = None
        self.response_msg = None
        self.txn_no = None
        self.txn_msg = None
        self.name = None
        self.cust_no = None
        self.address = None
        self.pincode = None
        self.partner = None
        self.contact_no = None
        self.email = None
        self.all_plans = None
        self.inactive_plans = None
        self.active_plans = None

    def request(self, cust_id):
        """Send request for GetCustomerInfo."""

        customer_info_xml = '''
        <REQUESTINFO>
            <KEY_NAMEVALUE>
                <KEY_NAME>CUSTOMERNO</KEY_NAME>
                <KEY_VALUE>{}</KEY_VALUE>
            </KEY_NAMEVALUE>
        </REQUESTINFO>'''.format(cust_id)

        res = self.client.service.GetCustomerInfo(
            customer_info_xml, self.ref_no
        )

        self.response_code, self.response_msg = res[0], res[1]

    def response(self):
        """Parse response for GetCustomerInfo."""

        if self.response_code == 200:
            res_tree = et.fromstring(self.response_msg)

            self.txn_no = res_tree.findtext('.//TRANSACTIONNO')
            self.txn_msg = res_tree.findtext('.//MESSAGE')
            self.name = '{} {} {}'.format(
                res_tree.findtext('.//FIRSTNAME').capitalize(),
                res_tree.findtext('.//MIDDLENAME').capitalize(),
                res_tree.findtext('.//LASTNAME').capitalize()
            )
            self.cust_no = res_tree.findtext('.//CUSTOMERNO')
            self.address = '{}, {}, {}, {}, {}'.format(
                res_tree.findtext('.//ADDRESS1'),
                res_tree.findtext('.//AREA'),
                res_tree.findtext('.//CITY'),
                res_tree.findtext('.//STATE'),
                res_tree.findtext('.//ZIPCODE')
            )
            self.partner = ' '.join(res_tree.findtext('.//OPENTITYNAME')
                                    .split('_'))
            self.contact_no = res_tree.findtext('.//MOBILEPHONE')
            self.email = res_tree.findtext('.//EMAIL')
            # get a list of the contract status
            contract_status = [
                plan.text for plan in res_tree.iterfind('.//CONTRACTSTATUS')
            ]
            # get a list of plan codes
            self.all_plans = [
                plan_code.text.strip()
                for plan_code in res_tree.iterfind('.//PLANCODE')
            ]
            # get a list of start dates
            start_dates = [
                plan_start.text
                for plan_start in res_tree.iterfind('.//STARTDATE')
            ]
            # get a list of end dates
            end_dates = [
                plan_end.text
                for plan_end in res_tree.iterfind('.//ENDDATE')
            ]
            # get a list of plan validity
            validities = [
                ' - '.join(period) for period in zip(start_dates, end_dates)
            ]
            # get a consolidated plan list
            # [(contract_status, plan_code, validity)]
            plans_with_validity = [
                plan for plan
                in zip(contract_status, self.all_plans, validities)
            ]
            # filter active plans
            self.active_plans = [
                plan for plan in plans_with_validity if plan[0] == 'Active'
            ]
            # filter inactive plans
            self.inactive_plans = [
                plan for plan in plans_with_validity if plan[0] == 'Inactive'
            ]

    def to_dict(self):
        """Define interface to dict."""
        return {
            'name': self.name,
            'cust_no': self.cust_no,
            'address': self.address,
            'partner': self.partner,
            'contact_no': self.contact_no,
            'email': self.email,
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
        self.valid_user = None
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

            # check if user is valid or not
            if self.error_no == '0':
                self.valid_user = True
                plans = [plan.text for plan in res_tree.iterfind('.//PlanCode')]
                end_dates = list(
                    map(
                        self._fix_date_fmt,
                        [plan.text for plan in res_tree.iterfind('.//EndDate')]
                    )
                )
                self.active_plans = [
                    entry for entry in zip(plans, end_dates)
                ]
            else:
                self.valid_user = False


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

    def request(self, cust_id, ticket_category, ticket_desc, ticket_nature):
        """Send request for RegisterTicket."""

        register_ticket_xml = '''
        <REQUESTINFO>
            <KEY_NAMEVALUE>
                <KEY_NAME>CUSTOMERNO</KEY_NAME>
                <KEY_VALUE>{customer_no}</KEY_VALUE>
            </KEY_NAMEVALUE>
            <REGISTERTICKET>
                <TICKETNO></TICKETNO>
                <TICKETCATEGORY>{ticket_category}</TICKETCATEGORY>
                <TICKETDESCRIPTION>{ticket_desc}</TICKETDESCRIPTION>
                <TICKETNATURE>{ticket_nature}</TICKETNATURE>
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
        </REQUESTINFO>'''.format(
            customer_no=cust_id,
            ticket_category=ticket_category,
            ticket_desc=ticket_desc,
            ticket_nature=ticket_nature,
        )

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
            self.error_no = res_tree.findtext('.//ERROR_NO')
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
            self.error_no = res_tree.findtext('.//ERROR_NO')
