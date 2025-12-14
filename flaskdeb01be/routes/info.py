from flask import Blueprint, jsonify, current_app, request


info_bp = Blueprint('info', __name__)

@info_bp.route("/",methods=['GET'])
def info():

    out = {
        'name': 'flaskdeb01be',
        'version': current_app.config['VERSION'],
        }
    
    return jsonify(out)
