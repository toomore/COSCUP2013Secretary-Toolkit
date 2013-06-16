===================================
COSCUP2013Secretary Tool Kit
===================================

以 jinja2 模板引擎排版電子報並利用 Amazon SES 發送，使用 twilio 傳送簡訊通知，所有的任務丟到 AWS SQS，再透過 AWS SNS 喚起執行任務。


安裝
-----------------------------------

需要 boto, jinja2 套件

- boto： https://github.com/boto/boto
- flask： https://pypi.python.org/pypi/Flask
- uwsgi： https://pypi.python.org/pypi/uWSGI
- twilio： https://pypi.python.org/pypi/twilio
- ujson： https://pypi.python.org/pypi/ujson

::

    pip install -r ./requirements.txt


需要 Amazon AWS ID, KEY, twilio SID, TOKEN

::

    請在 ./setting.py.tmp 鍵入必要資料後改名為 ./setting.py

電子報樣板
-----------------------------------

樣板位於 ./templates/，樣板範例預覽： `View <http://bit.ly/173gH41>`_


延伸功能
-----------------------------------

原來的程式有接來自資料庫使用者資料，但這部份只要在 sendall 改寫並餵入 [mail, user, nickname] 的基本欄位 dict 資料後就可以大量傳送郵件，歡迎嘗試改寫調整。


Web Server
-----------------------------------

Flask

- python ./app.py

uWSGI

- uwsgi -w app:app --http :6666 --logto /run/shm/coscup_sender_uwsgi.log
- uwsgi --ini ./uwsgi.ini

ScreenShot
-----------------------------------

.. image:: http://s3.toomore.net/coscup/2013-06-15+02.19.07.png

