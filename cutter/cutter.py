#!/usr/bin/python3
import sys, getopt
import mysql.connector
import ffmpeg
from ffprobe import FFProbe
from constants import constants
import subprocess
import time
import os
import json
import psutil
import glob

#xxxxxxxxxxxxxxxxxpython3 -m venv /home/user/venv/sandbox
#source venv/sandbox/bin/activate
#python3 python_llcut_like.py
#/mnt/3tera/recordings/1006_20190909164300.ts


#source venv/sandbox/bin/activate
#cd /home/user/github/cutter
#python3 cutter.py -i 1022_20190926185700.ts -o /mnt/3tera/videos/di_nuovo_in_gioco.mpg

#/usr/local/bin/mythuser2 %DIR% %FILE% %JOBID%
ERROR_ALREADY_RUNNING=254
ERROR_BAD_PARAMS=253
cutter_status = dict()
cutter_status_file = '/tmp/cutter.json'

class myStream(object):
    def __init__(self,l):
        self.l = l
        self.video = "Video:" in l
        self.audio = "Audio:" in l
        self.subtitle = "Subtitle:" in l
        self.index = int(l.split('#')[1].split('[')[0].split(':')[1])
        self.id = l.split(']')[0].split('x')[1]
        if self.video:
            self.framerate = int(l.split('fps')[0].split(',')[-1:][0].strip())
            self.height = int(l.split('[SAR')[0].split(',')[-1:][0].strip().split('x')[1])
            self.width = int(l.split('[SAR')[0].split(',')[-1:][0].strip().split('x')[0])
            self.lang = l.split('(')[1].split(')')[0]

        if self.audio:
            self.lang = l.split('(')[1].split(')')[0]
            
        if self.subtitle:
            self.lang = l.split('(')[1].split(')')[0].split(',')[0]
                 
    
    def is_video(self):
        return self.video

    def is_audio(self):
        return self.audio
        
    def is_subtitle(self):
        return self.subtitle
        
    def language(self):
        return self.lang

class myFFprobe(object):
    def __init__(self,file):    
        result = subprocess.run(["/usr/bin/ffprobe", f"{file}"],capture_output=True, text=True)
        self.streams = []
        print(result.stderr)
        for l in result.stderr.splitlines():
            if l.strip().startswith("Stream"):
                self.streams.append(myStream(l))

def cutter_store_status(status,file):
    with open(file, 'w') as fp:
        json.dump(status, fp)
        
def cutter_reset_status():
    return {
        "inp_file": "",
        "inp_folder": "",
        "temp_folder": "",
        "input_duration": 0,
        "input_bytes": 0,
        "output_bytes": 0,
        "pid": os.getpid(),
        "start": str(int(time.time())),
        "finish": "0",
        "status": "unknown",
        "step": 0,
        "total_steps": 0,
        'step_stats':  dict(),
        'conf': dict(),
        'title': '',
    }

def execute_function(func, *args, **kwargs):
    return func(*args, **kwargs)
    
def get_video_duration(file_path):
    """
    Restituisce la durata di un video in secondi.
    """
    command = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_entries", "format=duration", file_path
    ]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        duration = json.loads(result.stdout)["format"]["duration"]
        print(f"get_video_duration {file_path} {duration}")
        return float(duration)  # Restituisce la durata in secondi
    except Exception as e:
        print(f"Errore durante l'analisi del file: {e}")
        return float(0)
        
def compute_input_duration():
        global cutter_status
        secs = 0
        files = glob.glob(f"{cutter_status['temp_folder']}/segment-*.ts")
        print(f"compute_input_duration files:{repr(cutter_status)})")
        for f in files:
           seg_sec = get_video_duration(f"{f}")
           if seg_sec == 0:
                return 254
           secs += seg_sec 
        cutter_status['input_duration'] = int(secs)
        print(f"compute_input_duration out files:{repr(cutter_status)})")
        return 0

def get_file_birth_date(file_path):
    """
    Restituisce la data di creazione di un file in epoch format integer.
    in caso di errore 0
    """
    command = [
        "/usr/bin/stat", "--printf=%W", file_path
    ]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        birth_date = result.stdout
        print(f"get_file_birth_date {file_path} {birth_date}")
        return int(birth_date)
    except Exception as e:
        print(f"Errore durante l'analisi del file: {e}")
        return int(0)

