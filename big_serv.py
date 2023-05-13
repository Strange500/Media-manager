import datetime
import json
import os
import platform
import shutil
import threading
import time
from copy import deepcopy

import feedparser
import requests
import tmdbsimple as tmdb

###################################
#############VARIABLE##############
###################################

if platform.system() == "Windows":
    PYTHON = "python"
    NTERM = "start"
    REBOOT = "shutdown /r"
elif platform.system() == "Linux":
    PYTHON = "python3"
    NTERM = "gnome-terminal --"
    REBOOT = "reboot"
    VAR_DIR = "/var/lib/my-server"

JUDAS_DRIVE = "/run/user/1000/gvfs/google-drive:host=gmail.com,user=benjamin.rogetpro,prefix=%2FGVfsSharedDrives/GVfsSharedDrives/0AFiz8sCCcL37Uk9PVA"
GDRIVE_API_KEY = "AIzaSyCN3e10heRboPwtG1ONiFmqulI3gTioohc"
tmdb.API_KEY = "91d34b37526d54cfd3d6fcc5c50d0b31"
tmdb.REQUESTS_TIMEOUT = 5  # seconds, for both connect and read

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
ls = anime_dir + movie_dir + download_dir + sorter_dir
ls.append(install_dir)
ls.append(clip_load)
ls.append(clip_lib)

######### FILE CHECKING ##########

if "sources.txt" not in os.listdir(VAR_DIR):
    open(os.path.join(VAR_DIR, "sources.txt"), "w")
if "nyaa.json" not in os.listdir(VAR_DIR):
    json.dump({}, open(os.path.join(VAR_DIR, "nyaa.json"), "w"))
if "missing.json" not in os.listdir(VAR_DIR):
    json.dump({}, open(os.path.join(VAR_DIR, "missing.json"), "w"))
if "anime_id.json" not in os.listdir(VAR_DIR):
    json.dump({}, open(os.path.join(VAR_DIR, "anime_id.json"), 'w'))
if "anime_titles_database.json" not in os.listdir(VAR_DIR):
    json.dump({}, open(os.path.join(VAR_DIR, "anime_titles_database.json"), 'w'))
if "judas_anime_lib.json" not in os.listdir(VAR_DIR):
    json.dump({}, open(os.path.join(VAR_DIR, "judas_anime_lib.json"), 'w'))
if "anime_lib.json" not in os.listdir(VAR_DIR):
    json.dump({}, open(os.path.join(VAR_DIR, "anime_lib.json"), 'w'))

for elt in ls:
    try:
        os.makedirs(elt, exist_ok=True)
    except:
        pass

######### DIRECTORY ##########
os.makedirs(os.path.join(install_dir, "torrent"), exist_ok=True)

if "rss.txt" not in os.listdir(VAR_DIR):
    open(os.path.join(VAR_DIR, "rss.txt"), "w")
if "title_romaji.txt" not in os.listdir(VAR_DIR):
    open(os.path.join(VAR_DIR, "title_romaji.txt"), "w")
if "banned_words.txt" not in os.listdir(VAR_DIR):
    open(os.path.join(VAR_DIR, "banned_words.txt"), "w")
if "select_words.txt" not in os.listdir(VAR_DIR):
    open(os.path.join(VAR_DIR, "select_words.txt"), "w")
if "already_download.txt" not in os.listdir(VAR_DIR):
    open(os.path.join(VAR_DIR, "already_download.txt"), "w")
if "judas_not_vostfr.txt" not in os.listdir(VAR_DIR):
    open(os.path.join(VAR_DIR, "judas_not_vostfr.txt"), "w")
if "judas_vostfr.txt" not in os.listdir(VAR_DIR):
    open(os.path.join(VAR_DIR, "judas_vostfr.txt"), "w")


###################################
##########BASE FONCTION############
###################################
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
    with open(os.path.join(VAR_DIR, "title_romaji.txt"), "r", encoding="utf-8", errors='ignore') as f:
        for ligne in f:
            ligne = ligne.split(" : ")
            if title == ligne[0]:
                return ligne[1].replace("\n", "").strip()
    f.close()


def forbiden_car(name: str):
    """remove forbidden car for file naming"""
    for car in ["?", '"', "/", "\\", "*", ":", "<", ">", "|"]:
        name = name.replace(car, "")
    return name


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


# def mise_en_cache(file: str, string: str) -> None:
#     open(file, "ab").write(bytes(string, encoding="utf-8"))


def extract(dir):
    if "/" in dir:
        parent_dir = "/".join(dir.split("/")[:-1])
    elif "\\" in dir:
        parent_dir = "\\".join(dir.split("\\")[:-1])
    for file in os.listdir(dir):
        shutil.move(os.path.join(f"{dir}", f"{file}"), parent_dir)

    shutil.rmtree(dir)


# def check_cache(file) -> str:
#     open(file, "r", encoding="utf-8").read()


def log(to_log: str) -> None:
    if type(to_log) == str:
        l = f'[{time_log()}] {to_log}\n'
        open(f"{VAR_DIR}/log.txt", "a", encoding="utf-8").write(l)


def get_anime() -> None:
    """look for videos to sort and choose between movie and series"""
    for dir in download_dir:
        for file in os.listdir(dir):
            if "MOVIE" not in file and ("mp4" in file or "mkv" in file):
                if "E:" in dir:
                    try:
                        shutil.move(os.path.join(f"{dir}", f"{file}"), sorter_dir[0])
                    except shutil.Error:
                        try:
                            os.remove(os.path.join(sorter_dir[0], file))
                        except FileNotFoundError:
                            if len(sorter_dir) > 1:
                                os.remove(os.path.join(sorter_dir[0], file))

                        shutil.move(os.path.join(f"{dir}", f"{file}"), sorter_dir[0])
                    except OSError:
                        if len(sorter_dir) > 1:
                            shutil.move(os.path.join(f"{dir}", f"{file}"), sorter_dir[0])
                else:
                    try:
                        shutil.move(os.path.join(f"{dir}", f"{file}"), sorter_dir[0])
                    except shutil.Error:
                        try:
                            os.remove(os.path.join(sorter_dir[0], file))
                        except FileNotFoundError:
                            try:
                                os.remove(os.path.join(sorter_dir[0], file))
                            except FileNotFoundError:
                                pass
                        try:
                            shutil.move(os.path.join(f"{dir}", f"{file}"), sorter_dir[0])
                        except FileNotFoundError:
                            pass
                    except OSError:
                        shutil.move(os.path.join(f"{dir}", f"{file}"), sorter_dir[0])

            elif os.path.isdir(f'{dir}/{file}'):
                extract(f'{dir}/{file}')


