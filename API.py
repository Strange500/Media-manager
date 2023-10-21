import platform
import qbittorrentapi
from flask import Flask, jsonify, request, abort
from flask_cors import CORS
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename

if platform.system() == "Windows":
    pass
from Database import *

qbit_conn_info = dict(
    host="localhost",
    port=8080,
    username="admin",
    password="password"
)


class web_API(Server):

    def __init__(self, db: DataBase):
        super().__init__()
        self.db = db
        self.cpu_avg = 0
        self.cpu_temp_list = [0]

        self.app = Flask(__name__)
        self.app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024  # 10GB limit
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        CORS(self.app)

        @self.app.route("/anime/list")
        def get_anime():
            return jsonify(self.db.animes)

        @self.app.route("/anime/dirs")
        def get_anime_dirs():
            return jsonify(self.db.anime_dirs)

        @self.app.route("/show/list")
        def get_show():
            return jsonify(self.db.shows)

        @self.app.route("/show/dirs")
        def get_show_dirs():
            return jsonify(self.db.shows_dirs)

        @self.app.route("/movie/list")
        def get_movie():
            return jsonify(self.db.movies)

        @self.app.route("/movie/dirs")
        def get_movie_dirs():
            return jsonify(self.db.movie_dirs)

        @self.app.route('/torrent/upload', methods=['POST'])
        def upload_torrent():
            self.app.config['UPLOAD_FOLDER'] = Server.conf["torrent_dir"]
            return upload_file(self.app)

        @self.app.route('/alive')
        def alive():
            return jsonify(True)

        @self.app.route("/movie/size")
        def movie_size():
            return jsonify(get_total_free_and_used(self.db.movie_dirs))

        @self.app.route("/show/size")
        def show_size():
            return jsonify(get_total_free_and_used(self.db.shows_dirs))

        @self.app.route("/anime/size")
        def anime_size():
            return jsonify(get_total_free_and_used(self.db.anime_dirs))

        @self.app.route("/movie/nb")
        def movie_nb():
            return jsonify({"value": len(self.db.movies)})

        @self.app.route("/show/nb")
        def show_nb():
            return jsonify({"value": len(self.db.shows)})

        @self.app.route("/anime/nb")
        def anime_nb():
            return jsonify({"value": len(self.db.animes)})

        @self.app.route("/cpu_temp/current")
        def cpu_temp():
            return jsonify({"value": Server.CPU_TEMP})

        @self.app.route("/cpu_temp/avg")
        def cpu_avg():
            self.update_cpu_avg()
            return jsonify({"value": self.cpu_avg})

        @self.app.route("/torrent/donwloading")
        def get_downloading_torrent():
            q = qbittorrentapi.Client(**qbit_conn_info)
            torrents_info = {}

            for torrent in q.torrents_info(status_filter="active"):
                name = torrent['name']
                download_speed = torrent.info['dlspeed'] / (1024 * 1024)  # Download speed in MB/s
                progress = torrent.info['progress'] * 100  # Progress in percentage
                downloaded_size = torrent.info['downloaded'] / (1024 * 1024)  # Downloaded size in MB
                total_size = torrent.info['total_size'] / (1024 * 1024)  # Total size in MB
                torrents_info[name] = {"speed": download_speed,
                                       "total_size": total_size,
                                       "percent": progress,
                                       "downloaded": downloaded_size}
            return torrents_info

        @self.app.route("/tmdb/search", methods=['POST'])
        def seach_tmdb_show():
            if request.method == 'POST':
                if request.form.get("choice") in ["anime", "show"]:
                    self.search.tv(query=request.form.get("search"))
                    return jsonify({"results": self.search.results})
                elif request.form.get("choice") == "movie":
                    self.search.movie(query=request.form.get("search"))
                    return jsonify({"results": self.search.results})

        @self.app.route("/request/show", methods=['POST'])
        def add_show():
            if request.method == "POST":
                if request.form.get("id") == "0":
                    abort(400)
                if type(request.form.get("id")) == str and request.form.get("id").isnumeric():
                    if request.form.get("choice") == "show":
                        open(os.path.join(VAR_DIR, QUERY_SHOW), "a").write(request.form.get("id") + "\n")
                        return "ok"
                    elif request.form.get("choice") == "anime":
                        open(os.path.join(VAR_DIR, QUERY_ANIME), "a").write(request.form.get("id") + "\n")
                        return "ok"
                    elif request.form.get("choice") == "movie":
                        open(os.path.join(VAR_DIR, QUERY_MOVIE), "a").write(request.form.get("id") + "\n")
                        return "ok"
                    else:
                        abort(400)
                else:
                    abort(400)
            else:
                abort(400)

        @self.app.route('/upload', methods=['POST', "OPTIONS"])
        def upload_file():
            if 'file' not in request.files:
                return "Aucun fichier n'a été sélectionné", 400

            file = request.files['file']
            if file.filename == '':
                return "Le nom de fichier est vide", 400
            ch = request.form.get("up_choice")
            if ch == "anime":
                dir_save = self.db.to_sort_anime
            elif ch == "show":
                dir_save = self.db.to_sort_show
            elif ch == "movie":
                dir_save = self.db.to_sort_movie
            file.save(os.path.join(dir_save, secure_filename(file.filename)))

            return "Téléchargement réussi"

        @self.socketio.on('connect')
        def handle_connect():
            log('New client connected ...', debug=True)

        @self.socketio.on('disconnect')
        def handle_disconnect():
            log('Client disconnected.', debug=True)

        @self.socketio.on('message')
        def handle_message(data):
            log(data, debug=True)
            if data == "cpu_temp":
                self.socketio.emit("cpu_temp", json.dumps({"value": Server.CPU_TEMP}))
            elif data == "cpu_temp_avg":
                self.socketio.emit("cpu_temp_avg", json.dumps({"value": self.cpu_avg}))
            elif data == "disk":
                self.socketio.emit("disk", jsonify(get_total_free_and_used(self.db.movie_dirs)))
            elif data == "anime_size":
                self.socketio.emit("anime_size", json.dumps(get_total_free_and_used(self.db.anime_dirs)))
            elif data == "movie_size":
                self.socketio.emit("movie_size", json.dumps(get_total_free_and_used(self.db.movie_dirs)))
            elif data == "show_size":
                self.socketio.emit("show_size", json.dumps(get_total_free_and_used(self.db.shows_dirs)))

        def upload_file(app: Flask):
            file = request.files['file']
            if file:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                return 'File uploaded successfully'
            return 'No file uploaded'

    def run(self):
        self.socketio.run(host="0.0.0.0", app=self.app, allow_unsafe_werkzeug=True)

    def update_cpu_avg(self):
        self.cpu_avg = round(sum(self.cpu_temp_list) / len(self.cpu_temp_list), 2)
