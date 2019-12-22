# -*- coding: utf-8 -*-
''' My AWS Tools '''
import csv
import io
import string
from collections import OrderedDict
from datetime import datetime
from datetime import timedelta
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from random import sample
from uuid import uuid4

import setting

import boto3
import requests
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
            'description': description,  #html ok
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

        '''
        msg_all = MIMEMultipart()
        msg_all['From'] = kwargs['source']
        msg_all['To'] = kwargs['to_addresses']
        msg_all['Subject'] = kwargs['subject']
        msg_all['X-Github'] = 'toomore/COSCUP2013Secretary-Toolkit'

        msg_all.attach(MIMEText(kwargs['body'], 'html', 'utf-8'))

        #return self.client.send_raw_email(
        #        RawMessage={'Data': msg_all.as_string()})
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
        attachment = MIMEBase('text', 'calendar; name=calendar.ics; method=REQUEST; charset=UTF-8')
        attachment.set_payload(ics.encode('utf-8'))
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', 'attachment; filename=%s' % "calendar.ics")

        msg_all.attach(attachment)

        # CSV
        #csv_file = io.StringIO()
        #fieldnames=('name', 'text')
        #csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        #csv_writer.writeheader()
        #csv_writer.writerow({'name': 'toomore', 'text': '1111.'})
        #csv_writer.writerow({'name': 'toomore', 'text': '2222.'})
        #csv_writer.writerow({'name': 'toomore', 'text': u'私は多いです.'})

        #csv_attach = MIMEBase('text', 'csv; name=info.csv; charset=utf-8')
        #csv_attach.set_payload(csv_file.getvalue().encode('utf-8'))
        #encoders.encode_base64(csv_attach)
        #csv_attach.add_header('Content-Disposition', 'attachment; filename=info.csv')
        #msg_all.attach(csv_attach)

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
        attachment = MIMEBase('text', 'calendar; name=calendar.ics; method=REQUEST; charset=UTF-8')
        attachment.set_payload(ics.encode('utf-8'))
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', 'attachment; filename=%s' % "calendar.ics")

        msg_all.attach(attachment)

        #image
        with open('./qrcode/program/%s.png' % kwargs['token'], 'rb') as i:
            img = MIMEImage(i.read())

        img.add_header('Content-Disposition', 'attachment; filename=%s.png' % kwargs['token'])
        msg_all.attach(img)

        return self.client.send_raw_email(
                RawMessage={'Data': msg_all.as_string()})
        #return msg_all.as_string()

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
        attachment = MIMEBase('text', 'calendar; name=calendar.ics; method=REQUEST; charset=UTF-8')
        attachment.set_payload(ics.encode('utf-8'))
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', 'attachment; filename=%s' % "calendar.ics")

        msg_all.attach(attachment)

        #image
        with open('./qrcode/worker/%s.png' % kwargs['token'], 'rb') as i:
            img = MIMEImage(i.read())

        img.add_header('Content-Disposition', 'attachment; filename=%s.png' % kwargs['token'])
        msg_all.attach(img)

        #return self.client.send_raw_email(
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
        attachment = MIMEBase('text', 'calendar; name=calendar.ics; method=REQUEST; charset=UTF-8')
        attachment.set_payload(ics.encode('utf-8'))
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', 'attachment; filename=%s' % "calendar.ics")

        msg_all.attach(attachment)

        #image
        with open('./qrcode/attendee/%s.png' % kwargs['token'], 'rb') as i:
            img = MIMEImage(i.read())

        img.add_header('Content-Disposition', 'attachment; filename=%s.png' % kwargs['token'])
        msg_all.attach(img)

        return self.client.send_raw_email(
                RawMessage={'Data': msg_all.as_string()})
        #return msg_all.as_string()

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
        attachment = MIMEBase('text', 'calendar; name=calendar.ics; method=REQUEST; charset=UTF-8')
        attachment.set_payload(ics.encode('utf-8'))
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', 'attachment; filename=%s' % "calendar.ics")

        msg_all.attach(attachment)

        # CSV
        csv_file = io.StringIO()
        fieldnames=('name', 'token', u'OPass Link')
        csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
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
        csv_attach.add_header('Content-Disposition', 'attachment; filename=tokens.csv')
        msg_all.attach(csv_attach)

        # HTML
        with open('./tpl/user_reminder_no_btn.html', 'r+') as files:
            html = MIMEText(files.read())

        html.add_header('Content-Disposition', 'attachment; filename=reminder.html')
        msg_all.attach(html)

        return self.client.send_raw_email(
                RawMessage={'Data': msg_all.as_string()})
        #return msg_all.as_string()

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

        #image
        with open('./taigi_qrcode/%s.png' % kwargs['token'], 'rb') as i:
            img = MIMEImage(i.read())

        img.add_header('Content-Disposition', 'attachment; filename=%s.png' % kwargs['token'])
        msg_all.attach(img)

        #return self.client.send_raw_email(
        #        RawMessage={'Data': msg_all.as_string()})
        return msg_all.as_string()


def worker_1(path, dry_run=True):
    '''

        need fields: mail, code, team

    '''
    template = TPLENV.get_template('./worker_apply_1.html')
    with open(path, 'r') as csv_file:
        csvReader = csv.DictReader(csv_file)
        _n = 0
        for i in csvReader:
            if i['status'] != 'Send_apply_1':
                continue

            for rk in ('mail', 'code', 'team'):
                if rk not in i:
                    raise Exception('Required `%s`' % rk)

            for k in i:
                i[k] = i[k].strip()

            _n += 1
            print(_n)
            print(i)
            if not dry_run:
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                    to_addresses=i['mail'],
                    subject=u'[COSCUP2019] 工作人員登錄與調查 [code:%s]' % i['code'],
                    body=template.render(i),
                ))


def worker_2(path, dry_run=True):
    '''

        need fields: mail, nickname

    '''
    template = TPLENV.get_template('./worker_apply_2.html')
    with open(path, 'r') as csv_file:
        csvReader = list(csv.reader(csv_file))

        _n = 0
        for i in csvReader[1:]:
            i = [s.strip() for s in i]
            data = OrderedDict(zip(csvReader[0], i))
            if not (data['form_ok'] == '1' and data['account_ok'] == '1' and not data['cofirm_ok']):
                continue

            data['form_content'] = [u'註冊碼：%(code)s' % data, ]
            for i in data:
                if i.startswith('f_') and data[i]:
                    data['form_content'].append('%s：%s' % (i[2:], data[i]))

            _n += 1
            print(_n)
            print(data['form_content'])

            if not dry_run:
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(data['nickname'], data['mail']),
                    subject=u'[COSCUP2019] 歡迎加入 COSCUP - %s' % data['nickname'],
                    body=template.render(data),
                ))
            else:
                print(AwsSESTools.mail_header(data['nickname'], data['mail']))

        return

def send_with_ics(path, dry_run=True):
    template = TPLENV.get_template('./osc.html')
    with open(path, 'r') as csv_file:
        csvReader = csv.DictReader(csv_file)
        _n = 0
        for i in csvReader:
            _n += 1
            print(_n)
            print(i)
            if not dry_run:
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email_with_ics(
                    source=AwsSESTools.mail_header(u'COSCUP 2019 Attendee', 'attendee@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(i['name'], i['mail']),
                    subject=u'COSCUP 2019 開源貢獻者保留票申請 / Open Source Contributors (OSC) Tickets Application',
                    body=template.render(i),
                ))
            else:
                print(AwsSESTools.mail_header(i['name'], i['mail']))

def for_chief_report(path, dry_run=True):
    template = TPLENV.get_template('./worker_report.html')
    with open(path, 'r') as csv_file:
        csvReader = list(csv.DictReader(csv_file))
        data = {}
        for i in csvReader:
            if not i['team']:
                continue

            if i['team'] not in data:
                data[i['team']] = {}

        for i in csvReader:
            if not i['team']:
                continue

            if i['mail'] and not i['cofirm_ok']:
                if 'Send_apply_1' not in data[i['team']]:
                    data[i['team']]['Send_apply_1'] = []

                data[i['team']]['Send_apply_1'].append(i)

            elif i['form_ok'] == '1' and i['cofirm_ok'] == '1':
                if 'DONE' not in data[i['team']]:
                    data[i['team']]['DONE'] = []

                data[i['team']]['DONE'].append(i)

    with open('./chief.csv', 'r') as csv_file:
        csvReader = list(csv.DictReader(csv_file))

        for r in csvReader:
            _render = template.render(data=data, r=r).replace('Send_apply_1', u'填寫中')
            _render = _render.replace('DONE', u'完成')

            if not dry_run:
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(r['nickname'], r['mail']),
                    subject=u'[COSCUP2019] 各組登錄狀況 %s' % datetime.now().strftime('%Y-%m-%d'),
                    body=_render,
                ))
            else:
                print(AwsSESTools.mail_header(r['nickname'], r['mail']))


def send_babysister(dry_run=True):
    template = TPLENV.get_template('./babysitter.html')
    with open('./all_2018_users_uni_uuid.csv', 'r') as csv_file:
        csvReader = list(csv.DictReader(csv_file))
        _n_all = len(csvReader)
        _n = 0
        for u in csvReader:
            _n += 1
            if u['osc'] == '1':
                u['osc'] = True
            else:
                u['osc'] = False

            print('>>> %s/%s' % (_n, _n_all))
            print(u)

            _render = template.render(u)
            if not dry_run:
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
                    subject=u'[COSCUP2019] 托育服務問卷與意願調查',
                    body=_render,
                ))
            else:
                print(AwsSESTools.mail_header(u['name'], u['mail']))


def send_osc_deny(dry_run=True):
    template = TPLENV.get_template('./osc_deny.html')
    with open('./osc.csv', 'r') as csv_file:
        csvReader = list(csv.DictReader(csv_file))
        _n_all = len(csvReader)
        _n = 0
        for u in csvReader:
            if u['Status'] == 'PASS':
                continue

            _n += 1
            print(_n)
            print(u)

            _name = u['nickname'].strip() if u['nickname'] else u['name'].strip()
            _doc = []
            for i in ('自介 / Self Introduction',
                      '開放原始碼專案或活動名稱 / Open Source Project or Event Name',
                      '開放原始碼專案 Repo 位置 / Open Source Project Repo',
                      '其他有效證明 / Other Valid Proof ',
                      '開放原始碼專案或活動說明 / Description of Open Source Project or Event ',
                      '您是海外參與者嗎? / Are you an oversea attendee?',
                      ):
                _doc.append('※%s' % i)
                _doc.append('%s' % u[i])
                _doc.append('')

            _render = template.render(
                    name=_name,
                    reason=u['note_type'],
                    doc='\r\n'.join(_doc))

            if not dry_run:
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(_name, u['mail'].lower().strip()),
                    subject=u'[COSCUP2019] 未通過 開源貢獻者保留票申請',
                    body=_render,
                ))
            else:
                print(AwsSESTools.mail_header(_name, u['mail'].lower().strip()))


def send_hotel(path, dry_run=True):
    template = TPLENV.get_template('./worker_hotel.html')
    with open(path, 'r') as csv_file:
        csvReader = list(csv.DictReader(csv_file))

        for u in csvReader:
            _name = u['name'].strip()
            _doc = []
            _doc.append('code: %s' % u['code'])
            _doc.append('team: %s' % u['team'])
            _doc.append('info: %s' % u['info'])
            _doc.append('group: %s' % u['group'])

            _render = template.render(
                    name=_name,
                    doc='\r\n'.join(_doc),
            )

            if not dry_run:
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(_name, u['mail'].lower().strip()),
                    subject=u'[COSCUP2019] 住宿分房名單 2019-05-25 前確認',
                    body=_render,
                ))
            else:
                print(AwsSESTools.mail_header(_name, u['mail'].lower().strip()))


def send_osc_fail(path, dry_run=True):
    template = TPLENV.get_template('./osc_fail.html')
    with open(path, 'r') as csv_file:
        csvReader = list(csv.DictReader(csv_file))

        _n = 0
        for u in csvReader:
            if u['in_pass'] == '1':
                continue

            _n += 1
            print(_n)
            u['nickname'] = u['nickname'].strip()
            u['mail'] = u['mail'].lower().strip()

            if not dry_run:
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(u['nickname'], u['mail']),
                    subject=u'[COSCUP2019] OSC 開源貢獻者保留票申請結果 - Deny',
                    body=template.render(u),
                ))
            else:
                print(AwsSESTools.mail_header(u['nickname'], u['mail']))


def send_osc_pass(path, dry_run=True):
    template = TPLENV.get_template('./osc_pass.html')
    with open(path, 'r') as csv_file:
        csvReader = list(csv.DictReader(csv_file))

        _n = 0
        for u in csvReader:
            if u['lost'] != '1':
                continue

            _n += 1
            print(_n)
            u['nickname'] = u['nickname'].strip()
            u['mail'] = u['mail'].lower().strip()

            if not dry_run:
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(u['nickname'], u['mail']),
                    subject=u'[提醒][COSCUP2019] OSC 開源貢獻者保留票申請結果 - Approved',
                    body=template.render(u),
                ))
            else:
                print(AwsSESTools.mail_header(u['nickname'], u['mail']))


def chief_vip(path, title, dry_run=True):
    with open('./chief_vip_code.csv', 'r') as files:
        csv_reader = csv.DictReader(files)
        ticket = {}
        for r in csv_reader:
            if r['mail'] not in ticket:
                ticket[r['mail']] = []
            ticket[r['mail']].append(r['code'])

    template = TPLENV.get_template(path)

    with open('./chief.csv', 'r') as files:
        csv_reader = csv.DictReader(files)
        for u in csv_reader:
            for code in ticket[u['mail']]:
                if not dry_run:
                    print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                        source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                        to_addresses=AwsSESTools.mail_header(u['nickname'], u['mail']),
                        subject=u'[COSCUP2019] %s - %s' % (title, code),
                        body=template.render(code=code),
                    ))
                else:
                    print(AwsSESTools.mail_header(u['nickname'], u['mail']), code)

def baby_form(path, dry_run=True):
    #template = TPLENV.get_template('./baby_form.html')
    template = TPLENV.get_template('./baby_form_not_st.html')

    with open(path, 'r') as files:
        csv_reader = csv.DictReader(files)
        for u in csv_reader:
            print(u['mail'])
            if not dry_run:
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
                    subject=u'[COSCUP2019] 托育服務申請 - %s' % u['name'],
                    body=template.render(u),
                ))
            else:
                print(AwsSESTools.mail_header(u['name'], u['mail']), u['code'])


def installation(dry_run=True):
    template = TPLENV.get_template('./installation.html')

    with open('./works_form.csv', 'r+') as files:
        csv_reader = csv.DictReader(files)
        user = {}
        for u in csv_reader:
            user[u['mail']] = u['nickname']

        for mail in user:
            if not dry_run:
                print(mail)
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(user[mail], mail),
                    subject=u'[COSCUP2019] 協助場務組場佈',
                    body=template.render(name=user[mail]),
                ))
            else:
                print(AwsSESTools.mail_header(user[mail], mail))


def installation_reminder(dry_run=True):
    template = TPLENV.get_template('./installation_reminder.html')

    with open('./works_form.csv', 'r+') as files:
        csv_reader = csv.DictReader(files)
        user = {}
        for u in csv_reader:
            if u['team'] == u'場務組':
                user[u['mail']] = u['nickname']

        for mail in user:
            if not dry_run:
                print(mail)
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP 場務組', 'service@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(user[mail], mail),
                    subject=u'[COSCUP2019] 場務組行前通知信',
                    body=template.render(name=user[mail]),
                ))
            else:
                print(AwsSESTools.mail_header(user[mail], mail))


def reminder_to_cancel(path, dry_run=True):
    template = TPLENV.get_template('./190801_cancel.html')

    with open(path, 'r+') as files:
        csv_reader = csv.DictReader(files)
        _n = 0
        for u in csv_reader:
            print(">>>", _n)
            _n += 1
            if not dry_run:
                print(u['mail'])
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
                    subject=u'[COSCUP2019] Attendance Confirmation / 出席確認',
                    body=template.render(name=u['name']),
                ))
            else:
                print(AwsSESTools.mail_header(u['name'], u['mail']))


def reminder_program_speak(path, temp, title, dry_run=True):
    template = TPLENV.get_template(temp)

    with open(path, 'r+') as files:
        csv_reader = csv.DictReader(files)
        _n = 0
        for u in csv_reader:
            print('>>>', _n)
            _n += 1
            if not dry_run:
                print(u['mail'])
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_attach_program(
                    source=AwsSESTools.mail_header(u'COSCUP Program', 'program@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
                    subject=title,
                    body=template.render(name=u['name']),
                    token=u['token'],
                ))
            else:
                if not Path('./qrcode/program/%s.png' % u['token']).is_file():
                    raise Exception('no png file', u['token'])
                print(AwsSESTools.mail_header(u['name'], u['mail']), u['token'])


def reminder_workers(path, temp, title, dry_run=True):
    template = TPLENV.get_template(temp)

    with open(path, 'r+') as files:
        csv_reader = csv.DictReader(files)
        _n = 0
        for u in csv_reader:
            print('>>>', _n)
            _n += 1
            if not dry_run:
                print(u['mail'])
                body = AwsSESTools(setting.AWSID, setting.AWSKEY).send_attach_worker(
                    source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
                    subject=title,
                    body=template.render(**u),
                    token=u['token'],
                )
                queue_sender(body)
                return
            else:
                if not Path('./qrcode/worker/%s.png' % u['token']).is_file():
                    raise Exception('no png file', u['token'])
                print(AwsSESTools.mail_header(u['name'], u['mail']), u['token'])


def reminder_attendee(path, temp, title, dry_run=True):
    template = TPLENV.get_template(temp)

    with open(path, 'r+') as files:
        csv_reader = csv.DictReader(files)
        _n = 0
        for u in csv_reader:
            print('>>>', _n)
            _n += 1
            if not dry_run:
                print(u['mail'])
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_attach_attendee(
                    source=AwsSESTools.mail_header(u'COSCUP Attendee', 'attendee@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
                    subject=title,
                    body=template.render(**u),
                    token=u['token'],
                ))
            else:
                if not Path('./qrcode/attendee/%s.png' % u['token']).is_file():
                    raise Exception('no png file', u['token'])
                print(AwsSESTools.mail_header(u['name'], u['mail']), u['token'])


def group_sponsor(path, tokens):
    with open(path, 'r+') as files:
        csv_reader = csv.DictReader(files)
        data = {}
        for r in csv_reader:
            if int(r['token_nums']) == 0:
                continue

            data[int(r['no'])] = {
                'type': r['type'],
                'sponsor': r['sponsor'],
                'users': [{'name': r['name_1'], 'mail': r['mail_1'].lower().strip()}, ],
                'token_nums': int(r['token_nums']),
                'tokens': [],
                'game': r['game'],
                'link': r['link'],
            }
            if r['name_2']:
                data[int(r['no'])]['users'].append({'name': r['name_2'], 'mail': r['mail_2'].lower().strip()})

            if r['name_3']:
                data[int(r['no'])]['users'].append({'name': r['name_3'], 'mail': r['mail_3'].lower().strip()})

    with open(tokens) as files:
        csv_reader = csv.DictReader(files)
        for t in csv_reader:
            if int(t['no']) in data:
                data[int(t['no'])]['tokens'].append(t['token'])

    return data

def reminder_sponsor(temp, title, data, dry_run=True):
    template = TPLENV.get_template(temp)

    _n = 0
    for u in data:
        print('>>>', _n)
        _n += 1
        if not dry_run:
            for uu in data[u]['users']:
                print(uu['mail'])
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_attach_csv_sponsor(
                    source=AwsSESTools.mail_header(u'COSCUP Sponsorship', 'sponsorship@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(uu['name'], uu['mail']),
                    subject=title,
                    body=template.render(name=uu['name'], **data[u]),
                    data=data[u],
                ))
        else:
            for uu in data[u]['users']:
                print(AwsSESTools.mail_header(uu['name'], uu['mail']))


def reminder_baby(dry_run=True):
    template = TPLENV.get_template('./baby_reminder.html')

    with open('./baby_user.csv', 'r+') as files:
        csv_reader = csv.DictReader(files)
        _n = 0
        for u in csv_reader:
            print('>>>', _n)
            _n += 1
            if not dry_run:
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
                    subject=u'[COSCUP2019] 托育服務行前通知',
                    body=template.render(u),
                ))
            else:
                print(AwsSESTools.mail_header(u['name'], u['mail']))


def after_baby(dry_run=True):
    template = TPLENV.get_template('./baby_after.html')

    with open('./baby_user.csv', 'r+') as files:
        csv_reader = csv.DictReader(files)
        _n = 0
        for u in csv_reader:
            print('>>>', _n, u['mail'])
            _n += 1
            if not dry_run:
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
                    subject=u'[COSCUP2019] 托育服務問卷調查',
                    body=template.render(u),
                ))
            else:
                print(AwsSESTools.mail_header(u['name'], u['mail']))


def reminder_190817(dry_run=True):
    template = TPLENV.get_template('./190817_notice.html')
    data = {}
    with open('./works_form.csv', 'r+') as files:
        csv_reader = csv.DictReader(files)
        for u in csv_reader:
            data[u['mail']] = u['nickname']

        _n = 0
        for mail in data:
            if not dry_run:
                print('>>>', _n)
                _n += 1
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(data[mail], mail),
                    subject=u'[COSCUP2019] 8/18 ＊注意事項＊',
                    body=template.render(name=data[mail]),
                ))
            else:
                print(AwsSESTools.mail_header(data[mail], mail))

def reminder_190818(dry_run=True):
    template = TPLENV.get_template('./190818.html')
    data = {}
    with open('./attendee_token.csv', 'r+') as files:
        csv_reader = csv.DictReader(files)
        for u in csv_reader:
            data[u['mail']] = u['name']

        _n = 0
        for mail in data:
            if not dry_run:
                print('>>>', _n)
                print('>>>', mail)
                _n += 1
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(data[mail], mail),
                    subject=u'[COSCUP2019] 8/18 ＊Important!! 注意事項＊',
                    body=template.render(name=data[mail]),
                ))
            else:
                print(AwsSESTools.mail_header(data[mail], mail))


def reminder_190818_sponsor(dry_run=True):
    template = TPLENV.get_template('./190818_sponor.html')

    with open('./attendee_token.csv', 'r+') as files:
        csv_reader = csv.DictReader(files)
        data = {}
        for u in csv_reader:
            if int(u['fee']) < 2500:
                continue

            data[u['mail']] = u['name']

        if not dry_run:
            for mail in data:
                print(mail)
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP Sponsorship', 'sponsorship@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(data[mail], mail),
                    subject=u'[COSCUP2019] 速領取個人贊助贈品 到 15:30 TR513',
                    body=template.render(name=data[mail]),
                ))
        else:
            for mail in data:
                print(AwsSESTools.mail_header(data[mail], mail))


def after_coscup(dry_run=True):
    template = TPLENV.get_template('./after_coscup.html')

    with open('./after_coscup_maillist_uuid.csv', 'r+') as files:
        csv_reader = csv.DictReader(files)

        _n = 0
        if not dry_run:
            for u in csv_reader:
                print(_n, u['mail'])
                _n += 1
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP Attendee', 'attendee@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
                    subject=u'[COSCUP2019] 會後問卷 / Survey',
                    body=template.render(u),
                ))
        else:
            for u in csv_reader:
                print(AwsSESTools.mail_header(u['name'], u['mail']))


def after_traffic(dry_run=True):
    template = TPLENV.get_template('./traffic_after.html')

    with open('./traffic.csv', 'r+') as files:
        csv_reader = csv.DictReader(files)

        _n = 0
        if not dry_run:
            for u in csv_reader:
                print(_n, u['mail'])
                _n += 1
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
                    subject=u'[COSCUP2019] 交通費補助會後請領辦法 2019/09/01 截止',
                    body=template.render(u),
                ))
        else:
            for u in csv_reader:
                print(AwsSESTools.mail_header(u['name'], u['mail']))


def after_speak(dry_run=True):
    template = TPLENV.get_template('./program_speak_after.html')

    with open('./program_speak_after.csv', 'r+') as files:
        csv_reader = csv.DictReader(files)

        _n = 0
        if not dry_run:
            for u in csv_reader:
                print(_n, u['mail'])
                _n += 1
                print(AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP Program', 'program@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(u['name'], u['mail']),
                    subject=u'[COSCUP2019] Speaker Survey / 講者問卷',
                    body=template.render(u),
                ))
        else:
            for u in csv_reader:
                print(AwsSESTools.mail_header(u['name'], u['mail']))


def after_coscup_review(dry_run=True):
    template = TPLENV.get_template('./after_coscup_review.html')

    users = {}
    with open('./works_form.csv', 'r+') as files:
        csv_reader = csv.DictReader(files)

        for u in csv_reader:
            users[u['mail']] = u['nickname']

        _n = 0
        for mail in users:
            if not dry_run:
                print(_n, mail)
                _n += 1
                raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(users[mail], mail),
                    subject=u'[COSCUP2019] 協助檢討文件完成',
                    body=template.render(name=users[mail]),
                )
                queue_sender(raw)
            else:
                print(AwsSESTools.mail_header(users[mail], mail))


def after_coscup_review_2(dry_run=True):
    template = TPLENV.get_template('./after_coscup_review_2.html')

    users = {}
    with open('./after_reviews_2.csv', 'r+') as files:
        csv_reader = csv.DictReader(files)

        datas = []
        for u in csv_reader:
            datas.append(u)

        for u in datas:
            users[u['mail']] = {'name': u['name'], 'codes': []}

        for u in datas:
            users[u['mail']]['codes'].append(u['code'])

        users.pop('')

        _n = 0
        for mail in users:
            if not dry_run:
                print(_n, mail)
                _n += 1
                raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(users[mail]['name'], mail),
                    subject=u'[COSCUP2019] 檢討會地點與報名',
                    body=template.render(name=users[mail]['name'],
                                         codes=', '.join(users[mail]['codes'])),
                )
                queue_sender(raw)
            else:
                print(AwsSESTools.mail_header(users[mail]['name'], mail))


def after_coscup_review_staff(dry_run=True):
    template = TPLENV.get_template('./after_coscup_review_staff.html')

    with open('./works_form.csv', 'r+') as files:
        csv_reader = csv.DictReader(files)

        _n = 0
        for u in csv_reader:
            print(_n, u['mail'])
            _n += 1
            if not dry_run:
                raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP 行政組', 'secretary@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(u['nickname'], u['mail']),
                    subject=u'[COSCUP2019] 檢討會 9/21 night | TeSA 青島學堂',
                    body=template.render(name=u['nickname']),
                )
                queue_sender(raw)
            else:
                print(AwsSESTools.mail_header(u['nickname'], u['mail']))


def after_coscup_osc_tokyo(dry_run=True):
    template = TPLENV.get_template('./after_coscup_osc_tokyo.html')

    users = {}
    with open('./attendee_epaper.csv', 'r+') as files:
        csv_reader = csv.DictReader(files)

        for u in csv_reader:
            users[u['mail']] = u['name']

        users = {'toomore0929@gmail.com': 'Toomore'}

        _n = 0
        for mail in users:
            print(_n, mail)
            _n += 1
            if not dry_run:
                raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP Attendee', 'attendee@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(users[mail], mail),
                    subject=u'[COSCUP2019+1] 來去上海、來去東京！COSCon 與 OSC Tokyo「COSCUP 特別軌」徵稿開始！|',
                    body=template.render(name=users[mail]),
                )
                queue_sender(raw)
                return
            else:
                print(AwsSESTools.mail_header(users[mail], mail))

def coscup_taigi(dry_run=True):
    template = TPLENV.get_template('./coscup_taigi.html')

    users = {}
    with open('./attendee_epaper.csv', 'r+') as files:
        csv_reader = csv.DictReader(files)

        for u in csv_reader:
            users[u['mail']] = u['name']

        #users = {'toomore0929@gmail.com': 'Toomore'}

        _n = 0
        for mail in users:
            print(_n, mail)
            _n += 1
            if not dry_run:
                raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
                    source=AwsSESTools.mail_header(u'COSCUP Attendee', 'attendee@coscup.org'),
                    to_addresses=AwsSESTools.mail_header(users[mail], mail),
                    subject=u'[COSCUP2019 Taigi] 來用台語講開源 2019/12/21 即刻報名 |',
                    body=template.render(name=users[mail]),
                )
                queue_sender(raw)
            else:
                print(AwsSESTools.mail_header(users[mail], mail))

def coscup_taigi_notice(dry_run=True):
    template = TPLENV.get_template('./coscup_taigi_qrcode.html')

    users = []
    with open('./taigi_attendees_mail.csv', 'r+') as files:
        csv_reader = csv.DictReader(files)

        for u in csv_reader:
            users.append(u)

    _n = 0
    for u in users:
        print(_n, u['id'], u['token'])
        _n += 1

        #if dry_run:
        #    u['mail'] = 'toomore0929@gmail.com'

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_attach_taigi(
            source=AwsSESTools.mail_header(u'COSCUP Attendee', 'attendee@coscup.org'),
            to_addresses=AwsSESTools.mail_header(u['nickname'], u['mail']),
            subject=u'COSCUP「來台講」 + QRCode 報到、行前通知：明仔載，愛來！ (%s)' % u['id'],
            body=template.render(name=u['nickname']),
            token=u['token'],
        )
        queue_sender(raw)

def coscup_taigi_after(dry_run=True):
    template = TPLENV.get_template('./coscup_taigi_after.html')

    users = []
    with open('./taigi_attendees_mail.csv', 'r+') as files:
        csv_reader = csv.DictReader(files)

        for u in csv_reader:
            users.append(u)

    _n = 0
    for u in users:
        print(_n, u['id'], u['mail'])
        _n += 1

        #if dry_run:
        #    u['mail'] = 'toomore0929@gmail.com'

        raw = AwsSESTools(setting.AWSID, setting.AWSKEY).send_raw_email(
            source=AwsSESTools.mail_header(u'COSCUP Attendee', 'attendee@coscup.org'),
            to_addresses=AwsSESTools.mail_header(u['nickname'], u['mail']),
            subject=u'COSCUP「來台講」 會後問卷 (%s)' % u['id'],
            body=template.render(name=u['nickname']),
        )
        queue_sender(raw)


def queue_sender(body):
    requests.post('%s/exchange/coscup/secretary.1' % setting.QUEUEURL, data={'body': body})


if __name__ == '__main__':
    #worker_1('worker_1.csv', dry_run=False)
    #worker_2('works_form.csv', dry_run=False)
    #send_with_ics('./osc.csv', dry_run=False)
    #send_with_ics('./all_2018_users.csv')
    #for_chief_report('./works_form.csv', dry_run=False)
    #send_osc_deny(dry_run=False)
    #send_hotel('./hotel.csv', False)
    #for i in range(30):
    #    print(rand_str())
    #send_babysister(dry_run=False)
    #send_osc_fail('./osc_count_fail.csv', dry_run=False)
    #send_osc_pass('./osc_count_pass.csv', dry_run=False)
    #chief_vip('chief_vip_code_zh.html', u'邀請碼', False)
    #chief_vip('chief_vip_code_en.html', u'VIP Code', False)
    #baby_form('./baby.csv', False)
    #baby_form('./baby_1563508968.csv', False)
    #installation(dry_run=False)
    #reminder_to_cancel('./attendees-20190731.csv', dry_run=False)
    #reminder_program_speak(
    #        path='./program_speak.csv',
    #        temp='./program_speak.html',
    #        title=u'[COSCUP2019] [Please Read!] Your ticket and information about COSCUP2019',
    #        dry_run=False,
    #    )
    #reminder_program_speak(
    #        path='./program_invite.csv',
    #        temp='./program_invite.html',
    #        title=u'[COSCUP2019] [Please Read!] Your ticket and information about COSCUP2019',
    #        dry_run=False,
    #    )
    #reminder_workers(
    #        path='./worker_token.csv',
    #        temp='./worker_reminder.html',
    #        title=u'COSCUP2019 志工夥伴行前通知信',
    #        dry_run=False,
    #    )
    #reminder_attendee(
    #        path='./attendee_token.csv',
    #        temp='./user_reminder.html',
    #        title=u'COSCUP2019 Attendee Reminder / 會眾行前通知信',
    #        dry_run=False,
    #    )
    #from pprint import pprint
    #pprint(group_sponsor('./sponsor_list.csv', './sponsor_token.csv'))
    #reminder_sponsor(
    #        temp='./sponsor_en.html',
    #        title=u'COSCUP2019 Tickets（Include reminder letter）',
    #        data=group_sponsor('./sponsor_list.csv', './sponsor_token.csv'),
    #        dry_run=False,
    #    )
    #installation_reminder(dry_run=False)
    #reminder_baby(dry_run=False)
    #reminder_190817(dry_run=False)
    #reminder_190818(dry_run=False)
    #reminder_190818_sponsor(dry_run=False)
    #after_coscup(dry_run=False)
    #after_baby(dry_run=False)
    #after_traffic(dry_run=False)
    #after_speak(dry_run=False)
    #after_coscup_review(dry_run=False)
    #after_coscup_review_2(dry_run=False)
    #after_coscup_review_staff(dry_run=False)
    #after_coscup_osc_tokyo(dry_run=False)
    #coscup_taigi(dry_run=False)
    #coscup_taigi_notice(dry_run=True)
    #coscup_taigi_after(dry_run=True)
    pass