def list_season(dir):
    ls = []
    for file in os.listdir(dir):
        if os.path.isdir(f"{dir}/{file}"):
            if "Season" in file:
                ls.append({f"{dir}/{file}": list_season(f"{dir}/{file}")})
            else:
                ls += list_season(f"{dir}/{file}")

        elif os.path.isfile(os.path.join(f"{dir}", f"{file}")) and ("mp4" in file or "mkv" in file):
            ls.append(file)
    return ls


###specific to database.py ############
def ep_file(file):
    print(file)
    if " - " in file:
        return file.split(" - ")[1]


# def merge(folder1, folder2):
#     """move file from 2 to 1"""
#     if folder1 == folder2:
#         return
#     list_folder1 = os.listdir(folder1)
#     list_folder2 = os.listdir(folder2)
#     for file in list_folder2:
#         # fichier en double non video
#         if file in list_folder1 and not os.path.isdir(os.path.join(folder2, file)) and "mkv" not in file and "mp4" not in file:
#             print("not ep" + " " + file)
#             os.remove(os.path.join(folder2, file))
#         # fichier pas en double et non video
#         elif file not in list_folder1 and not os.path.isdir(os.path.join(folder2, file)) and "mkv" not in file and "mp4" not in file:
#             print(os.path.join(folder2, file) + " -----> " + folder1 + "/" + file)
#             shutil.move(os.path.join(folder2, file), os.path.join(folder1, file))
#         # dossier pas en double
#         elif os.path.isdir(os.path.join(folder2, file)) and file not in list_folder1:
#             print(os.path.join(folder2, file) + " -----> " + os.path.join(folder1, file))
#             try:
#                 print(os.path.join(folder2, file))
#                 shutil.move(os.path.join(folder2, file), os.path.join(folder1, file))
#             except:
#                 pass
#             print("dossier " + file)
#         # dossier en double
#         elif os.path.isdir(os.path.join(folder2, file)) and file in list_folder1:
#             merge(os.path.join(folder1, file), os.path.join(folder2, file))
#         # episode
#         elif "mkv" in file or "mp4" in file:
#             if list_folder1 != NoneType:
#                 for file_folder1 in list_folder1:
#                     if ep_file(file) == ep_file(file_folder1):
#                         try:
#                             print(file + " remove")
#                             os.remove(os.path.join(folder2, file))
#                         except FileNotFoundError:
#                             pass
#                         except:
#                             pass
#                     else:
#                         try:
#                             print(os.path.join(folder2, file) + " -----> " + os.path.join(folder1, file))
#                             shutil.move(os.path.join(folder2, file), os.path.join(folder1, file))
#                         except FileNotFoundError:
#                             pass

#     try:
#         open(os.path.join(VAR_DIR, "delete.txt"), "a").write(folder2 + "\n")
#         print(f"deleting {folder2}")
#         shutil.rmtree(folder2)
#     except:
#         pass


def list_anime():
    """liste les different anime ainsi que les dossier correspondant"""
    log(f"DATABASE: SCANNING LIBRARY")
    dic = {}
    for dir in anime_dir:
        for file in os.listdir(dir):
            if os.path.isdir(os.path.join(dir, file)):
                try:
                    title = Anime(file).title
                    if title in dic.keys():
                        dic[title].append(os.path.join(dir, file))
                    else:
                        dic[title] = [os.path.join(dir, file)]
                except IndexError:
                    print(f"[WARNING] can't determine {file}")
                except requests.exceptions.JSONDecodeError:
                    print(f"[WARNING] can't determine {file}")
                except requests.exceptions.ConnectTimeout:
                    print(f"[WARNING] can't determine {file}")

    return dic


# def determine_merge(dico: dict, dir) -> None:
#     for keys in dico.keys():
#         os.makedirs(os.path.join(dir, forbiden_car(keys)), exist_ok=True)
#         print(keys, dico[keys])
#         if len(dico[keys]) > 1:
#             for values in dico[keys]:
#                 try:
#                     merge(os.path.join(dir, forbiden_car(keys)), f"{values}")
#                 except FileNotFoundError:
#                     pass
#         else:
#             if dico[keys][0].split("/")[-1] != forbiden_car(keys):
#                 try:
#                     print("path changed")
#                     new = "/".join(dico[keys][0].split("/")[:-1] + [forbiden_car(keys)])
#                     os.rename(dico[keys][0], new)
#                 except FileExistsError:
#                     pass


def delete_duplicate() -> None:
    # use os.path.getctime() to choose between duplicate
    ls = []
    # try:
    for dir in anime_dir:
        for anime in os.listdir(dir):
            try:
                ls = list_season(os.path.join(dir, anime))[0]

                ep = {}
                for elt in ls:

                    for file in ls[elt]:
                        if " -  -Strange" in file:
                            os.remove(f"{elt}/{file}")
                            pass
                        elif " - SEhe - " in ls:
                            os.remove()
                            pass


                        elif not file.split(" - ")[1].split("E")[-1].strip() in ep.keys():
                            ep[file.split(" - ")[1].split("E")[-1].strip()] = f"{elt}/{file}"
                        else:
                            if os.path.getsize(ep[file.split(" - ")[1].split("E")[-1].strip()]) <= os.path.getsize(
                                    os.path.join(elt, file)):
                                ep[file.split(" - ")[1].split("E")[-1].strip()] = os.path.join(elt, file)
                            elif os.path.getctime(ep[file.split(" - ")[1].split("E")[-1].strip()]) >= os.path.getctime(
                                    os.path.join(elt, file)):
                                ep[file.split(" - ")[1].split("E")[-1].strip()] = os.path.join(elt, file)
                            else:
                                os.remove(os.path.join(elt, file))
                                print(f"del {file}")
            except IndexError:
                pass
            except FileNotFoundError:
                pass


