import json
import os
import shutil
import time
import urllib.parse

import random
import requests
import tmdbsimple as tmdb
import wmi
from bs4 import BeautifulSoup as bs

user_list = ["admin", "Lester", "La mom", "Apo", "Antoine", "DrazZ"]

tmdb.API_KEY = "91d34b37526d54cfd3d6fcc5c50d0b31"
tmdb.REQUESTS_TIMEOUT = 5  # seconds, for both connect and read
tixai_url = "http://82.65.222.143:8888"


def get_page(url: str):
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
    text, n = "", 0
    t = open("log.txt", "r", encoding="utf-8").read().split("\n")[::-1]
    if len(t) < 50:
        return json.dumps({"value": "\n".join(t)}, indent=5)
    else:
        return json.dumps({"value": "\n".join(t[:50])}, indent=5)


def nb_uncomplete():
    d = json.load(open("missing.json", "r"))
    d = [elt for elt in d if d[elt] == []]
    return len(d)


def stat_show():
    dic = {}
    dic["nb_show"] = len(json.load(open("anime_lib.json", "r")))
    dic["uncomplete"] = round(nb_uncomplete() / dic["nb_show"], 2) * 100

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

    return "nothing found"


def dl(req: str):
    try:
        req = req.split("?")[-1].split("&")
        is_show = req[0].split("=")[-1]
        list_id = [i.split(":") for i in req[-1].split("=")[-1].split("+")]
        if is_show == "true":
            return json.dumps({"statut": "error"}, indent=5)
            pass

        else:
            print(list_id)
            for id in list_id:
                url = find_file_movie(int(id[0]), id[1])
                os.makedirs("torrent", exist_ok=True)
                open(f"torrent/{str(random.randint(500, 500000))}.magnet", "w").write(url)
                time.sleep(1)  # avoid ban ip
            print("done")
            return json.dumps({"statut": "sucess"}, indent=5)

    except:
        return json.dumps({"statut": "error"}, indent=5)


def downloading():
    # scrap tixati
    scrap = bs(get_page(f"{tixai_url}/transfers"), "html.parser")
    current = scrap.find_all("tr",class_="downloading")
    dic = {"files" : []}
    for elt in current:
        title = elt.find("a").text
        size = elt.find_all("td")[3].text
        percent = elt.find_all("td")[4].text
        speed = elt.find_all("td")[6].text
        url = f" {tixai_url}{elt.find('a')['href']}"
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

def stop_dl(url):
    try:
        requests.post(url,{
                "stop" : "stop"
            })
    except: 
        return json.dumps({"statut": "error"}, indent=5)
def rm_dl(url):
    try:
        requests.post(url,{
                "remove" : "Remove"
            })
    except:
        return json.dumps({"statut": "error"}, indent=5)
def st_dl(url):
    try:
        requests.post(url,{
                "start" : "Start"
            })
    except:
        return json.dumps({"statut": "error"}, indent=5)

if __name__ == "__main__":
    requests.post(tixai_url+"/transfers/23ddb96c16454692/details/action",
    data={
        "start" : "Start"
    })
    print(complete())

    # print(serv_log())
    # print(find_file_movie(680,"pulp fiction"))
    # print(dl("http://127.0.0.1:8080/dl/?is_show=false&q=767:Harry%20Potter%20and%20the%20Half-Blood%20Prince+674:Harry%20Potter%20and%20the%20Goblet%20of%20Fire"))
