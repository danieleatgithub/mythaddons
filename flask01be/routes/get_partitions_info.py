import subprocess
import json
import time
from constants import constants
import logging
from flask import Blueprint, jsonify, request, current_app
import psutil



get_partitions_info_bp = Blueprint('get_partitions_info', __name__)

       

@get_partitions_info_bp.route("/",methods=['GET'])
def get_partitions_info():
    response = {}
    response['error'] = True
    response['debug'] = ""
    response['out'] = {}
    response['message'] = ""
    all_partitions = psutil.disk_partitions()   
    partitions = {
        '/mnt/2tera': {'label': 'Windows  ROOT + Linux fs' },
        '/mnt/3tera': {'label': 'Linux fs' },
        '/mnt/1tera': {'label': 'Linux fs' },
        '/mnt/2terb': {'label': 'Linux root' },
        '/var/lib/mysql': {'label': 'databases' },
        '/var/www': {'label': 'www root' },
        '/var/sddtmp': {'label': 'temp on SDD' },
    }
    response['count'] = len(partitions.keys())
    for p in all_partitions:
        if p.mountpoint in  partitions.keys():
            partitions[p.mountpoint]['device'] = p.device
            partitions[p.mountpoint]['fstype'] = p.fstype
            usage = psutil.disk_usage(p.mountpoint)
            partitions[p.mountpoint]['total'] = usage.total
            partitions[p.mountpoint]['used'] = usage.used
            partitions[p.mountpoint]['free'] = usage.free
            partitions[p.mountpoint]['percent'] = usage.percent
    if request.method == 'GET':
        data = request.form
        current_app.logger.info(f"get_partitions_info {{disk}} {repr(partitions)}")
        response['error'] = False  
        response['out'] = partitions
    return(json.dumps(response))
    


