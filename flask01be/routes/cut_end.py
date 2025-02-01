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



cut_end_bp = Blueprint('cut_end', __name__)

@cut_end_bp.route("/",methods=['POST'])
def cut_end():
    if request.method == 'POST':
        id = request.args.get('id', default = '*', type = str)
        thread_pool = current_app.config['THREAD_POOL']
        if id != "*":
            thread_pool[id].stop()
            thread_pool[id].join()
            del thread_pool[id]
        else:    
            for t in list(thread_pool.keys()):
                thread_pool[t].stop()
            for t in list(thread_pool.keys()):
                thread_pool[t].join()
                del thread_pool[t]
                
        return {'status': 'ok'}, 200
    else:
        return {'status': 'Method not allowed'}, 405
    
