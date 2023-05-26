import datetime
import json
import os
import platform
import shutil
import subprocess
import threading
import time

import feedparser
import psutil
import pythoncom
import requests
import tmdbsimple as tmdb
from flask import Flask, jsonify, request, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename

if platform.system() == "Windows":
    import ctypes, wmi

    PYTHON = "python"
    NTERM = "start"
    REBOOT = "shutdown /r"
    VAR_DIR = "C:\\Users\\benja\\AppData\\Local\\my-server"
elif platform.system() == "Linux":
    PYTHON = "python3"
    NTERM = "gnome-terminal --"
    REBOOT = "reboot"
    VAR_DIR = "/var/lib/my-server"

CONF_FILE = "server.conf"
TMDB_TITLE = os.path.join("lib", "tmdb_tile.json")
ANIME_LIB = os.path.join("lib", "anime.json")
SHOWS_LIB = os.path.join("lib", "shows.json")
MOVIES_LIB = os.path.join("lib", "movie.json")
TMDB_DB = os.path.join("lib", "tmdb_db.json")
RSS_ANIME = "rss_anime.dat"
RSS_MOVIE = "rss_movie.dat"
RSS_SHOW = "rss_show.dat"
QUERY_SHOW = "query_show.dat"
QUERY_MOVIE = "guery_movie.dat"
GGD_LIB = os.path.join("lib", "ggd_lib.json")


def list_all_files(directory: str) -> list:
    if not os.path.isdir(directory):
        return []
    list_files = []
    for root, directories, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            list_files.append(file_path)
    return list_files


def is_movie(path_file):
    file_name = os.path.basename(path_file).lower()
    return "movie" in file_name


def compare_dictionaries(dict1, dict2):
    return sorted(dict1.items()) == sorted(dict2.items())


def safe_move(src, dst, max_retries=2, retry_delay=1):
    if not is_video(src):
        retries = 0
        while retries < max_retries:
            try:
                shutil.move(src, dst)
                if os.path.isfile(src):
                    os.remove(src)
                return True
            except PermissionError:
                retries += 1
                time.sleep(retry_delay)
            except RuntimeError:
                retries += 1
                time.sleep(retry_delay)
    return False


def extract_files(source_dir, dest_dir):
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            src_path = os.path.join(root, file)
            dst_path = os.path.join(dest_dir, file)
            safe_move(src_path, dst_path)


def is_video(file_path):
    """
    Checks if a file at the given path is a video file.

    Args:
        file_path (str): The path to the file.

    Returns:
        bool: True if the file is a video file, False otherwise.
    """
    # Check by file extension
    video_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.mkv']
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext in video_extensions:
        return True

    # Not a video file
    return False


def get_free_space(path):
    if platform.system() == "Windows":
        # Call the Win32 API function to get the free space
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p(path),
            None,
            None,
            ctypes.pointer(free_bytes)
        )
        # Return the free space in bytes
        return free_bytes.value
    else:
        # Use the Unix-based os.statvfs function to get the free space
        st = os.statvfs(path)
        # Return the free space in bytes
        return st.f_bavail * st.f_frsize


def get_directory_size(directory):
    total_size = 0

    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            total_size += os.path.getsize(filepath)

    return total_size


def get_dir_and_free(dir):
    dic = {"used": get_directory_size(dir),
           "free": get_free_space(dir)
           }
    return dic


def get_total_free_and_used(list_dir: list | str) -> dict:
    dic = {"used": 0, "free": 0}
    if type(list_dir) == str:
        return get_dir_and_free(list_dir)
    else:
        for dir in list_dir:
            d = get_dir_and_free(dir)
            dic["used"] += d["used"]
            dic["free"] += d["free"]
        return dic


def get_path_with_most_free_space(paths: str | list):
    if type(paths) == str:
        return paths
    max_free_space = 0
    path_with_max_free_space = ''
    for path in paths:
        free_space = get_free_space(path)
        if free_space > max_free_space:
            max_free_space = free_space
            path_with_max_free_space = path
    return path_with_max_free_space


def get_video_language(file_path):
    if os.path.splitext(file_path)[1] == '.mkv':
        # Use mkvmerge to extract the metadata of the video file
        output = subprocess.check_output(['mkvmerge', '-J', file_path])
        metadata = json.loads(output)

        # Find the language of the audio and subtitle tracks
        audio_langs = []
        subtitle_langs = []
        for track in metadata['tracks']:
            if track['type'] == 'audio':
                if track['properties']['language'] == 'fre':
                    audio_langs.append('French')  # Ignore French audio tracks
                elif track['properties']['language'] == 'jpn':
                    audio_langs.append('Japanese')
            elif track['type'] == 'subtitles':
                if track['properties']['language'] == 'fre':
                    subtitle_langs.append('French')
                elif track['properties']['language'] == 'jpn':
                    continue  # Ignore Japanese subtitle tracks

        # Determine the video language based on the audio and subtitle languages
        if 'French' in audio_langs and 'Japanese' in audio_langs:
            return 'VF/VO'
        if 'French' in audio_langs:
            return 'VF'
        if 'Japanese' in audio_langs and 'French' in subtitle_langs:
            if len(audio_langs) > 1:
                return 'VOSTFR+'
            else:
                return 'VOSTFR'
        else:
            return 'Unknown'
    elif os.path.splitext(file_path)[1] == '.mp4':
        cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'stream:tags', '-print_format', 'json', file_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            output = result.stdout.decode('utf-8')
            data = json.loads(output)
            audio_langs = []
            sub_langs = []
            for stream in data['streams']:
                if stream['codec_type'] == 'audio':
                    if 'language' in stream['tags']:
                        audio_langs.append(stream['tags']['language'])
                elif stream['codec_type'] == 'subtitle':
                    if 'language' in stream['tags']:
                        sub_langs.append(stream['tags']['language'])
            if 'fra' in audio_langs:
                return 'VF'
            elif 'jpn' in audio_langs:
                if 'fra' in sub_langs:
                    return 'VOSTFR'
                else:
                    return 'VO'
            else:
                return 'Unknown'
        else:
            return 'Unknown'
    else:
        return 'Invalid file format'


