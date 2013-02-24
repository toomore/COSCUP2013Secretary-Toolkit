===================================
jinja2 - mail
===================================

以 jinja2 模板引擎排版電子報並利用 Amazon SES 發送


安裝
-----------------------------------

需要 boto, jinja2 套件

- boto： https://github.com/boto/boto
- jinja2： https://github.com/mitsuhiko/jinja2

::

    pip install -r ./requirements.txt


需要 Amazon AWS ID, KEY

::

    請在 ./piconfig_temp.py 鍵入必要資料後改名為 ./piconfig.py

電子報樣板
-----------------------------------

樣板位於 ./templates/，樣板範例預覽： `View <http://toomore.s3.amazonaws.com/pipaper/pi_isuphoto_org_paper20121210.htm>`_

如何發送
-----------------------------------

執行：

::

    python ./t.py (功能) (樣板位置)

功能：

#. output：匯出電子報檔案。

#. send：寄送電子報。

#. sendall：大量傳送電子報。

範例：

::

    python ./t.py output ./paper20121210.htm #輸出到 /run/shm/ppaper.htm

::

    python ./t.py send ./paper20121210.htm #寄送郵件

延伸功能
-----------------------------------

原來的程式有接來自資料庫使用者資料，但這部份只要在 sendall 改寫並餵入 [mail, user, nickname] 的基本欄位 dict 資料後就可以大量傳送郵件，歡迎嘗試改寫調整。
