import subprocess
from constants import constants
from error_codes import ErrorCode
from flask import Blueprint, jsonify, current_app, request


umount_bp = Blueprint('umount', __name__)

@umount_bp.route("/",methods=['POST'])
def umount():
    out = {
        'name': 'flaskdeb01be',
        'version': current_app.config.get('VERSION', 'unknown'),
        'service': 'umount',
        'retcode': ErrorCode.GENERIC_ERROR,
        'success': [],
        'failed': [],
        'message': None
    }
    data = request.get_json() or {}
    mountpoint = data.get("mountpoint", None)
    fstype = data.get("fstype", None)
    if fstype is None and mountpoint is None:
        out['message'] = "Missing parameter"
        out["retcode"] = ErrorCode.PARAMETER_ERROR
        return jsonify(out), 400

    with open("/proc/mounts", "r") as f:
        for line in f:
            parts = line.split()
            act_mountpoint = parts[1]
            act_fstype = parts[2]
            if mountpoint is not None and mountpoint == act_mountpoint \
                or fstype is not None and fstype == act_fstype :
                current_app.logger.info(f"try umount: {act_mountpoint}")
                try:
                    if act_mountpoint in ('/', '/boot', '/boot/efi'):
                        out['message'] = f"Invalid mountpoint {act_mountpoint}"
                        out["retcode"] = ErrorCode.GENERIC_ERROR
                        return jsonify(out), 500
                    result = subprocess.run(
                        ['/usr/bin/sudo', '/usr/bin/umount', act_mountpoint],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
    
                    if result.returncode == 0:
                        current_app.logger.info(f"umount executed successfully: {act_mountpoint}")
                        out['success'].append({'partition': act_mountpoint})
                    else:
                        current_app.logger.error(f"umount failed: {act_mountpoint}: {result.returncode} err:{result.stderr}")
                        out['failed'].append(act_mountpoint)
                except Exception as e:
                    current_app.logger.error(f"umount exception: {e}")
                    out['message'] = str(e)
                    return jsonify(out), 500
    return jsonify(out), 200