def update_anime():
    json.dump(list_anime(), open(os.path.join(VAR_DIR, "anime_lib.json"), "w"))
    return json.load(open(os.path.join(VAR_DIR, "anime_lib.json"), "r"))


def check_double():
    """merge anime folder and delete double episode"""
    dic = update_anime()  ### update needed
    try:
        determine_merge(dic, anime_dir[0])

    except:
        if len(anime_dir) > 1:
            determine_merge(dic, anime_dir[1])
    finally:
        delete_duplicate()
        update_anime()


def find_anime_dir(anime: str):
    anime = title_to_romaji(anime)
    for dir in anime_dir:
        for file in os.listdir(dir):
            if anime == title_to_romaji(file):
                return f"{dir}/{file}"
    return None


def get_source(anime: str):
    """return sources if in file name else return None"""
    if "/" not in anime or "\\" not in anime:
        dir, r = find_anime_dir(anime), None
        if dir == "no dir":
            return
    else:
        dir = anime
    for file in os.listdir(dir):
        if os.path.isdir(f"{dir}/{file}") and "Season " in file:
            return get_source(f"{dir}/{file}")
        elif ("mkv" in file or "mp4" in file) and file != "theme.mp4":
            try:
                r = file.split(" -")[-1].split(".")[0].strip()
            except:
                pass
            if r in ["Strange-encoded", "Strange"]:
                return
            return r


def get_nyaajson():
    return json.load(open(os.path.join(VAR_DIR, "nyaa.json"), "r"))


def insert_nyaajson(database):
    json.dump(database, open(os.path.join(VAR_DIR, "nyaa.json"), "w"), indent=4)


def get_animeid():
    return json.load(open(os.path.join(VAR_DIR, "anime_id.json"), "r"))


def insert_animeid(database):
    json.dump(database, open(os.path.join(VAR_DIR, "anime_id.json"), "w"), indent=4)


def get_title_database():
    return json.load(open(os.path.join(VAR_DIR, "anime_titles_database.json"), "r"))


def insert_title_databse(database):
    json.dump(database, open(os.path.join(VAR_DIR, "anime_titles_database.json"), "w"), indent=4)


def store_nyaa(result: dict):
    database = get_nyaajson()
    for keys in result.keys():
        if not keys in database.keys():
            database[keys] = result[keys]
    insert_nyaajson(database)


def find_anime_id(title):
    anime_id = get_animeid()
    anime = title_to_romaji(title)

    if anime not in anime_id.keys():
        anime_id[anime] = Anime(anime).id
        insert_animeid(anime_id)
        return anime_id[anime]
    else:
        for keys in anime_id:
            if keys == anime:
                return anime_id[keys]


def find_alternative_title(title):
    id = str(find_anime_id(title))
    anime_titles_database = get_title_database()
    if id not in anime_titles_database.keys():
        anime_titles_database[id] = [i for i in tmdb.tv.TV(id).alternative_titles()["results"] if
                                     i["iso_3166_1"] in ["JP", "MX", "PL", "US"]]
        insert_title_databse(anime_titles_database)
        return anime_titles_database[id]
    else:
        for keys in anime_titles_database:
            if keys == id:
                return anime_titles_database[keys]


def prepare_url(search):
    ban = "+".join([f"-{i}" for i in banned_words])
    sel = "+".join(select_words)
    return f"{search}+{ban}+{sel}"


def get_missing():
    return json.load(open(os.path.join(VAR_DIR, "missing.json"), "r"))


def insert_missing(database):
    json.dump(database, open(os.path.join(VAR_DIR, "missing.json"), "w"), indent=4)


def database_check():
    dic = get_animeid()
    missing = {}
    for keys in dic:
        ls = []

        anime = Anime(keys)

        for nb in range(1, anime.number_of_season + 1):
            for dir in dic[keys]:
                os.makedirs(f"{dir}/Season {nb:02}", exist_ok=True)

            # checking season and all ep
            try:
                season_info = tmdb.TV_Seasons((anime.tmbd.id), nb).info()
            except requests.exceptions.HTTPError:
                break
            if nb == anime.number_of_season:
                try:
                    last_ep = tmdb.TV(find_anime_id(keys)).info()["last_episode_to_air"]["episode_number"]
                    season_ep = [f"{k:02}" for k in [i for i in range(1, len(season_info["episodes"]) + 1)] if
                                 k <= last_ep]
                except TypeError:
                    season_ep = tmdb.TV_Seasons((anime.tmbd.id), nb).info()["episodes"]
                except requests.exceptions.JSONDecodeError:
                    break
                except json.decoder.JSONDecodeError:
                    break
                except requests.exceptions.HTTPError:
                    break
            else:
                season_ep = tmdb.TV_Seasons((anime.tmbd.id), nb).info()["episodes"]
            y, z = [os.listdir(f'{k}/Season {nb:02}') for k in dic[keys]], []
            for file in y:
                z += file
            current_ep = [i.split(" - ")[1].split("E")[-1] for i in z if ".mkv" in i or ".mp4" in i]
            if len(current_ep) == len(season_ep):
                pass
            elif len(current_ep) == 0:
                ls.append("S" + str(nb))
            elif len(current_ep) < len(season_ep):

                for epi in [f"{i:02}" for i in range(1, len(season_ep) + 1)]:
                    if epi in current_ep:
                        pass
                    else:
                        ls.append(f"S{nb:02}E{epi}")
        if ls != []:
            print(f"Missing ep are: " + ",".join(ls))
            missing[anime.title] = ls

    insert_missing(missing)


