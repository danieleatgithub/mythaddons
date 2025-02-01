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
from flask import Blueprint, jsonify, current_app, request
import logging


cut_recording_bp = Blueprint('cut_recording', __name__)

@cut_recording_bp.route("/",methods=['POST'])
def cut_recording():
    response = {}
    response['error'] = True
    response['debug'] = ""
    response['out'] = {}
    response['message'] = ""
    response['count'] = 0
    if request.method == 'POST':
        data = request.form
        cn_myth = mysql.connector.connect(user=constants['mysql_user'], password=constants['mysql_password'],database='mythconverg',auth_plugin='mysql_native_password')
        c_myth = cn_myth.cursor(dictionary=True)
        video_path = get_setting('videos',current_app.logger)
        dryrun = request.args.get('dryrun', default=False, type=bool)

        # get video filename and title
        query = f"select recorded.basename,recorded.title from recorded where recorded.recordedid = {data['videoid']}"
        c_myth.execute(query)
        data = c_myth.fetchall()        
        basename=data[0]['basename']
        title = data[0]['title']
        
        video_inp_path = get_media_path(basename,logger=current_app.logger)
        if video_inp_path is None:
            response['out'] = {}
            response['debug'] = str(basename)
            response['message'] = f"{str(basename)} Video not found"
            current_app.logger.error(response['message'])
            return(json.dumps(response))
 
        # Get videos paths
        out_basename = clean_title(title,filename=True,logger=current_app.logger)
        video_out = video_path + out_basename + '.mpg'
        query = 'select storagegroup.dirname as dirname from storagegroup where storagegroup.groupname = "Videos"'
        c_myth.execute(query)
        for item in c_myth.fetchall():
            if os.path.isfile(item['dirname'].decode('utf8') + out_basename):
                response['out'] = {}
                response['debug'] = str(basename)
                response['message'] = f"Video {item['dirname'].decode('utf8') + out_basename} already exists"
                app.logger.error(response['message'])
                return (json.dumps(response))

        # Build output filename
        # ###################
        cut_thread = CutJob(video_inp_path,basename,video_out)
        cut_thread.prepare_job(dryrun)
        cut_thread.start()
        id = cut_thread.get_id()
        current_app.config['THREAD_POOL'][id] = cut_thread
        
        out = {'name': 'flask01be', 'title': title, 'data': basename, 'video_inp_path':  video_inp_path, 'id': id, 'video_out': video_out }
        response['error'] = False
        response['out'] = json.dumps(out)
        response['debug'] = str(video_inp_path + basename)
    else:
        response['out'] = {}
        response['debug'] = request
    return(json.dumps(response))

