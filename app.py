#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask
from flask import flash
from flask import render_template
from flask import make_response
from flask import request
from flask import url_for
from flask import redirect
from flask import session
from functools import wraps
from setting import ALLOWED_EXTENSIONS
from setting import LEADER_SMS
from setting import FLASK_KEY
from setting import FLASK_SESSION
from setting import LOGIN_ID
from setting import LOGIN_PWD
from setting import LOGIN_CHOICE
from setting import STAFF_CNO
from setting import STAFF_SMS
from setting import QUEUE_NAME_SENDFIRST
from setting import QUEUE_NAME_LIST
from setting import QUEUE_NAME_SMSLEADER
from util import read_csv
import t
import sns
import sqs
import ujson as json


app = Flask(__name__)
app.session_cookie_name = FLASK_SESSION
app.secret_key = FLASK_KEY
app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


def login_required(f):
    @wraps(f)
    def cklogin(*args, **kwargs):
        if session.get('user') == 1:
            pass
        else:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return cklogin


@app.route("/")
@login_required
def hello():
    return make_response(render_template('base.htm'))


@app.route("/send_welcome", methods=['POST', 'GET'])
@login_required
def send_welcome():
    title = u'Send Welcome'
    if request.method == "POST":
        t.template = t.env.get_template('./coscup_welcome.htm')
        t.send_welcome(request.form.to_dict())
        flash(u'已寄送歡迎信：{nickname} / {mail} / {leaderno}'.format(
            **request.form.to_dict()))
        return redirect(url_for('send_welcome'))
    else:
        return make_response(render_template('t_sendwelcome.htm',
                                             title=title, send_welcome=1))


@app.route("/send_sms", methods=['POST', 'GET'])
@login_required
def send_sms():
    title = u'Send SMS'
    if request.method == "POST":
        leaderno = request.form.getlist('leaderno')
        body = request.form.get('msg')
        if body:
            msgs = []
            if 'all' in leaderno:
                for i in LEADER_SMS.values():
                    msgs.append({'to': i, 'body': body})
                    flash(u'{0} {1}'.format(i, body))

                sqs.add(QUEUE_NAME_SMSLEADER, msgs)
            else:
                if leaderno:
                    for i in leaderno:
                        msgs.append({'to': LEADER_SMS[i], 'body': body})
                        flash(u'{0} {1}'.format(LEADER_SMS[i], body))

                    sqs.add(QUEUE_NAME_SMSLEADER, msgs)
                else:
                    flash(u'沒有選擇組別！')
        else:
            flash(u'沒有內容！')

        return redirect(url_for('send_sms'))
    else:
        return make_response(render_template('t_sendsms.htm', title=title,
                                             send_sms=1))


@app.route("/send_sms_coll", methods=['POST', 'GET'])
@login_required
def send_sms_coll():
    title = u'Send SMS by Coll'
    if request.method == "POST":
        cno = request.form.getlist('cno')
        body = request.form.get('msg')
        cno = STAFF_SMS if 'all' in cno else cno

        if body:
            for i in cno:
                msgs = []
                for u in STAFF_SMS[i]:
                    msgs.append({'to': u['phone'], 'body': body})
                    flash(u'{0} {1}'.format(u['phone'], body))

                sqs.add(QUEUE_NAME_SMSLEADER, msgs)
        else:
            flash(u'沒有內容！')

        return redirect(url_for('send_sms_coll'))
    else:
        coll = []
        for i in STAFF_SMS:
            coll.append({'CNO': i,
                         'CNO_NAME': STAFF_CNO[i], })

        return make_response(render_template('t_sendsmscoll.htm', coll=coll,
                                             title=title, send_sms_coll=1))


@app.route("/send_first", methods=['POST', 'GET'])
@login_required
def send_first():
    title = u'Send First'
    if request.method == "POST":
        t.template = t.env.get_template('./coscup_first.htm')
        t.send_first(request.form.to_dict())
        flash(u'已寄送登錄信：{nickname} / {mail}'.format(**request.form.to_dict()))
        return redirect(url_for('send_first'))
    else:
        return make_response(render_template('t_sendfirst.htm',
                                             title=title, send_first=1))


