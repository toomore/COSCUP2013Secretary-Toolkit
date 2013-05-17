#!/usr/bin/env python
# -*- coding: utf-8 -*-
from boto.sqs import connect_to_region
import setting
import json
import t


AWSSQS = connect_to_region(
        setting.AWSREGION,
        aws_access_key_id=setting.AWSID,
        aws_secret_access_key=setting.AWSKEY
        )

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

    return []

def sqs_send_first():
    t.template = t.env.get_template('./coscup_first.htm')
    r = keepgoing(setting.QUEUE_NAME_SENDFIRST, t.send_first)
    print r

def sqs_send_register():
    t.template = t.env.get_template('./coscup_register.htm')
    r = keepgoing(setting.QUEUE_NAME_REGISTER, t.send_register)
    print r

if __name__ == '__main__':
    #print clear(setting.QUEUE_NAME_SENDFIRST)
    #add(setting.QUEUE_NAME, [str(datetime.now()), str(datetime.now())])
    print 'IN SQS.'