def time_log():
    # Get the current time
    current_time = datetime.datetime.now()
    datetime.datetime.now().strftime("%H")

    # Format the time as a string with the hour, minute, and second
    return current_time.strftime("%H:%M:%S")


def log(to_log: str, warning=False, error=False) -> None:
    if type(to_log) == str:
        l = ""
        if error:
            l = f'[{time_log()}] ERROR :  {to_log}\n'
        elif warning:
            l = f'[{time_log()}] WARNING :  {to_log}\n'
        open(f"{VAR_DIR}/log.txt", "a", encoding="utf-8").write(l)


def forbiden_car(name: str):
    """remove forbidden car for file naming"""
    for car in ["?", '"', "/", "\\", "*", ":", "<", ">", "|"]:
        name = name.replace(car, "")
    return name


def delete_from_to(str: str, fromm: str, to: str) -> str:
    r = ""
    while str[0] != fromm:
        r += str[0]
        str = str[1:]
    while str[0] != to:
        str = str[1:]
    str = str[1:]
    return r + str


def isolate_numbers(temp_file: str) -> list:
    """return a list of all numbers in the string"""
    ls = []
    while temp_file != "":
        n = ""
        if temp_file[0].isnumeric():
            n += temp_file[0]
            temp_file = temp_file[1:]
            while temp_file != "" and temp_file[0].isnumeric():
                n += temp_file[0]
                temp_file = temp_file[1:]
            ls.append(n)
            n = ""
        else:
            temp_file = temp_file[1:]
    return ls


def check_json(path: str) -> bool:
    if not "json" in path:
        return True
    try:
        json.load(open(path, "r", encoding="utf-8"))
        return True
    except json.decoder.JSONDecodeError:
        return False


class Server():
    tmdb_title: dict
    tmdb_db: dict
    conf: dict

    list_file = [ANIME_LIB, QUERY_MOVIE, QUERY_SHOW, MOVIES_LIB, SHOWS_LIB, CONF_FILE, TMDB_TITLE, TMDB_DB,
                 RSS_SHOW, RSS_ANIME,
                 RSS_MOVIE, GGD_LIB]
    for file in list_file:
        path = os.path.join(VAR_DIR, file)
        if os.path.isfile(path) and check_json(path):
            pass
        else:
            if "json" in file:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                json.dump({}, open(path, "w"))
            else:
                open(path, "w")

    tmdb_db = json.load(open(os.path.join(VAR_DIR, TMDB_DB), "r", encoding="utf-8"))
    # tmdb_title = {i.split(" : ")[0]: i.split(" : ")[1].replace("\n", "") for i in
    #              open(os.path.join(VAR_DIR, TMDB_TITLE), "r", encoding="utf-8")}
    tmdb_title = json.load(open(os.path.join(VAR_DIR, TMDB_TITLE), "r", encoding="utf-8"))

    def load_config(lib: str | None = VAR_DIR) -> dict:
        """list of all elt contained in config:
            shows_dir
            movie_dir
            serv_dir
            download_dir
            sorter_anime_dir
            clip_load
            clip_lib
            temp_dir
            Judas_dir

            GGD_Judas
            Clip"""
        try:
            config = {}
            with open(os.path.join(lib, CONF_FILE), "r", encoding="utf-8") as f:
                for lines in f:
                    if lines[0] in ["#", "\n", ""]:
                        pass
                    else:
                        line = lines.replace("\n", "").split(" = ")
                        try:
                            if "," in line[1]:
                                line[1] = [elt.strip() for elt in line[1].split(",")]
                            else:
                                line[1] = line[1].strip()
                            arg1, arg2 = line[0].strip(), line[1]
                        except IndexError as e:
                            print(
                                f"some values are not set in {CONF_FILE}, please make sure you have all set here is the line where's the issue : {lines}")
                            quit()
                        config[arg1] = arg2

            if config["GGD"]:
                if config["GGD"] == "FALSE":
                    config.pop("GGD_dir")
                elif config["GGD"] == "TRUE":
                    pass
                else:
                    raise ValueError(
                        f"The value of GGD_Judas in {os.path.join(VAR_DIR, CONF_FILE)} have to be TRUE or FALSE")
            if config["Clip"]:
                if config["Clip"] == "FALSE":
                    config.pop("clip_load")
                    config.pop("clip_lib")
                elif config["Clip"] == "TRUE":
                    pass
                else:
                    raise ValueError(
                        f"The value of Clip in {os.path.join(VAR_DIR, CONF_FILE)} have to be TRUE or FALSE")
            if config["Downloader"]:
                if config["Downloader"] == "FALSE":
                    config.pop("download_dir")
                    config.pop("torrent_dir")
                elif config["Downloader"] == "TRUE":
                    pass
                else:
                    raise ValueError(
                        f"The value of Downloader in {os.path.join(VAR_DIR, CONF_FILE)} have to be TRUE or FALSE")

            for key in config:
                if "dir" in key:
                    if type(config[key]) == list:
                        for dirs in config[key]:
                            if not os.path.isdir(dirs):
                                raise NotADirectoryError(
                                    f"The directory in {VAR_DIR} specified as {dirs} does not exist")
                    else:
                        if not os.path.isdir(config[key]):
                            raise NotADirectoryError(
                                f"The directory in {VAR_DIR} specified as {config[key]} does not exist")
                else:
                    if config[key] == "FALSE":
                        config[key] = False
                    elif config[key] == "TRUE":
                        config[key] = True
                    else:
                        pass
            return config
        except IOError as e:
            print(e)
            quit()

    conf = load_config()

    def __init__(self, enable=True):
        if enable:
            tmdb.API_KEY = Server.conf["TMDB_API_KEY"]
            tmdb.REQUESTS_TIMEOUT = 5
            self.search = tmdb.Search()

    def check_system_files(self):
        list_file = [ANIME_LIB, QUERY_MOVIE, QUERY_SHOW, MOVIES_LIB, SHOWS_LIB, CONF_FILE, TMDB_TITLE, TMDB_DB,
                     RSS_SHOW, RSS_ANIME,
                     RSS_MOVIE, GGD_LIB]
        for file in list_file:
            path = os.path.join(VAR_DIR, file)
            if os.path.isfile(path) and check_json(path):
                pass
            else:
                if "json" in file:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    json.dump({}, open(path, "w"))
                else:
                    open(path, "w")

    def get_file(self):
        for file in Server.conf["temp_dir"]:
            path = os.path.join(Server.conf["temp_dir"], file)
            if os.path.isdir(path):
                if "anime" in file:
                    extract_files(path, Server.conf["sorter_anime_dir"])
                elif "movie" in file:
                    extract_files(path, Server.conf["sorter_movie_dir"])
                elif "show" in file:
                    extract_files(path, Server.conf["sorter_show_dir"])

    def update_tmdb_db(self, title, n_item):
        Server.tmdb_db[title] = n_item

    def add_tmdb_title(dertermined_title: str, tmdb_title):
        Server.tmdb_title[dertermined_title] = tmdb_title

    def get_tmdb_title(determined_title: str):
        return Server.tmdb_title.get(determined_title, None)


