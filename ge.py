#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gevent import pywsgi
from app import app

W = pywsgi.WSGIServer(('0.0.0.0', 6666), app)
print W.get_environ()
W.serve_forever()
