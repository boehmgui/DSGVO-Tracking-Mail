"""
This script enabled to hanlde tracking emails from logistician in a DSGVO compliant way.
For detailed info refer to README.md
"""
__author__ = "Guido Boehm"
__copyright__ = "Copyright 2022, TrackingMailProvider"
__filename__ = "DSGVO_Tracking_Mail.py"
__credits__ = [""]
__version__ = "2.0.0"
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
#

import logging
import sys
import traceback
from csv import reader
from logging.handlers import RotatingFileHandler
from pathlib import Path

import yaml

from classes import *

see__version__ = "v.2.0.0"

SCRIPT_DIR = Path(sys.argv[0]).resolve().parent

# instantiate logger outside so that is it available everywhere
logger = logging.getLogger(__name__)


def create_logging(config):
    """
    :param config: Liste mit folgenden Werten:
                    0. Pfad/Name des Logfiles
                    1. Logging Level für Dateilogs
                    2. Logging Level für Screenlogs
                    3. Logfilegröße bevor rotiert wird
                    4. Anzahl der rotierten Logfiles
    :return: Handle zum Logger
    """
    pathtolog = config[0]
    level_file = logging.getLevelName((config[1]).upper())
    level_screen = logging.getLevelName(config[2].upper())
    filesize = int(config[3])
    filecount = int(config[4])

    # Logfile logger
    logger.setLevel(level_file)
    # Add the log message handler to the logger
    handler = logging.handlers.RotatingFileHandler(
            pathtolog, maxBytes=filesize, backupCount=filecount)
    formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # create console handler
    ch = logging.StreamHandler()
    ch.setLevel(level_screen)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


def import_new_aliases(import_file, db_con):
    """
    Imports data from csv file into DB.
    Sample data:
    foo@foobar.com,firstname.secondname@domain.com
    The current date (yyyy-mm-dd) will be added as 3rd value
    Args:
        import_file (Path): location of the import file
        db_con : db handler

    Returns:

    """
    logger.debug('Aliases werden zur DB hinzugefügt')
    with import_file.open('r') as file:
        line = reader(file)
        # import the alias entries from - date will always be the current one
        counter = 0
        for row in line:
            try:
                db_con.add_alias(row[0], row[1], date.today().strftime('%Y-%m-%d'))
                counter += 1
            except sqlite3.IntegrityError:
                logger.error('Alias {0} existiert bereits in DB -> uebersprungen'.format(row[1]))
        logger.debug('{0} Einträge zur DB hinzugefügt'.format(counter))
    # delete file
    import_file.unlink()