class Show(Server):

    def __init__(self, path: str, title: str, is_valid=False):
        super().__init__()
        self.path = path
        if not is_valid:
            try:
                self.search.tv(query=title)
                self.title = self.search.results[0]["name"]
                super().update_tmdb_db(self.title, tmdb.TV(self.search.results[0]["id"]).info())
                Server.add_tmdb_title(title, self.title)
                self.info = Server.tmdb_db[self.title]
                self.id = self.info['id']
            except IndexError as e:
                log(f"Can't determine the show named {title}", error=True)
        else:
            self.title = title
            if Server.tmdb_db.get(self.title, None) is None:
                self.id = self.search.tv(query=title)
                self.id = self.search.results[0]['id']
                self.tmdb = tmdb.TV(self.id)
                self.info = self.tmdb.info()
                super().update_tmdb_db(self.title, self.info)
            else:
                self.info = Server.tmdb_db[title]
                self.id = self.info['id']
            self.seasons = self.list_season()

    def update_data(self):
        super().update_tmdb_db(self.title, tmdb.TV(self.id).info())

    def list_season(self) -> list:
        ls = []
        for sea in self.info["seasons"]:
            path_dir = os.path.join(self.path, f"Season {str(sea['season_number']).zfill(2)}")
            os.makedirs(path_dir, exist_ok=True)
            ls.append(Season(self, path_dir, sea))
        return ls

    def delete(self):
        shutil.rmtree(self.path)

    def delete_ep(self, season_number: int, ep_number: int) -> bool:
        for elt in self.seasons:
            if elt.info['season_number'] == season_number:
                for ep in elt.list_ep:
                    if ep.ep == ep_number:
                        ep.delete()
                        elt.list_ep.remove(ep)
                        elt.is_completed = elt.info["episode_count"] == len(elt.list_ep)
                        return True
        return False

    def delete_season(self, season_number: int) -> bool:
        for elt in self.seasons:
            if elt.info['season_number'] == season_number:
                for ep in elt.list_ep:
                    ep.delete()
                self.seasons.remove(elt)
                return True
        return False

    def add_season(self, nb: int):
        for sea in self.info["seasons"]:
            if nb == sea['season_number']:
                return
        path_dir = os.path.join(self.path, f"Season {str(nb).zfill(2)}")
        os.makedirs(path_dir, exist_ok=True)
        self.seasons.append(Season(self, path_dir, sea))
        return

    def __str__(self):
        dic = {}
        dic[self.title] = [s.__str__() for s in self.list_season()]
        return dic.__str__()


class Anime(Show):
    def __init__(self, path: str, title: str, is_valid=False):
        super().__init__(path, title, is_valid)


