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
from utils.utilities import clean_title, get_setting, get_media_path
from constants import constants
import ffmpeg
from ffprobe import FFProbe
import logging

from routes.cut_end import cut_end_bp
from routes.cut_recording import cut_recording_bp
from routes.cut_status import cut_status_bp
from routes.get_cleaned_title import get_cleaned_title_bp
from routes.get_video_path import get_video_path_bp
from routes.info import info_bp
from routes.get_disks_info import get_disks_info_bp
from routes.get_partitions_info import get_partitions_info_bp

#journalctl --no-pager -fxeu flask01be.service

app = Flask(__name__)
CORS(app)

app.config['VERSION'] = '2.0'
app.config['THREAD_POOL'] = {}


app.register_blueprint(cut_end_bp, url_prefix='/cut_end')
app.register_blueprint(cut_recording_bp, url_prefix='/cut_recording')
app.register_blueprint(cut_status_bp, url_prefix='/cut_status')
app.register_blueprint(get_cleaned_title_bp, url_prefix='/get_cleaned_title')
app.register_blueprint(get_video_path_bp, url_prefix='/get_video_path')
app.register_blueprint(info_bp, url_prefix='/info')
app.register_blueprint(get_disks_info_bp, url_prefix='/get_disks_info')
app.register_blueprint(get_partitions_info_bp, url_prefix='/get_partitions_info')



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
        
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=18800)

