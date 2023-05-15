import datetime
import json
import os
import platform
import shutil
import subprocess
import time

import feedparser
import tmdbsimple as tmdb
from pymediainfo import MediaInfo

if platform.system() == "Windows":
    import ctypes

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
TMDB_TITLE = "tmdb_tile.dat"
ANIME_LIB = os.path.join("lib", "anime.json")
SHOWS_LIB = os.path.join("lib", "shows.json")
MOVIES_LIB = os.path.join("lib", "movie.json")
TMDB_DB = os.path.join("lib", "tmdb_db.json")
RSS_ANIME = "rss_anime.dat"
RSS_MOVIE = "rss_movie.dat"
RSS_SHOW = "rss_show.dat"


def extract_files(source_dir, dest_dir):
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            src_path = os.path.join(root, file)
            dst_path = os.path.join(dest_dir, file)
            shutil.move(src_path, dst_path)


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


class Server():
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

            if config["GGD_Judas"]:
                if config["GGD_Judas"] == "FALSE":
                    config.pop("Judas_dir")
                elif config["GGD_Judas"] == "TRUE":
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

    def __init__(self, enable=True):
        if enable:
            self.conf = Server.load_config()
            tmdb.API_KEY = self.conf["TMDB_API_KEY"]
            tmdb.REQUESTS_TIMEOUT = 5
            self.search = tmdb.Search()
            self.tmdb_db = json.load(open(os.path.join(VAR_DIR, TMDB_DB), "r", encoding="utf-8"))

    def check_system_files(self):
        list_file = [ANIME_LIB, MOVIES_LIB, SHOWS_LIB, CONF_FILE, TMDB_TITLE, TMDB_DB, RSS_SHOW, RSS_ANIME, RSS_MOVIE]
        for file in list_file:
            if os.path.isfile(os.path.join(VAR_DIR, file)):
                pass
            else:
                if "json" in file:
                    os.makedirs(os.path.dirname(os.path.join(VAR_DIR, file)), exist_ok=True)
                    json.dump({}, open(os.path.join(VAR_DIR, file), "w"))
                else:
                    open(os.path.join(VAR_DIR, file), "w")

    def update_tmdb_db(self, title, n_item):
        self.tmdb_db[title] = n_item
        json.dump(self.tmdb_db, open(os.path.join(VAR_DIR, TMDB_DB), "w", encoding="utf-8"), indent=5)


class Show(Server):

    def __init__(self, path: str, title: str, is_valid=False):
        super().__init__()
        self.path = path
        if not is_valid:
            try:
                self.search.tv(query=title)
                self.title = self.search.results[0]["name"]
                super().update_tmdb_db(self.title, tmdb.TV(self.search.results[0]["id"]).info())
            except IndexError as e:
                log(f"Can't determine the show named {title}", error=True)
        else:
            self.title = title
            if not self.title in self.tmdb_db:
                self.id = self.search.tv(query=title)
                self.id = self.search.results[0]['id']
                self.tmdb = tmdb.TV(self.id)
                self.info = self.tmdb.info()
                super().update_tmdb_db(self.title, self.info)
            else:
                self.info = self.tmdb_db[title]
                self.id = self.info['id']
                self.tmdb = tmdb.TV(self.id)
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

    def __str__(self):
        dic = {}
        dic[self.title] = [s.__str__() for s in self.list_season()]
        return dic.__str__()


class Anime(Show):
    def __init__(self, path: str, title: str, is_valid=False):
        super().__init__(path, title, is_valid)


class Sorter(Server):
    def __init__(self, file_path: str, is_movie=False, for_test=False):
        super().__init__()
        self.is_movie = is_movie
        self.path = file_path
        self.file_name = os.path.basename(self.path)
        self.clean_file_name = os.path.splitext(self.file_name)[0].replace(".", " ")  # get file name with no extension
        if not is_movie:
            self.source = self.determine_source()
        self.ext = os.path.splitext(self.file_name)[1]
        self.make_clean_file_name()
        if not for_test:
            self.media_info = MediaInfo.parse(self.path)
            self.spec = self.video_spec()
            if "format" in self.spec:
                self.codec = self.spec["format"]
            else:
                self.codec = "Unknown_codec"
            self.lang = self.determine_language()
        if not is_movie:
            self.season = self.determine_season()
            self.title = Show("ok", self.determine_title(), is_valid=False).title
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

    def determine_language(self) -> str:
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

            elif track.track_type == "Text":

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

            elif track.track_type == "Menu":

                try:
                    tracks_list_subs.append(track.to_data()["language"])
                except KeyError:
                    pass

        return {"subs": tracks_list_subs, "audio": tracks_list_audio}

    def determine_resolution(self):
        if "1080" in self.file_name:
            return "1080"
        elif "720" in self.file_name:
            return "720"
        elif "480" in self.file_name:
            return "480"
        else:
            try:
                return self.spec["height"]
            except KeyError:
                return "no resolution"

    def video_spec(self) -> dict:
        """Retourne un dictionnaire contenant toute les information lier à une piste vidéo"""
        media_info = self.media_info
        for track in media_info.tracks:
            if track.track_type == "Video":
                return track.to_data()
        return {}

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
            return forbiden_car(
                f"{self.title} - [{self.lang} {self.determine_resolution()} {self.codec}] -Strange {self.ext}")
        else:
            return forbiden_car(
                f"{self.title} - S{self.season}E{self.ep} - [{self.lang} {self.determine_resolution()} {self.codec}] -{self.source} {self.ext}")