@app.route("/send_all_first", methods=['POST', 'GET'])
@login_required
def send_all_first():
    title = u'Send All People First'
    if request.method == "POST":
        f = request.files.get('file')
        if f and allowed_file(f.filename):
            if request.form.get('sendby') == 'sqs':
                sqs.add(QUEUE_NAME_SENDFIRST, read_csv(f))
                flash(u'丟到 AWS SQS')

            elif request.form.get('sendby') == 'mail':
                #t.template = t.env.get_template('./coscup_first.htm')
                #t.sendall(read_csv(f), t.send_first)
                flash(u'寄送大量登錄信')

            else:
                flash(u'錯誤選擇！')

        return redirect(url_for('send_all_first'))
    else:
        return make_response(render_template('t_sendallfirst.htm',
                                             title=title, send_all_first=1))


@app.route("/send_transportation_fare", methods=['POST', 'GET'])
@login_required
def send_transportation_fare():
    title = u'Send Transportation Fare'
    if request.method == "POST":
        t.template = t.env.get_template('./coscup_transportation_fare.htm')
        t.send_transportation_fare(request.form.to_dict())
        flash(u'已交通費確認信：{nickname} / {mail}'.format(**request.form.to_dict()))
        return redirect(url_for('send_transportation_fare'))
    else:
        return make_response(render_template('t_sendtransportation_fare.htm',
                                             title=title,
                                             send_transportation_fare=1))

@app.route("/awssqs", methods=['POST', 'GET'])
@login_required
def awssqs():
    title = u'AWS SQS'
    if request.method == "POST":
        f = request.files.get('file')
        if f and allowed_file(f.filename):
            sendby = request.form.get('sendby')
            if sendby:
                sqs.add(sendby, read_csv(f))
                flash(u'丟到 AWS SQS {0}'.format(sendby))
            else:
                flash(u'錯誤選擇！')

        return redirect(url_for('awssqs'))
    else:
        return make_response(render_template('t_awssqs.htm', title=title,
                                             qlist=QUEUE_NAME_LIST, awssqs=1))


@app.route("/awssns", methods=['POST', 'GET'])
@login_required
def awssns():
    title = u'AWS SNS'
    if request.method == "POST":
        sendby = request.form.get('sendby')
        if sendby:
            sns.publish(sendby, 'COSCUPSNS')
            flash(u'啟動 AWS SQS {0}'.format(sendby))
        else:
            flash(u'錯誤選擇！')

        return redirect(url_for('awssns'))
    else:
        return make_response(render_template('t_awssns.htm', title=title,
                                             qlist=sqs.AWSSQSLIST, awssns=1))


@app.route("/send_weekly", methods=['POST', 'GET'])
@login_required
def send_weekly():
    title = u'Send Weekly'
    if request.method == "POST":
        f = request.files.get('file')
        if f and allowed_file(f.filename):
            no = int(request.form.get('no'))
            mail = request.form.get('mail')
            t.send_weekly(no, f.stream.read(), mail)
            flash(u'已寄送週報：#{0:02} / {1}'.format(no, mail))
            return redirect(url_for('send_weekly'))
        else:
            flash(u'沒有檔案！')
            return redirect(url_for('send_weekly'))
    else:
        return make_response(render_template('t_sendweekly.htm', title=title,
                                             send_weekly=1))


@app.route("/api", methods=['POST', ])
def api():
    if request.method == "POST":
        ## For getting AWS SNS comfirm msgs.
        ## print request.headers, request.data
        sqsmessage = json.loads(request.data).get('Message')
        getattr(sqs, sqsmessage)() if hasattr(sqs, sqsmessage) else None
    return ''


@app.route("/login", methods=['POST', 'GET'])
def login():
    title = u'Login'
    if request.method == "POST":
        u = request.form.get('user')
        pwd = request.form.get('pwd')
        pwdw = request.form.get('pwdw')
        if u == LOGIN_ID and pwd == LOGIN_PWD and pwdw == LOGIN_CHOICE:
            session['user'] = 1
            #return u'IN POST {0}'.format(request.form)
            return redirect(url_for('hello'))
        else:
            return redirect(url_for('logout'))
    else:
        if session.get('user'):
            return redirect(url_for('hello'))
        else:
            return make_response(render_template('t_login.htm', title=title))


@app.route("/logout")
def logout():
    session.pop('user', None)
    return redirect(url_for('hello'))


if __name__ == "__main__":
    #app.run(host='127.0.0.1',debug=True)
    app.run(host='0.0.0.0', port=6666, debug=True)
