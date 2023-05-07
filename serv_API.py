# -*- coding: utf-8 -*

from http.server import CGIHTTPRequestHandler, HTTPServer, SimpleHTTPRequestHandler
import json, platform, datetime, os, shutil, time, urllib.parse, psutil, random, requests, subprocess, cgi
import tmdbsimple as tmdb
from bs4 import BeautifulSoup as bs

if platform.system() == "Windows" :
    import  wmi
    PYTHON = "python"
    NTERM = "start"
    REBOOT = "shutdown /r"
    
elif platform.system() == "Linux" :
    PYTHON = "python3"
    NTERM = "gnome-terminal --"
    REBOOT = "reboot"
    VAR_DIR = "/var/lib/my-server"

ls = open(os.path.join(VAR_DIR, "config.txt"), 'r', encoding="utf-8").read().split("\n")
config = {}
for elt in ls:
    try:
        config[elt.split(" : ")[0]] = elt.split(" : ")[1]
    except IndexError:
        pass
del ls
try:
    banned_words = open(os.path.join(VAR_DIR, "banned_words.txt"), "r", encoding="utf-8").read().split("\n")
    select_words = open(os.path.join(VAR_DIR, "select_words.txt"), "r", encoding="utf-8").read().split("\n")
except FileNotFoundError:
    banned_words, select_words = [], []
    print("WARNING NO FILTER ON DOWNLOAD")
sources = open(os.path.join(VAR_DIR, "sources.txt"), "r").read().split("\n")
anime_dir = config['anime_dir'].split(",")
movie_dir = config['movie_dir'].split(",")
install_dir = config["serv_dir"]
download_dir = config['download_path'].split(",")
sorter_dir = config['sorter_anime_dir'].split(",")
clip_load = config['clip_load']
clip_lib = config['clip_lib']
temp_dir = config["temp"]
HTML_FILE_NAME = 'alive'
PORT_NUMBER = 8081

UPLOAD_DIR = os.path.join(install_dir,'upload')

def time_log():
    # Get the current time
    current_time = datetime.datetime.now()
    datetime.datetime.now().strftime("%H")

    # Format the time as a string with the hour, minute, and second
    return current_time.strftime("%H:%M:%S")
user_list = ["admin", "Lester", "La mom", "Apo", "Antoine", "DrazZ"]

tmdb.API_KEY = "91d34b37526d54cfd3d6fcc5c50d0b31"
tmdb.REQUESTS_TIMEOUT = 5  # seconds, for both connect and read
tixai_url = "http://127.0.0.1:8888"

class Waifu2x():

    def __init__(self, scale: int | None = 2, noise : int | None = 2, format: str |None = "png") -> None:
        self.__scale = scale
        self.__noise = noise
        self.__format = format

    @property
    def scale(self):
        return self.__scale
    @property
    def noise(self):
        return self.__noise
    @property
    def format(self):
        return self.__format
    

    def run(self, file_path: str, target_dir : str) -> str:
        """upsacle input image and return the path of the upscaled image"""
        if self.format:
            file_name = file_path.split("/")[-1].replace(".jpg",f".{self.format}")
        else:
            file_name = file_path.split("/")[-1].split(".")[0]+".png"
        print(f"upscale_engine/waifu2x.exe -i {file_path} -o {f'{target_dir}/{file_name}'} -n {self.noise} -s {self.scale} ")
        subprocess.run(f"upscale_engine/waifu2x.exe -i {file_path} -o {f'{target_dir}/{file_name}'} -n {self.noise} -s {self.scale} ")
        return f'{target_dir}/{file_name}'

def get_page(url: str):
    return requests.get(url).content


def alive() -> json:
    return json.dumps({"alive": True}, indent=4)


def space():
        if platform.system() == "Linux":
            list_disk, json_list = anime_dir, {}
        elif platform.system() == "Windows":
            list_disk, json_list = [f"{i}:\\" for i in [chr(k) for k in range(ord("A"), ord("Z") + 1)]], {}
        for disk in list_disk:
            if disk == "G:\\":
                pass
            else:
                try:
                    total, used, free = shutil.disk_usage(disk)
                    json_list[disk] = {"total": total, "used": used, "free": free}
                except:
                    pass

        return json.dumps(json_list, indent=5)


def restart():
    os.system("shutdown /r")
    return json.dumps({"status": "ok"}, indent=5)


def is_user(req: str):
    req = urllib.parse.unquote(req)
    user = req.split("/")[-1].split("u=")[-1]
    if user in user_list:
        return json.dumps({"is_user": True})
    else:
        return json.dumps({"is_user": False})


