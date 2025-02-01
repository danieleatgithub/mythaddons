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
#xxxxxxxxxxxxxxxxxpython3 -m venv /home/user/venv/sandbox
#source venv/sandbox/bin/activate
#python3 python_llcut_like.py
#/mnt/3tera/recordings/1006_20190909164300.ts


#source venv/sandbox/bin/activate
#cd /home/user/github/cutter

cutter_status = dict()
cutter_status_file = '/tmp/cutter.json'


def kill_process_and_children(pid):
    
    try:
        # Ottieni il processo principale
        parent = psutil.Process(pid)
        # Ottieni tutti i figli del processo (ricorsivamente)
        children = parent.children(recursive=True)
        # Termina tutti i figli
        print(f"Terminating child processes:",end="")
        for child in children:
            print(f"{child.pid},",end="")
            child.terminate()
        # Termina il processo principale
        print(f"Main : {parent.pid}")
        parent.terminate()

        # Attendi la terminazione di tutti i processi
        gone, still_alive = psutil.wait_procs(children, timeout=5)
        if still_alive:
            for p in still_alive:
                p.kill()  # Forza la terminazione
        parent.wait(5)  # Aspetta la terminazione del processo principale
        print(f"Process {pid} and its children have been terminated.")
    except psutil.NoSuchProcess:
        print(f"Process {pid} does not exist.")
        return(10)
    except Exception as e:
        print(f"An error occurred: {e}")
        return(11)
    return(0)

def cutter_store_status(status,file):
    with open(file, 'w') as fp:
        json.dump(status, fp)

        
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
 
   if not psutil.pid_exists(cutter_status['pid']) and cutter_status['status'] != 'completed':
        print(f"Cutter pid {cutter_status['pid']} not running status:{cutter_status['status']}")
        return(2)

   ret= kill_process_and_children(cutter_status['pid'])  
   cutter_status['status']='killed'
   cutter_status['finish']=str(int(time.time()))
   cutter_store_status(cutter_status,cutter_status_file)  
   return(ret)
   
if __name__ == "__main__":
   exit_val = main(sys.argv[1:])
   sys.exit(exit_val)