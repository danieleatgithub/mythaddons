#!/usr/bin/python3
import sys, getopt
import mysql.connector
import datetime
import ffmpeg
from ffprobe import FFProbe
import subprocess

#python3 -m venv /home/user/venv/sandbox
#source venv/sandbox/bin/activate
#python3 python_llcut_like.py
#/mnt/3tera/recordings/1006_20190909164300.ts


#10004_20230102201000.ts  non ci resta che piangere
#10077_20221218195500.ts  il nome della rosa
#10509_20221029191500.ts  lady gucci
#10034_20221023144000.ts  Cetto ce senzadubbiamente
#1005_20211116202700.ts   joker
def main(argv):
   inputfile = '1006_20190909164300.ts'
   inputfolder = '/mnt/3tera/recordings'
   outputfile = '/mnt/3tera/videos/newcut.ts'
   tempfolder = '/home/user/ts_tmp'
   verbose = False
   dryrun  = False
   opts, args = getopt.getopt(argv,"hi:o:f:t:dv",["ifile=","ofile=","ifolder=","tempfolder=","dryrun","verbose"])
   for opt, arg in opts:
      if opt == '-h':
         print ('cutter.py -i <inputfile> -f <inputfolder> -o <outputfile> -t <tempfolder> ')
         print ('python3 cutter.py -i 10004_20230102201000.ts -o /mnt/3tera/videos/non_ci_resta_che_piangere.mpg')
         print ('python3 cutter.py -i 10077_20221218195500.ts -o /mnt/3tera/videos/il_nome_della_rosa.mpg')
         print ('python3 cutter.py -i 10509_20221029191500.ts -o /mnt/3tera/videos/lady_gucci_interview.mpg')
         print ('python3 cutter.py -i 10034_20221023144000.ts -o /mnt/3tera/videos/cetto_ce_senzadubbiamente.mpg')
         print ('python3 cutter.py -i 1005_20211116202700.ts -o /mnt/3tera/videos/joker.mpg')
         sys.exit()
      elif opt in ("-i", "--ifile"):
         inputfile = arg
      elif opt in ("-f", "--ifolder"):
         inputfolder = arg
      elif opt in ("-t", "--tempfolder"):
         tempfolder = arg
      elif opt in ("-o", "--ofile"):
         outputfile = arg
      elif opt in ("-v", "--verbose"):
         verbose = True
      elif opt in ("-d", "--dryrun"):
         dryrun = True
   if verbose:
       print ('Input file is ', inputfile)
       print ('Input folder is ', inputfolder)
       print ('Temp folder is ', tempfolder)
       print ('Output file is ', outputfile)
   
   local_file_path= inputfolder + '/' + inputfile
   metadata=FFProbe(local_file_path)
  
   #s.DISPOSITION:attached_pic      s.bit_rate                      s.color_primaries               s.height                        s.nb_read_frames
   #s.DISPOSITION:clean_effects     s.bits_per_raw_sample           s.color_range                   s.id                            s.nb_read_packets
   #s.DISPOSITION:comment           s.chroma_location               s.color_space                   s.index                         s.pix_fmt
   #s.DISPOSITION:default           s.closed_captions               s.color_transfer                s.is_attachment()               s.pixel_format()
   #s.DISPOSITION:dub               s.codec()                       s.display_aspect_ratio          s.is_audio()                    s.profile
   #s.DISPOSITION:forced            s.codec_description()           s.duration                      s.is_avc                        s.r_frame_rate
   #s.DISPOSITION:hearing_impaired  s.codec_long_name               s.duration_seconds()            s.is_subtitle()                 s.refs
   #s.DISPOSITION:karaoke           s.codec_name                    s.duration_ts                   s.is_video()                    s.sample_aspect_ratio
   #s.DISPOSITION:lyrics            s.codec_tag                     s.field_order                   s.language()                    s.start_pts
   #s.DISPOSITION:original          s.codec_tag_string              s.frame_size()                  s.level                         s.start_time
   #s.DISPOSITION:timed_thumbnails  s.codec_type                    s.framerate                     s.max_bit_rate                  s.time_base
   #s.DISPOSITION:visual_impaired   s.coded_height                  s.frames()                      s.nal_length_size               s.width
   #s.avg_frame_rate                s.coded_width                   s.has_b_frames                  s.nb_frames
   
   stream_map = ""   
   for s in metadata.streams:
        if s.is_video():
            framerate= float(s.framerate)
            stream_map = stream_map + f"-map 0:{s.index} -c:{s.index} copy "
            if verbose:
                print(f"{s.index}: Video id:{s.id} fps:{s.framerate} size:{s.height}x{s.width}")            
        elif s.is_audio():
            stream_map = stream_map + f"-map 0:{s.index} -c:{s.index} copy "
            if verbose:
                print(f"{s.index}: Audio id:{s.id} lang:{s.language()}")
        elif s.is_subtitle():
            stream_map = stream_map + f"-map 0:{s.index} -c:{s.index} copy "
            if verbose:
                print(f"{s.index}: Subtitle id:{s.id} lang:{s.language()}")
        else:
            if verbose:
                print(f"{s.index}: id:{s.id}")
        
   cnx = mysql.connector.connect(user='root', password='a',host='127.0.0.1',database='mythconverg',auth_plugin='mysql_native_password')
   cursor = cnx.cursor(dictionary=True)
   query = f"select chanid from recorded where basename='{inputfile}'"
   cursor.execute(query)
   data = cursor.fetchall()
   chanid=data[0]['chanid']

   query = f"select starttime from recorded where basename='{inputfile}'"
   cursor.execute(query)
   data = cursor.fetchall()
   starttime = str(data[0]['starttime'])

   query = f"select mark,type from recordedmarkup where chanid={chanid} and starttime='{starttime}' and type in (0,1) order by mark;"
   cursor.execute(query)
   data = cursor.fetchall()
   
