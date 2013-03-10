#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask
from flask import render_template
from flask import make_response
from flask import request
from flask import url_for
from flask import redirect
from flask import session
from functools import wraps
import t
app = Flask(__name__)
app.session_cookie_name = 'COSCUP_session'
app.secret_key = 'LGV\x1a\tfp\xd2z\xfa[\xc0u\xde\x7f\xe4(\x08\x1a\x9bT\xd9\xb3\x90\xb6\xde\x05\x1c\x07\x07c\xf7\xcb\x91^\x99\x97yPi\xd1\xe0\x81\x8dW\x8f\x96\xad:\xd3@g\x8d\x8ex\xc8^)\xb0O\x0c\x04\xf7*' #os.urandom(128)

def getmenu():
    lg = url_for('logout') if session.get('user') else url_for('login')
    lgw = u'Logout' if session.get('user') else u'Login'
    return u"<a href='{0}'>登錄信</a> | <a href='{1}'>歡迎信</a> | <a href='{2}'>{3}</a>".format(
        url_for('sendfirst'), url_for('sendwelcome'), lg, lgw)

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
def hello():
    return getmenu()

@app.route("/send_welcome", methods=['POST', 'GET'])
@login_required
def sendwelcome():
    if request.method == "POST":
        t.template = t.env.get_template('./coscup_welcome.htm')
        t.send_welcome(request.form.to_dict())
        return u'{0}<br>{1}'.format(request.form.to_dict(), getmenu())
    else:
        return make_response(render_template('t_sendwelcome.htm'))


@app.route("/send_first", methods=['POST', 'GET'])
@login_required
def sendfirst():
    if request.method == "POST":
        t.template = t.env.get_template('./coscup_first.htm')
        t.send_first(request.form.to_dict())
        return u'{0}<br>{1}'.format(request.form.to_dict(), getmenu())
    else:
        return make_response(render_template('t_sendfirst.htm'))

@app.route("/login", methods=['POST', 'GET'])
def login():
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
            return make_response(render_template('t_login.htm'))

@app.route("/logout")
def logout():
    session.pop('user', None)
    return redirect(url_for('hello'))

if __name__ == "__main__":
    #app.run(host='127.0.0.1',debug=True)
    app.run(host='0.0.0.0', port=6666, debug=True)