def cpu_temp():
    if platform.system() == "Linux":
        return json.dumps({"value" : psutil.sensors_temperatures()["k10temp"][0].current})
    else:
        w = wmi.WMI(namespace="root\OpenHardwareMonitor")
        temperature_infos = w.Sensor()
        for sensor in temperature_infos:

            if sensor.SensorType == u'Temperature' and sensor.name == "CPU Package":
                return json.dumps({"value": sensor.value})


def serv_log():
    text, n = "", 0
    t = open(os.path.join(VAR_DIR,"log.txt"), "r", encoding="utf-8").read().split("\n")[::-1]
    if len(t) < 50:
        return json.dumps({"value": "\n".join(t)}, indent=5)
    else:
        return json.dumps({"value": "\n".join(t[:50])}, indent=5)

def get_missing():
    return json.load(open(os.path.join(VAR_DIR, "missing.json"), "r"))

def nb_uncomplete():
    d = get_missing()
    return len(d)

def get_anime_lib():
    return json.load(open(os.path.join(VAR_DIR, "anime_lib.json"), "r"))

def stat_show():
    dic = {}
    try:
        dic["nb_show"] = len(get_anime_lib())
        dic["uncomplete"] = round(nb_uncomplete() / dic["nb_show"], 2) * 100
    except:
        return json.dumps({"nb_show" : 0, "uncomplete" : 0}, indent=5)
    return json.dumps(dic, indent=5)


def find_show_file(id, search):
    pass


def find_file_movie(id, search):
    # YFI on thepiratebay
    #1334x RARBG
    

    search = search.replace(" ", "%20")
    scrap = bs(get_page(f"https://yts.rs/browse-movies/{search}/all/all/0/latest"), "html.parser")
    elt = scrap.find_all("a", class_="title")
    for title in elt:
        s = tmdb.Search()
        id_test = s.movie(query=title.text)
        id_test = s.results[0]['id']
        if id_test == id:
            scrap = bs(get_page("https://yts.rs" + title["href"]), "html.parser")
            elt = scrap.find_all("a", class_="download-torrent")
            ls = [i["href"] for i in elt if "1080" in i["title"] and "magnet" in i["href"]]
            return ls[0]

    return 


def dl(req: str):
    r = json.dumps({"statut": "sucess"}, indent=5)
    try:
        req = req.split("?")[-1].split("&")
        is_show = req[0].split("=")[-1]
        list_id = [i.split(":") for i in req[-1].split("=")[-1].split("+")]
        if is_show == "true":
            return json.dumps({"statut": "error"}, indent=5)
            pass

        else:
            for id in list_id:
                url = find_file_movie(int(id[0]), id[1])
                if type(url) == str:
                    os.makedirs("torrent", exist_ok=True)
                    open(f"torrent/{str(random.randint(500, 500000))}.magnet", "w").write(url)
                    time.sleep(1)  # avoid ban ip
                    
                else:
                    r = json.dumps({"statut": "error"}, indent=5)
                
            
            return r

    except:
        return json.dumps({"statut": "error"}, indent=5)


def downloading():
    # scrap tixati
    scrap = bs(get_page(f"{tixai_url}/transfers"), "html.parser")
    current = scrap.find_all("tr",class_="downloading")
    dic = {"files" : []}
    for elt in current:
        el = LightFile(elt.find("a").text)
        title = f"{el.title()} S{el.season}E{el.ep}"
        size = elt.find_all("td")[3].text
        percent = elt.find_all("td")[4].text
        speed = elt.find_all("td")[6].text
        url = f"{tixai_url}{elt.find('a')['href']}"
        dic["files"].append({"title" : title,
                            "size" : size,
                            "percent" : percent,
                            "speed" : speed,
                            "url" : url})
    return json.dumps(dic, indent=5)

def complete():
    # scrap tixati
    scrap = bs(get_page(f"{tixai_url}/transfers"), "html.parser")
    current = scrap.find_all("tr",class_="complete")
    dic = {"files" : []}
    for elt in current:
        title = elt.find("a").text
        size = elt.find_all("td")[3].text
        percent = elt.find_all("td")[4].text
        speed = elt.find_all("td")[6].text
        url = f" {tixai_url}{elt.find('a')['href']}"
        dic["files"].append({"title" : title,
                            "size" : size,
                            "url" : url})
    return json.dumps(dic, indent=5)

