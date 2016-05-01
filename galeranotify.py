#!/usr/bin/env python3
#
# Script to send email notifications when a change in Galera cluster membership
# occurs.
#
# Complies with http://www.codership.com/wiki/doku.php?id=notification_command
#
# Author: Gabe Guillen <gguillen@gesa.com>
# Modified by: Josh Goldsmith <joshin@hotmail.com>
# Modified by: Stephan Wienczny <stephan.wienczny@ybm-deutschland.de>
# Version: 1.4
# Release: 5/14/2015
# Use at your own risk.  No warranties expressed or implied.
#

import sys
import argparse
import socket

from datetime import datetime
from abc import ABC, abstractmethod

# Change this to some value if you don't want your server hostname to show in
# the notification emails
THIS_SERVER = socket.gethostname()

# Server hostname or IP address
SMTP_SERVER = 'YOUR_SMTP_HERE'
# Server port
SMTP_PORT = 25

# Set to True if you need SMTP over SSL
SMTP_SSL = False

# Set to True if you need to authenticate to your SMTP server
SMTP_AUTH = False
# Fill in authorization information here if True above
SMTP_USERNAME = ''
SMTP_PASSWORD = ''

# Takes a single sender
MAIL_FROM = 'YOUR_EMAIL_HERE'
# Takes a list of recipients
MAIL_TO = ['SOME_OTHER_EMAIL_HERE']
# Subject of mail sent
MAIL_SUBJECT = 'Galera Notification: ' + THIS_SERVER


# Edit below at your own risk
################################################################################


def main(argv):
    parser = argparse.ArgumentParser(add_help=True, description='Mysql wsrep notification script')
    parser.add_argument("-u", "--uuid", action="store", dest="uuid",
                        help="node uuid", metavar="UUID")
    parser.add_argument("-i", "--index", action="store", dest="index",
                        help="node index", metavar="INDEX")
    parser.add_argument("-s", "--status", action="store", dest="status",
                        help="node status", metavar="STATUS")
    parser.add_argument("-p", "--primary", action="store", dest="primary",
                        help="node primary state <yes/no>", metavar="PRIMARY")
    parser.add_argument("-m", "--members", action="store", dest="members",
                        help="comma-separated list of the component member UUIDs", metavar="MEMBERS")
    parser.add_argument("-d", "--debug", action="store_true", dest="debug", default=False,
                        help="print state and exit")

    args = parser.parse_args(args=argv)

    message_obj = GaleraStatus(THIS_SERVER)
    message_obj.set_uuid(args.uuid)
    message_obj.set_index(args.index)
    message_obj.set_status(args.status)
    message_obj.set_primary(args.primary)
    message_obj.set_members(args.members)

    if args.debug:
        print(str(message_obj))

    actions = []
    if SMTP_SERVER:
        actions.append(SMTPAction(SMTP_SERVER, SMTP_PORT, SMTP_SSL, SMTP_AUTH, SMTP_USERNAME,
                                  SMTP_PASSWORD, MAIL_FROM, MAIL_TO, MAIL_SUBJECT))

    return_code = 0

    for action in actions:
        try:
            action.notify(message_obj)
        except Exception as e:
            print("Unable to send notification: %s" % e)
            return_code = 1

    sys.exit(return_code)


class NotificationAction(ABC):
    @abstractmethod
    def notify(self, message):
        pass


class SMTPAction(NotificationAction):
    def __init__(self, smtp_server, smtp_port, use_ssl, use_auth, smtp_user, smtp_pass, smtp_from,
                 smtp_to, smtp_subject):
        self._server = smtp_server
        self._port = smtp_port
        self._use_ssl = use_ssl
        self._use_auth = use_auth
        self._user = smtp_user
        self._pass = smtp_pass
        self._from = smtp_from
        self._to = smtp_to
        self._subject = smtp_subject

    def notify(self, message):
        from smtplib import SMTP, SMTP_SSL
        from email.mime.text import MIMEText

        if message.get_count() <= 0:
            return

        msg = MIMEText(str(message))

        msg['From'] = self._from
        msg['To'] = ', '.join(self._to)
        msg['Subject'] = self._subject
        msg['Date'] = datetime.now().strftime("%m/%d/%Y %H:%M")

        with SMTP_SSL() if self._use_ssl else SMTP() as mailer:
            mailer.connect(self._server, self._port)
            if self._use_auth:
                mailer.login(self._user, self._pass)
            mailer.send_message(msg)


class GaleraStatus:
    def __init__(self, server):
        self._server = server
        self._status = ""
        self._uuid = ""
        self._primary = ""
        self._members = ""
        self._index = ""
        self._count = 0

    def set_status(self, status):
        self._status = status
        self._count += 1

    def get_status(self):
        return self._status

    def set_uuid(self, uuid):
        self._uuid = uuid
        self._count += 1

    def get_uuid(self):
        return self._uuid

    def set_primary(self, primary):
        if primary is not None:
            self._primary = primary.capitalize()
            self._count += 1

    def get_primary(self):
        return self._primary

    def set_members(self, members):
        if members is not None:
            self._members = members.split(',')
            self._count += 1

    def get_members(self):
        return self._members

    def set_index(self, index):
        if index is not None:
            self._index = index
            self._count += 1

    def get_index(self):
        return self._index

    def get_count(self):
        return self._count

    def __str__(self):
        message = "Galera running on {} has reported the following cluster membership change{}:" \
                  "\n\n".format(self._server, "s" if self._count > 0 else "")

        if self._status:
            message += "Status of this node: {}\n\n" .format(self._status)

        if self._uuid:
            message += "Cluster state UUID: {}\n\n".format(self._uuid)

        if self._primary:
            message += "Current cluster component is primary: {}\n\n".format(self._primary)

        if self._members:
            message += "Current members of the component:\n"

            if self._index:
                for i in range(len(self._members)):
                    if i == int(self._index):
                        message += "-> "
                    else:
                        message += "-- "

                    message += self._members[i] + "\n"
            else:
                message += "\n".join(("  " + str(x)) for x in self._members)

            message += "\n"

        if self._index:
            message += "Index of this node in the member list: {}\n".format(self._index)

        return message


if __name__ == "__main__":
    main(sys.argv[1:])
