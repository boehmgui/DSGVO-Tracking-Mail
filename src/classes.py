"""
Project: TrackingMailProvider

Description:

"""
__author__ = "Guido Boehm"
__copyright__ = "Copyright 2022, TrackingMailProvider"
__filename__ = "classes.py"
__credits__ = [""]
__version__ = "0.0.1"
__maintainer__ = "Guido Boehm"
__email__ = "olb@family-boehm.de"
__status__ = "Prototype"
__license__ = "see LICENSE file"

#  Copyright 2022, Guido Boehm
#  All Rights Reserved.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#  OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#  NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#  HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#  WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#  OTHER DEALINGS IN THE SOFTWARE.
#  """

import email
import imaplib
import re
import smtplib
import sqlite3

from Validator_Classes import CharField, IntegerField, BoolField, FQDNField

from email.parser import HeaderParser
from datetime import datetime, timedelta, date


class MailHost:
    """
    base class for IMAP and SMTP that defines common attrutes and methods
    """
    username = CharField(1)
    password = CharField(1)
    host = FQDNField()
    port = IntegerField(1, 9999)
    tls = BoolField()
    ssl = BoolField()

    def __init__(self, username, password):
        if username is None or password is None:
            raise ValueError('username or password cannot be empty')
        self.username = username
        self.password = password

    def __str__(self):
        return f'host: {self.host} - port: {self.port}'

    def __repr__(self):
        return f'host:({self.host}) - port:({self.port})'


class IMAP_Class(MailHost):
    """
    this class connects to an IMAP server and provides several methods to read, delete etc. messages
    """
    retention_period = IntegerField(0, 99)

    def __init__(self, username, password, host=None, port=143, ssl=False, tls=False):
        super().__init__(username, password)
        self.host = host
        self.port = port
        self.ssl = ssl
        self.tls = tls
        self.session = None
        if self.ssl:
            self.session = imaplib.IMAP4_SSL(self.host, self.port)
        else:
            self.session = imaplib.IMAP4(self.host, self.port)
        if self.tls:
            # tls_context = ssl.create_default_context()
            # imap_session.starttls(ssl_context=tls_context)
            self.session.starttls()

    def login(self):
        """
        this method logs into the IMAP server with given credentials
        Returns:

        """
        _, ddata = self.session.login(self.username, self.password)

    def folder(self, folder):
        """
        selects a specific folder
        Args:
            folder (str): folder name that shall be selected

        Returns:
            n/a

        """
        self.session.select(folder)

    def empty_folder(self, folder):
        """
        purges emails makred as deleted
        Args:
            folder (str): folder in which the emails are to be purged

        Returns:
            n/a

        """
        self.folder(folder)
        self.session.expunge()

    def trash_mails(self):
        """
        marks all emails older than retention_preiod
        Returns:
            n/a

        """
        before_date = (date.today() - timedelta(days=IMAP_Class.retention_period)).strftime("%d-%b-%Y")
        _, data = self.session.search(None, '(BEFORE "{0}")'.format(before_date))

        msg_ids = data[0].split()
        for msg_id in msg_ids:
            self.session.store(msg_id, '+FLAGS', '\\Deleted')  # move to trash

    def get_email_ids(self, criterion):
        """
        gets ids for all messages based on criterion (e.g. 'UNSEEN')
        Args:
            criterion:

        Returns:

        """
        # filter unseen messages
        _, msg_ids = self.session.search(None, '{0}'.format(criterion))
        return msg_ids[0].split()

    def fetch_message_by_id(self, msg_id):
        """
        reads and returns message  based on id from server
        Args:
            msg_id:

        Returns:

        """
        _, data = self.session.fetch(msg_id, "(RFC822)")
        return data[0][1]

    def quit(self):
        """
        close and release session
        Returns:

        """
        self.session.close()
        self.session.logout()


class Message:
    """
    class that holds an email message
    """
    check_spf = False
    whitelist = []
    SPF_CODES = ["pass", "Pass", "softfail", "SoftFail", "neutral", "Neutral", "none", "None"]

    def __init__(self, message):
        self.message = email.message_from_bytes(message)
        self.bcc = []
        self._spf_check()
        self._whitelist_check()

    def _spf_check(self):
        """
        check whether SPF is OK. If cls attribute check_spf is set to True nno check will be performed and
        _spf_status set to True
        Returns:
            n/a

        """
        if Message.check_spf:
            parser = HeaderParser()
            headers = parser.parsestr(self.message_as_string)
            received_spf = headers.get('Received-SPF')
            self._spf_status = any(code in received_spf for code in Message.SPF_CODES)
        else:
            self._spf_status = True

    @staticmethod
    def get_domain(from_address):
        """
        extrahiert Domain aus der E-Mail Adresse
        :param from_address: zB noreply@dhl.de
        :return: dhl.de
        """
        # return only the domain part
        return re.findall(r'@([a-zA-Z0-9][\w\.-]*[a-zA-Z0-9]\.[a-zA-Z][a-zA-Z\.]*[a-zA-Z])', from_address)[0]

    def _whitelist_check(self):
        """
        check whether sender domain is in whitelist
        Returns:
            n/a

        """
        # if whiteliste is empty set status to true
        if not Message.whitelist:
            self._domain_whitelisted = True
        else:
            # nur die Domain ist relevant
            domain = Message.get_domain(self.message['From'])

            if domain in Message.whitelist:
                self._domain_whitelisted = True
            else:
                self._domain_whitelisted = False

    @property
    def TO_address(self):
        """
        return the 'To' address for this message
        Returns:
            To (str): 'To' address

        """
        return self.message['To']

    @TO_address.setter
    def TO_address(self, addr):
        """
        sets 'To' address
        Args:
            addr (str): valid email address

        Returns:
            n/a

        """
        self.message.replace_header("To", addr)

    @property
    def FROM_address(self):
        """
        returns "From' address for this message
        Returns:
            From (str): 'From' address

        """
        return self.message['From']

    @FROM_address.setter
    def FROM_address(self, addr):
        """
        sets the 'From' address for this message
        Args:
            addr (str): valid email address

        Returns:
            n/a

        """
        self.message.replace_header("FROM", addr)

    @property
    def BCC_address(self) -> list:
        """
        returns 'BCC addresses
        Returns:
            Bcc (lst): list of email addresses

        """
        return self.bcc

    @BCC_address.setter
    def BCC_address(self, addr: list):
        """
        sets 'Bcc' addresses for this message
        Args:
            addr (lst): list of valid email addresse

        Returns:
            n/a

        """
        if not isinstance(addr, list):
            raise ValueError(f'{addr} must be a list of one or more email addresses.')
        self.bcc = addr

    @property
    def spf_status(self):
        """
        returns SPF check status
        Returns:
            _spf_status (bool): result of the SPF check

        """
        return self._spf_status

    @property
    def domain_whitelisted(self):
        """
        returns domain whitelist check status
        Returns:
            _domain_whitelisted (bool): restult of domain whitelist check

        """
        return self._domain_whitelisted

    @property
    def message_as_string(self):
        """
        return message as a string so that it can be sent via smtp
        Returns:

        """
        return self.message.as_string()


