#!/usr/bin/env python
#coding=utf-8
"""
Author:         Xia Kai <xiaket@gmail.com>
Filename:       mailer
Type:           Utility
Last modified:  2010-05-20 20:14

Description:
This script would send mail to me, I shall later filter the mail with KMail.
"""
import smtplib
import sys
from email.mime.text import MIMEText


def send(**kwargs):
    category = kwargs.get('category', 'Generic')
    subject = kwargs.get('subject', 'No Subject')
    content = kwargs.get('content', None)
    fromaddr = "<xiaket@bolt>"
    toaddrs = "<xiaket@bolt>"
    mail = MIMEText(content, 'plain', 'utf-8')
    mail['Subject'] = subject
    mail['From'] = "%s <xiaket@localhost>" % category
    mail['To'] = 'me <xiaket@localhost>'
 
    # I used a bizzare port to receive mail.
    server = smtplib.SMTP('localhost', '9025')
    server.sendmail(fromaddr, toaddrs, mail.as_string())
    server.quit()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print "Usage: mailer <category> <subject> <content>"
        exit(1)
    send(
        category=sys.argv[1], 
        subject=sys.argv[2], 
        content=sys.argv[3],
    )
