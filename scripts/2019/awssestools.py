# -*- coding: utf-8 -*-
''' My AWS Tools '''
import csv
import string
from datetime import datetime
from datetime import timedelta
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from random import sample
from uuid import uuid4

import setting

import boto3
from jinja2 import Environment
from jinja2 import FileSystemLoader


TPLENV = Environment(loader=FileSystemLoader('./tpl'))


def rand_str(l=6):
    return ''.join(sample(string.ascii_lowercase+string.digits, l))


def dateisoformat(date=None, with_z=True):
    if not date:
        date = datetime.utcnow() + timedelta(hours=8)

    if with_z:
        return date.strftime('%Y%m%dT%H%M%SZ')

    return date.strftime('%Y%m%dT%H%M%SZ')[:-1]


def render_ics(title, description, location, start, end, created, admin,
        admin_mail, url):
    # https://tools.ietf.org/html/rfc2445
    return u'''BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Toomore//Toomore Events v1.0//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VTIMEZONE
TZID:Asia/Taipei
BEGIN:STANDARD
TZOFFSETFROM:+0800
TZOFFSETTO:+0800
TZNAME:CST
DTSTART:19700101T000000
END:STANDARD
END:VTIMEZONE
BEGIN:VEVENT
DTSTAMP:%(created)s
DTSTART;TZID=Asia/Taipei:%(start)s
DTEND;TZID=Asia/Taipei:%(end)s
STATUS:CONFIRMED
SUMMARY:%(title)s
DESCRIPTION:%(description)s
ORGANIZER;CN=%(admin)s Reminder:MAILTO:%(admin_mail)s
CLASS:PUBLIC
CREATED:%(created)s
LOCATION:%(location)s
URL:%(url)s
LAST-MODIFIED:%(created)s
UID:%(uuid)s
END:VEVENT
END:VCALENDAR''' % {
            'title': title,
            'description': description,
            'location': location.replace(',', '\,'),
            'start': dateisoformat(start, False),
            'end': dateisoformat(end, False),
            'created': dateisoformat(created),
            'admin': admin,
            'admin_mail': admin_mail,
            'url': url,
            'uuid': uuid4(),
            }


class AwsSESTools(object):
    ''' AWS SES tools

        :param str aws_access_key_id: aws_access_key_id
        :param str aws_secret_access_key: aws_secret_access_key

        .. todo::
           - Add integrated with jinja2 template.

    '''
    def __init__(self, aws_access_key_id, aws_secret_access_key):
        ''' Make a connect '''
        self.client = boto3.client(
                'ses',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name='us-east-1')

    @staticmethod
    def mail_header(name, mail):
        ''' Encode header to base64

            :param str name: user name
            :param str mail: user mail
            :rtype: string
            :returns: a string of "name <mail>" in base64.
        '''
        return formataddr((name, mail))

    def send_email(self, *args, **kwargs):
        ''' Send email

            seealso `send_email` in :class:`boto.ses.connection.SESConnection`
        '''
        return self.client.send_email(*args, **kwargs)

    def send_raw_email(self, **kwargs):
        ''' still in dev

        :param str source: from
        :param str to_addresses: to
        :param str subject: subject
        :param str body: body

        '''
        msg_all = MIMEMultipart()
        msg_all['From'] = kwargs['source']
        msg_all['To'] = kwargs['to_addresses']
        msg_all['Subject'] = kwargs['subject']

        msg_all.attach(MIMEText(kwargs['body'], 'html', 'utf-8'))

        #ics = render_ics(
        #    title=u'COSCUP x GNOME.Asia x openSUSE.Asia 2018',
        #    description=u'https://coscup2018.kktix.cc/events/coscup2018regist',
        #    location=u'台灣科技大學+國際大樓, 10607 台北市大安區基隆路四段43號',
        #    start=datetime(2018, 8, 11, 8),
        #    end=datetime(2018, 8, 12, 18, 30),
        #    created=None,
        #    admin=u'COSCUP2018 Attendee',
        #    admin_mail=u'attendee@coscup.org',
        #    url=u'https://2018.coscup.org/'
        #)
        #attachment = MIMEBase('text', 'calendar; name=calendar.ics; method=REQUEST; charset=UTF-8')
        #attachment.set_payload(ics.encode('utf-8'))
        #encoders.encode_base64(attachment)
        #attachment.add_header('Content-Disposition', 'attachment; filename=%s' % "calendar.ics")

        #msg_all.attach(attachment)

        #image
        #with open('./png_worker/%s.png' % kwargs['token'], 'r') as i:
        #    img = MIMEImage(i.read())

        #img.add_header('Content-Disposition', 'attachment; filename=%s.png' % kwargs['token'])
        #msg_all.attach(img)

        #with open('./png_worker/t-shirt.jpg', 'r') as i:
        #    img = MIMEImage(i.read())

        #img.add_header('Content-Disposition', 'attachment; filename=t-shirt.jpg')
        #msg_all.attach(img)

        #with open('./png_worker/eatmap.png', 'r') as i:
        #    img = MIMEImage(i.read())

        #img.add_header('Content-Disposition', 'attachment; filename=eatmap.png')
        #msg_all.attach(img)

        return self.client.send_raw_email(
                RawMessage={'Data': msg_all.as_string()})
        #return msg_all.as_string()


def worker_1(path):
    '''

        need fields: mail, code, team

    '''
    template = TPLENV.get_template('./worker_apply_1.html')
    with open(path, 'r') as csv_file:
        csvReader = csv.DictReader(csv_file)
        _n = 0
        for i in csvReader:
            for k in i:
                i[k] = i[k].strip()

            _n += 1
            print(_n)
            print(i)
            print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                to_addresses=i['mail'],
                subject=u'[COSCUP2019] 工作人員登錄 - %s' % i['code'],
                body=template.render(i),
            ))


def worker_2(path):
    '''

        need fields: mail, nickname

    '''
    template = TPLENV.get_template('./worker_apply_2.html')
    with open(path, 'r') as csv_file:
        csvReader = csv.DictReader(csv_file)
        _n = 0
        for i in csvReader:
            for k in i:
                i[k] = i[k].strip()

            _n += 1
            print(_n)
            print(i)
            print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                to_addresses=AwsSESTools.mail_header(i['nickname'], i['mail']),
                subject=u'[COSCUP2019] 歡迎加入 - %s' % i['nickname'],
                body=template.render(i),
            ))


if __name__ == '__main__':
    #worker_1('worker_1.csv')
    #worker_2('worker_2.csv')
    for i in range(30):
        print(rand_str())