class Sorter(Server):
    def __init__(self, file_path: str, is_movie=False, for_test=False):
        super().__init__(enable=False)  # Not needed
        self.is_movie = is_movie
        self.path = file_path
        self.for_test = for_test
        self.file_name = os.path.basename(self.path)
        self.clean_file_name = os.path.splitext(self.file_name)[0].replace(".", " ").replace("_",
                                                                                             " ")  # get file name with no extension
        if not is_movie:
            self.source = self.determine_source()
        self.ext = os.path.splitext(self.file_name)[1]
        self.make_clean_file_name()
        if not for_test:
            self.spec = self.video_spec()
            try:
                self.codec = self.spec["video"]["codec"]
            except:
                self.codec = "Unknown_codec"
            self.lang = self.determine_language()
            self.list_subs_lang = self.spec["subtitles"]["language"]
            self.list_audio_lang = self.spec["audio"]["language"]
            self.resolution = f'{self.spec["video"]["height"]}p'
        if not is_movie:

            self.season = self.determine_season()
            self.title = self.determine_title()
            temp = Server.get_tmdb_title(self.title)
            if temp != None:
                self.show = Show("ok", temp, is_valid=True)
            else:
                self.show = Show("ok", self.title, is_valid=False)
            self.tmdb_info = self.show.info
            self.id = self.show.id
            self.title = self.show.title
            self.ep = self.determine_ep()

        else:
            self.title = self.det_title_movie()

    def make_clean_file_name(self):
        for banned_car in [("[", "]"), ("{", "}"), ("(", ")")]:
            car1, car2 = banned_car
            while car1 in self.clean_file_name and car2 in self.clean_file_name:
                self.clean_file_name = delete_from_to(self.clean_file_name, car1, car2)

    def det_title_movie(self):
        file = self.clean_file_name
        if "(" in self.file_name:
            return self.file_name[:self.file_name.index("(")].strip()
        else:
            for car in file:
                if car.isnumeric():
                    return file.split(car)[0].strip()

    def determine_title(self) -> str:
        """return the title of a video"""
        file = self.clean_file_name
        for to_delete in ["2nd Season", "1st Season", "3rd Season", "Cour 2"]:
            file = file.replace(to_delete, "")
        if " - " in file:
            file = file.split(" - ")[0]
            if "Season" in file:
                file = file.split("Season")[0]
            if f"S{self.season}" in file:
                file = file.split(f"S{self.season}")[0]
            if f"S{self.season[1]}" in file:
                file = file.split(f"S{self.season[1]}")[0]
            if file[-1].isnumeric() and file[-2] == " ":
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
            if car.isnumeric():
                return file.split(car)[0].strip()
        return file.split(" ")[0]

    def determine_season(self) -> str:
        """return the season of a video file from it's title"""
        file, ls = self.clean_file_name, []
        if "oav" in file.lower():
            return "00"
        if "nd Season" in file:
            return "02"
        if "st Season" in file:
            return "01"
        if "rd Season" in file:
            return "03"
        try:
            while file[0].isnumeric():
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

    def determine_language(self):
        if "vf" in self.file_name.lower() and "vostfr" in self.file_name.lower():
            return "VF/VOSTFR"

        elif "vf" in self.file_name.lower():
            return "VF"
        elif "vostfr" in self.file_name.lower():
            return "VOSTFR"
        result = ""
        if len(self.spec["subtitles"]["language"]) > 1:
            result = "Multi-Subs"
            if len(self.spec["audio"]["language"]) > 1:
                result += " Multi-Audios"
                return result
            return result
        else:
            if "fre" in self.spec["subtitles"]["language"] and "jpn" in self.spec["audio"]["language"]:
                return "VOSTFR"
            else:
                return "Unknown"

    def determine_language_old(self) -> str:
        if "vf" in self.file_name.lower() and "vostfr" in self.file_name.lower():
            return "VF/VOSTFR"

        elif "vf" in self.file_name.lower():
            return "VF"
        elif "vostfr" in self.file_name.lower():
            return "VOSTFR"

        else:
            tr = self.tracks()
            if not tr == {}:
                if "ja" in tr["audio"] and tr["subs"] == []:
                    return "VOSTFR"
                if "fr" in tr["subs"] and "ja" in tr["audio"] and "fr" in tr["audio"]:
                    return "VF/VOSTFR"
                elif "fr" in tr["subs"] and "ja" in tr["audio"]:
                    return "VOSTFR"
                elif "fr" in tr["audio"]:
                    return "VF"

            return "UKNOWNLANG"

    def video_spec(self) -> dict[str, dict[str, list[str]] | dict[str, list[str]] | dict[str, int]]:

        track_info = {'audio': {"codec": [],
                                "language": []},
                      'subtitles': {"codec": [],
                                    "language": []
                                    },
                      'video': {"codec": None,
                                "height": None, }}
        # Run the ffprobe command and capture the output
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", self.path]
        result = subprocess.check_output(cmd, universal_newlines=True, errors="ignore")

        # Parse the JSON output to extract the subtitle languages
        data = json.loads(result)
        for streams in data["streams"]:
            type = streams["codec_type"].lower()
            if type == "video":
                try:
                    track_info["video"]["height"] = streams["height"]
                except KeyError:
                    pass
                try:
                    track_info["video"]["codec"] = streams["codec_name"].upper()
                except KeyError:
                    pass
            elif type == "audio":
                try:
                    track_info["audio"]["codec"].append(streams["codec_name"].upper())
                except KeyError:
                    pass
                try:
                    track_info["audio"]["language"].append(streams["tags"]["language"].lower())
                except KeyError:
                    pass
            elif type == "subtitle":
                try:
                    track_info["subtitles"]["codec"].append(streams["codec_name"].upper())
                except KeyError:
                    pass
                try:
                    track_info["subtitles"]["language"].append(streams["tags"]["language"].lower())
                except KeyError:
                    pass

        return track_info

    def determine_ep(self) -> str:
        """return the ep of a video file from it's title"""
        file, ls, temp = self.clean_file_name, [], None
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

    def determine_source(self) -> str:
        """return the source of a video from it's file name"""
        title, source = self.clean_file_name, ""
        if "[" == title[0] and "]" in title:
            while title[0] != "[":
                title = title[1:]
            title = title[1:]
            while title[0] != "]":
                source = source + title[0]
                title = title[1:]
            return source
        try:
            r = title.split(" -")[-1].strip()
            return r
        except:
            return "Strange"

    def __str__(self):
        if self.is_movie:
            if self.for_test:
                return forbiden_car(
                    f"{self.title} -Strange {self.ext}")
            return forbiden_car(
                f"{self.title} - [{self.lang} {self.resolution} {self.codec}] -Strange {self.ext}")
        else:
            if self.for_test:
                return forbiden_car(
                    f"{self.title} - S{self.season}E{self.ep} -{self.source} {self.ext}")
            return forbiden_car(
                f"{self.title} - S{self.season}E{self.ep} - [{self.lang} {self.resolution} {self.codec}] -{self.source} {self.ext}")


