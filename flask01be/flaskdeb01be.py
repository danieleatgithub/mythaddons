from flask import Flask
from flask_cors import CORS


from routes.get_cleaned_title import get_cleaned_title_bp
from routes.get_video_path import get_video_path_bp
from routes.info import info_bp
from routes.get_disks_info import get_disks_info_bp
from routes.get_partitions_info import get_partitions_info_bp

#journalctl --no-pager -fxeu flask01be.service

app = Flask(__name__)
CORS(app)

app.config['VERSION'] = '2.0'
app.config['THREAD_POOL'] = {}


app.register_blueprint(get_cleaned_title_bp, url_prefix='/get_cleaned_title')
app.register_blueprint(get_video_path_bp, url_prefix='/get_video_path')
app.register_blueprint(info_bp, url_prefix='/info')
app.register_blueprint(get_disks_info_bp, url_prefix='/get_disks_info')
app.register_blueprint(get_partitions_info_bp, url_prefix='/get_partitions_info')

    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=18800)

