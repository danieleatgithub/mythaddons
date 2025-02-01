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



get_video_path_bp = Blueprint('get_video_path', __name__)

@get_video_path_bp.route("/",methods=['GET'])
def get_video_path():
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
        group = request.args.get('group', default="Default", type=str)
        if basename is None:
            response['message'] = "basename is not set"
        else:
            path = get_media_path(basename,group,logger=current_app.logger)
            if path is not None:
                out['path'] = path
                response['error'] = False
        response['out'] = out
    return(json.dumps(response))
    