def det_var(url:str):
    url, dic = url.split("?")[-1], {}
    url = url.split("=")
    var = [i for i in url if url.index(i) % 2 == 0]
    values = [i for i in url if url.index(i) % 2 != 0]
    for name, value in zip(var, values):
        dic[name] = value
    return dic


def stop_dl(url):
    url = det_var(url)["url"]
    try:
        requests.post(f"{url}/action",data={
                "stop" : "Stop"
            })
    except: 
        return json.dumps({"statut": "error"}, indent=5)
def rm_dl(url):
    url = det_var(url)["url"]
    try:
        requests.post(f"{url}/action",data={
                "remove" : "Remove"
            })
    except:
        return json.dumps({"statut": "error"}, indent=5)
def st_dl(url):
    url = det_var(url)["url"]
    try:
        requests.post(f"{url}/action",data={
                "start" : "Start"
            })
    except:
        return json.dumps({"statut": "error"}, indent=5)

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

def upscale():
    w, dir, target, r = Waifu2x(), "to_upscale", "upscaled", {}
    os.makedirs(dir, exist_ok=True)
    os.makedirs(target, exist_ok=True)
    for file in os.listdir(dir):
            r[file] = w.run(file_path=f"{dir}/{file}", target_dir=target)
    return json.dumps(r, indent=5)
def isolate_numbers(temp_file: str) -> list:

    """return a list of all numbers in the string"""
    ls = []
    while temp_file != "":  # isolate all number in file_name then associate number with season
        nb = ""
        try:
            while temp_file[0] not in [str(i) for i in range(0, 10)]:
                temp_file = temp_file[1:]
        except IndexError:
            break
        try:
            while temp_file[0] in [str(i) for i in range(0, 10)]:
                nb = nb + temp_file[0]
                temp_file = temp_file[1:]
            if len(nb) <= 4:
                ls.append(nb)


        except IndexError:
            if len(nb) < 4:
                ls.append(nb)
    return ls
def car_to_car(string: str, car1: str, car2: str) -> str:
    """return str without car between two character"""
    if car1 in string and car2 in string:
        while car1 in string or car2 in string:
            new_str = ""

            while string[0] != car1 and car1 in string:
                new_str = new_str + string[0]
                string = string[1:]
            while string[0] != car2 and car2 in string:
                string = string[1:]
            string = string[1:]
            string = new_str + string
        return string.strip()
    else:
        return string
def title_already_checked(title: str) -> str:
    with open(os.path.join(VAR_DIR, "title_romaji.txt"),"r", encoding="utf-8", errors='ignore') as f:
        for ligne in f:
            ligne = ligne.split(" : ")
            if title == ligne[0]:
                return ligne[1].replace("\n", "").strip()
    f.close()
def title_to_romaji(title):
    ttt = title_already_checked(title)
    if ttt != None:
        return ttt
    try:
        tt = Anime(title).title
        open(os.path.join(VAR_DIR, "title_romaji.txt"), "a").write(f"{title} : {tt}\n")
    except IndexError:
        return title
    except UnicodeEncodeError:
        return title
    except requests.exceptions.HTTPError:
        return title
    return tt
def forbiden_car(name: str):
    """remove forbidden car for file naming"""
    for car in ["?", '"', "/", "\\", "*", ":", "<", ">", "|"]:
        name = name.replace(car, "")
    return name
class Anime:
    """Provide a view on the anime"""

    def __init__(self, title) -> None:
        search = tmdb.Search()
        try:
            os.makedirs(os.path.join(VAR_DIR,"anime_database"), exist_ok=True)
        except PermissionError:
            print("WARNING can't determine existance of anime_database in /var/lib/my-server")
        try:
            if not f"{title}.json" in os.listdir(os.path.join(VAR_DIR, "anime_database")):
                self.__id = search.tv(query=title)
                self.__id = search.results[0]['id']
                self.__tmbd = tmdb.TV(self.id)
                self.__info = self.__tmbd.info()
            else:
                with open(os.path.join(VAR_DIR,f"anime_database",f"{title}.json"), "r") as f:
                    try:
                        self.__info = json.load(f)
                    except json.decoder.JSONDecodeError:
                        f.close()
                        try:
                            
                            os.remove(os.path.join(f"anime_database",f"{title}.json"))
                        except FileNotFoundError:
                            pass
                        self.__init__(title)
                        return

                    self.__id = self.info['id']

            self.__title = self.info["name"]
            self.__season = self.info["number_of_seasons"]
            self.__ep = self.info["number_of_episodes"]
            try:
                with open(os.path.join(VAR_DIR,f"anime_database",f"{forbiden_car(self.title)}.json"), "w") as f:
                    json.dump(self.info, f, indent=4)
            except:
                pass
        except IndexError:
            if " " in title:
                title = title.split(" ")[:-1]
                self.__init__(" ".join(title))
            else:
                raise IndexError("Aucun résultat ne correspond")

    @property
    def tmbd(self):
        if hasattr(self, "__tmdb"):
            return self.__tmdb
        else:
            self.__tmdb = tmdb.TV(self.id)
            return self.__tmdb

    @property
    def ep(self):
        return self.__ep

    @property
    def id(self) -> int:
        return self.__id

    @property
    def info(self) -> dict:
        return self.__info

    @property
    def number_of_season(self) -> int:
        return self.__season

    @property
    def title(self) -> str:
        return self.__title

    def __str__(self) -> str:
        return f"{self.title} : {self.number_of_season} seasons"