#COMM_OPTS="-avoid_negative_ts make_zero -map 0:0 -c:0 copy -map 0:1 -c:1 copy -map 0:2 -c:2 copy -map 0:3 -c:3 copy -map_metadata 0 -movflags +faststart -default_mode infer_no_subs -ignore_unknown -f mpegts -y"
#CMD_1="ffmpeg -hide_banner -ss 292.990 -i $TS_INP -to 420.000 $COMM_OPTS $TS_TMP_01"
   
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
        osegment=f"{tempfolder}/segment-{segment}.ts"
        cmd=f"ffmpeg -hide_banner -ss {start_mark} -i {local_file_path} -t {cut_duration} {stream_map}"
        cmd+=" -map_metadata 0 -movflags +faststart -default_mode infer_no_subs -ignore_unknown -f mpegts -y "
        cmd+=osegment
        merge_segments.append(f"file file:{osegment}")
        segment+=1
        if verbose:
            print(cmd)
        jobs.append(cmd)

#CMD_3="echo -e \"file file:$TS_TMP_01\nfile file:$TS_TMP_02\" | ffmpeg -hide_banner -f concat -safe 0 -protocol_whitelist file,pipe -i - -map 0:0 -c:0 copy -map 0:1 -c:1 copy -map 0:2 -c:2 copy -map 0:3 -c:3 copy -movflags +faststart -default_mode infer_no_subs -ignore_unknown -f mpegts -y $TS_OUT"
   segments_name="\\n".join(merge_segments)
   
   # ok da shell da errore con subprocess
   cmd=f'echo "{segments_name}" | ffmpeg -hide_banner -f concat -safe 0 -protocol_whitelist file,pipe -i - {stream_map} -movflags +faststart -default_mode infer_no_subs -ignore_unknown -f mpegts -y {outputfile}'
   if verbose:
    print(cmd)
   
   jobs.append(cmd)
   
   # serve sudo
   jobs.append(f"chown mythtv.mythtv {outputfile}")
   print("\n\n".join(jobs))
   step=0
   if not dryrun:
       with open(f'{tempfolder}/out_{step}.txt','w+') as fout:
           with open(f'{tempfolder}/err_{step}.txt','w+') as ferr:
               subprocess.run([f"rm -Rf {tempfolder}/*"],shell=True,stdout=fout,stderr=ferr)
       for job in jobs:
           with open(f'{tempfolder}/out_{step}.txt','w+') as fout:
               with open(f'{tempfolder}/err_{step}.txt','w+') as ferr:
                   subprocess.run([job],shell=True,stdout=fout,stderr=ferr,universal_newlines=True)
                   step+=1
       
   
   # 1006 studio apert
   # cut1 inizio ---  4:54.120   294.120  rosso (tagliare)
   # cut2 4:54.120--  6.21.720   381.720  verde  (salvare ... bastone rosso 104 tattoo bari)   
   # cut3 6.21.720..  25.24.840 1524.840  rosso  /tagliare
   # cut4 25.24.840.. 30.57.960 1857.960  verde  (salvare ... nuoto fine pollice up piscina)
   # cut5 30.57.960.. fine      rosso  (tagliare)   
   # mark=7353 type=0 - 294.12
   # mark=9543 type=1 - 381.72
   # mark=38121 type=0 - 1524.84
   # mark=46449 type=1 - 1857.96
   # mark=81967 type=0 - 3278.68
   
        
   cursor.close()
   cnx.close()
   
if __name__ == "__main__":
   main(sys.argv[1:])