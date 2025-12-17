import subprocess
from pathlib import Path
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
        'success': [],
        'failed': [],
        'message': None
    }
    data = request.get_json() or {}
    req_mount_target= data.get("mount_target", None)
    req_mount = data.get("mount", True)
    if req_mount_target not in list(constants['lenovosrv']['mount_target'].keys()):
        out['retcode'] = ErrorCode.PARAMETER_ERROR
        out['message'] = f"Invalid mount_target {req_mount_target}"
        current_app.logger.error(out)
        return jsonify(out), 500
    if req_mount:
        suffix = 'mount'
    else:
        suffix = 'umount'
    for target in constants['lenovosrv']['mount_target'][req_mount_target]:
        p = Path(target)
        current_app.logger.info(f'check for: {target}')
        if p.is_dir():
            cmd = ['/usr/bin/sudo', '/usr/bin/' + suffix, target]
        else:
            p = Path(target + suffix + '.sh')
            if p.is_file():
                cmd = ['/usr/bin/sudo', target + suffix + '.sh']
            else:
                out['retcode'] = ErrorCode.PARAMETER_ERROR
                out['message'] = f"Invalid mount_target Not a file or mount point {req_mount_target}"
                current_app.logger.error(out)
                return jsonify(out), 500
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode != 0:
                fail = (target,result.returncode,result.stdout,result.stderr)
                out['failed'].append(fail)
                current_app.logger.info(f"Mount failed: {fail}")
            else:
                success = (target, result.returncode, result.stdout, result.stderr)
                out['success'].append(success)
                current_app.logger.info(f"Mount success: {success}")
        except Exception as e:
            current_app.logger.error(f"Mount exception: {target} exc: {e}")
            out['message'] = str(e)
            return jsonify(out), 500
    return jsonify(out), 200



@mount_bp.route("/", methods=['GET'])
def mount_status():
    mounts = []
    fstypes = ['nfs4', 'vfat', 'ext4', 'btrfs', 'cifs']
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

