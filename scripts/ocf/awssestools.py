# -*- coding: utf-8 -*-
''' My AWS Tools '''
import csv
import io
import string
from datetime import datetime, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from random import choice, sample
from uuid import uuid4

import boto3
import requests
from jinja2 import Environment, FileSystemLoader

import setting

TPLENV = Environment(loader=FileSystemLoader('./tpl'))


def queue_sender(body):
    ''' Send to queue '''
    requests.post(f'{setting.QUEUEURL}/exchange/coscup/secretary.1',
                  data={'body': body}, timeout=30)


def rand_str(l=6):
    ''' rand str '''
    return ''.join(sample(string.ascii_lowercase+string.digits, l))


def dateisoformat(date=None, with_z=True):
    ''' Date ISO format '''
    if not date:
        date = datetime.now(timezone.utc)

    if with_z:
        return date.strftime('%Y%m%dT%H%M%SZ')

    return date.strftime('%Y%m%dT%H%M%SZ')[:-1]


def render_ics(title, description, location, start, end, created, admin,
               admin_mail, url, all_day=False):  # pyling: disable:R0913:too-many-arguments
    ''' Render ICS '''
    # https://tools.ietf.org/html/rfc2445
    return '''BEGIN:VCALENDAR
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
        'location': location.replace(',', r'\,'),
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
        msg_all['X-Mailer'] = 'OCF IT Technical Support Team'

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
            title='COSCUP 2019',
            description="No.43, Keelung Rd., Sec.4, Da'an Dist., Taipei 10607, Taiwan",
            location='10607 臺北市大安區基隆路四段43號',
            all_day=True,
            start='20190817',
            end='20190819',
            created=datetime.now(),
            admin='COSCUP2019 Attendee',
            admin_mail='attendee@coscup.org',
            url='https://coscup.org/2019/'
        )
        attachment = MIMEBase(
            'text', 'calendar; name=calendar.ics; method=REQUEST; charset=UTF-8')
        attachment.set_payload(ics.encode('utf-8'))
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition',
                              'attachment; filename=calendar.ics')

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
            title='COSCUP 2019',
            description="No.43, Keelung Rd., Sec.4, Da'an Dist., Taipei 10607, Taiwan",
            location='10607 臺北市大安區基隆路四段43號',
            all_day=True,
            start='20190817',
            end='20190819',
            created=datetime.now(),
            admin='COSCUP2019 Attendee',
            admin_mail='attendee@coscup.org',
            url='https://coscup.org/2019/'
        )
        attachment = MIMEBase(
            'text', 'calendar; name=calendar.ics; method=REQUEST; charset=UTF-8')
        attachment.set_payload(ics.encode('utf-8'))
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition',
                              'attachment; filename=calendar.ics')

        msg_all.attach(attachment)

        # image
        with open(f"./qrcode/program/{kwargs['token']}.png", 'rb') as i:
            img = MIMEImage(i.read())

        img.add_header('Content-Disposition',
                       f"attachment; filename={kwargs['token']}.png")
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
            title='COSCUP 2019',
            description="No.43, Keelung Rd., Sec.4, Da'an Dist., Taipei 10607, Taiwan",
            location='10607 臺北市大安區基隆路四段43號',
            all_day=True,
            start='20190817',
            end='20190819',
            created=datetime.now(),
            admin='COSCUP2019 Attendee',
            admin_mail='attendee@coscup.org',
            url='https://coscup.org/2019/'
        )
        attachment = MIMEBase(
            'text', 'calendar; name=calendar.ics; method=REQUEST; charset=UTF-8')
        attachment.set_payload(ics.encode('utf-8'))
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition',
                              'attachment; filename=calendar.ics')

        msg_all.attach(attachment)

        # image
        with open(f"./qrcode/worker/{kwargs['token']}.png", 'rb') as i:
            img = MIMEImage(i.read())

        img.add_header('Content-Disposition',
                       f"attachment; filename={kwargs['token']}.png")
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
            title='COSCUP 2019',
            description="No.43, Keelung Rd., Sec.4, Da'an Dist., Taipei 10607, Taiwan",
            location='10607 臺北市大安區基隆路四段43號',
            all_day=True,
            start='20190817',
            end='20190819',
            created=datetime.now(),
            admin='COSCUP2019 Attendee',
            admin_mail='attendee@coscup.org',
            url='https://coscup.org/2019/'
        )
        attachment = MIMEBase(
            'text', 'calendar; name=calendar.ics; method=REQUEST; charset=UTF-8')
        attachment.set_payload(ics.encode('utf-8'))
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition',
                              'attachment; filename=calendar.ics')

        msg_all.attach(attachment)

        # image
        with open(f"./qrcode/attendee/{kwargs['token']}.png", 'rb') as i:
            img = MIMEImage(i.read())

        img.add_header('Content-Disposition',
                       "attachment; filename={kwargs['token']}.png")
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
            title='COSCUP 2019',
            description="No.43, Keelung Rd., Sec.4, Da'an Dist., Taipei 10607, Taiwan",
            location='10607 臺北市大安區基隆路四段43號',
            all_day=True,
            start='20190817',
            end='20190819',
            created=datetime.now(),
            admin='COSCUP2019 Attendee',
            admin_mail='attendee@coscup.org',
            url='https://coscup.org/2019/'
        )
        attachment = MIMEBase(
            'text', 'calendar; name=calendar.ics; method=REQUEST; charset=UTF-8')
        attachment.set_payload(ics.encode('utf-8'))
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition',
                              'attachment; filename=calendar.ics')

        msg_all.attach(attachment)

        # CSV
        csv_file = io.StringIO()
        fieldnames = ('name', 'token', 'OPass Link')
        csv_writer = csv.DictWriter(
            csv_file, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        csv_writer.writeheader()
        _n = 1
        for token in kwargs['data']['tokens']:
            csv_writer.writerow({
                'name': f"{kwargs['data']['sponsor']} - {_n}",
                'token': token,
                'OPass Link': 'https://dl.opass.app/?link=https%3A%2F%2Fopass.app%2Fopen%2F%3Fevent_id%3DCOSCUP_2019%26token%3D' +  # pylint: disable: C0301:line-too-long
                token + '&apn=app.opass.ccip&amv=35&isi=1436417025&ibi=app.opass.ccip'})
            _n += 1

        csv_attach = MIMEBase('text', 'csv; name=info.csv; charset=utf-8')
        csv_attach.set_payload(csv_file.getvalue().encode('utf-8'))
        encoders.encode_base64(csv_attach)
        csv_attach.add_header('Content-Disposition',
                              'attachment; filename=tokens.csv')
        msg_all.attach(csv_attach)

        # HTML
        with open('./tpl/user_reminder_no_btn.html', 'r+', encoding='UTF8') as files:
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
        with open(f"./taigi_qrcode/{kwargs['token']}.png", 'rb') as i:
            img = MIMEImage(i.read())

        img.add_header('Content-Disposition',
                       f"attachment; filename={kwargs['token']}.png")
        msg_all.attach(img)

        # return self.client.send_raw_email(
        #        RawMessage={'Data': msg_all.as_string()})
        return msg_all.as_string()


def send_240813(dry_run=True):
    ''' Send 240813 Press info '''
    template = TPLENV.get_template('./ocf_20240813_inline.html')
    template_md = TPLENV.get_template('./ocf_20240813.md')

    if dry_run:
        path = './ocf_press_test.csv'
    else:
        path = './ocf_press.csv'

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
            '【新聞稿刊登邀請】9/14 活動：OCF 十週年「開源祭」：OpenLab、XREX、法白多場跨界對談揭示未來科技趨勢',
            '【新聞稿刊登邀請】9/14 活動：「開源祭」公館水岸登場！6 場音樂表演、5 場科技跨界對談通通免費看',
            '【新聞稿刊登邀請】9/14 活動：開源祭-林強、PUZZLEMAN、拷秋勤公館河岸免費開唱',
            '【新聞稿刊登邀請】9/14 活動：林強最新專輯《時間浸漬 BIOEROSION》首演在「開源祭」',
        ])

        u['preheader'] = choice([
            '關於十週年開源祭新聞稿內容，懇請協助我們傳達活動訊息！',
            '關於開放文化基金會十週年開源祭新聞稿內容，懇請協助我們傳達活動訊息！',

        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                '財團法人開放文化基金會 OCF', 'hi@ocf.tw'),
            list_unsubscribe='<mailto:hi+unsubscribe240813@ocf.tw>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_240827(dry_run=True):
    ''' Send 240827, 240814 Community '''
    template = TPLENV.get_template('./ocf_booth_240827_inline.html')
    template_md = TPLENV.get_template('./ocf_booth_240827.md')

    if dry_run:
        path = './ocf_community_test.csv'
    else:
        path = './ocf_community_240827.csv'

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
            '[社群攤位募集][即將截止] OCF 開源祭十週年特別活動社群攤位、工作人員募集',
            '[社群攤位][即將截止] OCF 開源祭十週年特別活動社群攤位、工作人員募集',
            '[攤位][即將截止] OCF 開源祭十週年特別活動社群攤位、工作人員募集',
            '[OCF 開源祭][即將截止] 社群攤位、工作人員募集中',
            '[即將截止] OCF 開源祭：社群攤位、工作人員募集中',
            '[即將截止] OCF 開源祭十週年特別活動：社群攤位、工作人員募集',
            '[即將截止] OCF 開源祭十週年特別活動 社群攤位、工作人員募集',
        ])

        u['preheader'] = choice([
            '關於十週年開源祭活動，懇請協助我們傳達活動訊息、社群攤位、工作人員招募！',
            '一起來和我們擺攤推廣開源社群、開源精神、開源文化。',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                '財團法人開放文化基金會 OCF', 'hi@ocf.tw'),
            list_unsubscribe='<mailto:hi+unsubscribe240827@ocf.tw>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_vl_240814(dry_run=True):
    ''' Send 240814 Volunteer '''
    template = TPLENV.get_template('./ocf_vl_240814_inline.html')
    template_md = TPLENV.get_template('./ocf_vl_240814.md')

    if dry_run:
        path = './ocf_vl_form_test.csv'
    else:
        path = './ocf_vl_form_240827.csv'

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
            '[請回覆] OCF 開源祭工作人員組別選擇、意願參與',
        ])

        u['preheader'] = choice([
            '關於十週年開源祭活動，懇請協助我們傳達活動訊息、社群攤位、工作人員招募！',
            '一起來和我們擺攤推廣開源社群、開源精神、開源文化。',
            '請幫我們呼朋引伴一起來參與志工協助開源祭活動的舉辦。',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                '財團法人開放文化基金會 OCF', 'hi@ocf.tw'),
            list_unsubscribe='<mailto:hi+unsubscribe240824@ocf.tw>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_240816(dry_run=True):
    ''' Send 240816 w1 promote '''
    template = TPLENV.get_template('./ocf_w1_promote_inline.html')
    template_md = TPLENV.get_template('./ocf_w1_promote.md')

    if dry_run:
        path = './ocf_kkcos_test.csv'
    else:
        path = './ocf_kkcos.csv'

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
            '[開源祭] 近期活動更新、募資活動開跑',
            '[開源祭] 募資活動開跑、公民團體、開源社群、市集攤位招募中',
            '[開源祭] 募資活動開跑「開源精神」《時間浸漬 BIOEROSION》募資計畫',
            '[開源祭] 《時間浸漬 BIOEROSION》募資計畫已開跑、攤位、工作人員募集中',
            'OCF 開源祭近期活動更新、募資活動開跑',
            'OCF 開源祭募資活動開跑、公民團體、開源社群、市集攤位招募中',
            'OCF 開源祭募資活動開跑「開源精神」《時間浸漬 BIOEROSION》募資計畫',
            'OCF 開源祭《時間浸漬 BIOEROSION》募資計畫已開跑、攤位、工作人員募集中',
        ])

        u['preheader'] = choice([
            '關於十週年開源祭活動，懇請協助我們傳達活動訊息、社群攤位、工作人員招募！',
            '一起來和我們擺攤推廣開源社群、開源精神、開源文化。',
            '請幫我們呼朋引伴一起來參與志工協助開源祭活動的舉辦。',
            '最開源的專輯，限量彩膠募資項目，一起來收藏開源音樂專輯',
            '林強攜手義大利藝術家 Luca Bonaccorsi，首次表演其基於「開放」與「分享」兩大核心理念所創作的全新專輯',
            '等待 19 年後終於等到林強再次推出新專輯，特別獻給「開源祭」、保證限量發行。這意味著您擁有的不僅僅是一張唱片，而是一件創意且富含「開源精神」的藝術品',
            '在募資平台 flyingV 上還有搭配彩膠作品的組合包，由於彩膠的數量真的只有限量生產，微微的心動就不要再懷疑了，錯過這次的募資可能就會遺憾終生',
            '讓這份獨特獻給臺灣開源圈的音樂收藏成為您生活的一部分！',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                '財團法人開放文化基金會 OCF', 'hi@ocf.tw'),
            list_unsubscribe='<mailto:hi+unsubscribe240816@ocf.tw>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_booth_240821(dry_run=True):
    ''' Send 240821 booth for CSOs '''
    template = TPLENV.get_template('./ocf_booth_cso_inline.html')
    template_md = TPLENV.get_template('./ocf_booth_cso.md')

    if dry_run:
        path = './ocf_booth_cso_test.csv'
    else:
        path = './ocf_booth_cso.csv'

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
            '[邀請] OCF 開源祭活動擺攤邀請',
        ])

        u['preheader'] = choice([
            '關於十週年開源祭活動，懇請參與社群攤位',
            '一起來和我們擺攤推廣開源社群、開源精神、開源文化。',
            '請幫我們呼朋引伴一起來參與志工協助開源祭活動的舉辦。',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                '財團法人開放文化基金會 OCF', 'hi@ocf.tw'),
            list_unsubscribe='<mailto:hi+unsubscribe240821@ocf.tw>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_240822_crm(dry_run=True):
    ''' Send 240822 CRM promote '''
    template = TPLENV.get_template('./ocf_crm_promote_inline.html')
    template_md = TPLENV.get_template('./ocf_crm_promote.md')

    if dry_run:
        path = './ocf_send_list_1724307791_test.csv'
    else:
        path = './ocf_send_list_1724307791.csv'

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
            '[開源祭] 近期活動更新、募資活動開跑',
            '[開源祭] 募資活動開跑、公民團體、開源社群、市集攤位招募中',
            '[開源祭] 募資活動開跑「開源精神」《時間浸漬 BIOEROSION》募資計畫',
            '[開源祭] 《時間浸漬 BIOEROSION》募資計畫已開跑、攤位、工作人員募集中',
            'OCF 開源祭近期活動更新、募資活動開跑',
            'OCF 開源祭募資活動開跑、公民團體、開源社群、市集攤位招募中',
            'OCF 開源祭募資活動開跑「開源精神」《時間浸漬 BIOEROSION》募資計畫',
            'OCF 開源祭《時間浸漬 BIOEROSION》募資計畫已開跑、攤位、工作人員募集中',
        ])

        u['preheader'] = choice([
            '關於十週年開源祭活動，懇請協助我們傳達活動訊息、社群攤位、工作人員招募！',
            '一起來和我們擺攤推廣開源社群、開源精神、開源文化。',
            '請幫我們呼朋引伴一起來參與志工協助開源祭活動的舉辦。',
            '最開源的專輯，限量彩膠募資項目，一起來收藏開源音樂專輯',
            '林強攜手義大利藝術家 Luca Bonaccorsi，首次表演其基於「開放」與「分享」兩大核心理念所創作的全新專輯',
            '等待 19 年後終於等到林強再次推出新專輯，特別獻給「開源祭」、保證限量發行。這意味著您擁有的不僅僅是一張唱片，而是一件創意且富含「開源精神」的藝術品',
            '在募資平台 flyingV 上還有搭配彩膠作品的組合包，由於彩膠的數量真的只有限量生產，微微的心動就不要再懷疑了，錯過這次的募資可能就會遺憾終生',
            '讓這份獨特獻給臺灣開源圈的音樂收藏成為您生活的一部分！',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                '財團法人開放文化基金會 OCF', 'hi@ocf.tw'),
            list_unsubscribe='<mailto:hi+unsubscribe240822crm@ocf.tw>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_booth_osc_240822(dry_run=True):
    ''' Send 240822 booth for OSCs '''
    template = TPLENV.get_template('./ocf_booth_osc_inline.html')
    template_md = TPLENV.get_template('./ocf_booth_osc.md')

    if dry_run:
        path = './ocf_booth_osc_test.csv'
    else:
        path = './ocf_booth_osc.csv'

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
            '[邀請] OCF 開源祭活動擺攤邀請',
        ])

        u['preheader'] = choice([
            '關於十週年開源祭活動，懇請參與社群攤位',
            '一起來和我們擺攤推廣開源社群、開源精神、開源文化。',
            '請幫我們呼朋引伴一起來參與志工協助開源祭活動的舉辦。',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                '財團法人開放文化基金會 OCF', 'hi@ocf.tw'),
            list_unsubscribe='<mailto:hi+unsubscribe240821@ocf.tw>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_240828(dry_run=True):
    ''' Send 240828 pr '''
    template = TPLENV.get_template('./ocf_pr_240828_inline.html')
    template_md = TPLENV.get_template('./ocf_pr_240828.md')

    if dry_run:
        path = './ocf_kk0828_test.csv'
    else:
        path = './ocf_kk0828.csv'

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
            '[開源祭] 近期活動更新、感謝募資計畫順利達標',
            '[開源祭] 募資計畫達標、公民團體、開源社群、市集攤位招募中',
            '[開源祭] 「開源精神」《時間浸漬 BIOEROSION》募資達標',
            '[開源祭] 社群懷舊物件、結緣品緊急募集中、感謝募資計畫順利達標',
            'OCF 「開源祭」近期活動更新、感謝募資計畫順利達標',
            'OCF 「開源祭」感謝募資計畫順利達標、公民團體、開源社群、市集攤位招募中',
            'OCF 「開源祭」社群懷舊物件、結緣品緊急募集中、感謝募資計畫順利達標',
        ])

        u['preheader'] = choice([
            '關於十週年開源祭活動，懇請協助我們傳達活動訊息、社群攤位、工作人員招募！',
            '一起來和我們擺攤推廣開源社群、開源精神、開源文化。',
            '請幫我們呼朋引伴一起來參與志工協助開源祭活動的舉辦。',
            '最開源的專輯，限量彩膠募資項目，一起來收藏開源音樂專輯',
            '林強攜手義大利藝術家 Luca Bonaccorsi，首次表演其基於「開放」與「分享」兩大核心理念所創作的全新專輯',
            '等待 19 年後終於等到林強再次推出新專輯，特別獻給「開源祭」、保證限量發行。這意味著您擁有的不僅僅是一張唱片，而是一件創意且富含「開源精神」的藝術品',
            '在募資平台 flyingV 上還有搭配彩膠作品的組合包，由於彩膠的數量真的只有限量生產，微微的心動就不要再懷疑了，錯過這次的募資可能就會遺憾終生',
            '讓這份獨特獻給臺灣開源圈的音樂收藏成為您生活的一部分！',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                '財團法人開放文化基金會 OCF', 'hi@ocf.tw'),
            list_unsubscribe='<mailto:hi+unsubscribe240828@ocf.tw>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_booth_240830(dry_run=True):
    ''' Send 240830 booth accepted for OSCs '''
    template = TPLENV.get_template('./ocf_booth_240830_inline.html')
    template_md = TPLENV.get_template('./ocf_booth_240830.md')

    if dry_run:
        path = './ocf_booth_accept_test.csv'
    else:
        path = './ocf_booth_accept.csv'

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
            f"[已錄取] OCF 開源祭活動擺攤已確認錄取 - {u['org']}",
        ])

        u['preheader'] = choice([
            '十週年開源祭活動，感謝參與社群攤位',
            '感謝一起來和我們擺攤推廣開源社群、開源精神、開源文化。',
            '也請幫我們呼朋引伴一起來參與志工協助開源祭活動的舉辦。',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                '財團法人開放文化基金會 OCF', 'hi@ocf.tw'),
            list_unsubscribe='<mailto:hi+unsubscribe240830@ocf.tw>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_booth_240904(dry_run=True):
    ''' Send 240904 booth for OSCs '''
    template = TPLENV.get_template('./ocf_booth_240904_inline.html')
    template_md = TPLENV.get_template('./ocf_booth_240904.md')

    if dry_run:
        path = './ocf_booth_accept_test.csv'
    else:
        path = './ocf_booth_accept.csv'

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
            f"[協助宣傳] OCF 開源祭活動社群行銷素材包 - {u['org']}",
        ])

        u['preheader'] = choice([
            '十週年開源祭活動，感謝參與社群攤位',
            '感謝一起來和我們擺攤推廣開源社群、開源精神、開源文化。',
            '也請幫我們呼朋引伴一起來參與志工協助開源祭活動的舉辦。',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                '財團法人開放文化基金會 OCF', 'hi@ocf.tw'),
            list_unsubscribe='<mailto:hi+unsubscribe240904@ocf.tw>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_pr_240911(dry_run=True):
    ''' Send PR 240911 '''
    template = TPLENV.get_template('./ocf_pr_240911_inline.html')
    template_md = TPLENV.get_template('./ocf_pr_240911.md')

    if dry_run:
        path = './ocf_pr_240911_test.csv'
    else:
        path = './ocf_pr_240911.csv'

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
            "[開源祭] 活動即將開始，帶給您目前活動的最新狀況",
            "[開源祭] 本週末十週年回顧展，探索開源運動歷史",
            "[開源祭] 市集攤位與開源福利社，還有開源運動回顧展",
            "[開源祭] 不要錯過！本週末十週年回顧展與現場 RPG 冒險！",
            "[開源祭] 行程與指南都準備好了！假日一起來水岸廣場走走",
            "[開源祭] 科技跨界對談、音樂影像表演、開源運動回顧與開源福利社",
        ])

        u['preheader'] = choice([
            '十週年開源祭活動，感謝參與社群攤位',
            '感謝一起來和我們擺攤推廣開源社群、開源精神、開源文化。',
            '也請幫我們呼朋引伴一起來參與志工協助開源祭活動的舉辦。',
            '開源祭詳盡行程與遊玩指南都在這裡',
            '成為「開源人」，體驗實體 RPG 冒險遊戲',
            '當科技遇上音樂與藝術，一同狂歡一整晚',
            '募資計劃順利達標，感謝您的支持',
            '找找你的懷舊物件，讓更多人回味開源歷程',
            '新聞稿專區和素材包，推廣開源祭活動',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                '財團法人開放文化基金會 OCF', 'hi@ocf.tw'),
            list_unsubscribe='<mailto:hi+unsubscribe240911@ocf.tw>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_vl_240912(dry_run=True):
    ''' Send 240912 Volunteer '''
    template = TPLENV.get_template('./ocf_vl_240912_inline.html')
    template_md = TPLENV.get_template('./ocf_vl_240912.md')

    if dry_run:
        path = './ocf_vl_0911_test.csv'
    else:
        path = './ocf_vl_0911.csv'

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
            '[請回覆] [開源祭] 工作任務分配與晚餐是否訂購',
        ])

        u['preheader'] = choice([
            '關於十週年開源祭活動，懇請協助我們傳達活動訊息、社群攤位、工作人員招募！',
            '一起來和我們擺攤推廣開源社群、開源精神、開源文化。',
            '請幫我們呼朋引伴一起來參與志工協助開源祭活動的舉辦。',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                '財團法人開放文化基金會 OCF', 'hi@ocf.tw'),
            list_unsubscribe='<mailto:hi+unsubscribe240912vl@ocf.tw>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_booth_240912(dry_run=True):
    ''' Send 240912 booth for OSCs '''
    template = TPLENV.get_template('./ocf_booth_240912_inline.html')
    template_md = TPLENV.get_template('./ocf_booth_240912.md')

    if dry_run:
        path = './ocf_booth_240912_test.csv'
    else:
        path = './ocf_booth_240912.csv'

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
            f"[開源祭] 開源社群與公民團體擺攤資訊 - {u['org']}",
        ])

        u['preheader'] = choice([
            '十週年開源祭活動，感謝參與社群攤位',
            '感謝一起來和我們擺攤推廣開源社群、開源精神、開源文化。',
            '也請幫我們呼朋引伴一起來參與志工協助開源祭活動的舉辦。',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                '財團法人開放文化基金會 OCF', 'hi@ocf.tw'),
            list_unsubscribe='<mailto:hi+unsubscribe240912@ocf.tw>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


def send_booth_241028(dry_run=True):
    ''' Send 241028 booth for CSOs '''
    template = TPLENV.get_template('./ocf_booth_cso_241027_inline.html')
    template_md = TPLENV.get_template('./ocf_booth_cso_241027.md')

    if dry_run:
        path = './ocf_booth_cso_test.csv'
    else:
        path = './ocf_booth_cso.csv'

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
            '[感謝] OCF 開源祭活動擺攤與後續規劃',
        ])

        u['preheader'] = choice([
            '關於十週年開源祭活動，感謝參與社群攤位',
        ])

        u['subject'] = subject

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(
                '財團法人開放文化基金會 OCF', 'hi@ocf.tw'),
            list_unsubscribe='<mailto:hi+unsubscribe241028@ocf.tw>',
            to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
            subject=subject,
            body=template.render(**u),
            text_body=template_md.render(**u),
        )

        queue_sender(raw)


if __name__ == '__main__':
    # send_240813(dry_run=True)
    # send_240827(dry_run=True)
    # send_vl_240814(dry_run=True)
    # send_240816(dry_run=True)
    # send_booth_240821(dry_run=True)
    # send_240822_crm(dry_run=True)
    # send_booth_osc_240822(dry_run=True)
    # send_240828(dry_run=True)
    # send_booth_240830(dry_run=True)
    # send_booth_240904(dry_run=True)
    # send_pr_240911(dry_run=True)
    # send_vl_240912(dry_run=True)
    # send_booth_240912(dry_run=True)
    # send_booth_241028(dry_run=True)
    pass
