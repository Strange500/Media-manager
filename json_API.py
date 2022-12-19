import json
import os
import shutil
import urllib.parse
import tmdbsimple as tmdb
tmdb.API_KEY ="TMDB_API_KEY"
tmdb.REQUESTS_TIMEOUT = 5  # seconds, for both connect and read
import wmi,requests
from bs4 import BeautifulSoup as bs

user_list = ["admin", "Lester", "La mom", "Apo", "Antoine", "DrazZ"]


def get_page(url:str):
    return requests.get(url).content



def alive() -> json:
    return json.dumps({"alive": True}, indent=4)


def space():
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
    w = wmi.WMI(namespace="root\OpenHardwareMonitor")
    temperature_infos = w.Sensor()
    for sensor in temperature_infos:

        if sensor.SensorType == u'Temperature' and sensor.name == "CPU Package":
            return json.dumps({"value": sensor.value})


def serv_log():
    text,n = "",0
    with open("log.txt", "r") as f:
        for line in f:
            text,n = text + line,n+1
            if n == 50:
                break
            
    return json.dumps({"value": text}, indent=5)

def nb_uncomplete():
    d = json.load(open("missing.json","r"))
    d = [elt for elt in d if d[elt] == [] ]
    return len(d)


def stat_show():
    dic={}
    dic["nb_show"] = len(json.load(open("anime_lib.json","r")))
    dic["uncomplete"] = round(nb_uncomplete() / dic["nb_show"],2)*100

    return json.dumps(dic,indent=5)


def find_file_movie(id):
    # YFI on thepiratebay
    search = "fight club"
    search = search.replace(" ","%20")
    scrap = bs(get_page(f"https://yts.rs/browse-movies/{search}/all/all/0/latest"),"html.parser")
    elt = scrap.find_all("a",class_="title")
    for title in elt:
        print(title.text)


if __name__=="__main__":
    print(find_file_movie(680))