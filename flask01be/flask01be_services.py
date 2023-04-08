from __main__ import app, version, thread_pool
from flask import request
import json
import mysql.connector
import logging
from flask01be_constants import constants


@app.route("/info",methods=['GET'])
def info():
    cn_myth = mysql.connector.connect(user=constants['mysql_user'], password=constants['mysql_password'],database='mythconverg',auth_plugin='mysql_native_password')
    c_myth = cn_myth.cursor(dictionary=True)
    
    query = f"select count(*) as recordings from recorded"
    c_myth.execute(query)
    data = c_myth.fetchall()
    recordings=data[0]['recordings']
    
    out = {'name': 'flask01be', 'version': version, 'recordings': recordings, 'thread_pool': len(thread_pool.keys())}
    return(json.dumps(out))
