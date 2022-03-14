# TrackingMailProvider
Für die Sendungsverfolgung werden anonymisierte E-Mail Adressen an den 
jeweiligen Logistiker gegeben.
Der TrackingMailProvider wandelt diese anonyme E-Mail Adresse in die 
richtige des Kunden und leitet die Versandbenacheichtigungen 
(Tracking-Mails) an den Kunden weiter.

## Konzept
Über den Versanddatenexport der JTL-Wawi wird statt der echten Kunden 
E-Mail Adresse eine in der Formm <Auftragsnummer>@tracking.sannes-stickdesign.de> an den Logistiker übergeben.

Die E-Mail an diese Adressen landen in einem Catch-All-Mailkonto. Das 
Script prüft, ob neue E-Mail ein getroffen sind. Dazu wird es in 
intervallen, zB über einen Cron Job (Linux) oder die Aufgabenplanung 
(Windows) in intervallen gestartet.

Bei einer neuen E-Mail prüft das Script
1. ob die Domain der Absenderadresse in einer Whitelist steht (Verhinderung 
   von unerwünschtem Spam)
2. ob es zu der Auftragsnummer aus dr Empfängeradresse (Teil vor dem @) 
   einen Auftrag in der JTL Wawi gibt
Die richtige Ziel-, also Kunden E-Mail Adresse wird dann aus den 
   Auftragsdaten der Wawi ausgelesen


## Konfigurationsdatei
Die einzige Konfigurationsdatei ist eine .ini (imap.ini) mit den folgenden 
Sektionen:
``` ini
[IMAP]
HOST = <ip-addresse oder FQDN des E-Mail Servers mit dem CATCH-ALL Postfach
USERNAME = <Benutzername>
PASSWORD = <Passwort>
imap_port = 143
ssl = True
tls = True
idle = 10
retention_period = 360

[SMTP]
HOST = <ip-addresse oder FQDN des E-Mail Servers über welchen die E-Mail an 
die Kunden gesendet werden>
USERNAME = <Benutzername>
PASSWORD = <Passwort>
ssl = True
tls = True
smtp_port = 587

[FORWARD]
FROM: <Absenderaddresse für die E-Mails an die Kunden>
BCC: <E-Mail Adresse für BCC>
SPFcheck = True

[MSSQL]
host = <ip adresse/FQDN>\JTLWAWI
username = <Benutzername>
password = <Passwort>
database = eazybusiness
driver = {SQL Server}
port = 49751

[LOGGING]
logfilename = imap.log
path_to_logfile = ./
level_file = INFO
level_screen = INFO
filesize = 10000000
filecount = 5

[SQL]
sql_query = select k.kKunde, k.cMail from tRechnungsadresse k inner join tBestellung b on k.kKunde=b.tKunde_kKunde and b.cBestellNr =

[WHITELIST]
allowed_domains = ["dhl.de","dpd.de","parcel.one","family-boehm.de","sannes-sticdesign.de"]
```