class Movie(Server):

    def __init__(self, path: str, title: str, is_valid=False):
        super().__init__()
        self.path = path
        if not is_valid:
            try:
                self.search.movie(query=title)
                self.title = self.search.results[0]["name"]
                super().update_tmdb_db(self.title, tmdb.Movies(self.search.results[0]["id"]).info())
                Server.add_tmdb_title(title, self.title)
            except IndexError:
                log(f"Can't determine the movie named {title}", error=True)
        else:
            self.title = title
            if not self.title in Server.tmdb_db:
                self.id = self.search.movie(query=title)
                self.id = self.search.results[0]['id']
                self.tmdb = tmdb.Movies(self.id)
                self.info = self.tmdb.info()
                super().update_tmdb_db(self.title, self.info)
            else:
                self.info = Server.tmdb_db[title]
                self.id = self.info['id']

    def add(self, file: Sorter):
        if os.path.isfile(file.path):
            path = os.path.join(self.path, file.__str__())
            shutil.move(file.path, path)

    def delete(self):
        shutil.rmtree(self.path)


class Season(Server):
    def __init__(self, anime: Show | Anime, path: str, info: dict):
        super().__init__()
        self.anime = anime
        self.path = path
        self.info = info
        self.list_ep = self.list_episode()
        self.is_completed = self.info["episode_count"] == len(self.list_ep)

    def list_episode(self) -> list:
        ls = []
        for file in os.listdir(self.path):
            p = os.path.join(self.path, file)
            if os.path.isfile(p) and is_video(p):
                ls.append(Episode(self, p))
        return ls

    def add_ep(self, file: Sorter):
        if os.path.isfile(file.path):
            path = os.path.join(self.path, file.__str__())
            shutil.move(file.path, path)
            self.list_ep.append(Episode(self, path))

    def __str__(self):
        dic = {}
        dic[f"Season {str(self.info['season_number']).zfill(2)}"] = [ep.path for ep in self.list_ep]
        return dic.__str__()


class Episode(Server):
    def __init__(self, season: Season, path):
        super().__init__()
        self.path = path
        self.s = season
        self.file_name = os.path.splitext(os.path.basename(path))[0]
        self.season = str(season.info['season_number']).zfill(2)
        self.ep = int(self.file_name.split(" - ")[1].split("E")[-1])
        self.codec = self.file_name.split(" - ")[2].split(" ")[-1].split("]")[0]
        try:
            self.res = int(self.file_name.split(" - ")[2].split(" ")[1])
        except ValueError:
            pass
        self.lang = self.file_name.split(" - ")[2].split(" ")[0]
        self.source = self.file_name[::-1].split("- ")[0]

    def delete(self):
        os.remove(self.path)


def choose_best_version(v_cur: Episode, v_new: Sorter) -> Sorter | Episode:
    if "judas" in v_new.file_name.lower():
        return v_new
    elif "judas" in v_cur.file_name.lower():
        return v_cur
    else:
        return v_new


