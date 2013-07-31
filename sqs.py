#!/usr/bin/env python
# -*- coding: utf-8 -*-
from boto.sqs import connect_to_region
from sms import SMS
import setting
import ujson as json
import t


AWSSQS = connect_to_region(setting.AWSREGION,
                           aws_access_key_id=setting.AWSID,
                           aws_secret_access_key=setting.AWSKEY)

AWSSQSLIST = []


def SQSLIST(f):
    AWSSQSLIST.append(f.__name__)
    return f


def add(QUEUE_NAME, DATA):
    isinstance(DATA, list)

    q = AWSSQS.get_queue(QUEUE_NAME)

    for i in DATA:
        q.write(q.new_message(json.dumps(i)))


def doing(QUEUE_NAME, DOING):
    q = AWSSQS.get_queue(QUEUE_NAME)
    result = []

    for i in xrange(setting.FEEDS):
        read_m = q.read()

        if read_m:
            result.append(DOING(json.loads(read_m.get_body())))
            q.delete_message(read_m)
        else:
            result.append(False)

    return result


def clear(QUEUE_NAME):
    q = AWSSQS.get_queue(QUEUE_NAME)
    q.clear()


def keepgoing(QUEUE_NAME, DOING):
    sleep_times = 0
    q = AWSSQS.get_queue(QUEUE_NAME)

    while 1:
        rest = q.count()
        print sleep_times
        if rest:
            d = doing(QUEUE_NAME, DOING)
            print d
            if any(d):
                sleep_times = 0
            else:
                sleep_times += 1
        else:
            sleep_times += 1
            if sleep_times >= setting.SLEEP_TIMES:
                break


@SQSLIST
def sqs_send_first():
    t.template = t.env.get_template('./coscup_first.htm')
    keepgoing(setting.QUEUE_NAME_SENDFIRST, t.send_first)


@SQSLIST
def sqs_send_register():
    t.template = t.env.get_template('./coscup_register.htm')
    keepgoing(setting.QUEUE_NAME_REGISTER, t.send_register)


@SQSLIST
def sqs_send_speakerparty():
    t.template = t.env.get_template('./coscup_speakerparty.htm')
    keepgoing(setting.QUEUE_NAME_SENDSPEAKERPARTY, t.send_speakerparty)


@SQSLIST
def sqs_send_attendee_reminder():
    t.template = t.env.get_template('./coscup_attendee.htm')
    keepgoing(setting.QUEUE_NAME_SENDATTENDEEREMINDER, t.send_attendee_reminder)


@SQSLIST
def sqs_send_paper():
    keepgoing(setting.QUEUE_NAME_SENDPAPER, t.send_paper)


@SQSLIST
def sqs_send_welcome():
    t.template = t.env.get_template('./coscup_welcome.htm')
    keepgoing(setting.QUEUE_NAME_SENDWELCOME, t.send_welcome)


@SQSLIST
def sqs_send_leadervipcode():
    t.template = t.env.get_template('./coscup_leader_vip.htm')
    keepgoing(setting.QUEUE_NAME_SENDLEADERVIPCODE, t.send_leadervipcode)


@SQSLIST
def sqs_send_oscvipcode():
    t.template = t.env.get_template('./coscup_osc.htm')
    keepgoing(setting.QUEUE_NAME_SENDOSCVIPCODE, t.send_leadervipcode)


@SQSLIST
def sqs_send_personalsponsor():
    t.template = t.env.get_template('./coscup_personal_sponsor.htm')
    keepgoing(setting.QUEUE_NAME_SENDPERSONALSPONSOR, t.send_personal_sponsor)


@SQSLIST
def sqs_send_personalsponsorresend():
    t.template = t.env.get_template('./coscup_personal_sponsor_resend.htm')
    keepgoing(setting.QUEUE_NAME_SENDPERSONALSPONSORRESEND,
              t.send_personal_sponsor)


@SQSLIST
def sqs_sms_leader():
    doing_sms = SMS().send
    keepgoing(setting.QUEUE_NAME_SMSLEADER, doing_sms)


if __name__ == '__main__':
    #print clear(setting.QUEUE_NAME_SMSLEADER)
    #add(setting.QUEUE_NAME, [str(datetime.now()), str(datetime.now())])
    print 'IN SQS.'
