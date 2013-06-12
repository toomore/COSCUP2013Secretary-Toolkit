#!/usr/bin/env python
# -*- coding: utf-8 -*-
from twilio.rest import TwilioRestClient
from setting import TWILIO_FROM
from setting import TWILIO_ID
from setting import TWILIO_PWD


class SMS(object):
    ''' SMS object '''
    def __init__(self):
        self.client = TwilioRestClient(TWILIO_ID, TWILIO_PWD)

    def send(self, msg):
        data = {
                'to': msg['to'],
                'body': u'[COSCUP]{0}'.format(msg['body'][:152]),
                'from_': TWILIO_FROM,
                }
        try:
            m = self.client.sms.messages.create(**data)
            return {
                    'status': True,
                    'msg': m,
                    'sid': m.sid,
                    'price': m.price,
                    }
        except Exception as e:
            return {
                    'status': False,
                    'ERROR': str(e),
                    'data': data,
                    }