class DataBase(Server):
    def __init__(self):
        super().__init__(enable=True)
        super().check_system_files()
        self.shows_dirs = Server.conf["shows_dir"]
        self.anime_dirs = Server.conf["anime_dir"]
        self.movie_dirs = Server.conf["movie_dir"]
        self.to_sort_anime = Server.conf["sorter_anime_dir"]
        self.to_sort_show = Server.conf["sorter_show_dir"]
        self.to_sort_movie = Server.conf["sorter_movie_dir"]
        try:
            self.animes = json.load(open(os.path.join(VAR_DIR, ANIME_LIB), "r", encoding="utf-8"))
        except IOError as e:
            log(f"can't acces to {ANIME_LIB}", error=True)
            quit()
        try:
            self.shows = json.load(open(os.path.join(VAR_DIR, SHOWS_LIB), "r", encoding="utf-8"))
        except IOError as e:
            log(f"can't acces to {SHOWS_LIB}", error=True)
            quit()
        try:
            self.movies = json.load(open(os.path.join(VAR_DIR, MOVIES_LIB), "r", encoding="utf-8"))
        except IOError as e:
            log(f"can't acces to {MOVIES_LIB}", error=True)
            quit()
        self.check_database()

    def check_database(self):
        """check if all information from self.shows/anime/movies are correct (dir exist)"""
        ls = self.animes.copy()
        for media in self.animes:
            if not os.path.isdir(self.animes[media]):
                ls.pop(media)
        if not compare_dictionaries(self.animes, ls):
            self.animes = ls.copy()
            json.dump(self.animes, open(os.path.join(VAR_DIR, ANIME_LIB), "w", encoding="utf-8"), indent=5)
        ls.clear()
        ls = self.shows.copy()
        for media in self.shows:
            if not os.path.isdir(self.shows[media]):
                ls.pop(media)
        if not compare_dictionaries(self.shows, ls):
            self.shows = ls.copy()
            json.dump(self.shows, open(os.path.join(VAR_DIR, SHOWS_LIB), "w", encoding="utf-8"), indent=5)
        ls.clear()
        ls = self.movies.copy()
        for media in self.movies:
            if not os.path.isdir(self.movies[media]):
                ls.pop(media)
        if not compare_dictionaries(self.movies, ls):
            self.movies = ls.copy()
            json.dump(self.movies, open(os.path.join(VAR_DIR, MOVIES_LIB), "w", encoding="utf-8"), indent=5)

    def var(self, anime=False, shows=False, movie=False) -> tuple[dict, Anime | Show | Movie, list, str]:
        self.check_database()
        if anime:
            dic = self.animes
            r = Anime
            dirs = Server.conf["anime_dir"]
            lib = ANIME_LIB
        elif shows:
            dic = self.shows
            r = Show
            dirs = Server.conf["shows_dir"]
            lib = SHOWS_LIB
        elif movie:
            dic = self.movies
            r = Movie
            dirs = Server.conf["movie_dir"]
            lib = MOVIES_LIB
        return (dic, r, dirs, lib)

    def find_tmdb_title(self, title: str, anime=False, shows=False, movie=False):
        tmdb_title = Server.get_tmdb_title(title)
        if tmdb_title != None:
            return tmdb_title
        if anime or shows:
            self.search.tv(query=title)
        else:
            self.search.movie(query=title)
        try:
            super().update_tmdb_db(self.search.results[0]["name"], self.search.results[0])
            Server.add_tmdb_title(title, self.search.results[0]["name"])
            return self.search.results[0]["name"]
        except IndexError as e:
            log(f"No title found for {title}", warning=True)
            return False

    def find(self, title, anime=False, shows=False, movie=False, is_valid=False) -> Anime | Show | Movie | bool:
        dic, r, dirs, lib = self.var(anime, shows, movie)
        if not is_valid:
            title = self.find_tmdb_title(title, anime, shows, movie)
            if title == False:
                return False
            return self.find(title, anime, shows, movie, is_valid=True)
        elif dic != {}:
            try:
                path = dic[title]
                return r(path, title, is_valid)
            except KeyError:
                return False
        else:
            return False

    def update_lib(self, n_item, value, anime=False, shows=False, movie=False, delete=False):
        dic, r, dirs, lib = self.var(anime, shows, movie)
        if anime:
            if not delete:
                self.animes[n_item] = value
            else:
                self.animes.pop(n_item)
            json.dump(self.animes, open(os.path.join(VAR_DIR, lib), "w", encoding="utf-8"), indent=5)
        elif shows:
            if not delete:
                self.shows[n_item] = value
            else:
                self.shows.pop(n_item)
            json.dump(self.shows, open(os.path.join(VAR_DIR, lib), "w", encoding="utf-8"), indent=5)
        elif movie:
            if not delete:
                self.movies[n_item] = value
            else:
                self.movies.pop(n_item)
            json.dump(self.movies, open(os.path.join(VAR_DIR, lib), "w", encoding="utf-8"), indent=5)

    def get_dir_freer(self, anime=False, shows=False, movie=False) -> str:
        """return the direcotires with the more free space
            choose between anime, shows and movie, it returns only one result at the time"""
        dic, r, dirs, lib = self.var(anime, shows, movie)
        max, max_dir = 0, ""
        return get_path_with_most_free_space(dirs)

    def add(self, title, anime=False, shows=False, movie=False, is_valid=False) -> bool:
        dict, r, dirs, lib = self.var(anime, shows, movie)
        if not is_valid:
            title = r("path", title, is_valid).title
            test = self.find(title, anime=anime, shows=shows, movie=movie, is_valid=False)
            if test != False:
                return self.add(title, anime=anime, shows=shows, movie=movie, is_valid=True)
            else:
                return self.add(title, anime=anime, shows=shows, movie=movie, is_valid=True)
        elif title not in dict:
            dir = self.get_dir_freer(anime, shows, movie)
            try:
                path = os.path.join(dir, forbiden_car(title))
                os.makedirs(path)
                self.update_lib(title, path, anime, shows, movie)

            except OSError as e:
                print(e)
                log(e, error=True)
            return r(path, title, is_valid=True)
        else:
            return r(dict[title], title, is_valid=True)

    def add_file(self, file: Sorter, anime=False, shows=False, movie=False) -> bool:
        elt = self.add(file.title, anime, shows, movie, is_valid=True)
        if elt != False and not movie:
            for season in elt.seasons:
                if str(season.info['season_number']).zfill(2) == file.season:
                    for ep in season.list_ep:
                        if f"{int(ep.ep):02}" == file.ep:
                            if choose_best_version(ep, file) == file:
                                self.replace(ep, file, anime, shows, movie)
                                return True
                            else:
                                os.remove(file.path)
                                return True
                            return True
                    season.add_ep(file)
                    return
            log(f"Episode is unknown for the databse : {file}", error=True)
            if anime:
                st = "anime"
            elif shows:
                st = "show"
            elif movie:
                st = movie
            os.makedirs(os.path.join(Server.conf["errors_dir"], st), exist_ok=True)
            safe_move(file.path, os.path.join(Server.conf["errors_dir"], st))  # add to error directory for manual sort
        elif movie:
            elt.add(file)
        else:
            self.add_file(file, anime, shows, movie)

    def replace(self, ep: Episode, new_file: Sorter, anime=False, shows=False, movie=False):
        ep.s.anime.delete_ep(int(ep.season), ep.ep)
        self.add_file(new_file, anime, shows, movie)

    def delete(self, title, anime=False, shows=False, movie=False) -> bool:
        dict, r, dirs, lib = self.var(anime, shows, movie)
        elt = self.find(title, anime, shows, movie)
        if elt != False and os.path.isdir(elt.path):
            elt.delete()
            self.update_lib(title, None, anime, shows, movie, delete=True)
            return True
        return False

    def sort(self, anime=False, shows=False, movie=False):
        if anime:
            dir = self.to_sort_anime
        elif shows:
            dir = self.to_sort_show
        elif movie:
            dir = self.to_sort_movie
        if type(dir) == str:
            for file in os.listdir(dir):
                path = os.path.join(dir, file)
                if os.path.isfile(path) and is_video(path):
                    try:
                        s = Sorter(path, movie)
                        self.add_file(s, anime, shows, movie)
                    except RuntimeError as e:
                        pass
                    except PermissionError:
                        pass
                    except subprocess.CalledProcessError:
                        pass
                    except IndexError:
                        pass

                elif os.path.isdir(path):
                    extract_files(path, self.to_sort_anime)
                elif type(dir) == list:
                    for dirs in dir:
                        for file in os.listdir(dirs):
                            path = os.path.join(dirs, file)
                            if os.path.isfile(path) and is_video(path):
                                try:
                                    s = Sorter(path, movie)
                                    self.add_file(s, anime, shows, movie)
                                except RuntimeError:
                                    pass
                                except PermissionError:
                                    pass
                            elif os.path.isdir(path):
                                extract_files(path, self.to_sort_anime)
                                self.sort(anime, shows, movie)

    def serve_forever(self):
        try:
            while True:
                if type(self.to_sort_anime) == str and os.listdir(self.to_sort_anime) != []:
                    self.sort(anime=True)
                elif type(self.to_sort_anime) == list:
                    for dir in self.to_sort_anime:
                        if os.listdir(dir) != []:
                            self.sort(anime=True)
                if type(self.to_sort_show) == str and os.listdir(self.to_sort_show) != []:
                    self.sort(shows=True)
                elif type(self.to_sort_show) == list:
                    for dir in self.to_sort_show:
                        if os.listdir(dir) != []:
                            self.sort(shows=True)
                if type(self.to_sort_movie) == str and os.listdir(self.to_sort_movie) != []:
                    self.sort(movie=True)
                elif type(self.to_sort_movie) == list:
                    for dir in self.to_sort_movie:
                        if os.listdir(dir) != []:
                            self.sort(shows=True)
                time.sleep(5)
        except KeyboardInterrupt:
            print("shutting down")

    def have_ep(self, file: Sorter, anime=False, shows=False, movie=False) -> bool:
        elt = self.find(file.title, anime, shows, movie)
        if elt == False:
            return False
        elif not movie:
            for season in elt.seasons:
                for ep in season.list_ep:
                    if f"{int(ep.ep):02}" == file.ep:
                        return True
            return False
        return False

    def save_tmdb_title(self):
        json.dump(Server.tmdb_title, open(os.path.join(VAR_DIR, TMDB_TITLE), "w", encoding="utf-8"), indent=5)