def main(argv):
   global cutter_status
   global cutter_status_file
   inputfile = 'test.ts'
   inputfolder = '/tmp'
   outputfile = '/tmp/newcut.ts'
   config_file = '/var/www/cutter_config.json'
   settings = dict()
   framerate = 0.0
   cut_duration = 0

   pid = os.getpid()
   opts, args = getopt.getopt(argv,"hi:o:f:t:dvsl:p:c:",["ifile=","ofile=","ifolder=","tempfolder=","dryrun","verbose","subtitle","cpulimit=","preset=","config="])
   for opt, arg in opts:
      if opt == '-h':
         print ('cutter.py -i <inputfile> -f <inputfolder> -o <outputfile> -t <tempfolder> ')
         print ('python3 cutter.py -i 10004_20230102201000.ts -o /mnt/3tera/videos/non_ci_resta_che_piangere.mpg')
         print (f' Current config file {config_file} ')
         sys.exit()
      elif opt in ("-i", "--ifile"):
         inputfile = arg
      elif opt in ("-f", "--ifolder"):
         inputfolder = arg
      elif opt in ("-o", "--ofile"):
         outputfile = arg
      elif opt in ("-c", "--config"):
         config_file = arg


   try:
      with open(config_file, 'r') as file:
         settings = json.load(file)
   except json.JSONDecodeError as e:
      print(f"Errore nel parsing del file JSON: {e}")
      return ERROR_BAD_PARAMS

            
   for opt, arg in opts:
      if opt in ("-t", "--tempfolder"):
         settings['tempfolder'] = arg
      elif opt in ("-v", "--verbose"):
         settings['verbose'] = True
      elif opt in ("-s", "--subtitle"):
         settings['subtitle'] = True
      elif opt in ("-d", "--dryrun"):
         settings['dryrun'] = True
      elif opt in ("-l", "--cpulimit"):
         settings['cpulimit'] = arg
      elif opt in ("-p", "--preset"):
         settings['preset'] = arg

   if settings['verbose']:
       print ('Input file is ', inputfile)
       print ('Input folder is ', inputfolder)
       print ('Temp folder is ', settings['tempfolder'])
       print ('Output file is ', outputfile)
       print (f'settings is: {repr(settings)}')
   
         
   try:
        with open(cutter_status_file, 'r') as file:
            cutter_status = json.load(file)
   except:
        cutter_status = cutter_reset_status()

   if cutter_status['pid'] != pid:
        if psutil.pid_exists(cutter_status['pid']):
            print(f"Cutter already running desc:{cutter_status})")
            return ERROR_ALREADY_RUNNING

   cutter_status = cutter_reset_status()
   cutter_store_status(cutter_status,cutter_status_file)   
   
   local_file_path= inputfolder + '/' + inputfile
   try:
       metadata=FFProbe(local_file_path)
   except:
       print("FFProbe broken - try to use myFFprobe")
       metadata=myFFprobe(local_file_path)

   cutter_status['recording_date']= get_file_birth_date(local_file_path)
   cutter_status['pid'] = os.getpid()
   cutter_status['status']='starting'
   cutter_status['title']=''
   cutter_status['out_file']=outputfile
   cutter_status['inp_file']=inputfile
   cutter_status['inp_folder']=inputfolder
   cutter_status['temp_folder']=settings['tempfolder']
   cutter_status['input_duration']=0
   cutter_status['input_bytes']=0
   cutter_status['compress_rate']=0
   cutter_status['output_bytes']=0
   cutter_status['jobtype']="none"
   cutter_status['step_stats']= dict()
   cutter_status['conf']= settings
   cutter_store_status(cutter_status,cutter_status_file)   
 
   stream_map_cut = ""   
   stream_map_merge = ""   
   out_index = 0
   for s in metadata.streams:
        if s.is_video():
            framerate= float(s.framerate)
            stream_map_cut = stream_map_cut + f"-map 0:{s.index} -c:{out_index} copy "
            stream_map_merge = stream_map_merge + f"-map 0:{out_index} -c:{out_index} libx265 -preset {settings['preset']} -crf 28 "
            out_index += 1
            if settings['verbose']:
                print(f"{s.index}: Video id:{s.id} fps:{s.framerate} size:{s.height}x{s.width}")            
        elif s.is_audio():
            stream_map_cut = stream_map_cut + f"-map 0:{s.index} -c:{out_index} copy "
            stream_map_merge = stream_map_merge + f"-map 0:{out_index} -c:{out_index} aac -b:{out_index} 192k "
            out_index += 1
            if settings['verbose']:
                print(f"{s.index}: Audio id:{s.id} lang:{s.language()}")
        elif s.is_subtitle() and not settings['skip_subtitle']:
            stream_map_cut = stream_map_cut + f"-map 0:{s.index} -c:{out_index} copy "
            stream_map_merge = stream_map_merge + f"-map 0:{out_index} -c:{out_index} copy "
            out_index += 1
            if settings['verbose']:
                print(f"{s.index}: Subtitle id:{s.id} lang:{s.language()}")
        else:
            if settings['verbose']:
                print(f"{s.index}: id:{s.id}")
        
   cnx = mysql.connector.connect(user='root', password=constants['mysql_password'],host='127.0.0.1',database='mythconverg',auth_plugin='mysql_native_password')
   cursor = cnx.cursor(dictionary=True)
   query = f"select chanid from recorded where basename='{inputfile}'"
   cursor.execute(query)
   data = cursor.fetchall()
   chanid=data[0]['chanid']

   query = f"select starttime from recorded where basename='{inputfile}'"
   cursor.execute(query)
   data = cursor.fetchall()
   starttime = str(data[0]['starttime'])
   
   query = f"select title from recorded where basename='{inputfile}'"
   cursor.execute(query)
   data = cursor.fetchall()
   title = str(data[0]['title'])
   cutter_status['title']=title
   cutter_store_status(cutter_status,cutter_status_file)   

   query = f"select mark,type from recordedmarkup where chanid={chanid} and starttime='{starttime}' and type in (0,1) order by mark;"
   cursor.execute(query)
   data = cursor.fetchall()
   
   cursor.close()
   cnx.close()
     
   start_mark = float(0)
   segment = 0
   merge_segments=[]
   jobs = []
   for (m) in data:
        if m['type'] == 0:
            start_mark = float(m['mark'])/framerate
            continue
        if m['type'] == 1:
            end_mark = float(m['mark'])/framerate
            cut_duration = round((end_mark - start_mark),3)
        osegment=f"{settings['tempfolder']}/segment-{segment}.ts"
        cmd=f"cpulimit -f -l {settings['cpulimit']} -- ffmpeg -threads 2 -nostdin -stats_period 5 -hide_banner -fflags +genpts -hide_banner -ss {start_mark} -i {local_file_path} -t {cut_duration} {stream_map_cut}"
        cmd+=' -map_metadata 0 -movflags +faststart -default_mode infer_no_subs -ignore_unknown -f mpegts -y '
        cmd+=osegment
       
        merge_segments.append(f"file file:{osegment}")
        segment+=1

        if settings['verbose']:
            print(cmd)
        jobs.append(("cut",cmd))

   segments_name="\\n".join(merge_segments)
   
   jobs.append(("function",compute_input_duration)) 
   
   cmd=  f'echo "{segments_name}" | '
   cmd+= f'cpulimit -f -l {settings['cpulimit']} -- ffmpeg -threads 2 -nostdin -stats_period 5 -hide_banner -f concat -safe 0 -fflags +genpts -protocol_whitelist fd,file,pipe '
   cmd+= f'-i - {stream_map_merge}   {outputfile}'
   
   if settings['verbose']:
    print(cmd)
   
   jobs.append(("merge",cmd))


   if settings['verbose']:
    print(cmd)
    
   # serve sudo farlo dal bash con il serverino flask
   #jobs.append(f"chown mythtv:mythtv {outputfile}")
   
   step=0
   exit_value = 0
   total_jobs = len(jobs)
   cutter_status['status']='running'
   cutter_store_status(cutter_status,cutter_status_file)   
   if not settings['dryrun']:
       with open(f'{settings["tempfolder"]}/out_{step}.txt','w+') as fout:
           with open(f'{settings["tempfolder"]}/err_{step}.txt','w+') as ferr:
               subprocess.run([f"rm -Rf {settings['tempfolder']}/*"],shell=True,stdout=fout,stderr=ferr)
       cutter_status['total_steps']=total_jobs


       for jobtype, job in jobs:
           step+=1
           cutter_status['jobtype']=jobtype
           cutter_status['step']=step
           stats = {'begin': str(int(time.time())), 'type': jobtype}
           cutter_status['step_stats'][step]=stats
           cutter_store_status(cutter_status,cutter_status_file)
           segment = 0
           with open(f'{settings["tempfolder"]}/out_{step}.txt','w+') as fout:
               with open(f'{settings["tempfolder"]}/err_{step}.txt','w+') as ferr:
                   if jobtype=='function':
                        exit_value = execute_function(job)
                        cutter_store_status(cutter_status,cutter_status_file)
                   else:
                        completed_process = subprocess.run([job],shell=True,stdout=fout,stderr=ferr,universal_newlines=True)
                        exit_value = completed_process.returncode
                   if jobtype=='cut':     
                        cutter_status['input_bytes'] += os.path.getsize(f"{settings['tempfolder']}/segment-{segment}.ts")
                        segment += 1
                   if jobtype=='merge':     
                        cutter_status['output_bytes'] = os.path.getsize(f"{outputfile}")
                        cutter_status['compress_rate'] = 100 * ( 1 - cutter_status['output_bytes'] / cutter_status['input_bytes'])
                   stats['end'] = str(int(time.time()))
                   cutter_status['step_stats'][step]=stats
                   cutter_store_status(cutter_status,cutter_status_file)
                   print(f"STEP {step}/{total_jobs} exit value - {exit_value}")
                   if exit_value != 0:
                         print(f"ERROR {exit_value} - {job}")
                         break
       cutter_status['step']=step
       cutter_store_status(cutter_status,cutter_status_file)

   else:
       for jobtype, job in jobs:
            print(f"{jobtype}:{job}")
            time.sleep(1)
        
   if exit_value != 0:
        cutter_status['status']='error'
   else:
        cutter_status['status']='completed'

   cutter_status['finish']=str(int(time.time()))
   cutter_store_status(cutter_status,cutter_status_file)   
   return(exit_value)
   
if __name__ == "__main__":
   exit_val = main(sys.argv[1:])
   sys.exit(exit_val)
