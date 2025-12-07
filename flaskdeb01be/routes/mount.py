import json
import subprocess
from constants import constants
from error_codes import ErrorCode
from flask import Blueprint, jsonify, current_app, request


mount_bp = Blueprint('mount', __name__)

@mount_bp.route("/",methods=['POST'])
def mount():
    out = {
        'name': 'flaskdeb01be',
        'version': current_app.config.get('VERSION', 'unknown'),
        'service': 'mount',
        'retcode': ErrorCode.GENERIC_ERROR,
        'stdout': '',
        'stderr': ''
    }

    try:
        result = subprocess.run(
            ['/usr/bin/sudo', '/usr/bin/mount', '-a'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        out['stdout'] = result.stdout
        out['stderr'] = result.stderr
        out['retcode'] = result.returncode

        if result.returncode != 0:
            current_app.logger.error(f"Mount error: {result.stderr}")
            return jsonify(out), 500

        current_app.logger.info(f"Mount executed successfully: {result.stdout}")
        return jsonify(out), 200

    except Exception as e:
        current_app.logger.error(f"Mount exception: {e}")
        out['stderr'] = str(e)
        return jsonify(out), 500


@mount_bp.route("/", methods=['GET'])
def mount_status():
    mounts = []
    fstypes = ['nfs4', 'vfat', 'ext4', 'btrfs']
    try:
        with open("/proc/mounts", "r") as f:
            for line in f:
                parts = line.split()
                if parts[2] not in fstypes:
                    continue
                mounts.append({
                    "device": parts[0],
                    "mountpoint": parts[1],
                    "fstype": parts[2],
                    "options": parts[3]
                })

        out = {
            'name': 'flaskdeb01be',
            'version': current_app.config.get('VERSION', 'unknown'),
            'service': 'mount',
            'mounts': mounts
        }
        return jsonify(out), 200

    except Exception as e:
        current_app.logger.error(f"mount_status error: {e}")
        return jsonify({"error": str(e)}), 500
