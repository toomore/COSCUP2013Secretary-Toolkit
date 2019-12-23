# -*- coding: utf-8 -*-
''' My AWS Tools '''
import csv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

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


def process_csv(path):
    data = {
        'deny': [],
        'insufficient_for': [],
        'pass': [],
    }

    with open(path, 'r+') as files:
        csv_reader = csv.DictReader(files)
        for r in csv_reader:
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
            body = template.render(**r)
            raw = make_raw_email(
                nickname=r['nickname'],
                mail=r['mail'],
                subject=u'[OSCVPass] Result: Deny',
                body=body,
                dry_run=dry_run,
            )
            SENDER.client.send_raw_email(RawMessage={'Data': raw})


if __name__ == '__main__':
    #from pprint import pprint
    data = process_csv('./oscvpass_191217.csv')
    #for case in data:
    #    print(case, len(data[case]))

    #pprint(data['deny'])
    send(data=data, case=('deny', ))
    pass