import subprocess
from flask import Blueprint, jsonify, current_app, request
from datetime import datetime

shutdown_bp = Blueprint('shutdown', __name__)

@shutdown_bp.route("/", methods=['POST'])
def shutdown():
    data = request.get_json() or {}

    out = {
        'name': 'flaskdeb01be',
        'version': current_app.config.get('VERSION', 'unknown'),
        'service': 'shutdown',
        'message': ''
    }

    try:
        cancel_result = subprocess.run(
            ['/usr/bin/sudo', '/usr/sbin/shutdown', '-c'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if cancel_result.returncode != 0:
            current_app.logger.error(f"Error canceling shutdown: {cancel_result.stderr}")
            out['message'] = {"error canceling previous shutdown": cancel_result.stderr}
            return jsonify(out), 500
        out['message'] = {"message": "Previous shutdown canceled", "stdout": cancel_result.stdout}
    except Exception as e:
        current_app.logger.error(f"Error canceling shutdown: {e}")
        out['message'] = {"error canceling previous shutdown": str(e)}
        return jsonify(out), 500

    current_app.logger.info(f"Shutdown cancelled")
    if not all(k in data for k in ('day', 'month', 'year', 'hour', 'minute')) and not data.get('now', False):
        out['message']=f"No shutdown schedule requested now:{data.get('now', False)}"
        current_app.logger.info(out['message'] + f"data:{repr(data)}")
        return jsonify(out)

    try:
        current_app.logger.info(f"now:{data.get('now', False)} data:{repr(data)}")
        minutes_from_now = 2
        if not data.get('now', False):
            day = int(data['day'])
            month = int(data['month'])
            year = int(data['year'])
            hour = int(data['hour'])
            minute = int(data['minute'])

            shutdown_time = datetime(year, month, day, hour, minute)
            now = datetime.now()
            delta = shutdown_time - now
            minutes_from_now = int(delta.total_seconds() // 60)

        if minutes_from_now <= 0:
            out['message'] = {"error": "Shutdown time must be in the future"}
            return jsonify(out), 400

        # comando shutdown con +m
        schedule_result = subprocess.run(
            ['/usr/bin/sudo', '/usr/sbin/shutdown', '-h', '--no-wall', f'+{minutes_from_now}'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        current_app.logger.info(f"Shutdown scheduled {schedule_result.stdout} {schedule_result.stderr}")

        if schedule_result.returncode != 0:
            current_app.logger.error(f"Error scheduling shutdown: {schedule_result.stderr}")
            out['message'] = {"error scheduling shutdown": schedule_result.stderr}
            return jsonify(out), 500

        out['message'] = {
            "stderr": schedule_result.stderr,
            "stdout": schedule_result.stdout
        }
        return jsonify(out)

    except KeyError as e:
        out['message'] = {"error": f"Missing parameter: {e}"}
        return jsonify(out), 400
    except ValueError as e:
        out['message'] = {"error": f"Invalid parameter value: {e}"}
        return jsonify(out), 400
    except Exception as e:
        out['message'] = {"error": str(e)}
        current_app.logger.error(f"Shutdown error: {e}")
        return jsonify(out), 500


@shutdown_bp.route("/", methods=['GET'])
def get_scheduled_shutdown():
    out = {
        'name': 'flaskdeb01be',
        'version': current_app.config.get('VERSION', 'unknown'),
        'service': 'shutdown',
        'scheduled_shutdown': None
    }

    try:
        # Controllo se esiste uno shutdown schedulato
        result = subprocess.run(
            ['/usr/bin/sudo', '/usr/sbin/shutdown', '--show'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode == 0:
            out['scheduled_shutdown'] = {"message": result.stderr}
            return jsonify(out)
        if result.returncode == 1:
            out['scheduled_shutdown'] = {"message": "No shutdown scheduled"}
            return jsonify(out)

        current_app.logger.error(f"Error checking scheduled shutdown: {result.returncode} err:{result.stderr}")
        out['scheduled_shutdown'] = {"error": result.stderr}
        return jsonify(out), 500

    except Exception as e:
        current_app.logger.error(f"Error getting scheduled shutdown: {e}")
        out['scheduled_shutdown'] = {"error": str(e)}
        return jsonify(out), 500
