#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask
from flask import render_template
from flask import make_response
from flask import request
from flask import url_for
import t
app = Flask(__name__)

def getmenu():
    return u"<a href='{0}'>登錄信</a> | <a href='{1}'>歡迎信</a>".format(
        url_for('sendfirst'), url_for('sendwelcome'))

@app.route("/")
def hello():
    return getmenu()

@app.route("/send_welcome", methods=['POST', 'GET'])
def sendwelcome():
    if request.method == "POST":
        t.template = t.env.get_template('./coscup_welcome.htm')
        t.send_welcome(request.form.to_dict())
        return u'{0}<br>{1}'.format(request.form.to_dict(), getmenu())
    else:
        return make_response(render_template('t_sendwelcome.htm'))


@app.route("/send_first", methods=['POST', 'GET'])
def sendfirst():
    if request.method == "POST":
        t.template = t.env.get_template('./coscup_first.htm')
        t.send_first(request.form.to_dict())
        return u'{0}<br>{1}'.format(request.form.to_dict(), getmenu())
    else:
        return make_response(render_template('t_sendfirst.htm'))


if __name__ == "__main__":
    app.run(host='127.0.0.1',debug=True)
