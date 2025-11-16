import json
import mysql.connector
from constants import constants
from flask import Blueprint, jsonify, current_app, request


info_bp = Blueprint('info', __name__)

@info_bp.route("/",methods=['GET'])
def info():
    cn_myth = mysql.connector.connect(user=constants['mysql_user'], password=constants['mysql_password'],host=constants['mysql_ip'],database='mythconverg',auth_plugin='mysql_native_password')
    c_myth = cn_myth.cursor(dictionary=True)
    
    query = f"select count(*) as recordings from recorded"
    c_myth.execute(query)
    data = c_myth.fetchall()
    recordings=data[0]['recordings']
    out = {
        'name': 'flask01be', 
        'version': current_app.config['VERSION'], 
        'recordings': recordings, 
        'thread_pool': len(current_app.config['THREAD_POOL'].keys())
        }
    
    return json.dumps(out)
