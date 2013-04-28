#!/usr/bin/env python
# -*- coding: utf-8 -*-
from twilio.rest import TwilioRestClient
from piconfig import TWILIO_ID, TWILIO_PWD, TWILIO_FROM


class SMS(object):
    ''' SMS object '''
    def __init__(self):
        self.client = TwilioRestClient(TWILIO_ID, TWILIO_PWD)

    def send(self, to, body, from_=TWILIO_FROM):
        data = {
                'to': to,
                'body': u'[COSCUP]{0}'.format(body[:152]),
                'from_': from_,
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
