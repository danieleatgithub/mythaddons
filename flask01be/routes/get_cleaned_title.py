import subprocess
import threading
import json
import sys, getopt
import mysql.connector
import datetime
import ffmpeg
import time
import uuid
import os.path
from utils.utilities import clean_title, get_setting, get_media_path
from constants import constants
import ffmpeg
from ffprobe import FFProbe
import logging
from flask import Blueprint, jsonify, request, current_app



get_cleaned_title_bp = Blueprint('get_cleaned_title', __name__)

@get_cleaned_title_bp.route("/",methods=['GET'])
def get_cleaned_title():
    response = {}
    response['error'] = True
    response['debug'] = ""
    response['out'] = {}
    response['message'] = ""
    response['count'] = 0
    out = {}
    if request.method == 'GET':
        data = request.form
        cn_myth = mysql.connector.connect(user=constants['mysql_user'], password=constants['mysql_password'],database='mythconverg',auth_plugin='mysql_native_password')
        c_myth = cn_myth.cursor(dictionary=True)
        basename = request.args.get('basename', default=None, type=str)
        raw_title = request.args.get('raw_title', default=None, type=str)
        if raw_title is None and basename is None:
            response['message'] = "basename and raw_title are not set"
        else:
            title = None
            if basename is not None:
                query = f"select recorded.title from recorded where recorded.basename = '{basename}'"
                c_myth.execute(query)
                data = c_myth.fetchall()        
                current_app.logger.info(f"get_cleaned_title: {data}")
                if len(data) == 0:
                    response['message'] = f"basename {basename} not found"
                    response['debug'] = query
                else:
                    title = data[0]['title']
            else:
                title = raw_title        
            if title is not None:
                out['filename'] = clean_title(title,filename=True,logger=current_app.logger)
                out['title'] = clean_title(title,filename=False,logger=current_app.logger)
                response['error'] = False
        response['out'] = out
    return(json.dumps(response))

