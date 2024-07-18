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


def send_240118(dry_run=True):
    ''' Send 240118 '''
    template = TPLENV.get_template('./volunteer_20240118_inline.html')
    template_md = TPLENV.get_template('./volunteer_20240118.md')

    if dry_run:
        path = './coscup_paper_subscribers_6d1k94jz_test.csv'
    else:
        path = './coscup_paper_subscribers_6d1k94jz_20240118_010356.csv'

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
            'COSCUP 2024 志工夥伴招募中 Welcome to join us',
            '開源人年會 2024 志工夥伴招募中',
            '[COSCUP] 開源人年會 2024 呼朋引伴一起來籌備年會 Volunteer with us',
        ])

        u['preheader'] = choice([
            'Volunteering',
            '捲起袖子一起加入籌備團隊',
            '志工招募中',
            'FOSDEM 2024',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                'COSCUP Volunteer 志工服務', 'volunteer@coscup.org'),
            list_unsubscribe='<mailto:volunteer+unsubscribe240118@coscup.org>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_240228(dry_run=True):
    ''' Send 240228 '''
    template = TPLENV.get_template('./volunteer_20240228_inline.html')
    template_md = TPLENV.get_template('./volunteer_20240228.md')

    if dry_run:
        path = './coscup_paper_subscribers_2fe2dbv8_test.csv'
    else:
        path = './coscup_paper_subscribers_2fe2dbv8_20240228_044142.csv'

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
            'COSCUP 2024 近期籌備進度更新 Update Report 2024/02',
            '近期籌備進度更新 Update Report 2024/02',
            '[COSCUP] 近期籌備進度更新 Update Report 2024/02',
            'COSCUP 2024 招募社群參與 議程 攤位 CfP Call for participate proposals booths/stands',
            '招募社群參與 議程 攤位 CfP Call for participate proposals booths/stands',
            '[COSCUP] 招募社群參與 議程 攤位 CfP Call for participate proposals booths/stands',
            'COSCUP 2024 近期更新 我們從 FOSDEM 回來了 Return from FOSDEM',
            '近期更新 我們從 FOSDEM 回來了 Return from FOSDEM',
            '[COSCUP] 近期更新 我們從 FOSDEM 回來了 Return from FOSDEM',
            'COSCUP 2024 近期更新 電子報舊報攤開張 Archived Newsletters Online',
            '近期更新 電子報舊報攤開張 Archived Newsletters Online',
            '[COSCUP] 近期更新 電子報舊報攤開張 Archived Newsletters Online',
            'COSCUP 2024 近期更新 即將前往 SCaLE21x 加州參與擺攤推廣',
        ])

        u['preheader'] = choice([
            '捲起袖子一起加入籌備團隊',
            '我們從 FOSDEM 回來了',
            '攤位 議程 社群參與招募中',
            '過往電子報上線，舊報攤開張',
            '即將前往 SCaLE21x 加州參與推廣',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                'COSCUP Volunteer 志工服務', 'volunteer@coscup.org'),
            list_unsubscribe='<mailto:volunteer+unsubscribe240118@coscup.org>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_240315(dry_run=True):
    ''' Send 240315 '''
    template = TPLENV.get_template('./volunteer_20240315_inline.html')
    template_md = TPLENV.get_template('./volunteer_20240315.md')

    if dry_run:
        path = './coscup_paper_subscribers_q36x36i5_test.csv'
    else:
        path = './coscup_paper_subscribers_q36x36i5_20240315_153846.csv'

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
            'COSCUP 2024 近期籌備進度更新 Update Report 2024/03',
            '近期籌備進度更新 Update Report 2024/03',
            '[COSCUP] 近期籌備進度更新 Update Report 2024/03',
            'COSCUP 2024/03 招募社群參與 議程 攤位 CfP Call for participate proposals booths/stands',
            '即將截止招募社群參與 議程 攤位 CfP Call for participate proposals booths/stands',
            '[COSCUP] 即將截止招募社群參與 議程 攤位 CfP Call for participate proposals booths/stands',
            'COSCUP 2024 近期更新 前往 SCaLE21x 加州參與擺攤推廣',
            'COSCUP 2024 前往 SCaLE21x 加州參與擺攤推廣與如何參與 COSCUP 指南',
            '[COSCUP] 如何參與 COSCUP 指南、前往 SCaLE21x 加州參與擺攤推廣與',
            '如何參與 COSCUP 指南、前往 SCaLE21x 加州參與擺攤推廣與',
        ])

        u['preheader'] = choice([
            '捲起袖子一起加入籌備團隊、如何參與 COSCUP 指南、SCaLE21x 加州參與推廣',
            '攤位 議程 社群參與招募中、如何參與 COSCUP 指南、SCaLE21x 加州參與推廣',
            '如何參與 COSCUP 指南、SCaLE21x 加州參與推廣、捲起袖子一起加入籌備團隊',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                'COSCUP Volunteer 志工服務', 'volunteer@coscup.org'),
            list_unsubscribe='<mailto:volunteer+unsubscribe240315@coscup.org>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_scale21x(dry_run=True):
    ''' Send scale21x '''
    template = TPLENV.get_template('./scale21x_inline.html')
    template_md = TPLENV.get_template('./scale21x.md')

    if dry_run:
        path = './scale21x_users_test.csv'
    else:
        path = './scale21x_users.csv'

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
            "[COSCUP] We are glad to have met you at SCaLE21x",
        ])

        u['preheader'] = choice([
            "Hope you have the chance to visit Taiwan together sometime",
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                'COSCUP Engagement Team', 'engagement@coscup.org'),
            list_unsubscribe='<mailto:engagement+unsubscribe240420@coscup.org>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_240423(dry_run=True):
    ''' Send 240423 '''
    template = TPLENV.get_template('./volunteer_20240423_inline.html')
    template_md = TPLENV.get_template('./volunteer_20240423.md')

    if dry_run:
        path = './coscup_paper_subscribers_0djoetwv_test.csv'
    else:
        path = './coscup_paper_subscribers_0djoetwv_20240423_080209.csv'

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
            'COSCUP 2024 近期籌備進度更新 Update Report 2024/04',
            '近期籌備進度更新 Update Report 2024/04',
            '[COSCUP] 近期籌備進度更新 Update Report 2024/04',
            'COSCUP 2024/04 招募社群參與 議程 攤位 CfP Call for participate proposals booths/stands',
            'COSCUP 2024 近期更新 前往 SCaLE21x, FOSSASIA 參與擺攤推廣',
            'COSCUP 2024 前往 SCaLE21x, FOSSASIA 參與擺攤推廣與如何參與 COSCUP 指南',
            '[COSCUP] 如何參與 COSCUP 指南、前往 SCaLE21x, FOSASIA 參與擺攤推廣',
            '如何參與 COSCUP 指南、前往 SCaLE21x, FOSSASIA 參與擺攤推廣',
            '[COSCUP] 如何投稿成為講者指南、前往 SCaLE21x, FOSASIA 參與擺攤推廣',
            '如何投稿成為講者指南、前往 SCaLE21x, FOSSASIA 參與擺攤推廣',
        ])

        u['preheader'] = choice([
            'Welcome to apply for community booths. What new discoveries do we have after the FOSSASIA event?',
            'Welcome to apply for community booths. What new discoveries do we have after the SCaLE21x event?',
            'What new discoveries do we have after the SCaLE21x, FOSSASIA event?',
            'The Speaker Guide has been completed',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                'COSCUP Volunteer 志工服務', 'volunteer@coscup.org'),
            list_unsubscribe='<mailto:volunteer+unsubscribe240423@coscup.org>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_240515(dry_run=True):
    ''' Send 240515 '''
    template = TPLENV.get_template('./volunteer_20240515_inline.html')
    template_md = TPLENV.get_template('./volunteer_20240515.md')

    if dry_run:
        path = './coscup_paper_subscribers_hnxg31pc_test.csv'
    else:
        path = './coscup_paper_subscribers_hnxg31pc_20240515_045844.csv'

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
            'COSCUP 2024/05 最後徵稿、新企劃「開．源遊會」 Final Chance to CfP, Open Source Fair Vendor Invitation',
            'COSCUP 2024/05 徵稿截止到 5/19、新企劃「開．源遊會」 Final Chance to CfP, Open Source Fair Vendor Invitation',
        ])

        u['preheader'] = choice([
            '不要再猶豫，徵稿最後期限到 5/19 請把握成為講者的機會',
            '徵稿最後期限到 5/19 請把握成為講者的機會，不要再猶豫',
            '新企劃「開．源遊會」募集招商中，傳說中的開源食譜即將呈現',
            '傳說中的開源食譜即將呈現，新企劃「開．源遊會」募集招商中',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                'COSCUP Volunteer 志工服務', 'volunteer@coscup.org'),
            list_unsubscribe='<mailto:volunteer+unsubscribe240515@coscup.org>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_goldcard(dry_run=True):
    ''' Send goldcard 240623 '''
    template = TPLENV.get_template('./taiwan_gold_card_inline.html')
    template_md = TPLENV.get_template('./taiwan_gold_card.md')

    if dry_run:
        path = './goldcard_240623_test.csv'
    else:
        path = './goldcard_240623.csv'

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
            'COSCUP X Taiwan Gold Card: a Special Invitation to International Digital Professionals and Talents',
        ])

        u['preheader'] = choice([
            'Thanks for your participant',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                'COSCUP Sponsorship', 'sponsorship@coscup.org'),
            list_unsubscribe='<mailto:sponsorship+unsubscribe240623@coscup.org>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_community_240701(dry_run=True):
    ''' Send community 240701 '''
    template = TPLENV.get_template('./community_20240701_inline.html')
    template_md = TPLENV.get_template('./community_20240701.md')

    if dry_run:
        path = './community_240701_test.csv'
    else:
        path = './community_240701.csv'

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
            'COSCUP 社群軌負責人相關活動資訊、前夜派對、一日志工、社群佈告欄',
        ])

        u['preheader'] = choice([
            '我們也將迎來第二個十年的里程碑，這一路上還是感謝開源社群不斷的參與與支持開源活動',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                'COSCUP 行政組', 'secretary@coscup.org'),
            list_unsubscribe='<mailto:volunteer+unsubscribe240701@coscup.org>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_ocf_240704(dry_run=True):
    ''' Send ocf 240704 '''
    template = TPLENV.get_template('./ocf_20240704_inline.html')
    template_md = TPLENV.get_template('./ocf_20240704.md')

    if dry_run:
        path = './coscup_paper_subscribers_51om8v1v_test.csv'
    else:
        path = './coscup_paper_subscribers_51om8v1v_20240704_145556.csv'

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
            "募集臺灣開源運動回憶 Collecting Memories of Taiwan's Open Source Movement",
            '招募社群回憶錄 - 開源運動在臺灣 Recruiting Community Memoirs - Open Source Movement in Taiwan',
            "募集臺灣開源運動回憶 7/12 前 Collecting Memories of Taiwan's Open Source Movement by 7/12",
            '招募社群回憶錄 - 開源運動在臺灣 7/12 前 Recruiting Community Memoirs - Open Source Movement in Taiwan by 7/12',
        ])

        u['preheader'] = choice([
            '開放文化基金會協助臺灣開源社群與年會財務與行政支援，十週年特展企劃請求支援中',
            '開放文化基金會除了協助臺灣開源社群與年會財務與行政支援外，我們也關心網路自由與數位人權',
            '網路自由、數位人權、開放科技等議題是開放文化基金會持續關注的議題',
            'Internet Freedom, Digital Human Rights, and Open Technology Issues Are Continually Monitored by the Open Culture Foundation',
            'The Open Culture Foundation assists the Taiwan open source community with financial and administrative support for annual conferences, and is currently seeking support for the 10th anniversary special exhibition project.',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                'COSCUP Volunteer 志工服務', 'volunteer@coscup.org'),
            list_unsubscribe='<mailto:volunteer+unsubscribe240704@coscup.org>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_sec_240714(dry_run=True):
    ''' Send sec 240714 '''
    template = TPLENV.get_template('./healing_20240714_inline.html')
    template_md = TPLENV.get_template('./healing_20240714.md')

    if dry_run:
        path = './healing_speakers_test.csv'
    else:
        path = './healing_speakers.csv'

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
            "療癒講座講者議程資訊 / Healing Lecture Speaker Agenda Information",
        ])

        u['preheader'] = choice([
            "Thank you for participating in COSCUP. If you have any questions, please feel free to reply to this email",
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                'COSCUP Secretary', 'secretary@coscup.org'),
            list_unsubscribe='<mailto:secretary+unsubscribe240714@coscup.org>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_240718(dry_run=True):
    ''' Send 240718 '''
    template = TPLENV.get_template('./volunteer_20240718_inline.html')
    template_md = TPLENV.get_template('./volunteer_20240718.md')

    if dry_run:
        path = './coscup_paper_subscribers_u9h7jxq5_test.csv'
    else:
        path = './coscup_paper_subscribers_u9h7jxq5_20240718_002421.csv'

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
            'COSCUP 2024/07 議程公告、前夜派對、會眾服務 Agenda Announcement, Eve Gathering, Attendee Services',
            'COSCUP 2024/07 前夜派對、議程公告、會眾服務 Agenda Announcement, Eve Gathering, Attendee Services',
            'COSCUP 2024/07 前夜派對、議程公告、開．源遊會招商 Agenda Announcement, Eve Gathering, Attendee Services',
            'COSCUP 2024/07 開．源遊會招商、前夜派對、議程公告 Agenda Announcement, Eve Gathering, Attendee Services',

        ])

        u['preheader'] = choice([
            '療癒講座關注創傷恢復、情感和社會互動的理解等議題講座',
            '親子工作坊焊接、自製電玩親子手作課程',
            '療癒市集（按摩小站、紅酒瑜伽、療癒彩繪、療癒睡眠）',
            '前夜派對酒券開賣中，還有套票可以選購，送禮自用皆宜',
            '新企劃「開．源遊會」募集招商中，傳說中的開源食譜即將呈現',
            '傳說中的開源食譜即將呈現，新企劃「開．源遊會」募集招商中',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                'COSCUP Volunteer 志工服務', 'volunteer@coscup.org'),
            list_unsubscribe='<mailto:volunteer+unsubscribe240718@coscup.org>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


if __name__ == '__main__':
    # send_240118(dry_run=True)
    # send_240228(dry_run=True)
    # send_240315(dry_run=True)
    # send_scale21x(dry_run=True)
    # send_240423(dry_run=True)
    # send_240515(dry_run=True)
    # send_goldcard(dry_run=True)
    # send_community_240701(dry_run=True)
    # send_ocf_240704(dry_run=True)
    # send_sec_240714(dry_run=True)
    # send_240718(dry_run=True)
    pass
