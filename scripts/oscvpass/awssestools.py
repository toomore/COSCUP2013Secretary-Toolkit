# -*- coding: utf-8 -*-
''' My AWS Tools '''
import csv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from uuid import uuid4

import setting

import boto3
import requests
from jinja2 import Environment
from jinja2 import FileSystemLoader


TPLENV = Environment(loader=FileSystemLoader('./tpl'))


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

MAIL_SOURCE = AwsSESTools.mail_header(u'OSCVPass', 'oscvpass@ocf.tw')
SENDER = AwsSESTools(setting.AWSID, setting.AWSKEY)

def make_raw_email(nickname, mail, subject, body, dry_run=True):
    if dry_run:
        mail = setting.TESTMAIL

    raw = SENDER.send_raw_email(
        source=MAIL_SOURCE,
        to_addresses=AwsSESTools.mail_header(nickname, mail),
        subject=subject,
        body=body,
    )
    return raw


def process_csv(path, _all=False):
    data = {
        'deny': [],
        'insufficient_for': [],
        'pass': [],
    }

    with open(path, 'r+') as files:
        csv_reader = csv.DictReader(files)
        for r in csv_reader:
            if not _all:
                if r['send'] != '':
                    continue

            if r['status'] == '拒絕':
                data['deny'].append(r)
            elif r['status'] == '補件':
                data['insufficient_for'].append(r)
            elif r['status'] == '通過':
                data['pass'].append(r)

    _fields = {
        'c_01': u'開放原始碼專案或活動名稱 / Open Source Project or Event Name',
        'c_02': u'開放原始碼專案 Repo 位置 / Open Source Project Repo',
        'c_03': u'其他有效證明 / Other Valid Proof ',
        'c_04': u'開放原始碼專案或活動說明 / Description of Open Source Project or Event ',
    }

    # ----- filter data ----- #
    for case in data:
        for r in data[case]:
            r['mail'] = r['mail'].strip()
            if len(r['nickname'].strip()) == 0:
                r['nickname'] = r['name'].strip()
            else:
                r['nickname'] = r['nickname'].strip()

            _doc = []
            for _f in ('c_01', 'c_02', 'c_03', 'c_04'):
                _doc.append('%s：' % _fields[_f])
                _doc.append('  %s' % r[_f])

            r['doc'] = '\r\n'.join(_doc)

    return data

def send(data, case, dry_run=True):
    ''' send mail

    :param dict data: include ``pass``, ``deny``, ``insufficient_for`` list data.
    :param tuple case: pass, deny, insufficient_for
    :param bool dry_run: Test mail

    '''
    if 'deny' in case:
        template = TPLENV.get_template('./deny.html')
        for r in data['deny']:
            if r['mail'] in setting.BLOCK:
                continue

            print('deny', r['mail'])
            body = template.render(**r)
            raw = make_raw_email(
                nickname=r['nickname'],
                mail=r['mail'],
                subject=u'[OSCVPass] Result: Deny (%s)' % r['nickname'],
                body=body,
                dry_run=dry_run,
            )
            if dry_run:
                continue

            SENDER.client.send_raw_email(RawMessage={'Data': raw})

    if 'insufficient_for' in case:
        template = TPLENV.get_template('./insufficient_for.html')
        for r in data['insufficient_for']:
            if r['mail'] in setting.BLOCK:
                continue

            print('insufficient_for', r['mail'])
            body = template.render(**r)
            raw = make_raw_email(
                nickname=r['nickname'],
                mail=r['mail'],
                subject=u'[OSCVPass] Result: Insufficient (%s)' % r['nickname'],
                body=body,
                dry_run=dry_run,
            )
            if dry_run:
                continue

            SENDER.client.send_raw_email(RawMessage={'Data': raw})

    if 'pass' in case:
        template = TPLENV.get_template('./pass.html')
        for r in data['pass']:
            if r['mail'] in setting.BLOCK:
                continue

            print('pass', r['mail'])
            body = template.render(**r)
            raw = make_raw_email(
                nickname=r['nickname'],
                mail=r['mail'],
                subject=u'[OSCVPass] Result: Pass (%s)' % r['nickname'],
                body=body,
                dry_run=dry_run,
            )
            if dry_run:
                continue

            SENDER.client.send_raw_email(RawMessage={'Data': raw})

def send_request_attendee(path, dry_run=True):
    with open(path, 'r') as files:
        csv_reader = csv.DictReader(files)

        template = TPLENV.get_template('./action_sitcon.html')
        for u in csv_reader:
            print(u)
            body = template.render(**u)
            raw = make_raw_email(
                nickname=u['name'],
                mail=u['mail'],
                subject=u'[OSCVPass] [提醒] 登記索取 SITCON (%s)' % u['name'],
                body=body,
                dry_run=dry_run,
            )
            SENDER.client.send_raw_email(RawMessage={'Data': raw})

def send_coscup_lpi(rows, dry_run=True):
    template = TPLENV.get_template('./lpi_token.html')
    _n = 1
    for u in rows:
        print(_n, u)
        _n += 1

        body = template.render(**u)
        raw = make_raw_email(
            nickname=u['name'],
            mail=u['mail'],
            subject=u'[OSCVPass] [提醒] 登記索取 LPI Exam 折扣券 (%s)' % u['name'],
            body=body,
            dry_run=dry_run,
        )
        SENDER.client.send_raw_email(RawMessage={'Data': raw})

        if dry_run:
            return

