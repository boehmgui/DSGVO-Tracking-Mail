"""
Project: TrackingMailProvider
Filename: ${FILE_NAME}
Description

"""
__author__ = "Guido Boehm"
__filename__ = "${FILE_NAME}"
__credits__ = [""]
__license__ = ""
__version__ = "0.0.1"
__maintainer__ = "Guido Boehm"
__email__ = "guido@family-boehm.de"
__status__ = "Prototype"
__copyright__ = "Copyright(c) 2022) - Guido Boehm"

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
#
import email
import sqlite3
import unittest

from csv import reader
from pathlib import Path
from src.classes import *
from unittest import TestCase
from datetime import datetime, timedelta, date

DATA_DIR = Path(Path.cwd(), 'data')


class Test_Credentials(TestCase):
    def test_invalid_username(self):
        """test that invalid username raises ValueErrors"""
        min_ = 1
        bad_values = list(range(min_ - 5, min_))
        bad_values += ['', None]
        for i, value in enumerate(bad_values):
            with self.subTest(test_number=i):
                with self.assertRaises(ValueError):
                    instance_ = MailHost(value, 'valid_password')

    def test_invalid_password(self):
        """test that invalid password raises ValueErrors"""
        min_ = 1
        bad_values = list(range(min_ - 5, min_))
        bad_values += ['', None]
        for i, value in enumerate(bad_values):
            with self.subTest(test_number=i):
                with self.assertRaises(ValueError):
                    instance_ = MailHost('valid_username', value)


class TestDBClass(TestCase):

    def setUp(self) -> None:
        self.table = 'alias'
        self.conn = DBClass(Path(DATA_DIR, 'test.db'), self.table)

    def tearDown(self) -> None:
        # delete DB
        self.conn.close()
        Path(DATA_DIR, 'test.db').unlink()

    def test_validate(self):
        """tests date format validation"""
        bad_values = ['a', 1, '2022.02.02', '01.01.2022', '2022/02/02', '2022-13-44']
        for i, value in enumerate(bad_values):
            with self.subTest(test_number=i):
                with self.assertRaises(ValueError):
                    DBClass.validate(value)

        # good value - must not raise any exception
        DBClass.validate(date.today().strftime('%Y-%m-%d'))

    def test_add_alias(self):
        import_file = Path(DATA_DIR, 'valid_data.csv')
        with import_file.open('r') as file:
            line = reader(file)
            i = 0
            for row in line:
                with self.subTest(test_number=i):
                    self.conn.add_alias(row[0], row[1], date.today().strftime('%Y-%m-%d'))
                    i += 1

        import_file = Path(DATA_DIR, 'invalid_data.csv')
        with import_file.open('r') as file:
            line = reader(file)
            for row in line:
                with self.subTest(test_number=i):
                    with self.assertRaises(sqlite3.IntegrityError):
                        self.conn.add_alias(row[0], row[1], date.today().strftime('%Y-%m-%d'))
                    i += 1

    def test_get_address(self):
        import_file = Path(DATA_DIR, 'valid_data.csv')
        with import_file.open('r') as file:
            line = reader(file)
            for row in line:
                self.conn.add_alias(row[0], row[1], date.today().strftime('%Y-%m-%d'))
        # query in DB
        self.assertEqual(self.conn.get_address('alias3@alias.com'), 'foo3@foobar.com')
        # query not in DB
        self.assertIsNone(self.conn.get_address('not_in_db'))

    def test_purge_old_entries(self):
        delta = [0, 5, 40, 10]
        import_file = Path(DATA_DIR, 'valid_data.csv')
        i = 0
        today_ = date.today()
        with import_file.open('r') as file:
            line = reader(file)
            for row in line:
                date_ = today_ - timedelta(delta[i])
                self.conn.add_alias(row[0], row[1], date_.strftime('%Y-%m-%d'))
                i += 1
        with self.subTest(test_number=0):
            # 1 row should have been deleted
            self.assertEqual(1, self.conn.purge_old_entries())

        with self.subTest(test_number=1):
            # no row should have been deleted
            self.assertEqual(0, self.conn.purge_old_entries())