def download_torrent(url: str, file_name) -> None:
    if f"{forbiden_car(file_name)}.torrent" not in os.listdir(os.path.join(install_dir, "torrent")):
        torrent = requests.request("GET", url)
        os.makedirs(f"{install_dir}/torrent", exist_ok=True)
        open(f"{install_dir}/torrent/{forbiden_car(file_name)}.torrent", "wb").write(torrent.content)
        time.sleep(1)


def check_nyaa_database(anime: str, season, ep_number: list) -> tuple:
    database = get_nyaajson()
    anime = title_to_romaji(anime)
    for keys in database.keys():
        try:
            info = LightFile(keys)
        except IndexError:
            break
        if info.ep in ep_number and info.season == season:
            if info.title() == anime and keys != None:
                return database[keys], keys
    return None, None


def get_source():
    return open(os.path.join(VAR_DIR, "sources.txt"), "r").read().split("\n")


def insert_source(database):
    json.dump(database, open(os.path.join(VAR_DIR, "sources.txt"), "w"), indent=4)


def search_ep(anime: str, season: str, ep_number: list):
    check, file = check_nyaa_database(anime, season, ep_number)
    if check != None:
        download_torrent(check, file_name=file)
        log(f"DATABASE: {file} downloaded via nyaa.json")
        return
    elif ep_number == []:
        return
    else:
        anime_source, anime_list = sources, find_alternative_title(anime) + [{"title": anime}]
        prefered_source = get_source(anime_list[0]["title"])
        if prefered_source != None:
            anime_source = [i for i in get_source() if prefered_source in i]
        for anime in anime_list:
            a = "|".join(['"' + anime["title"].replace(" ", "+") + '"' for anime in anime_list])
        for source in anime_source:
            if season == "01":
                url = source.replace("##search##", prepare_url(f"{a}"))
            else:
                s = season.replace("0", "")
                url = source.replace("##search##", prepare_url(f"{a}+{s}"))
            r = FeedAnime(url, banned_words, select_words)
            time.sleep(2)
            for keys in r.ep:
                file = File(keys)
                if ep_number == ["S"]:
                    if file.title == title_to_romaji(anime["title"]) and file.season == season:
                        download_torrent(r.ep[keys], file_name=keys)

                        log(f"DATABASE: {keys} downloaded via nyaa.si")

                elif ep_number != [] and file.title == title_to_romaji(
                        anime["title"]) and file.episode in ep_number and file.season == season:
                    download_torrent(r.ep[keys], file_name=keys)
                    ep_number.pop(ep_number.index(file.episode))
                    log(f"DATABASE: {keys} downloaded via nyaa.si")
        if ep_number != []:
            for source in sources:
                if season == "01":
                    url = source.replace("##search##", f"{a}")
                else:
                    s = season.replace("0", "")
                    url = source.replace("##search##", f"{a}+{s}")
                r = FeedAnime(url, banned_words, select_words)
                time.sleep(2)
                for keys in r.ep:
                    file = File(keys)
                    if ep_number != [] and file.title == title_to_romaji(
                            anime["title"]) and file.episode in ep_number and file.season == season:
                        download_torrent(r.ep[keys], file_name=keys)
                        ep_number.pop(ep_number.index(file.episode))
                        log(f"DATABASE: {keys} downloaded via nyaa.si")


def download_missing_ep(missing: dict):
    log(f"DATABASE: Searching missing episode")
    for keys in missing.keys():
        if len(missing[keys]) > 24:
            pass
        else:
            dic = {}
            # print(keys,missing[keys])
            for ep in missing[keys]:
                if len(ep) in [3, 2]:
                    dic[ep.split("S")[-1]] = ["S"]
                elif ep.split("S")[-1].split("E")[0] not in dic.keys():
                    dic[ep.split("S")[-1].split("E")[0]] = [ep.split("S")[-1].split("E")[-1]]
                elif ep.split("S")[-1].split("E")[-1] not in dic[ep.split("S")[-1].split("E")[0]]:
                    dic[ep.split("S")[-1].split("E")[0]].append(ep.split("S")[-1].split("E")[-1])
            for season in dic:
                # print(f"Missing ep for S{season} are : "+",".join(["S"+season+"E"+i for i in dic[season]]))
                try:
                    search_ep(keys, season, dic[season])
                except IndexError as e:
                    pass


def time_log():
    # Get the current time
    current_time = datetime.datetime.now()
    datetime.datetime.now().strftime("%H")

    # Format the time as a string with the hour, minute, and second
    return current_time.strftime("%H:%M:%S")


def get_anime_lib():
    return json.load(open(os.path.join(VAR_DIR, "anime_lib.json"), "r"))


def insert_source(database):
    json.dump(database, open(os.path.join(VAR_DIR, "anime_lib.json"), "w"), indent=4)


def already_in_folder(file: str, dir: list | None | str = None):
    if dir == None:
        t = title_to_romaji(File(file).title)
        ls_lib = get_anime_lib()
        try:
            dir = [ls_lib[anime] for anime in ls_lib if t == anime][-1]
        except IndexError:
            os.makedirs(f"{anime_dir[0]}/{forbiden_car(LightFile(file).title())}", exist_ok=True)

            return []
    ls = []
    try:
        ep = file.split(" - ")[1]
    except:
        ep = LightFile(file)
        ep = ep.__str__().split(" - ")[1]
    if type(dir) == list:
        for dirs in dir:
            for episode in os.listdir(dirs):
                if os.path.isdir(f"{dirs}/{episode}"):
                    for file in os.listdir(f"{dirs}/{episode}"):
                        try:
                            if ep == file.split(" - ")[1]:
                                ls.append(f"{dirs}/{episode}/{file}")
                        except:
                            pass

                try:
                    if ep == episode.split(" - ")[1]:
                        ls.append(f"{dir}/{episode}")
                except:
                    pass
    elif type(dir) == str:
        for file in os.listdir(dir):
            print(file)
            try:
                if ep == file.split(" - ")[1]:
                    ls.append(f"{dir}/{file}")
            except:
                pass

    return ls


def isolate_quote(file) -> list:
    contain, ls = "", []
    while file[0] != "(":
        print(file)
        file = file[1:]
    while file[0] != ")":
        contain += file[0]
        file = file[1:]
    ls.append(contain)
    if "(" in file and ")" in file:
        return ls + isolate_quote(file)
    else:
        return ls