def send_mopcon_token(rows, dry_run=True):
    template = TPLENV.get_template('./mopcon_token.html')
    _n = 1
    for u in rows:
        if u['mail'] in setting.BLOCK:
            continue

        print(_n, u)
        _n += 1

        if dry_run:
            u['mail'] = setting.TESTMAIL

        body = template.render(**u)
        raw = make_raw_email(
            nickname=u['name'],
            mail=u['mail'],
            subject=u'[OSCVPass][提醒] MOPCON2020 開源貢獻票 優惠券 (%s)' % u['name'],
            body=body,
            dry_run=dry_run,
        )
        SENDER.client.send_raw_email(RawMessage={'Data': raw})

        if dry_run:
            return

def send_g0v_token(rows, dry_run=True):
    template = TPLENV.get_template('./g0v_summit_token.html')
    _n = 1
    for u in rows:
        if u['mail'] in setting.BLOCK:
            continue

        print(_n, u)
        _n += 1

        if dry_run:
            u['mail'] = setting.TESTMAIL

        body = template.render(**u)
        raw = make_raw_email(
            nickname=u['name'],
            mail=u['mail'],
            subject=u'[OSCVPass][提醒] g0v Summit 2020 開源貢獻票 優惠券 (%s)' % u['name'],
            body=body,
            dry_run=dry_run,
        )
        SENDER.client.send_raw_email(RawMessage={'Data': raw})

        if dry_run:
            return

def pickup_unique(data, cases):
    maillist = []
    for case in cases:
        for row in data[case]:
            row['mail'] = ','.join(row['mail'].split(' '))
            row['mail'] = ','.join(row['mail'].split('/'))
            row['mail'] = [m.strip() for m in row['mail'].split(',') if m][0]
            maillist.append({'name': row['name'], 'mail': row['mail']})
            print(row['name'], row['mail'])

    return maillist

def add_uuid_export_csv(datas, path):
    with open(path, 'w+') as files:
        csv_writer = csv.DictWriter(files, fieldnames=('name', 'mail', 'uuid'))
        csv_writer.writeheader()
        for data in datas:
            data['uuid'] = ('%0.8x' % uuid4().fields[0]).upper()
            csv_writer.writerow(data)

def merge_token(datas, token_path, out_path):
    with open(token_path, 'r+') as files:
        tokens = list(csv.DictReader(files))

    _n = 0
    for user in datas:
        tokens[_n].update(user)
        _n += 1

    with open(out_path, 'w+') as files:
        csv_writer = csv.DictWriter(files, fieldnames=list(tokens[0].keys()), quoting=csv.QUOTE_NONNUMERIC)
        csv_writer.writeheader()
        csv_writer.writerows(tokens)

def update_token(datas, org_path, out_path):
    with open(org_path, 'r+') as files:
        mails = list(csv.DictReader(files))

    added = {i['mail'] for i in mails}
    for data in datas:
        if data['mail'] in added:
            continue

        for mail in mails:
            if not mail['mail']:
                mail['name'] = data['name']
                mail['mail'] = data['mail']
                break

    with open(out_path, 'w+') as files:
        csv_writer = csv.DictWriter(files, fieldnames=('mail', 'name', 'token', 'check'), quoting=csv.QUOTE_NONNUMERIC)
        csv_writer.writeheader()
        csv_writer.writerows(mails)

    print(mails)

if __name__ == '__main__':
    #from pprint import pprint
    #data = process_csv('./oscvpass_201021.csv', _all=False)
    #for case in data:
    #    print(case, len(data[case]))

    #pprint(data['deny'])
    #send(data=data, case=('deny', 'insufficient_for', 'pass'), dry_run=False)
    #send_request_attendee('/run/shm/hash_b0466044.csv', dry_run=True)

    # ----- send get token ----- #
    #data = process_csv('./oscvpass_200915.csv', _all=True)
    #maillist = pickup_unique(data=data, cases=('pass', ))
    #print(maillist, len(maillist))
    #merge_token(
    #        datas=maillist, token_path='./mopcon_2020_token.csv', out_path='./mopcon_2020_token_mails.csv')
    #send_coscup_lpi(rows=maillist, dry_run=False)

    # ----- export uuid csv ----- #
    #add_uuid_export_csv(maillist, './oscvpass_200729_uni_uuid.csv')

    # ----- send mopcon token ----- #
    #with open('./mopcon_2020_token_mails_201021_min.csv', 'r+') as files:
    #    rows = []
    #    for user in csv.DictReader(files):
    #        if not user['mail']:
    #            continue
    #        rows.append(user)

    #    send_mopcon_token(rows=rows, dry_run=False)

    # ----- g0v Summit ----- #
    #data = process_csv('./oscvpass_200930.csv', _all=True)
    #maillist = pickup_unique(data=data, cases=('pass', ))
    #print(maillist, len(maillist))
    #merge_token(
    #        datas=maillist, token_path='./g0v_summit_token.csv', out_path='./g0v_summit_token_mails.csv')

    # ----- send g0v token ----- #
    #with open('./g0v_summit_token_mails_201021_min.csv', 'r+') as files:
    #    rows = []
    #    for user in csv.DictReader(files):
    #        if not user['mail']:
    #            continue
    #        rows.append(user)

    #    send_g0v_token(rows=rows, dry_run=False)

    # ----- update token ----- #
    #data = process_csv('./oscvpass_201021.csv', _all=True)
    #maillist = pickup_unique(data=data, cases=('pass', ))
    #print(maillist, len(maillist))

    #update_token(datas=maillist,
    #        org_path='./mopcon_2020_token_mails_201014.csv',
    #        out_path='./mopcon_2020_token_mails_201021.csv')

    pass
