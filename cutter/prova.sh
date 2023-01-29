#!/bin/bash

#TS_INP='/mnt/3tera/recordings/1004_20190909072400.ts'
TS_INP='/mnt/3tera/recordings/1006_20190909164300.ts'
TS_TMP_01='/home/user/ts_tmp/seg_01.ts'
TS_TMP_02='/home/user/ts_tmp/seg_02.ts'
TS_OUT='/mnt/3tera/videos/prova_come_losslesscut.ts'
COMM_OPTS="-avoid_negative_ts make_zero -map 0:0 -c:0 copy -map 0:1 -c:1 copy -map 0:2 -c:2 copy -map 0:3 -c:3 copy -map_metadata 0 -movflags +faststart -default_mode infer_no_subs -ignore_unknown -f mpegts -y"

#ffmpeg -hide_banner -ss '2604.60000' -i '/home/user/1006_20190909164300.ts' -t '242.44000' -avoid_negative_ts make_zero -map '0:0' '-c:0' copy -map '0:1' '-c:1' copy -map '0:2' '-c:2' copy -map '0:3' '-c:3' copy -map_metadata 0 -movflags '+faststart' -default_mode infer_no_subs -ignore_unknown -f mpegts -y '/mnt/3tera/temp/1006_20190909164300-00.43.24.600-00.47.27.040-seg10.ts'

mkdir -p /home/user/ts_tmp
rm -f $TS_OUT
rm -f /home/user/ts_tmp/*
CMD_1="ffmpeg -hide_banner -ss 292.990 -i $TS_INP -to 420.000 $COMM_OPTS $TS_TMP_01"
CMD_2="ffmpeg -hide_banner -ss 1531.320 -i $TS_INP -to 1641.400 $COMM_OPTS $TS_TMP_02"

CMD_3="echo -e \"file file:$TS_TMP_01\nfile file:$TS_TMP_02\" | ffmpeg -hide_banner -f concat -safe 0 -protocol_whitelist file,pipe -i - -map 0:0 -c:0 copy -map 0:1 -c:1 copy -map 0:2 -c:2 copy -map 0:3 -c:3 copy -movflags +faststart -default_mode infer_no_subs -ignore_unknown -f mpegts -y $TS_OUT"


$CMD_1
$CMD_2
$CMD_3
echo "-------------------------------------------------------------"
echo $CMD_1
echo $CMD_2
echo $CMD_3
echo "-------------------------------------------------------------"
ls -l $TS_OUT