class Feed(DataBase):

    def __init__(self):
        super().__init__()
        self.feed_dict = self.get_feed()
        self.sort_feed()

    def get_feed(self) -> dict:
        rss_feeds = {"anime_feeds": [], "movie_feeds": [], "show_feeds": []}
        with open(os.path.join(VAR_DIR, RSS_ANIME), "r", encoding="utf-8") as f:
            for lines in f:
                if not lines[0] in ["#", '', "\n"]:
                    rss_feeds["anime_feeds"].append(lines.replace("\n", "").strip())
        with open(os.path.join(VAR_DIR, RSS_MOVIE), "r", encoding="utf-8") as f:
            for lines in f:
                if not lines[0] in ["#", '', "\n"]:
                    rss_feeds["movie_feeds_feeds"].append(lines.replace("\n", "").strip())
        with open(os.path.join(VAR_DIR, RSS_SHOW), "r", encoding="utf-8") as f:
            for lines in f:
                if not lines[0] in ["#", '', "\n"]:
                    rss_feeds["show_feeds"].append(lines.replace("\n", "").strip())
        return rss_feeds

    def get_ep_with_link(self, feed: feedparser.FeedParserDict) -> dict:
        dicto = {}
        for entry in feed.entries:
            for words in Server.conf["select_words_rss"]:
                if words in entry.title:
                    dicto[entry.title] = entry.link
            for words in Server.conf["banned_words_rss"]:
                if words not in entry.title:
                    dicto[entry.title] = entry.link
        return dicto

    def sort_feed(self) -> dict:

        for feed_list in self.feed_dict:
            ls = []
            for feed in self.feed_dict[feed_list]:
                time.sleep(2)  # avoid ban IP
                r = {}
                r.clear()
                feed = feedparser.parse(feed)
                dic = self.get_ep_with_link(feed)
                for ep in dic:
                    link = dic[ep]
                    if not "movie" in feed_list:
                        try:
                            ep = Sorter(ep, for_test=True)
                        except AttributeError as e:
                            log(f"can't determine the show {ep}", error=True)
                            pass
                        if "anime" in feed_list:
                            if not self.have_ep(ep, anime=True):
                                try:
                                    r[f"{ep.title} - S{ep.season}E{ep.ep} {ep.ext}"] = link
                                except AttributeError:
                                    ...
                        elif "show" in feed_list:
                            if not self.have_ep(ep, shows=True):
                                r[f"{ep.title} - S{ep.season}E{ep.ep} {ep.ext}"] = link
                    else:
                        mv = Sorter(ep, is_movie=True, for_test=True)
                        if not self.have_ep(ep, movie=True):
                            r[f"{mv.title} - {ep.ext}"] = link
                ls.append(r)
            self.feed_dict[feed_list] = ls

    def dl_torrent(self):
        for list_feed in self.feed_dict:
            for feed in self.feed_dict[list_feed]:
                for key in feed:
                    file_name = forbiden_car(f"{key}.torrent")
                    if file_name not in os.listdir(Server.conf['torrent_dir']):
                        print("dl ", key)
                        torrent = requests.request("GET", feed[key])
                        open(os.path.join(Server.conf['torrent_dir'], file_name), "wb").write(
                            torrent.content)
                        time.sleep(1)  # avoid ban ip


##########################################
################# API ####################
##########################################

