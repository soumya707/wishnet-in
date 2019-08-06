# -*- codiing: utf-8 -*-

"""Define helper functions for the application."""

import random, string

from lxml import etree as et

from suds.client import Client


class MQSAPI(object):
    """Base class for accessing MQS SOAP API."""

    def __init__(self, app, **kwargs):
        super(MQSAPI, self).__init__(**kwargs)
        self.app = app
        self.ref_no = self._generate_reference_no()
        self.client = self._generate_mqs_username_token()

    def _generate_reference_no(self):
        """Generate Reference number for transactions."""

        x = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        return x

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

    def request(self, cust_id):
        """Send request for TopUp."""

        plan = self.app.config['MQS_PLAN']

        topup_info_xml = """<REQUESTINFO>
        <KEY_NAMEVALUE>
        <KEY_NAME>CUSTOMERNO</KEY_NAME>
        <KEY_VALUE>{}</KEY_VALUE>
        </KEY_NAMEVALUE>
        <TOPUPINFO>
        <PLANCODE>{}</PLANCODE>
        </TOPUPINFO>
        </REQUESTINFO>""".format(cust_id, plan)

        res = self.client.service.TopUp(topup_info_xml, self.ref_no)

        self.response_code, self.response_msg = res[0], res[1]

    def response(self):
        """Parse response for TopUp."""

        if self.response_code == 200:
            res_tree = et.fromstring(self.response_msg)

            self.txn_no = res_tree.findtext('.//TRANSACTIONNO')
            self.txn_msg = res_tree.findtext('.//MESSAGE')


class CustomerInfo(MQSAPI):
    """Define GetCustomerInfo API."""

    def __init__(self, app, **kwargs):
        super(CustomerInfo, self).__init__(app, **kwargs)
        self.response_code = None
        self.response_msg = None
        self.txn_no = None
        self.txn_msg = None

    def request(self, cust_id):
        """Send request for GetCustomerInfo."""

        plan = self.app.config['MQS_PLAN']

        customer_info_xml = """<REQUESTINFO>
        <KEY_NAMEVALUE>
        <KEY_NAME>CUSTOMERNO</KEY_NAME>
        <KEY_VALUE>{}</KEY_VALUE>
        </KEY_NAMEVALUE>
        </REQUESTINFO>""".format(cust_id)

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
