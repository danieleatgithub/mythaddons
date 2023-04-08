import mysql.connector
import logging
import re
from flask01be_constants import constants

def get_setting(key,logger = None):
    cn_mythusr = mysql.connector.connect(user=constants['mysql_user'], password=constants['mysql_password'],
                                         host='127.0.0.1', database='mythusraddon',
                                         auth_plugin='mysql_native_password')
    c_mythusr = cn_mythusr.cursor(dictionary=True)
    query = f"select value_field from settings where key_field='{key}'"
    logger.info(f"query={query}")
    c_mythusr.execute(query)
    tmp = c_mythusr.fetchall()
    value = tmp[0]['value_field']
    return value


def clean_title(title,filename=False,logger = None):
    cn_myth = mysql.connector.connect(user=constants['mysql_user'], password=constants['mysql_password'], host='127.0.0.1', database='mythusraddon',
                                      auth_plugin='mysql_native_password')
    c_myth = cn_myth.cursor(dictionary=True)
    query = f"select level,fromtitle,totitle,tofilename from cleantitle order by level"
    c_myth.execute(query)
    rules = c_myth.fetchall()
    out_title = title
    for rule in rules:
        if not filename and rule['totitle'] is not None:
            out_title = re.sub(rule['fromtitle'],rule['totitle'],out_title)
        if filename and rule['tofilename'] is not None:
            out_title = re.sub(rule['fromtitle'], rule['tofilename'], out_title)
    out_title = out_title.strip()
    if filename:
        out_title = out_title.lower()
    logger.info(f"out={out_title}")
    return out_title