class LightFile():

    def title(self):
        """return the title of a video"""
        file = self.path
        for banned_car in [("[", "]"), ("{", "}"), ("(", ")")]:
            car1, car2 = banned_car
            file = car_to_car(file, car1, car2)
        file = file.split("/")[-1].strip()
        if "2nd Season" in file:
            file = file.replace("2nd Season", "")
        if "st Season" in file:
            file = file.replace("1st Season", "")
        if "rd Season" in file:
            file = file.replace("3rd Season", "")
        if "Cour 2" in file:
            file = file.replace("Cour 2", "")
        if " - " in file:
            file = file.split(" - ")[0]
            if "Season" in file:
                file = file.split("Season")[0]
            if f"S{self.season}" in file:
                file = file.split(f"S{self.season}")[0]
            if f"S{self.season[1]}" in file:
                file = file.split(f"S{self.season[1]}")[0]
            if file[-1] in [str(i) for i in range(0, 10)] and file[-2] == " ":
                file = file[:-1].strip()
            return title_to_romaji(file.strip())

        temp_file, index = file, None
        while "S" in temp_file:
            if "S" in temp_file and temp_file.index("S") + 3 < len(file) and temp_file[temp_file.index("S") + 3] == "E":
                index = temp_file.index("S")
                break
            elif "S" in temp_file:
                temp_file = temp_file.replace("S", " ", 1)
        if index != None:
            return title_to_romaji(file[:index].strip())
        for car in file:
            if car in [str(i) for i in range(10)]:
                return title_to_romaji(file.split(car)[0].strip())
        return title_to_romaji(file.split(" ")[0])

    def __init__(self, path_to_file) -> None:
        self.path = path_to_file
        self.file_name = path_to_file.split("/")[-1].strip()
        self.season = self.determine_season()
        self.ep = self.determine_ep()

    def determine_ep(self) -> str:
        """return the ep of a video file from it's title"""
        file, ls, temp = self.path, [], None
        file = file.replace(".mp4", "").strip()
        for banned_car in [("[", "]"), ("{", "}"), ("(", ")")]:
            car1, car2 = banned_car
            file = car_to_car(file, car1, car2)
        file = file.split("/")[-1].strip()
        temp_file = file
        ls = isolate_numbers(temp_file)
        if ls == []:
            return "MOVIE"
        if len(ls) == 1:
            return f"{ls[0]:02}"
        else:

            for elt in ls:
                try:
                    if file.split(elt)[0][-1] == "E":
                        if len(elt) <= 2:
                            return f"{int(elt):02}"
                        elif len(elt) == 3:
                            return f"{int(elt):03}"
                        elif len(elt) == 4:
                            return f"{int(elt):04}"
                except IndexError:
                    pass
                if len(elt) == 2:
                    if f"{int(elt):02}" == self.season:
                        temp = elt
                    else:
                        return f"{int(elt):02}"
            if temp != None:
                return f"{int(temp):02}"
            elif ls != []:
                ep = str(max([int(i) for i in ls]))
                if len(ep) <= 2:
                    return f"{int(ep):02}"
                elif len(ep) == 3:
                    return f"{int(ep):03}"
                elif len(ep) == 4:
                    return f"{int(ep):04}"

    def determine_season(self) -> str:
        """return the season of a video file from it's title"""
        file, ls = self.path, []
        file = file.replace(".mp4", "").strip()

        for banned_car in [("[", "]"), ("{", "}"), ("(", ")")]:
            car1, car2 = banned_car
            file = car_to_car(file, car1, car2)
        file = os.path.basename(file)
        if "oav" in file.lower():
            return "00"
        temp_file = file
        if "nd Season" in file:
            return "02"
        if "st Season" in file:
            return "01"
        if "rd Season" in file:
            return "03"
        try:
            while file[0] in [str(i) for i in range(0, 10)]:
                file = file[1:]
        except:
            pass
        ls = isolate_numbers(file)
        if len(ls) == 1:
            return "01"
        for elt in ls:
            try:
                if file.split(elt)[0][-1] in "sS":
                    elt = int(elt)
                    return f"{elt:02}"
            except IndexError:
                pass
        for elt in ls:
            temp_file, exemple = file.split(elt)[0], "Season "
            while temp_file[-1] == exemple[-1] and len(exemple) > 1 and len(temp_file) > 1:
                temp_file, exemple = temp_file[:-1], exemple[:-1]
            if exemple == "S":
                return f"{int(elt):02}"

        return "01"

    def __str__(self) -> str:
        return f"{self.title()} - S{self.season}E{self.ep} - .mkv"





