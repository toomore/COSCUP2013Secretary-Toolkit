# -*- coding: utf-8 -*-
''' My AWS Tools '''
import csv
import io
import string
from collections import OrderedDict
from datetime import datetime, timedelta
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from random import choice, sample
from uuid import uuid4

import boto3
import requests
from jinja2 import Environment, FileSystemLoader

import setting

TPLENV = Environment(loader=FileSystemLoader('./tpl'))


def queue_sender(body):
    requests.post('%s/exchange/coscup/secretary.1' %
                  setting.QUEUEURL, data={'body': body})


def rand_str(l=6):
    return ''.join(sample(string.ascii_lowercase+string.digits, l))


def dateisoformat(date=None, with_z=True):
    if not date:
        date = datetime.utcnow() + timedelta(hours=8)

    if with_z:
        return date.strftime('%Y%m%dT%H%M%SZ')

    return date.strftime('%Y%m%dT%H%M%SZ')[:-1]


def render_ics(title, description, location, start, end, created, admin,
               admin_mail, url, all_day=False):
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
        'description': description,  # html ok
        'location': location.replace(',', '\,'),
        'start': dateisoformat(start, False) if not all_day else start,
        'end': dateisoformat(end, False) if not all_day else end,
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
        :param str text_body: text_body
        :param object calendar: calendar

        '''
        msg_all = MIMEMultipart('mixed')

        msg_all['From'] = kwargs['source']
        msg_all['To'] = kwargs['to_addresses']
        if 'cc_addresses' in kwargs:
            msg_all['Cc'] = kwargs['cc_addresses']

        msg_all['Subject'] = kwargs['subject']
        msg_all['X-Github'] = 'toomore/COSCUP2013Secretary-Toolkit'
        msg_all['X-Mailer'] = 'COSCUP Secretary'

        if 'list_unsubscribe' in kwargs:
            msg_all['List-Unsubscribe'] = kwargs['list_unsubscribe']

        body_mine = MIMEMultipart('alternative')

        if 'text_body' in kwargs and kwargs['text_body']:
            body_mine.attach(MIMEText(kwargs['text_body'], 'plain', 'utf-8'))

        body_mine.attach(MIMEText(kwargs['body'], 'html', 'utf-8'))

        msg_all.attach(body_mine)

        if 'calendar' in kwargs and kwargs['calendar']:
            attachment = MIMEBase(
                'text', 'calendar; name=invite.ics; method=REQUEST; charset=UTF-8')
            attachment.set_payload(kwargs['calendar'].cal.to_ical())
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition',
                                  'attachment; filename=invite.ics')

            msg_all.attach(attachment)

        # image
        if 'image_path' in kwargs and kwargs['image_path']:
            with open(kwargs['image_path'], 'rb') as i:
                img = MIMEImage(i.read())

            img.add_header('Content-Disposition',
                           f"attachment; filename={kwargs['image_filename']}")
            msg_all.attach(img)

        return msg_all.as_string()

    def send_raw_email_with_ics(self, **kwargs):
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

        ics = render_ics(
            title=u'COSCUP 2019',
            description=u"No.43, Keelung Rd., Sec.4, Da'an Dist., Taipei 10607, Taiwan",
            location=u'10607 臺北市大安區基隆路四段43號',
            all_day=True,
            start='20190817',
            end='20190819',
            created=datetime.now(),
            admin=u'COSCUP2019 Attendee',
            admin_mail=u'attendee@coscup.org',
            url=u'https://coscup.org/2019/'
        )
        attachment = MIMEBase(
            'text', 'calendar; name=calendar.ics; method=REQUEST; charset=UTF-8')
        attachment.set_payload(ics.encode('utf-8'))
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition',
                              'attachment; filename=%s' % "calendar.ics")

        msg_all.attach(attachment)

        # CSV
        # csv_file = io.StringIO()
        # fieldnames=('name', 'text')
        # csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        # csv_writer.writeheader()
        # csv_writer.writerow({'name': 'toomore', 'text': '1111.'})
        # csv_writer.writerow({'name': 'toomore', 'text': '2222.'})
        # csv_writer.writerow({'name': 'toomore', 'text': u'私は多いです.'})

        # csv_attach = MIMEBase('text', 'csv; name=info.csv; charset=utf-8')
        # csv_attach.set_payload(csv_file.getvalue().encode('utf-8'))
        # encoders.encode_base64(csv_attach)
        # csv_attach.add_header('Content-Disposition', 'attachment; filename=info.csv')
        # msg_all.attach(csv_attach)

        # image
        # with open('./png_worker/%s.png' % kwargs['token'], 'r') as i:
        #    img = MIMEImage(i.read())

        # img.add_header('Content-Disposition', 'attachment; filename=%s.png' % kwargs['token'])
        # msg_all.attach(img)

        # with open('./png_worker/t-shirt.jpg', 'r') as i:
        #    img = MIMEImage(i.read())

        # img.add_header('Content-Disposition', 'attachment; filename=t-shirt.jpg')
        # msg_all.attach(img)

        # with open('./png_worker/eatmap.png', 'r') as i:
        #    img = MIMEImage(i.read())

        # img.add_header('Content-Disposition', 'attachment; filename=eatmap.png')
        # msg_all.attach(img)

        return self.client.send_raw_email(
            RawMessage={'Data': msg_all.as_string()})
        # return msg_all.as_string()

    def send_attach_program(self, **kwargs):
        ''' send attachment for program

        :param str source: from
        :param str to_addresses: to
        :param str subject: subject
        :param str body: body
        :param str token: token

        '''
        msg_all = MIMEMultipart()
        msg_all['From'] = kwargs['source']
        msg_all['To'] = kwargs['to_addresses']
        msg_all['Subject'] = kwargs['subject']

        msg_all.attach(MIMEText(kwargs['body'], 'html', 'utf-8'))

        ics = render_ics(
            title=u'COSCUP 2019',
            description=u"No.43, Keelung Rd., Sec.4, Da'an Dist., Taipei 10607, Taiwan",
            location=u'10607 臺北市大安區基隆路四段43號',
            all_day=True,
            start='20190817',
            end='20190819',
            created=datetime.now(),
            admin=u'COSCUP2019 Attendee',
            admin_mail=u'attendee@coscup.org',
            url=u'https://coscup.org/2019/'
        )
        attachment = MIMEBase(
            'text', 'calendar; name=calendar.ics; method=REQUEST; charset=UTF-8')
        attachment.set_payload(ics.encode('utf-8'))
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition',
                              'attachment; filename=%s' % "calendar.ics")

        msg_all.attach(attachment)

        # image
        with open('./qrcode/program/%s.png' % kwargs['token'], 'rb') as i:
            img = MIMEImage(i.read())

        img.add_header('Content-Disposition',
                       'attachment; filename=%s.png' % kwargs['token'])
        msg_all.attach(img)

        return self.client.send_raw_email(
            RawMessage={'Data': msg_all.as_string()})
        # return msg_all.as_string()

    def send_attach_worker(self, **kwargs):
        ''' send attachment for worker

        :param str source: from
        :param str to_addresses: to
        :param str subject: subject
        :param str body: body
        :param str token: token

        '''
        msg_all = MIMEMultipart()
        msg_all['From'] = kwargs['source']
        msg_all['To'] = kwargs['to_addresses']
        msg_all['Subject'] = kwargs['subject']

        msg_all.attach(MIMEText(kwargs['body'], 'html', 'utf-8'))

        ics = render_ics(
            title=u'COSCUP 2019',
            description=u"No.43, Keelung Rd., Sec.4, Da'an Dist., Taipei 10607, Taiwan",
            location=u'10607 臺北市大安區基隆路四段43號',
            all_day=True,
            start='20190817',
            end='20190819',
            created=datetime.now(),
            admin=u'COSCUP2019 Attendee',
            admin_mail=u'attendee@coscup.org',
            url=u'https://coscup.org/2019/'
        )
        attachment = MIMEBase(
            'text', 'calendar; name=calendar.ics; method=REQUEST; charset=UTF-8')
        attachment.set_payload(ics.encode('utf-8'))
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition',
                              'attachment; filename=%s' % "calendar.ics")

        msg_all.attach(attachment)

        # image
        with open('./qrcode/worker/%s.png' % kwargs['token'], 'rb') as i:
            img = MIMEImage(i.read())

        img.add_header('Content-Disposition',
                       'attachment; filename=%s.png' % kwargs['token'])
        msg_all.attach(img)

        # return self.client.send_raw_email(
        #        RawMessage={'Data': msg_all.as_string()})
        return msg_all.as_string()

    def send_attach_attendee(self, **kwargs):
        ''' send attachment for attendee

        :param str source: from
        :param str to_addresses: to
        :param str subject: subject
        :param str body: body
        :param str token: token

        '''
        msg_all = MIMEMultipart()
        msg_all['From'] = kwargs['source']
        msg_all['To'] = kwargs['to_addresses']
        msg_all['Subject'] = kwargs['subject']

        msg_all.attach(MIMEText(kwargs['body'], 'html', 'utf-8'))

        ics = render_ics(
            title=u'COSCUP 2019',
            description=u"No.43, Keelung Rd., Sec.4, Da'an Dist., Taipei 10607, Taiwan",
            location=u'10607 臺北市大安區基隆路四段43號',
            all_day=True,
            start='20190817',
            end='20190819',
            created=datetime.now(),
            admin=u'COSCUP2019 Attendee',
            admin_mail=u'attendee@coscup.org',
            url=u'https://coscup.org/2019/'
        )
        attachment = MIMEBase(
            'text', 'calendar; name=calendar.ics; method=REQUEST; charset=UTF-8')
        attachment.set_payload(ics.encode('utf-8'))
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition',
                              'attachment; filename=%s' % "calendar.ics")

        msg_all.attach(attachment)

        # image
        with open('./qrcode/attendee/%s.png' % kwargs['token'], 'rb') as i:
            img = MIMEImage(i.read())

        img.add_header('Content-Disposition',
                       'attachment; filename=%s.png' % kwargs['token'])
        msg_all.attach(img)

        return self.client.send_raw_email(
            RawMessage={'Data': msg_all.as_string()})
        # return msg_all.as_string()

    def send_attach_csv_sponsor(self, **kwargs):
        ''' Send to sponsor

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

        ics = render_ics(
            title=u'COSCUP 2019',
            description=u"No.43, Keelung Rd., Sec.4, Da'an Dist., Taipei 10607, Taiwan",
            location=u'10607 臺北市大安區基隆路四段43號',
            all_day=True,
            start='20190817',
            end='20190819',
            created=datetime.now(),
            admin=u'COSCUP2019 Attendee',
            admin_mail=u'attendee@coscup.org',
            url=u'https://coscup.org/2019/'
        )
        attachment = MIMEBase(
            'text', 'calendar; name=calendar.ics; method=REQUEST; charset=UTF-8')
        attachment.set_payload(ics.encode('utf-8'))
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition',
                              'attachment; filename=%s' % "calendar.ics")

        msg_all.attach(attachment)

        # CSV
        csv_file = io.StringIO()
        fieldnames = ('name', 'token', u'OPass Link')
        csv_writer = csv.DictWriter(
            csv_file, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        csv_writer.writeheader()
        _n = 1
        for token in kwargs['data']['tokens']:
            csv_writer.writerow({
                'name': u'%s - %s' % (kwargs['data']['sponsor'], _n),
                'token': token,
                u'OPass Link': u'https://dl.opass.app/?link=https%3A%2F%2Fopass.app%2Fopen%2F%3Fevent_id%3DCOSCUP_2019%26token%3D' + token + '&apn=app.opass.ccip&amv=35&isi=1436417025&ibi=app.opass.ccip'})
            _n += 1

        csv_attach = MIMEBase('text', 'csv; name=info.csv; charset=utf-8')
        csv_attach.set_payload(csv_file.getvalue().encode('utf-8'))
        encoders.encode_base64(csv_attach)
        csv_attach.add_header('Content-Disposition',
                              'attachment; filename=tokens.csv')
        msg_all.attach(csv_attach)

        # HTML
        with open('./tpl/user_reminder_no_btn.html', 'r+') as files:
            html = MIMEText(files.read())

        html.add_header('Content-Disposition',
                        'attachment; filename=reminder.html')
        msg_all.attach(html)

        return self.client.send_raw_email(
            RawMessage={'Data': msg_all.as_string()})
        # return msg_all.as_string()

    def send_attach_taigi(self, **kwargs):
        ''' send attachment for taigi

        :param str source: from
        :param str to_addresses: to
        :param str subject: subject
        :param str body: body
        :param str token: token

        '''
        msg_all = MIMEMultipart()
        msg_all['From'] = kwargs['source']
        msg_all['To'] = kwargs['to_addresses']
        msg_all['Subject'] = kwargs['subject']

        msg_all.attach(MIMEText(kwargs['body'], 'html', 'utf-8'))

        # image
        with open('./taigi_qrcode/%s.png' % kwargs['token'], 'rb') as i:
            img = MIMEImage(i.read())

        img.add_header('Content-Disposition',
                       'attachment; filename=%s.png' % kwargs['token'])
        msg_all.attach(img)

        # return self.client.send_raw_email(
        #        RawMessage={'Data': msg_all.as_string()})
        return msg_all.as_string()


def send_volunteer_2022_review(dry_run=True):
    template = TPLENV.get_template('./volunteer_2022_review.html')
    template_md = TPLENV.get_template('./volunteer_2022_review.md')

    if dry_run:
        path = './dump_all_users_test.csv'
    else:
        path = './dump_all_users_1672556080.csv'

    users = []
    with open(path, 'r+') as files:
        csv_reader = csv.DictReader(files)

        for u in csv_reader:
            users.append(u)

    _n = 0
    for u in users:
        print(_n, u['name'], u['mail'])
        _n += 1

        subject = choice([
            '志工服務平台 2022 回顧',
            '2022 平台回顧分享 | 志工服務平台',
            '2022 in review | COSCUP Volunteer'
        ])

        u['preheader'] = choice([
            '回顧 2022 展望 2023',
            '平台成長歷程',
            '一起來貢獻開源社群',
        ])

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                'COSCUP 志工服務平台', 'volunteer@coscup.org'),
            list_unsubscribe='<mailto:volunteer+unsubscribeme@coscup.org>',
            to_addresses=AwsSESTools.mail_header(u['mail'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def shuffle_list(data):
    ''' shuffle list '''
    return sample(data, len(data))


def send_250524(dry_run=True):
    ''' Send 250524 '''
    template = TPLENV.get_template('./paper_250524_inline.html')
    template_md = TPLENV.get_template('./paper_250524.md')

    if dry_run:
        path = './coscup_paper_subscribers_tds24l0i_test.csv'
    else:
        path = './coscup_paper_subscribers_tds24l0i_20250524_081839.csv'

    users = []
    with open(path, 'r+', encoding='UTF8') as files:
        csv_reader = csv.DictReader(files)

        for u in csv_reader:
            users.append(u)

    _n = 0
    for u in users:
        print(_n, u['name'], u['mail'])
        _n += 1

        subject = choice([
            'COSCUP 2025 籌備加速進行中！',
        ])

        u['preheader'] = choice([
            '開源好朋友 Ruby Taiwan 社群攜手合作，於台灣科技大學聯合舉辦 COSCUP x RubyConf Taiwan 2025！',
            '撐起大會活動的重要組別之一，歡迎第一次想參與志恩歐工，但不確定可以去哪裡的夥伴，先來場務組認識新朋友！',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                'COSCUP Volunteer 志工服務', 'volunteer@coscup.org'),
            list_unsubscribe='<mailto:volunteer+unsubscribe250524@coscup.org>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_250620(dry_run=True):
    ''' Send 250620 '''
    template = TPLENV.get_template('./paper_250620_inline.html')
    template_md = TPLENV.get_template('./paper_250620.md')

    if dry_run:
        path = './coscup_paper_subscribers_n7p95lou_test.csv'
    else:
        path = './coscup_paper_subscribers_n7p95lou_20250620_154724.csv'

    users = []
    with open(path, 'r+', encoding='UTF8') as files:
        csv_reader = csv.DictReader(files)

        for u in csv_reader:
            users.append(u)

    _n = 0
    for u in users:
        print(_n, u['name'], u['mail'])
        _n += 1

        subject = choice([
            'COSCUP 六月號，20 周年情報解禁！COSCUP June Edition: 20th Anniversary Info Revealed!',
        ])

        u['preheader'] = choice([
            '開源好朋友 Ruby Taiwan 社群攜手合作，於台灣科技大學聯合舉辦 COSCUP x RubyConf Taiwan 2025！',
            '撐起大會活動的重要組別之一，歡迎第一次想參與志恩歐工，但不確定可以去哪裡的夥伴，先來場務組認識新朋友！',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                'COSCUP 會眾信箱', 'attendee@coscup.org'),
            list_unsubscribe='<mailto:attendee+unsubscribe250620@coscup.org>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_250807(dry_run=True):
    ''' Send 250807 '''
    template = TPLENV.get_template('./paper_250807_inline.html')
    template_md = TPLENV.get_template('./paper_250807.md')

    if dry_run:
        path = './coscup_paper_subscribers_85e1uqh0_test.csv'
    else:
        path = './coscup_paper_subscribers_85e1uqh0_20250807_140846.csv'

    users = []
    with open(path, 'r+', encoding='UTF8') as files:
        csv_reader = csv.DictReader(files)

        for u in csv_reader:
            users.append(u)

    _n = 0
    for u in users:
        print(_n, u['name'], u['mail'])
        _n += 1

        subject = choice([
            'COSCUP x RubyConf TW 2025 行前通知信',
        ])

        u['preheader'] = choice([
            '開源好朋友 Ruby Taiwan 社群攜手合作，於台灣科技大學聯合舉辦 COSCUP x RubyConf Taiwan 2025！',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                'COSCUP 會眾信箱', 'attendee@coscup.org'),
            list_unsubscribe='<mailto:attendee+unsubscribe250807@coscup.org>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


if __name__ == '__main__':
    # send_250524(dry_run=True)
    # send_250620(dry_run=True)
    # send_250807(dry_run=True)
    pass
