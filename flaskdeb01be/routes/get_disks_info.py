import subprocess
import json


from flask import Blueprint, jsonify, current_app
from error_codes import ErrorCode

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
        if 'rotation_rate' not in list(dev_data.keys()) or dev_data['rotation_rate'] != 0:
            ret['type'] = 'hdd'
        else:
            ret['type'] = 'sdd'
        return(ret)
                       
    except Exception as e:
        current_app.logger.error(f"get_disk_inventory: {e}")
        return None

@get_disks_info_bp.route("/",methods=['GET'])
def get_disks_info():
    disks = ['sda', 'sdb', 'sdc']

    response = {
        'error': False,
        'retcode': ErrorCode.OK,
        'message': "",
        'count': len(disks),
        'out': {}
    }
    try:
        for disk in disks:
            dev = f"/dev/{disk}"
            response['out'][disk] = {
                'temperature': get_disk_temperature(dev),
                'inventory': get_disk_inventory(dev)
            }
            current_app.logger.info(f"get_disk_info {disk}: {response['out'][disk]}")
    except Exception as e:
        current_app.logger.error(f"get_disks_info error: {e}")
        response['error'] = True
        response['retcode'] = ErrorCode.GENERIC_ERROR
        response['message'] = str(e)
        return jsonify(response), 500

    return jsonify(response), 200
    