os.makedirs(UPLOAD_DIR, exist_ok=True)
# This class will handles any incoming request from the browser
class myHandler(CGIHTTPRequestHandler):

    
    def comfirm_request(self) -> None:
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def make_response(self) -> None:
        if self.path == "/upload":
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(open("index.html", "rb").read())
        if not "?" in self.path:
            req_dic = {
                "/alive": lambda: self.comfirm_request() or self.wfile.write(bytes(alive(), encoding="utf-8")),
                "/space": lambda: self.comfirm_request() or self.wfile.write(bytes(space(), encoding="utf-8")),
                "/restart": lambda: self.comfirm_request() or self.wfile.write(bytes(restart(), encoding="utf-8")),
                "/cpu_temp": lambda: self.comfirm_request() or self.wfile.write(bytes(cpu_temp(), encoding="utf-8")),
                "/log": lambda: self.comfirm_request() or self.wfile.write(bytes(serv_log(), encoding="utf-8")),
                "/stats_lib": lambda: self.comfirm_request() or self.wfile.write(bytes(stat_show(), encoding="utf-8")),
                "/check_dl": lambda: self.comfirm_request() or self.wfile.write(bytes(downloading(), encoding="utf-8"))

            }
            try:
                req_dic[self.path]()
            except KeyError:
                self.send_response(404, 'request means nothing: %s' % self.path)
        else:

            cgi_dic = {
                "/is_user": lambda: self.comfirm_request() or self.wfile.write(
                    bytes(is_user(self.path), encoding="utf-8")),
                "/dl": lambda: self.comfirm_request() or self.wfile.write(
                    bytes(dl(self.path), encoding="utf-8")),
                "/stop_dl" : lambda: self.comfirm_request() or self.wfile.write(
                    bytes(stop_dl(self.path), encoding="utf-8")),
                "/st_dl": lambda: self.comfirm_request() or self.wfile.write(
                    bytes(st_dl(self.path), encoding="utf-8")),
                "/rm_dl": lambda: self.comfirm_request() or self.wfile.write(
                    bytes(rm_dl(self.path), encoding="utf-8")),
            }
            try:
                print("/" + self.path.split("/")[1])
                cgi_dic["/" + self.path.split("/")[1]]()
            except KeyError:
                self.send_response(404, 'request means nothing: %s' % self.path)

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


    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header('Access-Control-Allow-Methods', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.do_POST()
        

    def do_GET(self):
        self.cgi_directories = ["/"]
        self.make_response()
        # if str(self.path)=="/":

        #     self.path = HTML_FILE_NAME

        # try:
        #     with open(curdir + sep + self.path, 'r',encoding="utf-8") as f:
        #         self.send_response(200)
        #         self.send_header('Content-type', 'text/html')
        #         self.end_headers()
        #         self.wfile.write(str(popen("python "+self.path).read()).encode('utf-8'))
        #     return
        # except IOError:
        #     self.send_error(404, 'File Not Found: %s' % self.path)


try:
    # Create a web server and define the handler to manage the incoming request

    print('Started httpserver on port %i.' % PORT_NUMBER)
    myHandler.cgi_directories = ["/"]
    # Wait forever for incoming http requests
    serv_api = HTTPServer(('', PORT_NUMBER), myHandler)
    print(f"[{time_log()}] MAIN: API STARTED")
    while True:
        serv_api.serve_forever()
    

except KeyboardInterrupt:
    serv_api.server_close()
    print('Interrupted by the user - shutting down the web server.')
