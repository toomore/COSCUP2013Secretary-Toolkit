#!/usr/bin/env python
# -*- coding: utf-8 -*-
from boto.sns import connect_to_region
import setting

AWSSNS = connect_to_region(setting.AWSREGION,
                           aws_access_key_id=setting.AWSID,
                           aws_secret_access_key=setting.AWSKEY)


def publish(*args):
    AWSSNS.publish(setting.COSCUSSNSARN, *args)

if __name__ == "__main__":
    #AWSSNS.publish(setting.COSCUSSNSARN, 'FROM PYTHON', 'COOL')
    print 'IN SNS.'
