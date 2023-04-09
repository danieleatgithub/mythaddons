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
from flask import Flask
from flask_cors import CORS
from flask import request
from flask01be_utility import clean_title, get_setting, get_media_path
from flask01be_constants import constants
import ffmpeg
from ffprobe import FFProbe

import logging

app = Flask(__name__)
CORS(app)

version = "1.0"
thread_pool = {}



#x refactor https://flask.palletsprojects.com/en/2.2.x/patterns/packages/
#x refactor https://github.com/pallets/flask/tree/2.2.3/examples/tutorial/flaskr
import flask01be_services

class CutJob(threading.Thread):
    def __init__(self,video_inp_path,video_inp_basename,video_out):
        super(CutJob, self).__init__()
        self.running = False
        self.count = 1
        self.video_inp_basename = video_inp_basename
        self.video_inp_path = video_inp_path
        self.video_out = video_out
        self.id = str(uuid.uuid4())
        self.stream_map = ""
        self.framerate = None
        self.jobs = []
        self.segments = 0
        self.video_temp = get_setting('videotemp',app.logger) + self.id
        self.stage = 0
        self.total_stages = 0
        self.dryrun = False

    def run(self):
        self.running = True
        app.logger.info(f"Worker {self.id} started for {self.video_inp_path+self.video_inp_basename} to {self.video_out} using {self.video_temp}")
        for job in self.jobs:
            if not self.running:
                break
            with open(f'{self.video_temp}/out_{self.stage}.txt', 'w+') as fout:
                with open(f'{self.video_temp}/err_{self.stage}.txt', 'w+') as ferr:
                    if not self.dryrun:
                        subprocess.run([job], shell=True, stdout=fout, stderr=ferr, universal_newlines=True)
                    app.logger.info(f"Worker {self.id} job {job}")
                    self.stage += 1
        self.running = False

    def prepare_job(self,dry_run=False):
        self.dryrun = dry_run
        metadata = FFProbe(self.video_inp_path+self.video_inp_basename)
        for s in metadata.streams:
            if s.is_video():
                self.framerate = float(s.framerate)
                self.stream_map = self.stream_map + f"-map 0:{s.index} -c:{s.index} copy "
                app.logger.info(f"{self.id} {s.index}: Video id:{s.id} fps:{s.framerate} size:{s.height}x{s.width}")
            elif s.is_audio():
                self.stream_map = self.stream_map + f"-map 0:{s.index} -c:{s.index} copy "
                app.logger.info(f"{self.id} {s.index}: Audio id:{s.id} lang:{s.language()}")
            elif s.is_subtitle():
                self.stream_map = self.stream_map + f"-map 0:{s.index} -c:{s.index} copy "
                app.logger.info(f"{self.id} {s.index}: Subtitle id:{s.id} lang:{s.language()}")
            else:
                app.logger.info(f"{self.id} {s.index}: other id:{s.id}")

        app.logger.info(f"{self.id} {metadata.streams}")
        cnx = mysql.connector.connect(user=constants['mysql_user'], password=constants['mysql_password'], host='127.0.0.1', database='mythconverg',
                                      auth_plugin='mysql_native_password')
        cursor = cnx.cursor(dictionary=True)
        query = f"select chanid from recorded where basename='{self.video_inp_basename}'"
        cursor.execute(query)
        data = cursor.fetchall()
        chanid = data[0]['chanid']

        query = f"select starttime from recorded where basename='{self.video_inp_basename}'"
        cursor.execute(query)
        data = cursor.fetchall()
        starttime = str(data[0]['starttime'])

        query = f"select mark,type from recordedmarkup where chanid={chanid} and starttime='{starttime}' and type in (0,1) order by mark;"
        app.logger.info(f"{self.id} {query}")
        cursor.execute(query)
        data = cursor.fetchall()

        # COMM_OPTS="-avoid_negative_ts make_zero -map 0:0 -c:0 copy -map 0:1 -c:1 copy -map 0:2 -c:2 copy -map 0:3 -c:3 copy -map_metadata 0 -movflags +faststart -default_mode infer_no_subs -ignore_unknown -f mpegts -y"
        # CMD_1="ffmpeg -hide_banner -ss 292.990 -i $TS_INP -to 420.000 $COMM_OPTS $TS_TMP_01"

        start_mark = float(0)
        merge_segments = []
        for (m) in data:
            if m['type'] == 0:
                start_mark = float(m['mark']) / self.framerate
                continue
            if m['type'] == 1:
                end_mark = float(m['mark']) / self.framerate
                cut_duration = round((end_mark - start_mark), 3)
            osegment = f"{self.video_temp}/segment-{self.segments}.ts"
            cmd = f"ffmpeg -hide_banner -ss {start_mark} -i {self.video_inp_path+self.video_inp_basename} -t {cut_duration} {self.stream_map}"
            cmd += " -map_metadata 0 -movflags +faststart -default_mode infer_no_subs -ignore_unknown -f mpegts -y "
            cmd += osegment
            merge_segments.append(f"file file:{osegment}")
            self.segments += 1
            app.logger.info(f"{self.id} {cmd}")
            self.jobs.append(cmd)

        # CMD_3="echo -e \"file file:$TS_TMP_01\nfile file:$TS_TMP_02\" | ffmpeg -hide_banner -f concat -safe 0 -protocol_whitelist file,pipe -i - -map 0:0 -c:0 copy -map 0:1 -c:1 copy -map 0:2 -c:2 copy -map 0:3 -c:3 copy -movflags +faststart -default_mode infer_no_subs -ignore_unknown -f mpegts -y $TS_OUT"
        segments_name = "\\n".join(merge_segments)

        # ok da shell da errore con subprocess
        cmd = f'echo "{segments_name}" | ffmpeg -hide_banner -f concat -safe 0 -protocol_whitelist file,pipe -i - {self.stream_map} -movflags +faststart -default_mode infer_no_subs -ignore_unknown -f mpegts -y {self.video_out}'
        app.logger.info(f"{self.id} {cmd}")

        self.jobs.append(cmd)
        self.jobs.append(f"chown mythtv.mythtv {self.video_out}")
        self.jobs.append(f"mythcommflag --rebuild --video {self.video_out}")
        self.total_stages = len(self.jobs)
        os.makedirs(self.video_temp)

    def stop(self):
        self.running = False
    
    def get_id(self):
        return self.id

    def get_stage(self):
        return self.stage

    def get_total_stages(self):
        return self.total_stages

    def get_files(self):
        return { 'out': self.video_inp_path+self.video_inp_basename }

    def is_running(self):
        return self.running

    def get(self):
        return self.jobs
        
