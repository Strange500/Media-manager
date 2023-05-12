import json, platform
import os
import shutil
import time
import urllib.parse
import psutil
import random
import requests
import tmdbsimple as tmdb
import subprocess
from bs4 import BeautifulSoup as bs
from file_analyse_lib import LightFile, anime_dir


if platform.system() == "Windows" :
    import  wmi

    
elif platform.system() == "Linux" :
    ...
    


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
    t = open("log.txt", "r", encoding="utf-8").read().split("\n")[::-1]
    if len(t) < 50:
        return json.dumps({"value": "\n".join(t)}, indent=5)
    else:
        return json.dumps({"value": "\n".join(t[:50])}, indent=5)


def nb_uncomplete():
    d = json.load(open("missing.json", "r"))
    return len(d)


def stat_show():
    dic = {}
    try:
        dic["nb_show"] = len(json.load(open("anime_lib.json", "r")))
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

if __name__ == "__main__":
    print(cpu_temp())
    