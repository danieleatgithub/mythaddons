import subprocess
import json
import time
from constants import constants
import logging
from flask import Blueprint, jsonify, request, current_app



get_disks_info_bp = Blueprint('get_disks_info', __name__)

def get_disk_temperature(device):
    try:
        result = subprocess.run(
            ['/usr/bin/sudo', '/usr/sbin/smartctl', '-Aj', device],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            current_app.logger.error(f"Error reading SMART data: {result.stderr}")
            return None

        dev_data = json.loads(result.stdout)
        #current_app.logger.debug(f"{repr(dev_data)}")
        return(dev_data['temperature']['current'])
    except Exception as e:
        current_app.logger.error(f"get_disk_temperature: {e}")
        return None

def parse_lsscsi(data):
    devices = {}
    interface2bay = {
        '': 'A',
        '[0:0:0:0]': 'F',
        '[1:0:0:0]': 'E',
        '[2:0:0:0]': 'D',
        '[3:0:0:0]': 'C',
        '[4:0:0:0]': 'B',
   }
    for line in data.strip().splitlines():
        parts = line.split()
        # Estraggo i campi principali
        bus = parts[0]
        type_ = parts[1]
        interface = parts[2]
        # Il nome del modello può avere spazi → tutto fino al penultimo campo
        model = " ".join(parts[3:-2])
        rev = parts[-2]
        dev = parts[-1]

        devices[dev] = {
            "bus": bus,
            "type": type_,
            "interface": interface,
            "model": model,
            "revision": rev,
            "bay": interface2bay[bus]
        }

    return(devices)


def get_disks_bay():
    try:
        result = subprocess.run(
            ['/usr/bin/sudo', '/usr/bin/lsscsi'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            current_app.logger.error(f"Error reading lsscsi data: {result.stderr}")
            return None
        current_app.logger.info(f"get_disks_bay: raw data: {result.stdout}");
        data = parse_lsscsi(result.stdout)
        current_app.logger.info(f"get_disks_bay: data: {data}");
        
        return(data)
                       
    except Exception as e:
        current_app.logger.error(f"get_disks_bay: {e}")
        return None

        
def get_disk_inventory(device):
    try:
        result = subprocess.run(
            ['/usr/bin/sudo', '/usr/sbin/smartctl', '-ij', device],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            current_app.logger.error(f"Error reading SMART data: {result.stderr}")
            return None

        dev_data = json.loads(result.stdout)
        if dev_data['smartctl']['exit_status'] != 0:
            current_app.logger.error(f"get_disk_inventory: exit {dev_data['smartctl']['exit_status']}")
            current_app.logger.info(f"get_disk_inventory exit error: {repr(dev_data)}")
            return None
        
        #current_app.logger.debug(f"{repr(dev_data)}")
        ret = dict()
        ret['model_name'] =     dev_data['model_name']
        ret['serial_number'] =  dev_data['serial_number']
        ret['bytes'] =          dev_data['user_capacity']['bytes']
        ret['smart_enabled'] =  dev_data['smart_support']['enabled']
        ret['sata_speed'] = dev_data['interface_speed']['current']['string']
        if 'rotation_rate' not in list(dev_data.keys()) or dev_data['rotation_rate'] != 0:
            ret['type'] = 'hdd'
        else:
            ret['type'] = 'ssd'
        return(ret)
                       
    except Exception as e:
        current_app.logger.error(f"get_disk_inventory: {e}")
        return None

@get_disks_info_bp.route("/",methods=['GET'])
def get_disks_info():
    disks = ['sda', 'sdb', 'sdc','sdd','sde']
    response = {}
    response['error'] = True
    response['debug'] = ""
    response['out'] = {}
    response['message'] = ""
    response['count'] = len(disks)
    out = {}
    if request.method == 'GET':
        data = request.form
        bays = get_disks_bay()
        for disk in disks:
            out[disk] = dict()
            out[disk]['temperature'] = get_disk_temperature(f"/dev/{disk}")
            out[disk]['inventory'] = get_disk_inventory(f"/dev/{disk}")
            out[disk]['bay'] = bays[f"/dev/{disk}"]['bay']
            current_app.logger.info(f"get_disk_info {disk} {repr(out[disk])}")
        response['error'] = False  
        response['out'] = out
    return(json.dumps(response))
    