@app.route("/cut_status",methods=['GET'])
def cut_status():
    response = {}
    response['error'] = True
    response['debug'] = ""
    response['out'] = {}
    response['message'] = ""
    response['count'] = 0
    if request.method == 'GET':
        id = request.args.get('id', default = '', type = str)
        if not id in thread_pool.keys():
            response['out'] = {}
            response['debug'] = str(request)
            response['message'] = f"id {id} not running"
            app.logger.error(f"{id} not running")
            return (json.dumps(response))

        jobs = thread_pool[id].get()
        running = thread_pool[id].is_running()
        stage = thread_pool[id].get_stage()
        total_stages = thread_pool[id].get_total_stages()
        files = thread_pool[id].get_files()
        out = {'name': 'flask01be', 'id':  id, 'running': running, 'stage': stage, 'total_stages': total_stages, 'files': files}
        response['error'] = False
        response['out'] = json.dumps(out)
        response['debug'] = ""
    else:
        response['out'] = {}
        response['debug'] = str(request)
    return(json.dumps(response))
    
@app.route("/cut_end",methods=['POST'])
def cut_end():
    if request.method == 'POST':
        id = request.args.get('id', default = '*', type = str)
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
    
@app.route("/cut_recording",methods=['POST'])
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
        video_path = get_setting('videos',app.logger)
        dryrun = request.args.get('dryrun', default=False, type=bool)

        # get video filename and title
        query = f"select recorded.basename,recorded.title from recorded where recorded.recordedid = {data['videoid']}"
        c_myth.execute(query)
        data = c_myth.fetchall()        
        basename=data[0]['basename']
        title = data[0]['title']
        
        video_inp_path = get_media_path(basename,logger=app.logger)
        if video_inp_path is None:
            response['out'] = {}
            response['debug'] = str(basename)
            response['message'] = f"{str(basename)} Video not found"
            app.logger.error(response['message'])
            return(json.dumps(response))
 
        # Get videos paths
        out_basename = clean_title(title,filename=True,logger=app.logger)
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
        thread_pool[id] = cut_thread
        
        out = {'name': 'flask01be', 'title': title, 'data': basename, 'video_inp_path':  video_inp_path, 'id': id, 'video_out': video_out }
        response['error'] = False
        response['out'] = json.dumps(out)
        response['debug'] = str(video_inp_path + basename)
    else:
        response['out'] = {}
        response['debug'] = request
    return(json.dumps(response))

@app.route("/get_cleaned_title",methods=['GET'])
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
                app.logger.info(f"get_cleaned_title: {data}")
                if len(data) == 0:
                    response['message'] = f"basename {basename} not found"
                    response['debug'] = query
                else:
                    title = data[0]['title']
            else:
                title = raw_title        
            if title is not None:
                out['filename'] = clean_title(title,filename=True,logger=app.logger)
                out['title'] = clean_title(title,filename=False,logger=app.logger)
                response['error'] = False
        response['out'] = out
    return(json.dumps(response))

@app.route("/get_video_path",methods=['GET'])
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
            path = get_media_path(basename,group,logger=app.logger)
            if path is not None:
                out['path'] = path
                response['error'] = False
        response['out'] = out
    return(json.dumps(response))
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=18800)

