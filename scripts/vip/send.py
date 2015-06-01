#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '...') # git rev-parse --show-toplevel

import csv
from boto.ses.connection import SESConnection
from email.header import Header
from jinja2 import Environment
from jinja2 import FileSystemLoader
from setting import AWSID
from setting import AWSKEY


ses = SESConnection(AWSID, AWSKEY)
env = Environment(loader=FileSystemLoader('./'))


def by_csv(csv_path, template_path):
    template = env.get_template(template_path)

    with open(csv_path, "r") as csv_files:
        reader = csv.DictReader(csv_files)

        for row in reader:
            row = {key: unicode(value, 'utf8') for key, value in row.iteritems()}
            row['body'] = template.render(row)
            print send(row)

def send(info):
    print "sending <%(name)s, %(email)s>" % info
    return ses.send_email(
        source='COSCUP2015 Attendee <attendee@coscup.org>',
        subject=u'COSCUP2015 VIP program: Need you provide more information.',
        to_addresses='"%s" <%s>' % (Header(info['name'], 'utf-8'), info['email']),
        format='html',
        return_path='attendee@coscup.org',
        reply_addresses='attendee@coscup.org',
        body=info['body'],
    )

if __name__ == '__main__':
    by_csv('./COSCUP_2015_VIP_UTF8_bk.csv', './tpl_vip.htm')