def judas_season(file):
    file = [i for i in isolate_quote(file) if "Season " in i or "Saison " in i]
    return [car for car in "".join(file) if car in [str(i) for i in range(0, 10)]]


def get_judas_vostfr():
    return open(os.path.join(VAR_DIR, "judas_vostfr.txt"), "r", encoding="utf-8").read().split("\n")


def get_judas_not_vostfr():
    return open(os.path.join(VAR_DIR, "judas_not_vostfr.txt"), "r", encoding="utf-8").read().split("\n")


def insert_judas_vostfr(path_to_anime_dir):
    open(os.path.join(VAR_DIR, "judas_vostfr.txt"), "a").write(path_to_anime_dir + "\n")


def insert_judas_not_vostfr(path_to_anime_dir):
    open(os.path.join(VAR_DIR, "judas_not_vostfr.txt"), "a").write(path_to_anime_dir + "\n")


def judas_is_vostfr(path_to_anime_dir):
    try:
        shutil.rmtree("test")
    except:
        pass

    for file in os.listdir(path_to_anime_dir):
        if "mkv" in file:
            judas_download_ep(f"{path_to_anime_dir}/{file}", f"test")
            statut = Episode(f"{path_to_anime_dir}/{file}").is_vostfr()
            os.remove(f"{path_to_anime_dir}/{file}")
            if statut:
                insert_judas_not_vostfr(path_to_anime_dir)
            else:
                insert_judas_vostfr(path_to_anime_dir)
            return statut


def judas_download_ep(src, dest):
    try:
        os.makedirs(dest, exist_ok=True)
        dest_name = src.split("/")[-1]
        with open(src, "rb") as f:
            open(f"{dest}/{dest_name}", "wb").write(f.read())
    except OSError:
        pass
    except NotADirectoryError:
        pass


def have_judas(anime) -> bool:
    """True if judas otherwise False"""
    if "/" not in anime or "\\" not in anime:
        dir, r = find_anime_dir(anime), None
    else:
        dir = anime
    # print(dir)
    if dir == None:
        return False
    statut = True
    for file in os.listdir(dir):
        # print(file)
        if os.path.isdir(f"{dir}/{file}") and "Season " in file:
            src = have_judas(f"{dir}/{file}")
            if src == True:
                pass
            else:
                return False
        elif ("mkv" in file or "mp4" in file) and file != "theme.mp4":
            try:
                r = file.split(" -")[-1].split(".")[0].strip()
            except:
                pass
            if r != "Judas":
                return False
    return statut


def download_judas_anime(title):
    title, judas = title_to_romaji(title), "G:\Drive partagés\Judas - DDL 1\Judas - DDL"
    for dir in os.listdir(judas):
        for anime in os.listdir(f'{judas}/{dir}'):
            if "Movie" in anime:
                pass
            else:
                temp = anime
                for banned_car in [("[", "]"), ("{", "}"), ("(", ")")]:
                    car1, car2 = banned_car
                    try:
                        temp = car_to_car(temp, car1, car2)
                    except:
                        pass
                print(temp)
                if title == title_to_romaji(temp):
                    for file in os.listdir(f'{judas}/{dir}/{anime}'):
                        judas_download_ep(f'{judas}/{dir}/{anime}/{file}', )
                    break


def judas_google_drive():
    print(os.listdir("G:\Drive partagés\Judas - DDL 1\Judas - DDL\[Judas] Webrip batches"))


def get_judas_anilib():
    return json.load(open(os.path.join(VAR_DIR, "judas_anime_lib.json"), "w"), indent=4)


def insert_judas_anilib(databse):
    json.dump(databse, open(os.path.join(VAR_DIR, "judas_anime_lib.json"), "w"), indent=4)


def list_judas_anime(path="G:\Drive partagés\Judas - DDL 1\Judas - DDL"):
    print("Scanning Judas anime")
    dic = {}
    for dir in os.listdir(path):
        for file in os.listdir(f"{path}/{dir}"):
            temp = file
            for banned_car in [("[", "]"), ("{", "}"), ("(", ")")]:
                car1, car2 = banned_car
                try:
                    temp = car_to_car(temp, car1, car2)
                except:
                    pass
            t = title_to_romaji(temp)

            if t in dic.keys():
                dic[t].append(f"{path}/{dir}/{file}")
            else:
                dic[t] = [f"{path}/{dir}/{file}"]
    insert_judas_anilib(dic)


def global_dir(directories: list) -> list:
    """return a list of all file off all directories"""
    ls = []
    for dir in directories:
        for file in os.listdir(dir):
            path = f"{dir}/{file}"
            if os.path.isdir(path):
                ls = ls + global_dir([path])
            else:
                ls.append(f"{dir}/{file}")
    return ls


def delete_duplicate():
    dic = update_anime()
    for anime in dic.keys():
        liste_ep = []

        for file in global_dir(dic[anime]):

            if ("mkv" in file or "mp4" in file) and "Judas" in file:
                ep = LightFile(file).__str__().split(" - ")[1]
                if ep not in liste_ep:
                    liste_ep.append(ep)
                else:
                    print("remove " + file)
                    os.remove(file)
        for file in global_dir(dic[anime]):
            if ("mkv" in file or "mp4" in file) and "Judas" not in file:
                ep = LightFile(file).__str__().split(" - ")[1]
                if ep not in liste_ep:
                    liste_ep.append(ep)
                else:
                    print("remove " + file)
                    os.remove(file)


###################################
##############CLASS################
###################################

