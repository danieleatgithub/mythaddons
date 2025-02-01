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
from flask import Blueprint, jsonify, current_app, request
from datetime import datetime
import re
import psutil

cut_status_bp = Blueprint('cut_status', __name__)
cutter_status_file = '/tmp/cutter.json'

def convert_seconds(total_seconds):
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return int(hours), int(minutes), int(seconds)
    
@cut_status_bp.route("/",methods=['GET'])
def cut_status():
    response = {}
    response['error'] = True
    response['debug'] = ""
    response['out'] = {}
    response['message'] = ""
    response['count'] = 0
    done_seconds = 0
    out = dict()
    if request.method == 'GET':
       try:
            with open(cutter_status_file, 'r') as file:
                cutter_status = json.load(file)
       except:
            response['message'] = "no status file"
            current_app.logger.error(f"no status file")
            response['out'] = {}
            response['debug'] = str(request)
            return(json.dumps(response))
       
       out['status'] = cutter_status                
       filename = cutter_status['out_file'].split('/')[-1]
       if not psutil.pid_exists(cutter_status['pid']) and cutter_status['status'] != 'completed':
            response['message'] = f"File: {filename}\nCutter pid {cutter_status['pid']} not running status:{cutter_status['status']}"
            current_app.logger.error(f"response['message']")
            response['error'] = False
       else:
            step = cutter_status['step']
            if cutter_status['jobtype']=='merge':
                stats = cutter_status['step_stats'][str(step)]
                elapsed = int(time.time() - int(stats['begin']))
                cmd = f"/usr/bin/sed 's/\\r/\\r\\n/g' {cutter_status['temp_folder']}/err_{cutter_status['step']}.txt | /usr/bin/grep time= | /usr/bin/tail -1"
                current_line = subprocess.run([cmd],stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,shell=True)
                match = re.search(r"time=(\d{2}):(\d{2}):(\d{2}\.\d+)", current_line.stdout)
                if match:
                    hours, minutes, seconds = map(float, match.groups())
                    done_seconds = hours * 3600 + minutes * 60 + seconds
                else:
                    done_seconds = 0
                    response['message'] = f"No time found in {current_line}"
    
            if done_seconds != 0:
                todo_seconds = cutter_status['input_duration'] - done_seconds
                speed = elapsed / done_seconds
                remain_estimated = todo_seconds * speed
                estimated_h, estimated_m, estimated_s = convert_seconds(remain_estimated)
                eta_s= int(time.time()) + remain_estimated
                eta = datetime.fromtimestamp(eta_s).strftime('%Y-%m-%d %H:%M:%S')
            else:
                todo_seconds = 0
                speed = 0
                estimated_h = estimated_m = estimated_s = 0
                remain_estimated = 0
                elapsed = 0
                eta = "N/A"
            out['stats'] = dict()
            out['stats']['video_done_seconds'] =  int(done_seconds)
            out['stats']['video_todo_seconds'] =  int(todo_seconds)
            out['stats']['video_encoding_elapsed'] =  int(elapsed)
            out['stats']['encoding_seconds_for_video_second'] =  speed
            out['stats']['encoding_eta'] =  eta
            out['stats']['encoding_remain_str'] =  f"{estimated_h}:{estimated_m}:{estimated_s}"
            out['stats']['encoding_remain_sec'] =  remain_estimated
            response['error'] = False

       response['out'] = out
       response['debug'] = ""
    else:
       response['out'] = {}
       response['debug'] = str(request)
    return(json.dumps(response))
    
