import traceback
import configparser
import os
import logging
import smtplib
import email
import imaplib
import sys
from email.parser import Parser

try:
    import pyodbc
except:
    pass
import json
import datetime
import ssl

from imapclient import IMAPClient
from logging.handlers import RotatingFileHandler

__version__ = "1.02"


# build path to config file
inifile = os.path.join(os.path.dirname(sys.argv[0]), "config/imap.ini")
# instantiate logger outside so that is it available everywhere
logger = logging.getLogger(__name__)

#  globale Parameter:
seenSearch = "SEEN"
notSeenSearch = "NOT SEEN"
spf_codes = ["pass", "softfail", "Pass", "SoftFail", "neutral", "Neutral"]


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
    level_file = logging.getLevelName(config[1])
    level_screen = logging.getLevelName(config[2])
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


def connect_to_db(driver, port, server, database, username, password):
    """

    :param driver:
    :param port:
    :param server:
    :param database:
    :param username:
    :param password:
    :return:
    """
    connection = pyodbc.connect(
            'DRIVER=' + driver + ';PORT=' + port + ';SERVER=' + server + \
            ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)

    return connection


def get_from_domain(from_address):
    """
    extrahiert Domain aus der E-Mail Adresse
    :param from_address: zB noreply@dhl.de
    :return: dhl.de
    """
    return from_address.split("@")[1]


def in_whitelist(from_address, whitelist):
    """

    :param from_address: zB noreply@dhl.de
    :param whitelist: [dhl.de, dpd.de}
    :return: true or false
    """

    # nur die Domain ist relevant
    domain = get_from_domain(from_address)

    if domain in whitelist:
        return True
    else:
        return False


def move_to_trash_before_date(connection, folder, days_before):
    before_date = (datetime.date.today() - datetime.timedelta(
            days_before)).strftime("%d-%b-%Y")  # date string, 04-Jan-2013
    typ, data = connection.search(None, '(BEFORE "{0}")'.format(
            before_date))  # search pointer for msgs before before_date

    if data != ['']:  # if not empty list means messages exist
        msg_ids = data[0].split()
        for msg_id in msg_ids:
            connection.store(msg_id, '+FLAGS', '\\Deleted')  # move to trash
            logger.info("Deleted message ID {0}.".format(msg_id))
    else:
        logger.warning("Keine alten E-mails zum Löschen gefunden")

    return


def empty_folder(connection, folder, do_expunge=True):
    logger.info("Empty '{0}' & Expunge all mail...".format(folder))
    if do_expunge:
        connection.expunge()
    return