class Anime:
    """Provide a view on the anime"""

    def __init__(self, title) -> None:
        search = tmdb.Search()
        try:
            os.makedirs(os.path.join(VAR_DIR, "anime_database"), exist_ok=True)
        except PermissionError:
            print("WARNING can't determine existance of anime_database in /var/lib/my-server")
        try:
            if not f"{title}.json" in os.listdir(os.path.join(VAR_DIR, "anime_database")):
                self.__id = search.tv(query=title)
                self.__id = search.results[0]['id']
                self.__tmbd = tmdb.TV(self.id)
                self.__info = self.__tmbd.info()
            else:
                with open(os.path.join(VAR_DIR, f"anime_database", f"{title}.json"), "r") as f:
                    try:
                        self.__info = json.load(f)
                    except json.decoder.JSONDecodeError:
                        f.close()
                        try:

                            os.remove(os.path.join(f"anime_database", f"{title}.json"))
                        except FileNotFoundError:
                            pass
                        self.__init__(title)
                        return

                    self.__id = self.info['id']

            self.__title = self.info["name"]
            self.__season = self.info["number_of_seasons"]
            self.__ep = self.info["number_of_episodes"]
            try:
                with open(os.path.join(VAR_DIR, f"anime_database", f"{forbiden_car(self.title)}.json"), "w") as f:
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


class Episode:

    def is_vostfr(self) -> bool:
        tracks = self.tracks()
        return "fr" in tracks["subs"] and "ja" in tracks["audio"]

    def video_spec(self) -> dict:
        """Retourne un dictionnaire contenant toute les information lier à une piste vidéo"""
        media_info = self.media_info
        for track in media_info.tracks:
            if track.track_type == "Video":
                return track.to_data()

        return {}

    def tracks(self):
        media_info = self.media_info
        tracks_list_subs = []
        tracks_list_audio = []
        for track in media_info.tracks:

            if track.track_type == "Audio":
                try:
                    tracks_list_audio.append(track.to_data()["language"])
                except KeyError:
                    tracks_list_audio.append("ja")

            if track.track_type == "Text":

                try:
                    tracks_list_subs.append(track.to_data()["language"])
                except KeyError:
                    try:
                        tracks_list_subs = tracks_list_subs + track.to_data()["other_language"]
                    except KeyError:
                        try:
                            if "FR" in track.to_data()["title"] or "fr" in track.to_data()["title"] or "Fr" in \
                                    track.to_data()["title"] or "francais" in track.to_data()["title"] or "français" in \
                                    track.to_data()["title"] or "Français" in track.to_data()["title"] or "french" in \
                                    track.to_data()["title"] or "French" in track.to_data()["title"]:
                                tracks_list_subs.append("fr")
                        except:
                            pass

            if track.track_type == "Menu":

                try:
                    tracks_list_subs.append(track.to_data()["language"])
                except KeyError:
                    pass

        return {"subs": tracks_list_subs, "audio": tracks_list_audio}

    def extension(self):
        if ".mp4" in self.path:
            return "mp4"
        elif ".mkv" in self.path:
            return "mkv"

    def __init__(self, path) -> None:
        self.path = path

    def __repr__(self) -> str:

        return self.path

    def info(self):
        dic = {
            "path": self.path
            , "track": self.track,
            "extension": self.ext,
            "codec": self.codec}
        return dic


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