class web_API(Server):

    def __init__(self, db: DataBase):
        super().__init__()
        self.db = db
        self.cpu_avg = 0
        self.cpu_temp_list = []

        self.app = Flask(__name__)
        self.app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024  # 10GB limit
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

        @self.app.route('/db/space')
        def space():
            for list_dir in self.db.movie_dirs:
                return jsonify()

        @self.app.route('/restart')
        def restart():
            os.system(REBOOT)
            return jsonify({"status": "ok"})

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
            pythoncom.CoInitialize()
            if platform.system() == "Linux":
                return jsonify({"value": psutil.sensors_temperatures()["k10temp"][0].current})
            else:
                w = wmi.WMI(namespace="root\OpenHardwareMonitor")
                temperature_infos = w.Sensor()
                for sensor in temperature_infos:

                    if sensor.SensorType == u'Temperature' and sensor.name == "CPU Package":
                        return jsonify({"value": sensor.value})

        @self.app.route("/cpu_temp/avg")
        def cpu_avg():
            self.update_cpu_avg()
            return jsonify({"value": self.cpu_avg})

        @self.app.route("/tmdb/search", methods=['POST'])
        def seach_tmdb_show():
            if request.method == 'POST':
                if request.form.get("choice") in ["anime", "show"]:
                    self.search.tv(query=request.form.get("search"))
                    print(self.search.results)
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
                    if request.form.get("choice") in ["anime", "show"]:
                        open(os.path.join(VAR_DIR, QUERY_SHOW), "a").write(request.form.get("id") + "\n")
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
            print(ch)
            if ch == "anime":
                dir_save = self.db.to_sort_anime
            elif ch == "show":
                dir_save = self.db.to_sort_show
            elif ch == "movie":
                dir_save = self.db.to_sort_movie
            file.save(os.path.join(dir_save, secure_filename(file.filename)))

            return "Téléchargement réussi"

        def upload_file(app: Flask):
            file = request.files['file']
            if file:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                return 'File uploaded successfully'
            return 'No file uploaded'

    def run(self):
        self.app.run()

    def update_cpu_temp(self):
        if platform.system() == "Linux":
            self.cpu_temp_list.append(psutil.sensors_temperatures()["k10temp"][0].current)
        else:
            w = wmi.WMI(namespace="root\OpenHardwareMonitor")
            temperature_infos = w.Sensor()
            for sensor in temperature_infos:

                if sensor.SensorType == u'Temperature' and sensor.name == "CPU Package":
                    self.cpu_temp_list.append(sensor.value)

    def update_cpu_avg(self):
        self.cpu_avg = round(sum(self.cpu_temp_list) / len(self.cpu_temp_list), 2)


class Gg_drive():
    dict_ep = json.load(open(os.path.join(VAR_DIR, GGD_LIB), "r", encoding="utf-8"))

    def __init__(self):
        self.d_dirs = Server.conf["GGD_dir"]

        self.exclude_dir = ["G:\Drive partagés\Judas - DDL (Full) (provided by BanglaDubZone)\[Judas] DDL exclusives",
                            "G:\Drive partagés\Judas - DDL (Full) (provided by BanglaDubZone)\[Judas] Bluray releases\My old releases as member of Hakata Ramen group",
                            "G:\Drive partagés\Judas - DDL (Full) (provided by BanglaDubZone)\[Judas] Webrip batches\My old releases as member of Hakata Ramen group"]

    def to_exlude(self, path):
        for p in self.exclude_dir:
            if p in path:
                return True
        return False

    def update_dict_ep(self, fast=False):
        list_files = []
        if type(self.d_dirs) == str:
            list_files = list_all_files(self.d_dirs)
        else:
            for dir in self.d_dirs:
                list_files += list_all_files(dir)
        dictionary_episode = {}
        for episode_path in list_files:
            if self.to_exlude(episode_path):
                pass
            elif is_video(episode_path):
                print(episode_path)
                movie = is_movie(episode_path)
                try:
                    try:
                        ep_info = Sorter(episode_path, movie, for_test=fast)
                    except subprocess.CalledProcessError as e:
                        try:
                            ep_info = Sorter(episode_path, movie, for_test=fast)
                        except subprocess.CalledProcessError:
                            continue
                        except UnicodeError:
                            continue
                    id = str(ep_info.id)
                    season = str(ep_info.season)
                    ep = str(ep_info.ep)
                    if Gg_drive.dict_ep.get(id, None) is None:
                        Gg_drive.dict_ep[id] = {}
                    if Gg_drive.dict_ep[id].get(season, None) is None:
                        Gg_drive.dict_ep[id][season] = {}
                    if Gg_drive.dict_ep[id][season].get(ep, None) is None:
                        Gg_drive.dict_ep[id][season][ep] = {}
                    if not fast:

                        Gg_drive.dict_ep[id][season][ep][ep_info.path] = {
                            "renamed": ep_info.__str__(),
                            "language": ep_info.lang,
                            "list_subs_language": ep_info.list_subs_lang,
                            "list_audio_language": ep_info.list_audio_lang,
                            "title": ep_info.title,
                            "height": ep_info.resolution,
                            "codec": ep_info.codec,
                        }

                    else:
                        Gg_drive.dict_ep[ep_info.id][ep_info.season][ep_info.ep][ep_info.path] = {
                            "renamed": ep_info.__str__(),
                            "title": ep_info.title,
                            "season_number": ep_info.season,
                        }
                except AttributeError as e:
                    pass

        json.dump(Gg_drive.dict_ep, open(os.path.join(VAR_DIR, GGD_LIB), "w", encoding="utf-8"), indent=5)
        return dictionary_episode

    def run(self):
        try:
            self.update_dict_ep()
        except KeyboardInterrupt:
            json.dump(Server.tmdb_db, open(os.path.join(VAR_DIR, TMDB_DB), "w", encoding="utf-8"), indent=5)


class deploy_serv():

    def __init__(self):
        self.db = DataBase()
        self.web_api = web_API(self.db)
        self.GGD = Gg_drive()

    def start(self):
        try:
            api = threading.Thread(target=self.web_api.run)
            api.start()

            db = threading.Thread(target=self.db.serve_forever)
            db.start()

            GGD = threading.Thread(target=self.GGD.run)
            GGD.start()

            while True:
                if len(self.web_api.cpu_temp_list) > 120:
                    self.web_api.cpu_temp_list = []
                self.web_api.update_cpu_temp()
                time.sleep(30)
        except KeyboardInterrupt:

            print("wait before closing saving data")
            print("saving GGD_lib")
            json.dump(Gg_drive.dict_ep, open(os.path.join(VAR_DIR, GGD_LIB), "w", encoding="utf-8"), indent=5)
            print("saving tmdb_title ...")
            self.db.save_tmdb_title()
            print("saving tmdb_db ...")
            json.dump(Server.tmdb_db, open(os.path.join(VAR_DIR, TMDB_DB), "w", encoding="utf-8"), indent=5)
            print("Shutting down")
            quit()


def main():
    server = deploy_serv()
    drive = Gg_drive()

    server.start()

    # db.serve_forever()


if __name__ == "__main__":
    main()