def main():
    """

    """
    config = configparser.ConfigParser()
    config.sections()
    config.read(inifile)

    imap = {
        'host': config.get('IMAP', 'HOST'),
        'username': config.get('IMAP', 'USERNAME'),
        'password': config.get('IMAP', 'PASSWORD'),
        'imap_port': config.getint('IMAP', 'imap_port'),
        'ssl': config.getboolean('IMAP', 'ssl'),
        'tls': config.getboolean('IMAP', 'tls')
        }
    retention_period = int(config.get('IMAP', 'retention_period'))
    smtp = {
        'host': config.get('SMTP', 'HOST'),
        'username': config.get('SMTP', 'USERNAME'),
        'password': config.get('SMTP', 'PASSWORD'),
        'smtp_port': config.getint('SMTP', 'smtp_port'),
        'ssl': config.getboolean('SMTP', 'ssl'),
        'tls': config.getboolean('SMTP', 'tls')
    }

    sql_uid = config.get('MSSQL', 'username')
    sql_pwd = config.get('MSSQL', 'password')
    sql_host = config.get('MSSQL', 'host')
    sql_port = config.get('MSSQL', 'port')
    sql_db = config.get('MSSQL', 'database')
    sql_driver = config.get('MSSQL', 'driver')

    sql_query = config.get('SQL', 'sql_query')

    from_addr = config.get('FORWARD', 'FROM')
    bcc_addr = config.get('FORWARD', 'BCC')

    SPF_check = config.getboolean('FORWARD', 'SPFcheck')

    logging = [os.path.join(config.get('LOGGING',
                                       'path_to_logfile') + config.get(
            'LOGGING', 'logfilename')),
               config.get('LOGGING', 'level_file'),
               config.get('LOGGING', 'level_screen'),
               config.get('LOGGING', 'filesize'),
               config.get('LOGGING', 'filecount')
               ]

    allowed_domains = json.loads(config.get("WHITELIST", "allowed_domains"))

    logger = create_logging(logging)
    logger.info('Programmstart Version {0}'.format(__version__))

    imap_session = None
    imap_error = True

    while imap_error:
        try:
            logger.info('Verbindung zum imap Server aufbauen')
            if imap['ssl']:
                imap_session = imaplib.IMAP4_SSL(imap['host'], imap['imap_port'])
            else:
                imap_session = imaplib.IMAP4(imap['host'], imap['imap_port'])
            if imap['tls']:
                # tls_context = ssl.create_default_context()
                # imap_session.starttls(ssl_context=tls_context)
                imap_session.starttls()
            imap_session.login(imap['username'], imap['password'])
            imap_session.select('INBOX')

            imap_error = False

        except TimeoutError as e:
            logger.error('Request timed out: %s' % e)
            imap_error = True

        except OSError as e:
            logger.error('Host not found: %s' % e)

        except Exception as e:
            logger.error('Unknown error: %s' % e)
            logger.error(traceback.format_exc())

        except IMAPClient.AbortError as e:
            imap_error = True
            logger.error('IMAPClient.AbortError: %s' % e)

        logger.info('Suche nach ungelesenen E-Mails')

        try:
            # filter unseen messages
            resp, msg_ids = imap_session.search(None, "UNSEEN")
            msg_ids = msg_ids[0].split()
        except:
            logger.error("Fehler beim Lesen der E-Mails")
            raise

        # Verbindung zur Wawi aufbauen
        try:
            db_connection = connect_to_db(sql_driver, sql_port,
                                          sql_host, sql_db, sql_uid, sql_pwd)
        except:
            # beende Skript, da weitermachen ohne Wawi Verbindung keinen Sinn
            # ergibt
            logger.error("Verbindung zur Wawi fehlgeschlagen")
            raise

        parser = Parser()
        for msg_id in msg_ids:
            logger.info("verarbeite Email ID : {0}".format(msg_id))

            resp, data = imap_session.fetch(msg_id, "(RFC822)")
            email_data = data[0][1]

            # extrahiere "Received-SPF" aus Header für SPF check
            email_header = parser.parsestr(str(data[0][1], 'utf-8'),
                                           headersonly=True)
            received_spf = email_header.get('Received-SPF')

            # create a Message instance from the email data
            message = email.message_from_bytes(email_data)
            logger.debug("To-Address: {0}".format(message['To']))

            if SPF_check and ((received_spf is None) or not (any(code in
                                                                 received_spf
                                                                 for code in
                                                                 spf_codes))
                              or not in_whitelist(message['From'][1:-1],
                                                  allowed_domains)):

                # mit nächstem Wert in mg_ids weitermachen, da Absender Domain
                # nicht in Whitelist vorhanden oder SPF Check fehlgeschlagen
                logger.warning("SPF Check fehlgeschlagen ({0}) - oder Domain "
                               "der "
                               "Absender Adresse {1} nicht in "
                               "whitelist".format(received_spf,
                                                  message['From']))
                continue

            elif not SPF_check and not in_whitelist(message['From'][1:-1],
                                                    allowed_domains):
                # mit nächstem Wert in mg_ids weitermachen,
                # da Absenderadresse nicht in WhiteList - SPF check nicht
                # notwendig
                logger.warning("Domain der Absender Adresse {0} nicht in "
                               "whitelist".format(
                                message['From']))
                continue

            # nur die eigentliche E-mail Adresse separieren
            # <abc@domain.de> -> abc@domain.de
            to_address = message['To']
            to_address = to_address.split("<")[-1]
            to_address = to_address.split(">")[0]

            # Teil vor "@" enthält die Auftragsnummer zu dieser E-Mail
            auftragsnummer = to_address.split("@")[0]
            query = sql_query + " '{0}'".format(auftragsnummer)

            try:
                with db_connection.cursor() as cursor:
                    cursor.execute(query)
                    row = cursor.fetchone()
            except:
                logger.error("Wawi DB Abfrage fehlgeschlagen")
                raise

            if row:
                # 2. Wert in row enthält die original E-Mail Adresse des
                # Auftrags
                to_addr = row[1]
                logger.debug("Korrespondierende E-Mail Adresse in Wawi "
                             "gefunden: {0}".format(to_addr))

                # replace headers (could do other processing here)
                message.replace_header("From", from_addr)
                message.replace_header("To", to_addr)

                # open authenticated SMTP connection and send message with
                # specified envelope from and to addresses
                recipients = [to_addr, bcc_addr]
                try:
                    if smtp['ssl']:
                        smtp_session = smtplib.SMTP_SSL(smtp['host'], smtp['smtp_port'])
                    else:
                        smtp_session = smtplib.SMTP(smtp['host'], smtp['smtp_port'])
                    if smtp['tls']:
                        smtp_session.starttls()
                    smtp_session.login(smtp['username'], smtp['password'])
                    smtp_session.sendmail(from_addr, recipients,
                                          message.as_string())
                    smtp_session.quit()
                    logger.info(
                            "E-Mail erfolgreich gesendet! {0}".format(
                                recipients))
                except Exception:
                    logger.error("Fehler beim senden des E-Mails")

        # Verbindung zur wawi beenden
        db_connection.close()

        # alte E-Mails löschen
        move_to_trash_before_date(imap_session, 'INBOX', retention_period)
        empty_folder(imap_session, 'INBOX', True)

        imap_session.close()
        imap_session.logout()


if __name__ == '__main__':
    print("###########################################")
    print("#                                         #")
    print("#                                         #")
    print("#      ShipmentTracking Version {0}      #".format(__version__))
    print("#                                         #")
    print("#                                         #")
    print("###########################################")
    main()