class SMTP_Class(MailHost):
    """
    class that holds session to a smtp server
    """

    def __init__(self, username, password, host=None, port=None, ssl=False, tls=False):
        super().__init__(username, password)
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.ssl = ssl
        self.tls = tls
        self.session = None
        if self.ssl:
            self.session = smtplib.SMTP_SSL(self.host, self.port)
        else:
            self.session = smtplib.SMTP(self.host, self.port)
        if self.tls:
            # tls_context = ssl.create_default_context()
            # imap_session.starttls(ssl_context=tls_context)
            self.session.starttls()

    def login(self):
        """
        logs into a smtp server
        Returns:
            n/a

        """
        self.session.login(self.username, self.password)

    def send_message(self, from_address, to_address, message):
        """
        sends an email message
        Args:
            from_address: email addres the message is sent from
            to_address: email addres the message is sent to
            message: email.message.object

        Returns:

        """
        self.session.sendmail(from_address, to_address, message)

    def quit(self):
        """
        terminates the smtp session
        Returns:

        """
        self.session.quit()


class DBClass:
    """
    class that hold connection to a sqlite DB
    """
    def __init__(self, database: str, table: str, retention_period=30, timeout=5):
        """
        - connects to a sqlite DB
        - creates the DB file if it doesn't exist
        - creates table is it doesn't exist
        Args:
            database: path + name of DB
            table: name of table
            timeout: (optional) connection timeout
        """
        self.table = table
        self. conn = sqlite3.connect(database, timeout)
        with self.conn:
            self.conn.execute('''CREATE TABLE IF NOT EXISTS alias (email text, alias text primary key, 
            date date_column)''')
        self.rentention_period = retention_period

    @staticmethod
    def validate(date):
        """
        validates date format
        Args:
            date (str): date to be verified

        Returns:
            n/a
        Raises:
            ValueError: if date is not in format %Y-%m-%d

        """
        if not isinstance(date, str):
            raise ValueError(f'{date} must be a string not integer.')
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError as ex:
            raise ValueError("Incorrect data format, must be YYYY-MM-DD - {0}".format(ex))

    def add_alias(self, address: str, alias: str, date: str):
        """
        method to add an alias to the database
        Args:
            address (str): original email address
            alias (str): email alias
            date (str): date the alias was added

        Returns:

        """
        DBClass.validate(date)
        with self.conn:
            self.conn.execute(f'''INSERT INTO {self.table} VALUES('{address}', '{alias}', '{date}')''')

    def get_address(self, alias: str) -> str:
        """
        method returns the email address based on alias
        Args:
            alias (str): alias to search for

        Returns:
            address (str): real email address-, the one the email will be sent to

        """
        c = self.conn.cursor()
        c.execute(f'''SELECT * FROM {self.table} WHERE alias='{alias}';''')
        row = c.fetchone()
        return row[0] if row else None

    def purge_old_entries(self):
        """
        method will delete entrie older than retention
        Args:

        Returns:
            deleted_rows (int): returns the number of deleted rows

        """
        cursor = self.conn.cursor()
        cursor.execute(f'''SELECT * FROM {self.table}''')
        row_count = len(cursor.fetchall())
        with self.conn:
            self.conn.execute(f'''DELETE FROM {self.table} WHERE date <= date("now", "-{self.rentention_period} day")''')

        cursor = self.conn.cursor()
        cursor.execute(f'''SELECT * FROM {self.table}''')
        new_row_count = len(cursor.fetchall())
        deleted_rows = row_count - new_row_count

        return deleted_rows

    def commit(self):
        """
        commits changes to DB
        Returns:

        """
        self.conn.commit()

    def close(self):
        """
        closes connection
        Returns:

        """
        self.conn.close()


def main(args=None):
    """
    main function
    Args:
        args:

    Returns:

    """
    pass


if __name__ == "__main__":

    main()
