from flask import Flask
from flask_cors import CORS



from routes.info import info_bp
from routes.get_disks_info import get_disks_info_bp
from routes.mount import mount_bp
from routes.shutdown import shutdown_bp
from routes.get_partitions_info import get_partitions_info_bp

#journalctl --no-pager -fxeu flaskdeb01be.service

app = Flask(__name__)
CORS(app)

app.config['VERSION'] = '2.0'

app.register_blueprint(info_bp, url_prefix='/info')
app.register_blueprint(get_disks_info_bp, url_prefix='/get_disks_info')
app.register_blueprint(get_partitions_info_bp, url_prefix='/get_partitions_info')
app.register_blueprint(mount_bp, url_prefix='/mount')
app.register_blueprint(shutdown_bp, url_prefix='/shutdown')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=18800)

