#!/usr/bin/python3
import sys, getopt
import mysql.connector
from constants import constants
import time
import os
import json


#/usr/local/bin/mythuser4 %DIR% %FILE% %JOBID%
ERROR_ALREADY_RUNNING=254
ERROR_BAD_PARAMS=253
ERROR_NO_CUT_STATUS=252
cutter_status = dict()
cutter_status_file = '/tmp/cutter.json'
cutter_status_recording_file = None

def cutter_store_status(status,file):
    with open(file, 'w') as fp:
        json.dump(status, fp)
        
def cutter_metadata_reset_status():
    return {
        "pid": os.getpid(),
        "start": str(int(time.time())),
        "finish": "0",
        "new_actor": 0,
        "status": "unknown",
        }
        
def execute_function(func, *args, **kwargs):
    return func(*args, **kwargs)

def execute_query(cursor,query):
   print(f"query: {query}")
   cursor.execute(query)
   data = cursor.fetchall()
   print("-" * 20 + f"\n{query}:\nLen={len(data)}\n{repr(data)}\n")
   return data

def main(argv):
   global cutter_status
   global cutter_status_file
   global cutter_status_recording_file
   config_file = '/var/www/cutter_config.json'
   settings = dict()
   exit_val = 0

   pid = os.getpid()
   opts, args = getopt.getopt(argv,"hi:t:dvl:c:",["ifile=","tempfolder=","dryrun","verbose","cpulimit=","config="])
   for opt, arg in opts:
      if opt == '-h':
         print ('cutter_metadata.py -i <inputfile> -t <tempfolder> ')
         print (f' Current config file {config_file} ')
         sys.exit()
      elif opt in ("-i", "--ifile"):
         inputfile = arg
      elif opt in ("-c", "--config"):
         config_file = arg

   try:
      with open(config_file, 'r') as file:
         settings = json.load(file)
   except json.JSONDecodeError as e:
      print(f"Errore nel parsing del file JSON: {e}")
      return(ERROR_BAD_PARAMS)

            
   for opt, arg in opts:
      if opt in ("-t", "--tempfolder"):
         settings['tempfolder'] = arg
      elif opt in ("-v", "--verbose"):
         settings['verbose'] = True
      elif opt in ("-d", "--dryrun"):
         settings['dryrun'] = True
      elif opt in ("-l", "--cpulimit"):
         settings['cpulimit'] = arg

   if settings['verbose']:
       print ('Temp folder is ', settings['tempfolder'])
       print (f'settings is: {repr(settings)}')

   cutter_status_recording_file =  os.path.join(settings['tempfolder'], 'cutter.json')
   try:
        with open(cutter_status_recording_file, 'r') as file:
            cutter_status = json.load(file)
   except Exception as e:
        print(f"Cutter status file {cutter_status_recording_file} error {e}")
        return(ERROR_NO_CUT_STATUS)

   video_filename = os.path.basename(cutter_status['out_file'])
   cutter_status['cutter_metadata']= cutter_metadata_reset_status()
   cutter_store_status(cutter_status,cutter_status_file)
   
   cnx = mysql.connector.connect(user='root', password=constants['mysql_password'],host='127.0.0.1',database='mythconverg',auth_plugin='mysql_native_password')
   cursor = cnx.cursor(dictionary=True)

   cutter_status['cutter_metadata']['status'] = 'running'
   cutter_store_status(cutter_status, cutter_status_file)

   #Getting key for input
   query = f"select chanid from recorded where basename='{inputfile}'"
   data = execute_query(cursor, query)
   chanid=data[0]['chanid']

   query = f"select progstart,originalairdate,description from recorded where basename='{inputfile}'"
   data = execute_query(cursor, query)
   progstart = str(data[0]['progstart'])
   originalairdate = data[0]['originalairdate']
   description = data[0]['description']

   query = f"select intid from videometadata where filename='{video_filename}'"
   data = execute_query(cursor, query)
   intid = str(data[0]['intid'])

   cutter_status['cutter_metadata']['keys'] = {'recorded.chanid': chanid, 'recorded.progstart': progstart, 'videometadata.intid': intid }
   cutter_store_status(cutter_status, cutter_status_file)

   #SELECT videometadatacast.idcast, videocast.* FROM  videometadatacast join videocast on idcast=videocast.intid WHERE idvideo=2869
   # query = f'SELECT  recordedcredits.role,recordedcredits.person,people.*,recorded.* FROM recordedcredits join people on recordedcredits.person=people.person join recorded on recorded.progstart=recordedcredits.starttime where recorded.chanid="{chanid}" and recordedcredits.starttime="{progstart}"'

   query = f'SELECT  recordedcredits.role,recordedcredits.person,people.* FROM recordedcredits join people on recordedcredits.person=people.person join recorded on recorded.progstart=recordedcredits.starttime where recorded.chanid="{chanid}" and recordedcredits.starttime="{progstart}"'
   credits = execute_query(cursor, query)
   video_director = 'Unknown'
   video_cast = []
   for r in credits:
      if 'director' in r['role']:
         video_director = r['name'].decode('utf-8')
      if 'actor' in r['role']:
         video_cast.append(r['name'].decode('utf-8'))


   if originalairdate is None:
      cutter_status['cutter_metadata']['year'] = 1895
   else:
      cutter_status['cutter_metadata']['year'] = originalairdate.year
   cutter_status['cutter_metadata']['director'] = video_director
   cutter_status['cutter_metadata']['cast'] = video_cast
   cutter_status['cutter_metadata']['description'] = description
   cutter_store_status(cutter_status, cutter_status_file)
   print(f'cutter_status={cutter_status}')

   d = description.replace("'", "\\'")
   query = (f"UPDATE videometadata SET director='{video_director}',"
            f"year='{cutter_status['cutter_metadata']['year']}',"
            f"plot='{d}' WHERE intid={intid};")
   print(f"Execute: '{query}'")
   cursor.execute(query)
   cnx.commit()

   #Add actor if not already present
   new_actor = 0
   for actor in video_cast:
      query = f"select intid from videocast where cast='{actor}'"
      data = execute_query(cursor, query)
      if len(data) == 0:
         query = f"insert into videocast (`cast`) VALUES ('{actor}')"
         print(f"Execute: '{query}'")
         cursor.execute(query)
         cnx.commit()
         new_actor += 1
      query = f"select intid from videocast where cast='{actor}'"
      data = execute_query(cursor, query)
      idcast = data[0]['intid']
      query = f"insert ignore into videometadatacast (`idvideo`,`idcast`) VALUES ('{intid}','{idcast}')"
      print(f"Execute: '{query}'")
      cursor.execute(query)
      cnx.commit()

   cutter_status['cutter_metadata']['status'] = "completed"
   cutter_status['cutter_metadata']['new_actor'] = new_actor
   cutter_status['cutter_metadata']['finish'] = str(int(time.time()))
   cutter_store_status(cutter_status, cutter_status_file)
   print(f'cutter_status={cutter_status}')


   cursor.close()
   cnx.close()
   return(exit_val)
   
if __name__ == "__main__":
   exit_val = main(sys.argv[1:])
   sys.exit(exit_val)