def main():
    """
    Main function

    """
    # build path to config file
    config_file = Path(SCRIPT_DIR, "config/config.yaml")
    with config_file.open('r') as file:
        # The FullLoader parameter handles the conversion from YAML
        # scalar values to Python the dictionary format
        config = yaml.full_load(file)

    logging = [Path(config['LOGGING']['path_to_logfile'] + config['LOGGING']['logfilename']),
               config['LOGGING']['level_file'],
               config['LOGGING']['level_screen'],
               config['LOGGING']['filesize'],
               config['LOGGING']['filecount']
               ]

    logger = create_logging(logging)
    logger.info('Programmstart Version {0}'.format(__version__))

    from_addr = config['FORWARD']['from']

    # check whether keys are present in yaml
    if config['FORWARD'].get('bcc') is None:
        bcc_addr = []
    else:
        # sanitize 'bcc' from None values
        bcc_addr = list(filter(None, config['FORWARD']['bcc']))

    Message.check_spf = config['FORWARD']['SPFcheck']

    # check whether keys are present in yaml
    if config['WHITELIST'] is None or config['WHITELIST'].get('allowed_domains') is None:
        Message.whitelist = []
    else:
        # sanitize from None values
        Message.whitelist = list(filter(None, config['WHITELIST'].get('allowed_domains')))

    Path(config['SQLITE']['directory']).mkdir(parents=True, exist_ok=True)
    database = str(Path(config['SQLITE']['directory'], config['SQLITE']['dbname']).resolve())

    # connect to DB and import new aliases
    db_con = DBClass(database, config['SQLITE']['table'], config['SQLITE']['retention_period'])
    if Path(config['IMPORT']['directory'], config['IMPORT']['filename']).is_file():
        import_file = Path(config['IMPORT']['directory'], config['IMPORT']['filename'])
        import_new_aliases(import_file, db_con)

    imap_error = False

    try:
        logger.debug('Verbindung zum imap Server aufbauen')
        imap_session = IMAP_Class(
                config['IMAP']['username'], config['IMAP']['password'], config['IMAP']['host'], config['IMAP']['port'],
                config['IMAP']['ssl'], config['IMAP']['tls']
        )
        imap_session.login()
        IMAP_Class.retention_period = config['IMAP']['retention_period']
    except TimeoutError as err:
        logger.error('Request timed out: %s' % err)
        imap_error = True

    except OSError as err:
        logger.error('Host {0}:{1} not found: {2}'.format(config['IMAP']['host'], config['IMAP']['port'], err))
        imap_error = True

    except imaplib.IMAP4.error as err:
        logger.error('IMAPClient.AbortError: %s' % err)
        imap_error = True

    except Exception as err:
        logger.error('Unknown error: %s' % err)
        logger.error(traceback.format_exc())
        imap_error = True

    # terminate script if imap_error
    if imap_error:
        sys.exit(1)

    # fetch unseen emails
    imap_session.folder('Inbox')
    try:
        msg_ids = imap_session.get_email_ids("NOT SEEN")
        logger.debug('{0} neue E-Mails gefunden'.format(len(msg_ids)))
    except imaplib.IMAP4.error as err:
        logger.error(f"Fehler beim Lesen der E-Mails\n{err}\nProgramm wird beendet")
        # terminate in case of exception
        imap_session.quit()
        sys.exit(1)

    # create list message instances from new emails
    messages = []
    for msg_id in msg_ids:
        message = Message(imap_session.fetch_message_by_id(msg_id))
        # get the real email address from DB based on "To" address, which is the alias from email
        # and replace headers
        # no need to further process this message if checks are not OK
        logger.debug('Message {0}: Domain whitelisted: {1}; SPF OK: {2}'.format(
                message.FROM_address, message.domain_whitelisted, message.spf_status))
        if not message.domain_whitelisted or not message.spf_status:
            continue
        # if alias not found, skip this message
        to_address = db_con.get_address(message.TO_address)
        if not to_address:
            logger.debug('keine E-Mail Adresse für Alias {0} in DB gefunden'.format(message.TO_address))
            continue
        message.TO_address = to_address
        message.FROM_address = from_addr
        message.BCC_address = bcc_addr
        messages.append(message)

    # purge old emails and close session
    # for an unknown reason sometines an EOF error ocurrs when searching for emails to be deleted.
    # as this is harmless (only mails will not be deleted) it is safe to continue
    try:
        imap_session.trash_mails()
    except Exception as err:
        logger.error('That damned EOF error has occurred again. When time permits, need to do RCA {0}'.format(err))
    imap_session.empty_folder('INBOX')
    imap_session.quit()

    # purge DB entries that are beyond retention period
    aliases_purged = db_con.purge_old_entries()
    logger.debug("{0} alte Einträge aus DB entfernt".format(aliases_purged))
    db_con.close()

    if not messages:
        logger.debug('keine Emails zu versenden')
        sys.exit(0)
    try:
        logger.debug('Verbindung zum smtp Server aufbauen')
        smtp_session = SMTP_Class(
                config['SMTP']['username'], config['SMTP']['password'], config['SMTP']['host'], config['SMTP']['port'],
                config['SMTP']['ssl'], config['SMTP']['tls']
        )
    except smtplib.SMTPException as err:
        logger.error(
                'Fehler bei der Verbindung mit SMTP Server {0}:{1} - {2}\nProgramm wird beendet'.format(
                        config['SMTP']['host'], config['SMTP']['port'], err))
        sys.exit(1)

    for message in messages:
        # open authenticated SMTP connection and send message with
        # specified envelope from and to addresses
        try:
            smtp_session.login()

            smtp_session.send_message(message.FROM_address, [message.TO_address] + message.BCC_address,
                                      message.message_as_string)
            smtp_session.quit()
            logger.debug("E-Mail erfolgreich gesendet! {0}".format([message.TO_address] + message.BCC_address))
        except Exception as err:
            logger.error("Fehler beim senden des E-Mails\n{0}".format(err))
            smtp_session.quit()


if __name__ == '__main__':
    print("###########################################")
    print("#                                         #")
    print("#                                         #")
    print("#      ShipmentTracking Version {0}      #".format(__version__))
    print("#                                         #")
    print("#                                         #")
    print("###########################################")
    main()