class Movie(Server):

    def __init__(self, path: str, title: str, is_valid=False):
        super().__init__()
        self.path = path
        if not is_valid:
            try:
                self.search.movie(query=title)
                self.title = self.search.results[0]["name"]
                super().update_tmdb_db(self.title, tmdb.Movies(self.search.results[0]["id"]).info())
            except IndexError:
                log(f"Can't determine the movie named {title}", error=True)
        else:
            self.title = title
            if not self.title in self.tmdb_db:
                self.id = self.search.movie(query=title)
                self.id = self.search.results[0]['id']
                self.tmdb = tmdb.Movies(self.id)
                self.info = self.tmdb.info()
                super().update_tmdb_db(self.title, self.info)
            else:
                self.info = self.tmdb_db[title]
                self.id = self.info['id']
                self.tmdb = tmdb.Movies(self.id)

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
        self.res = int(self.file_name.split(" - ")[2].split(" ")[1])
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
        super().__init__()
        self.shows_dirs = self.conf["shows_dir"]
        self.anime_dirs = self.conf["anime_dir"]
        self.movie_dirs = self.conf["movie_dir"]
        self.to_sort_anime = self.conf["sorter_anime_dir"]
        self.to_sort_show = self.conf["sorter_show_dir"]
        self.to_sort_movie = self.conf["sorter_movie_dir"]
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

    def var(self, anime=False, shows=False, movie=False) -> tuple[dict, Anime | Show | Movie, list, str]:
        if (anime):
            dic = self.animes
            r = Anime
            dirs = self.conf["anime_dir"]
            lib = ANIME_LIB
        elif (shows):
            dic = self.shows
            r = Show
            dirs = self.conf["shows_dir"]
            lib = SHOWS_LIB
        elif (movie):
            dic = self.movies
            r = Movie
            dirs = self.conf["movie_dir"]
            lib = MOVIES_LIB
        return (dic, r, dirs, lib)

    def find_tmdb_title(self, title: str, anime=False, shows=False, movie=False):
        with open(os.path.join(VAR_DIR, TMDB_TITLE), "r", encoding="utf-8") as f:
            for lines in f:
                lines = lines.split(" : ")
                if lines[0] == title:
                    return lines[1].strip().replace("\n", "")
        if anime or shows:
            self.search.tv(query=title)
        else:
            self.search.movie(query=title)
            try:
                with open(os.path.join(VAR_DIR, TMDB_TITLE), "a", encoding="utf-8") as f:
                    f.write(f"{title} : {self.search.results[0]['name']}\n")
                super().update_tmdb_db(self.search.results[0]["name"], self.search.results[0])
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
                path = os.path.join(dir, title)
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
            self.update_lib(title, None, delete=True)
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
                if os.path.isfile(path):
                    s = Sorter(path, movie)
                    self.add_file(s, anime, shows, movie)
                elif os.path.isdir(path):
                    extract_files(path, self.to_sort_anime)
                    self.sort(anime, shows, movie)
        elif type(dir) == list:
            for dirs in dir:
                for file in os.listdir(dirs):
                    path = os.path.join(dirs, file)
                    if os.path.isfile(path):
                        s = Sorter(path, movie)
                        self.add_file(s, anime, shows, movie)
                    elif os.path.isdir(path):
                        extract_files(path, self.to_sort_anime)
                        self.sort(anime, shows, movie)

    def serve_forever(self):
        try:
            while True:
                if type(self.anime_dirs) == str and os.listdir(self.anime_dirs) != []:
                    self.sort(anime=True)
                elif type(self.anime_dirs) == list:
                    for dir in self.anime_dirs:
                        if os.listdir(dir) != []:
                            self.sort(anime=True)
                if type(self.shows_dirs) == str and os.listdir(self.shows_dirs) != []:
                    self.sort(shows=True)
                elif type(self.shows_dirs) == list:
                    for dir in self.shows_dirs:
                        if os.listdir(dir) != []:
                            self.sort(shows=True)
                if type(self.movie_dirs) == str and os.listdir(self.movie_dirs) != []:
                    self.sort(movie=True)
                elif type(self.movie_dirs) == list:
                    for dir in self.movie_dirs:
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


class Feed(DataBase):

    def __init__(self):
        super().__init__()
        self.feed_dict = self.get_feed()

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
            for words in self.conf["select_words_rss"]:
                if words in entry.title:
                    dicto[entry.title] = entry.link
            for words in self.conf["banned_words_rss"]:
                if words not in entry.title:
                    dicto[entry.title] = entry.link
        return dicto

    def sort_feed(self) -> dict:
        r = {}
        for feed_list in self.feed_dict:
            for feed in self.feed_dict[feed_list]:
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
                                r[f"{ep.title} - S{ep.season}E{ep.ep} {ep.ext}"] = link
                        elif "show" in feed_list:
                            if not self.have_ep(ep, shows=True):
                                r[f"{ep.title} - S{ep.season}E{ep.ep} {ep.ext}"] = link
                    else:
                        mv = Sorter(ep, is_movie=True, for_test=True)
                        if not self.have_ep(ep, movie=True):
                            r[f"{mv.title} - {ep.ext}"] = link
        return r


def main():
    Server(enable=False).check_system_files()
    db = DataBase()
    feed = Feed()
    print(feed.feed_dict)
    print(feed.sort_feed())
    # print(db.find("naruto", anime=True).delete_season(1))
    db.sort(anime=True)
    # print(db.find("naruto", anime=True))
    # db.serve_forever()


if __name__ == "__main__":
    main()
