#!/usr/bin/python3
import sys, getopt
import mysql.connector
from datetime import datetime
import ffmpeg
from ffprobe import FFProbe
import subprocess
import time
import os
import json
import psutil
import re


cutter_status = dict()
cutter_status_file = '/tmp/cutter.json'

def convert_seconds(total_seconds):
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return int(hours), int(minutes), int(seconds)
        
def main(argv):
   global  cutter_status
   global  cutter_status_file
   done_seconds = 0
   pid = os.getpid()
   
   try:
        with open(cutter_status_file, 'r') as file:
            cutter_status = json.load(file)
   except:
        print(f"no status file")
        return(1)
   filename = cutter_status['out_file'].split('/')[-1]
   if not psutil.pid_exists(cutter_status['pid']) and cutter_status['status'] != 'completed':
        print(f"File: {filename}\nCutter pid {cutter_status['pid']} not running status:{cutter_status['status']}")
        return(1)
   
   step = cutter_status['step']
   if cutter_status['jobtype']=='merge':
        stats = cutter_status['step_stats'][str(step)]
        elapsed = int(time.time() - int(stats['begin']))
        cmd = f"/usr/bin/sed 's/\\r/\\r\\n/g' {cutter_status['temp_folder']}/err_{cutter_status['step']}.txt | grep time= | tail -1"
        current_line = subprocess.run([cmd],stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,shell=True)
        match = re.search(r"time=(\d{2}):(\d{2}):(\d{2}\.\d+)", current_line.stdout)
        if match:
            hours, minutes, seconds = map(float, match.groups())
            done_seconds = hours * 3600 + minutes * 60 + seconds
        else:
            done_seconds = 0
            print(f"No time found in {current_line}")
            return(1)
 
 
   if done_seconds != 0:
        todo_seconds = cutter_status['input_duration'] - done_seconds
        speed = elapsed / done_seconds
        remain_estimated = todo_seconds * speed
        estimated_h, estimated_m, estimated_s = convert_seconds(remain_estimated)
        eta_s= int(time.time()) + remain_estimated
        eta = datetime.fromtimestamp(eta_s).strftime('%Y-%m-%d %H:%M:%S')
   else:
        speed = 0
        todo_seconds = 0
        estimated_h = estimated_m = estimated_s = 0
        elapsed = 0
        eta = "N/A"
   msg  = f"FILE: {filename} {cutter_status['status']} ({cutter_status['step']}/{cutter_status['total_steps']})\n"
   msg += f"tot:{int(cutter_status['input_duration'])} done:{int(done_seconds)} todo:{int(todo_seconds)}\n"
   msg += f"elapsed:{elapsed} speed:{round(speed,3)} remain_estimated:{estimated_h}:{estimated_m}:{estimated_s} ETA:{eta} "
   
   print(msg)
   return(0) 
 
   
if __name__ == "__main__":
   exit_val = main(sys.argv[1:])
   sys.exit(exit_val)