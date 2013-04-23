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
from piconfig import ALLOWED_EXTENSIONS
import t

app = Flask(__name__)
app.session_cookie_name = 'COSCUP_session'
app.secret_key = 'LGV\x1a\tfp\xd2z\xfa[\xc0u\xde\x7f\xe4(\x08\x1a\x9bT\xd9\xb3\x90\xb6\xde\x05\x1c\x07\x07c\xf7\xcb\x91^\x99\x97yPi\xd1\xe0\x81\x8dW\x8f\x96\xad:\xd3@g\x8d\x8ex\xc8^)\xb0O\x0c\x04\xf7*'  # os.urandom(128)
app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS

def getmenu():
    lg = url_for('logout') if session.get('user') else url_for('login')
    lgw = u'Logout' if session.get('user') else u'Login'
    return u"<a href='{0}'>登錄信</a> | <a href='{1}'>歡迎信</a> | <a href='{4}'>週報</a> | <a href='{2}'>{3}</a>".format(
        url_for('sendfirst'), url_for('sendwelcome'), lg, lgw, url_for('send_weekly'))

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
        flash(u'已寄送歡迎信：{nickname} / {mail} / {leaderno}'.format(**request.form.to_dict()))
        return redirect(url_for('send_welcome'))
    else:
        return make_response(render_template('t_sendwelcome.htm', title=title, send_welcome=1))


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
        return make_response(render_template('t_sendfirst.htm', title=title, send_first=1))


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
        return make_response(render_template('t_sendweekly.htm', title=title, send_weekly=1))


@app.route("/login", methods=['POST', 'GET'])
def login():
    title = u'Login'
    if request.method == "POST":
        u = request.form.get('user')
        pwd = request.form.get('pwd')
        pwdw = request.form.get('pwdw')
        if u == 'coscup' and pwd == 'ticc' and pwdw == '3':
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