class File():
    def determine_source(self) -> str:
        """return the source of a video from it's file name"""
        title, source = self.file_name, ""
        if "[" == title[0] and "]" in title:
            while title[0] != "[":
                title = title[1:]
            title = title[1:]
            while title[0] != "]":
                source = source + title[0]
                title = title[1:]
            return source
        try:
            r = title.split(" -")[-1].split(".")[0].strip()
            return r
        except:

            return "Strange"

    def determine_season(self) -> str:
        """return the season of a video file from it's title"""
        file, ls = self.file_name, []
        file = file.replace(".mp4", "").strip()

        for banned_car in [("[", "]"), ("{", "}"), ("(", ")")]:
            car1, car2 = banned_car
            file = car_to_car(file, car1, car2)
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

    def determine_language(self) -> str:
        if "vf" in self.file_name.lower() and "vostfr" in self.file_name.lower():
            return "VF/VOSTFR"

        elif "vf" in self.file_name.lower():
            return "VF"
        elif "vostfr" in self.file_name.lower():
            return "VOSTFR"

        else:
            if not self.tracks == {}:
                if "ja" in self.tracks["audio"] and self.tracks["subs"] == []:
                    return "VOSTFR"
                if "fr" in self.tracks["subs"] and "ja" in self.tracks["audio"] and "fr" in self.tracks["audio"]:
                    return "VF/VOSTFR"
                elif "fr" in self.tracks["subs"] and "ja" in self.tracks["audio"]:
                    return "VOSTFR"
                elif "fr" in self.tracks["audio"]:
                    return "VF"

                return "UKNOWNLANG"

    def determine_ep(self) -> str:
        """return the ep of a video file from it's title"""
        file, ls, temp = self.file_name, [], None
        file = file.replace(".mp4", "").strip()
        for banned_car in [("[", "]"), ("{", "}"), ("(", ")")]:
            car1, car2 = banned_car
            file = car_to_car(file, car1, car2)
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

    def determine_encode(self) -> str:
        lencode = ["h264", "x264", "avc1", "h.264"]
        hencode = ["hevc", "h265", "x265", "hvc1", "h.265"]
        for encode in lencode:
            if encode in self.file_name.lower():
                return "h264"
        for encode in hencode:
            if encode in self.file_name.lower():
                return "h265"
        try:
            codec = self.__video_spec["codec_id"].lower()
            for encode in hencode:
                if encode in codec:
                    return "h265"
            for encode in lencode:
                if encode in codec:
                    return "h264"
        except KeyError:
            return "unknown"

        return codec

    def determine_resolution(self):
        if "1080" in self.file_name:
            return "1080"
        elif "720" in self.file_name:
            return "720"
        elif "480" in self.file_name:
            return "480"
        else:
            try:
                return self.video_spec["height"]
            except KeyError:
                return "no resolution"

    def determine_extension(self) -> str:
        if "mp4" in self.file_name or "mkv" in self.file_name:
            return self.file_name.split(".")[-1]
        else:
            return "mkv"

    def determine_title(self) -> str:
        """return the title of a video"""
        file = self.file_name.replace(".", " ", -2)
        for banned_car in [("[", "]"), ("{", "}"), ("(", ")")]:
            car1, car2 = banned_car
            file = car_to_car(file, car1, car2)
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
            return file.strip()

        temp_file, index = file, None
        while "S" in temp_file:
            if "S" in temp_file and temp_file.index("S") + 3 < len(file) and temp_file[temp_file.index("S") + 3] == "E":
                index = temp_file.index("S")
                break
            elif "S" in temp_file:
                temp_file = temp_file.replace("S", " ", 1)
        if index != None:
            return file[:index].strip()
        for car in file:
            if car in [str(i) for i in range(10)]:
                return file.split(car)[0].strip()
        return file.split(" ")[0]

    def __init__(self, path_to_file: str) -> None:
        self.__path = path_to_file
        try:
            self.__spec = Episode(self.path)
            self.__tracks = self.__spec.tracks()
            self.__video_spec = self.__spec.video_spec()
        except FileNotFoundError:
            self.__spec = None
            self.__tracks = {}
            self.__video_spec = {}
            self.__resolution = "no resolution"
        except OSError:
            self.__spec = None
            self.__tracks = {}
            self.__video_spec = {}
            self.__resolution = "no resolution"

        self.__file_name = os.path.basename(path_to_file)
        self.__season = self.determine_season()
        self.__ep = self.determine_ep()
        self.__title = title_to_romaji(self.determine_title())
        self.__src = self.determine_source()
        self.__codec = self.determine_encode()
        self.__ext = self.determine_extension()
        self.__lang = self.determine_language()
        self.__resolution = self.determine_resolution()

    def __str__(self) -> str:
        return f"{self.title} - S{self.season}E{self.episode} - [{self.lang} {self.codec} {self.__resolution}p] -{self.source} .{self.ext}"

    @property
    def path(self) -> str:
        return self.__path

    @path.setter
    def set_path(self, x: str) -> None:
        if type(x) == str and "/" in x:
            self.__path = x
        else:
            raise ValueError("Argument must be a path to a file")

    @property
    def file_name(self) -> str:
        return self.__file_name

    @file_name.setter
    def set_file_name(self, x: str) -> None:
        if type(x) == str and ".m" in x:
            self.__file_name = x
        else:
            raise ValueError("file_name must be a video with mp4 ou mkv as extension")

    @property
    def title(self) -> str:
        return self.__title

    @title.setter
    def set_title(self, x: str) -> None:
        if type(x) == str:
            self.__title = x
        else:
            raise ValueError("title must be str")

    @property
    def source(self) -> str:
        return self.__src

    @source.setter
    def set_source(self, x: str) -> None:
        if type(x) == str:
            self.__src = x
        else:
            raise ValueError("source must be str")

    @property
    def season(self) -> str:
        return self.__season

    @season.setter
    def set_season(self, x: str) -> None:
        if type(x) == str:
            self.__season = x
        else:
            raise ValueError("season must be a str")

    @property
    def episode(self) -> str:
        return self.__ep

    @episode.setter
    def set_episode(self, x):
        if type(x) == str:
            for car in x:
                if car not in [str(i) for i in range(0, 10)]:
                    raise ValueError("all character must be betewenn 0 and 9")
            self.__ep = x
        elif type(x) == int and x >= 0:
            self.__ep = str(x)
        else:
            raise ValueError('episode is a number')

    @property
    def codec(self) -> str:
        return self.__codec

    @codec.setter
    def set_codec(self, x) -> None:
        if x in ["h264", "hevc", "hvc1", "x264", "x264"]:
            self.__codec = x
        else:
            raise ValueError("Le codec doit être h265 ou h264")

    @property
    def ext(self) -> str:
        return self.__ext

    @ext.setter
    def set_ext(self, x: str) -> None:
        if type(x) == str:
            self.__ext = x
        else:
            raise ValueError("ext must be a str")

    @property
    def lang(self):
        return self.__lang

    @lang.setter
    def set_lang(self, x) -> None:
        if type(x) == str:
            self.__lang = x
        else:
            raise ValueError("language is str")

    @property
    def video_spec(self) -> dict:
        return self.__video_spec

    @property
    def tracks(self) -> dict:
        return self.__tracks


class FeedAnime():
    # utiliser classe File
    def analyse_titles(self) -> dict:
        dict, new_dictt = deepcopy(self.filtered_ep), {}
        for key in dict:
            analasing = LightFile(key)
            new_dictt[analasing.__str__()] = dict[key]
        already_in, newdict = [], {}
        for keys in new_dictt:
            if "MOVIE" in keys:
                pass
            elif not keys[:-4].strip() in already_in:
                newdict[keys] = new_dictt[keys]
                already_in.append(keys[:-4].strip())

        return newdict

    def get_ep_with_link(self):
        dicto = {}
        for entry in self.feed.entries:
            dicto[entry.title] = entry.link
        return dicto

    def filtre(self, banned_words: list, select_word: list) -> dict:
        dicto = deepcopy(self.__ep_link)
        for title in self.__ep_link:
            selected = True
            for select in select_word:
                if select in title or select == '':
                    selected = True
                    break
                else:
                    selected = False
            if not selected:
                dicto.pop(title)
        dictoo = deepcopy(dicto)
        for title in dicto:
            for banned in banned_words:
                if banned in title and banned != '':
                    dictoo.pop(title)
                    break
        return dictoo

    def __init__(self, url: str, banned_words: list, select_words: list) -> None:
        self.__url = url

        self.__feed = feedparser.parse(self.url)

        self.__ep_link = self.get_ep_with_link()

        store_nyaa(self.__ep_link)
        self.__filered_ep = self.filtre(banned_words, select_words)

        self.__ep = self.analyse_titles()

    @property
    def url(self) -> str:
        return self.__url

    @url.setter
    def set_url(self, url: str) -> None:
        if type(url) == str and 'http' in url:
            self.__url = url

    @property
    def feed(self):
        return self.__feed

    @property
    def filtered_ep(self) -> dict:
        return self.__filered_ep

    @property
    def ep(self):
        return self.__ep


def get_rss():
    return open(os.path.join(VAR_DIR, "rss.txt"), "r", encoding="utf-8").read().split("\n")


