
import cgi, os, http.server, socketserver, shutil, psutil, json

PORT = 8082
UPLOAD_DIR = "server/upload"
open("encoding.json", "a+").close()
os.makedirs("encoding/log", exist_ok=True)


Handler = http.server.SimpleHTTPRequestHandler

def get_last_line(file_path):
    with open(file_path, "r") as f:
        lines = f.readlines()
        return lines[-1] if lines else ""

def info_upload(log_dir="encoding/log") -> str:
    r = {}
    for file in os.listdir(log_dir):
        info = get_last_line(f"{log_dir}/{file}")
        percent = "".join(info.split(" ")[5:7])
        fps = "".join(info.split(" ")[7:9])[1:]
        avg_fps = "".join(info.split(" ")[10:12])
        time = info.split(" ")[-1][:-1]

        r[file.split(".txt")[0]] = [percent, fps, avg_fps, time]
    return json.dumps(r, indent=4)

def get_encode_statut():
    d, response =check_encode(), {}
    for file in d:
        video_name, dic = d[file].split("/")[-1], json.loads(info_upload())
        if is_running(file) :
            try:
                response[video_name] = f"{dic[video_name][0]}"[:-1]
            except KeyError:
                pass
        else:
            response[video_name] = f"100"
    return json.dumps(response, indent=4)

def path_file_ready():
    d, r= check_encode(), {"values" : []}
    for pid in d:
            if not is_running(pid):
                r["values"].append(d[pid])
    return json.dumps(r, indent=5)

def replace(file,dest_file):
    if "/" in dest_file:
        path=dest_file.split("/")
        path.pop(-1)
        path="/".join(path)
    os.replace(file,dest_file)


def is_running(pid:int):
    try:
        pid = int(pid)
    except:
        return False
    # Check if the process is running
    if psutil.pid_exists(int(pid)):
        
        return True
    else:
        open("encoding.txt", 'w', encoding="utf-8", errors="ignore").write("\n".join(check_encode().pop(str(pid))))
        return False

def check_encode()->dict:
    try:
        r = json.load(open("encoding.json", "r"))
    except json.decoder.JSONDecodeError:
        r = {}
    return r

def ready():
    return get_encode_statut()  

class FileUploadHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST',
                     'CONTENT_TYPE': self.headers['Content-Type'],
                     }
        )
        fileitem = form['file']

        if fileitem.filename:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            with open(os.path.join(UPLOAD_DIR, fileitem.filename), 'wb') as f:
                f.write(fileitem.file.read())

            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes('<html><body><h1>File uploaded!</h1></body></html>', 'utf-8'))
        else:
            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes('<html><body><h1>Error uploading file</h1></body></html>', 'utf-8'))


class myhandler(http.server.SimpleHTTPRequestHandler, FileUploadHandler):
    def comfirm_request(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def comfirm_req_API(self) -> None:
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_GET(self) -> None:

        if "." in self.path and not "html" in self.path:
            f = self.send_head()
            if f:
                try:
                    self.copyfile(f, self.wfile)
                finally:
                    f.close()
        elif "html" in self.path  and "." in self.path:
            self.comfirm_request()
            self.wfile.write(open(self.path[1:], "rb").read())
        else:
            req_dic = {
                "/ready": lambda: self.comfirm_req_API() or self.wfile.write(bytes(ready(), encoding="utf-8")),
                
            }
            try:
                req_dic[self.path]()
            except KeyError:
                self.send_response(404, 'request means nothing: %s' % self.path)

if __name__ == "__main__": 
    try:
        shutil.rmtree("encoding")
        json.dump(open("encoding.json","w"),check_encode(),indent=5)
    except:
        pass
    os.makedirs("encoding/log", exist_ok=True)
    Handler = myhandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print("serving at port", PORT)
        httpd.serve_forever()
    