class TestMessage(TestCase):

    def test_to_address(self):
        import_file = Path(DATA_DIR, 'test_subject.eml')
        with import_file.open('rb') as file:
            file_content = file.read()
            self.test_message = Message(file_content)

        with self.subTest(test_number=0):
            self.assertEqual(self.test_message.TO_address, 'testemail@example.com')
        self.test_message.TO_address = 'fritz_fuchs@bauwagen.de'
        with self.subTest(test_number=1):
            self.assertEqual(self.test_message.TO_address, 'fritz_fuchs@bauwagen.de')

    def test_from_address(self):
        import_file = Path(DATA_DIR, 'test_subject.eml')
        with import_file.open('rb') as file:
            file_content = file.read()
            self.test_message = Message(file_content)

        with self.subTest(test_number=0):
            self.assertEqual(self.test_message.FROM_address, 'Paul Positiv <paul_positive@example.com>')
        self.test_message.FROM_address = 'fritz_fuchs@bauwagen.de'
        with self.subTest(test_number=1):
            self.assertEqual(self.test_message.FROM_address, 'fritz_fuchs@bauwagen.de')

    def test_bcc_address(self):
        import_file = Path(DATA_DIR, 'test_subject.eml')
        with import_file.open('rb') as file:
            file_content = file.read()
            self.test_message = Message(file_content)
        self.test_message.bcc = ['foo@foobar.com', 'fritz_fuchs@bauwagen.de']
        self.assertEqual(self.test_message.bcc, ['foo@foobar.com', 'fritz_fuchs@bauwagen.de'])

    def test_spf_status(self):
        # SPF status: pass
        Message.check_spf = True
        import_file = Path(DATA_DIR, 'test_subject.eml')
        with import_file.open('rb') as file:
            file_content = file.read()
            self.test_message = Message(file_content)
        with self.subTest(test_number=0):
            self.assertEqual(self.test_message.spf_status, True)

        # SPF status "softfail"
        Message.check_spf = True
        import_file = Path(DATA_DIR, 'test_subject_softfail.eml')
        with import_file.open('rb') as file:
            file_content = file.read()
            self.test_message = Message(file_content)
        with self.subTest(test_number=1):
            self.assertEqual(self.test_message.spf_status, True)

        # SPF status "neutral"
        Message.check_spf = True
        import_file = Path(DATA_DIR, 'test_subject_neutral.eml')
        with import_file.open('rb') as file:
            file_content = file.read()
            self.test_message = Message(file_content)
        with self.subTest(test_number=2):
            self.assertEqual(self.test_message.spf_status, True)

        # SPF status "none"
        Message.check_spf = True
        import_file = Path(DATA_DIR, 'test_subject_none.eml')
        with import_file.open('rb') as file:
            file_content = file.read()
            self.test_message = Message(file_content)
        with self.subTest(test_number=3):
            self.assertEqual(self.test_message.spf_status, True)

        # SPF status "fail"
        Message.check_spf = True
        import_file = Path(DATA_DIR, 'test_subject_fail.eml')
        with import_file.open('rb') as file:
            file_content = file.read()
            self.test_message = Message(file_content)
        with self.subTest(test_number=4):
            self.assertEqual(self.test_message.spf_status, False)

        # SPF status "fail but check disabled
        Message.check_spf = False
        import_file = Path(DATA_DIR, 'test_subject_fail.eml')
        with import_file.open('rb') as file:
            file_content = file.read()
            self.test_message = Message(file_content)
        with self.subTest(test_number=5):
            self.assertEqual(self.test_message.spf_status, True)

    def test_domain_whitelisted(self):
        import_file = Path(DATA_DIR, 'test_subject.eml')
        with import_file.open('rb') as file:
            file_content = file.read()
            self.test_message = Message(file_content)
        # empty whitelist
        with self.subTest(test_number=0):
            self.assertEqual(self.test_message.domain_whitelisted, True)

        # domain in whitelist
        Message.whitelist = ['example.com']
        import_file = Path(DATA_DIR, 'test_subject.eml')
        with import_file.open('rb') as file:
            file_content = file.read()
            self.test_message = Message(file_content)
        with self.subTest(test_number=1):
            self.assertEqual(self.test_message.domain_whitelisted, True)

        # domain not in whitelist
        Message.whitelist = ['foobar.com']
        import_file = Path(DATA_DIR, 'test_subject.eml')
        with import_file.open('rb') as file:
            file_content = file.read()
            self.test_message = Message(file_content)
        self.test_message.whitelist = ['foobar.com']
        with self.subTest(test_number=2):
            self.assertEqual(self.test_message.domain_whitelisted, False)


def main(args=None):
    pass


if __name__ == "__main__":

    main()