def get_already_download():
    return open(os.path.join(VAR_DIR, "already_download.txt"), "r", encoding="utf-8").read().split("\n")


def insert_already_download(file_name):
    open(os.path.join(VAR_DIR, "already_download.txt"), "a", encoding="utf-8").write(f'{file_name}\n')


def downloader():
    for url in get_rss():
        feed = FeedAnime(url, banned_words, select_words)
        for episode in feed.ep:

            try:
                file_name = LightFile(episode).__str__()

            except:
                pass
            if file_name in get_already_download():
                pass

            elif already_in_folder(file_name) not in [[], None]:
                insert_already_download(file_name)
            else:
                insert_already_download(file_name)
                r = requests.request("GET", feed.ep[episode])
                open(os.path.join(install_dir, f"torrent/{forbiden_car(episode)}.torrent"), "wb").write(r.content)
                print(f"DOWNLOADER: {episode} ADDED")
                log(f"DOWNLOADER: {episode} ADDED")


def sorter():
    get_anime()
    for dir in sorter_dir:
        if "" in dir:  # remplacer par une fonction qui evalue la place restante
            move_dir = anime_dir[0]
        elif len(anime_dir) > 1000:
            move_dir = anime_dir[1]

        for file in os.listdir(dir):
            if ".mkv" in file or ".mp4" in file:
                sorting = File(f'{dir}/{file}')
                title = forbiden_car(sorting.title)
                os.makedirs(f"{move_dir}/{title}/Season {sorting.season}", exist_ok=True)
                for file_dup in already_in_folder(file):
                    os.remove(file_dup)
                    log(f"DATABASE: {file_dup} REMOVED (duplicate)")
                try:

                    shutil.move(f"{dir}/{file}",
                                f"{move_dir}/{title}/Season {sorting.season}/{forbiden_car(sorting.__str__())}")


                except FileExistsError:
                    os.remove(f"{move_dir}/{title}/Season {sorting.season}/{forbiden_car(sorting.__str__())}")
                    print(f"{file} already in so replaced by the newer one")
                    shutil.move(f"{dir}/{file}",
                                f"{move_dir}/{title}/Season {sorting.season}/{forbiden_car(sorting.__str__())}")
                except FileNotFoundError:
                    log(f"SORTER [WARNING]: {file} error while moving")
                finally:
                    logs = f"SORTER: {sorting.__str__()} ADDED TO LIBRARY"
                    log(logs)
                    print(logs)

            elif os.path.isdir(f"{dir}/{file}"):
                extract(f"{dir}/{file}")


def check_integrity():
    update_anime()
    database_check()
    download_missing_ep(get_missing())


def check_judas() -> None:
    delete_duplicate()
    anime_lib = get_anime_lib()

    list_judas_anime()
    judas_lib = get_judas_anilib()

    for anime in anime_lib:
        if anime in judas_lib.keys():
            if "Movie" in ["Movie" for i in judas_lib[anime] if "Movie" in i]:
                pass
            elif have_judas(anime) != True:
                liste_ep = []
                for dir in judas_lib[anime]:
                    if "One Piece" in dir:
                        pass
                    elif os.path.isdir(dir):
                        if judas_is_vostfr(dir) == True:
                            print(f"{anime} matching")
                            print("Searching for episode with better encode ...")

                            judas_ls_ep = [f.split(" - ")[1] for f in global_dir(anime_lib[anime]) if
                                           ("mkv" in f or "mp4" in f) and "Judas" in f]

                            for file in os.listdir(dir):
                                file_name = LightFile(file).__str__()

                                # if file_name.__str__() in os.listdir(find_anime_dir(dir.split("/")[-1])):
                                if file_name.split(" - ")[1] in judas_ls_ep:
                                    pass
                                elif ("mp4" in file or "mkv" in file) and liste_ep.append(
                                        file_name.split(" - ")[1]) not in liste_ep:
                                    try:
                                        judas_download_ep(f"{dir}/{file}", temp_dir)
                                        shutil.move(f"{temp_dir}/{file}", download_dir[1])
                                        print(f"{file} downloaded")
                                        log(f"JUDAS: {file} downloaded")
                                        liste_ep.append(file_name.split(" - ")[1])
                                    except OSError:
                                        log(f"JUDAS : (WARNING) An error occured for {file}")


# def main():

#     print(f"[{time_log()}] MAIN: SERVER STARTED")
#    # subprocess.Popen(f"{PYTHON} API.py", shell=True)


#     print(f"[{time_log()}] MAIN: WAITING FOR EVENTS")
#     while True:
#         date = datetime.datetime.now()
#         downloader()
#         for dir in download_dir:
#             if os.listdir(dir) != []:
#                 sorter()
#         if date.strftime('%H') == "04":
#             check_integrity()
#             check_judas()
#                 #t = subprocess.Popen(f"{PYTHON} theme.py", shell=True)
#                 #t.wait()
#             #os.system(REBOOT)

#         time.sleep(60)

def main():
    print(f"[{time_log()}] MAIN: SERVER STARTED")
    # subprocess.Popen(f"{PYTHON} API.py", shell=True)

    print(f"[{time_log()}] MAIN: WAITING FOR EVENTS")
    while True:
        date = datetime.datetime.now()
        downloader()
        # Create a thread for the downloader function and start it
        downloader_thread = threading.Thread(target=downloader)
        downloader_thread.start()

        # Create a thread for the sorter function and start it

        sorter_thread = threading.Thread(target=sorter)
        sorter_thread.start()

        # Check if it's 4 AM and start the integrity and judas threads
        if date.strftime('%H') == "04":
            integrity_thread = threading.Thread(target=check_integrity)
            integrity_thread.start()
            integrity_thread.join()
            # judas_thread = threading.Thread(target=check_judas)
            # judas_thread.start()
            # judas_thread.join()

        # Wait for all threads to finish before continuing
        downloader_thread.join()

        sorter_thread.join()

        # Wait for 60 seconds before checking again
        time.sleep(60)


if __name__ == '__main__':
    main()
