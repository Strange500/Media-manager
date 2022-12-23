import json
import os
import shutil
import time
from copy import deepcopy
from types import NoneType

import feedparser
import requests
import tmdbsimple as tmdb
from pymediainfo import MediaInfo

tmdb.API_KEY = "91d34b37526d54cfd3d6fcc5c50d0b31"
tmdb.REQUESTS_TIMEOUT = 5  # seconds, for both connect and read

import datetime


###CLASS###
class Anime:
    """Provide a view on the anime"""

    def __init__(self, title) -> None:
        search = tmdb.Search()
        os.makedirs("anime_database", exist_ok=True)

        try:
            if not f"{title}.json" in os.listdir("anime_database"):
                self.__id = search.tv(query=title)
                self.__id = search.results[0]['id']
                self.__tmbd = tmdb.TV(self.id)
                self.__info = self.__tmbd.info()
            else:
                with open(f"anime_database/{title}.json", "r") as f:
                    try:
                        self.__info = json.load(f)
                    except json.decoder.JSONDecodeError:
                        f.close()
                        try:
                            os.remove(f"anime_database/{title}.json")
                        except FileNotFoundError:
                            pass
                        self.__init__(title)
                        return

                    self.__id = self.info['id']

            self.__title = self.info["name"]
            self.__season = self.info["number_of_seasons"]
            self.__ep = self.info["number_of_episodes"]
            try:
                with open(f"anime_database/{forbiden_car(self.title)}.json", "w") as f:
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
        self.media_info = MediaInfo.parse(self.path)

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
        file = self.file_name
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

    def __str__(self) -> str:
        return f"{self.title()} - S{self.season}E{self.ep} - .mkv"


class File():
    def determine_source(self) -> str:
        """return the source of a video from it's file name"""
        title, source = self.file_name, ""
        if "[" in title and "]" in title:
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
        # while temp_file!="": #isolate all number in file_name then associate number with season
        #     nb=""
        #     try:
        #         while temp_file[0] not in [str(i) for i in range(0,10)]:
        #             temp_file=temp_file[1:]
        #     except IndexError:
        #         break
        #     try:
        #         while temp_file[0] in [str(i) for i in range(0,10)] :
        #             nb=nb+temp_file[0]
        #             temp_file=temp_file[1:]
        #         if len(nb)<4:
        #             ls.append(nb)

        #     except IndexError:
        #         if len(nb)<4:
        #             ls.append(nb)
        ls = isolate_numbers(file)
        # if ls[0]==[i for i in file if file.index(i) in [0,1,2] and i in [str(i) for i in range(0,10)]]:
        #     ls.pop(0)
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
        for encode in ["h264", "x264", "avc1", "h.264"]:
            if encode in self.file_name.lower():
                return "h264"
        for encode in ["hevc", "h265", "x265", "hvc1", "h.265"]:
            if encode in self.file_name.lower():
                return "h265"
        try:
            codec = self.__video_spec["codec_id"].lower()
            for encode in ["hevc", "h265", "x265", "hvc1", "h.265"]:
                if encode in codec:
                    return "h265"
            for encode in ["h264", "x264", "avc1", "h.264"]:
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

        self.__file_name = path_to_file.split("/")[-1].strip()
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
            analasing = File(key)
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
            for select in select_word:
                if select in title:
                    selected = True
                    break
                else:
                    selected = False
            if not selected:
                dicto.pop(title)
        dictoo = deepcopy(dicto)
        for title in dicto:
            for banned in banned_words:
                if banned in title:
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


###variable###

ls, config = open("config.txt", 'r', encoding="utf-8").read().split("\n"), {}
for elt in ls:
    config[elt.split(" : ")[0]] = elt.split(" : ")[1]
del ls

if "sources.txt" not in os.listdir():
    open("sources.txt", "w")
if "nyaa.json" not in os.listdir():
    json.dump({}, open("nyaa.json", "w"))
if "anime_id.json" not in os.listdir():
    json.dump({}, open("anime_id.json", 'w'))
if "anime_titles_database.json" not in os.listdir():
    json.dump({}, open("anime_titles_database.json", 'w'))
if "judas_anime_lib.json" not in os.listdir():
    json.dump({}, open("judas_anime_lib.json", 'w'))

banned_words, select_words = open("banned_words.txt", "r", encoding="utf-8").read().split("\n"), open(
    "select_words.txt", "r", encoding="utf-8").read().split("\n")
sources = open("sources.txt", "r").read().split("\n")
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
for elt in ls:
    try:
        os.makedirs(elt, exist_ok=True)
    except:
        pass

os.makedirs("torrent", exist_ok=True)

if "rss.txt" not in os.listdir():
    open("rss.txt", "w")
if "title_romaji.txt" not in os.listdir():
    open("title_romaji.txt", "w")
if "banned_words.txt" not in os.listdir():
    open("banned_words.txt", "w")
if "select_words.txt" not in os.listdir():
    open("select_words.txt", "w")
if "already_download.txt" not in os.listdir():
    open("already_download.txt", "w")
if "judas_not_vostfr.txt" not in os.listdir():
    open("judas_not_vostfr.txt", "w")
if "judas_vostfr.txt" not in os.listdir():
    open("judas_vostfr.txt", "w")


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
    with open("title_romaji.txt") as f:
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
        open("title_romaji.txt", "a").write(f"{title} : {tt}\n")
    except IndexError:
        return title
    except UnicodeEncodeError:
        return title
    except requests.exceptions.HTTPError:
        return title
    return tt


def mise_en_cache(file: str, string: str) -> None:
    open(file, "ab").write(bytes(string, encoding="utf-8"))


def extract(dir):
    if "/" in dir:
        parent_dir="/".join(dir.split("/")[:-1])
    elif "\\" in dir:
        parent_dir="\\".join(dir.split("\\")[:-1])
    for file in os.listdir(dir):
        shutil.move(f'{dir}/{file}',parent_dir)
    shutil.rmtree(dir)

def check_cache(file) -> str:
    open(file, "r", encoding="utf-8").read()


def log(to_log: str) -> None:
    if type(to_log) == str:
        open("log.txt", "a", encoding="utf-8").write(to_log + "\n")


def get_anime() -> None:
    ### remplacer anilist par imdb ####
    for dir in download_dir:
        for file in os.listdir(dir):
            if "MOVIE" not in file and ("mp4" in file or "mkv" in file):
                if "E:" in dir:
                    try:
                        shutil.move(f'{dir}/{file}', sorter_dir[0])
                    except shutil.Error:
                        os.remove(f"{sorter_dir[1]}/{file}")
                        shutil.move(f'{dir}/{file}', sorter_dir[0])
                    except OSError:
                        shutil.move(f'{dir}/{file}', sorter_dir[1])
                else:
                    try:
                        shutil.move(f'{dir}/{file}', sorter_dir[1])
                    except shutil.Error:
                        os.remove(f"{sorter_dir[0]}/{file}")
                        shutil.move(f'{dir}/{file}', sorter_dir[1])
                    except OSError:
                        shutil.move(f'{dir}/{file}',sorter_dir[0])
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

        elif os.path.isfile(f"{dir}/{file}") and ("mp4" in file or "mkv" in file):
            ls.append(file)
    return ls


def test_mode():
    #     ls=open("test.txt","r",encoding="utf-8").read().split("\n")
    #     # #print(File("[Tsundere-Raws] DanMachi S4 - 06 [WEB 1080p x264 AAC].mp4").season)
    #     for file in  ls:
    #     # for file in os.listdir():
    #     # print(File("[Pikari-Teshima] Shokei Shôjo no Virgin Road 12 VOSTFR [Web-Rip 1080p AAC].mkv"))
    #         # if "mkv" in file or "mp4" in file:
    test = File("Blue.Exorcist.S02E01.VOSTFR.FHD.1080p.x264-LIGHTNING.mkv")
    print(test)


#             # print(test.file_name)
#             print(title_to_romaji(test.title))
#     # fedd=FeedAnime("https://nyaa.si/?page=rss&u=Tsundere-Raws",["720","VF","576p"],["VOSTFR","1080"])
#     # pprint(fedd.filtered_ep)
#     # pprint(fedd.ep)
#     # print(f'{2:03}')
#     # print("####TEST MODE####")


###specific to database.py ############
def ep_file(file):
    print(file)
    if " - " in file:
        return file.split(" - ")[1]


def merge(folder1, folder2):
    """move file from 2 to 1"""
    if folder1 == folder2:
        return
    list_folder1 = os.listdir(folder1)
    list_folder2 = os.listdir(folder2)
    for file in list_folder2:
        # fichier en double non video
        if file in list_folder1 and not os.path.isdir(folder2 + "/" + file) and "mkv" not in file and "mp4" not in file:
            print("not ep" + " " + file)
            os.remove(folder2 + "/" + file)
        # fichier pas en double et non video
        elif file not in list_folder1 and not os.path.isdir(
                folder2 + "/" + file) and "mkv" not in file and "mp4" not in file:
            print(folder2 + "/" + file + " -----> " + folder1 + "/" + file)
            shutil.move(folder2 + "/" + file, folder1 + "/" + file)
        # dossier pas en double
        elif os.path.isdir(folder2 + "/" + file) and file not in list_folder1:
            print(folder2 + "/" + file + " -----> " + folder1 + "/" + file)
            try:
                print(folder2 + "/" + file)
                shutil.move(folder2 + "/" + file, folder1 + "/" + file)
            except:
                pass
            print("dossier " + file)
        # dossier en double
        elif os.path.isdir(folder2 + "/" + file) and file in list_folder1:
            merge(folder1 + "/" + file, folder2 + "/" + file)
        # episode
        elif "mkv" in file or "mp4" in file:
            if list_folder1 != NoneType:
                for file_folder1 in list_folder1:
                    if ep_file(file) == ep_file(file_folder1):
                        try:
                            print(file + " remove")
                            os.remove(folder2 + "/" + file)
                        except FileNotFoundError:
                            pass
                        except:
                            pass
                    else:
                        try:
                            print(folder2 + "/" + file + " -----> " + folder1 + "/" + file)
                            shutil.move(folder2 + "/" + file, folder1 + "/" + file)
                        except FileNotFoundError:
                            pass

            # liste_ep_folder1={}
            # liste_ep_folder2={}
            # for filee in list_folder1:
            #     if "mkv" in filee or "mp4" in filee and " - " in filee:
            #         liste_ep_folder1[ep_file(filee)]=filee
            # for fileee in list_folder2:
            #     if "mkv" in fileee or "mp4" in fileee and " - " in fileee:
            #         liste_ep_folder2[ep_file(fileee)]=fileee
            # for ep in liste_ep_folder2:
            #     if ep in liste_ep_folder1:

    try:
        open("delete.txt", "a").write(folder2 + "\n")
        print(f"deleting {folder2}")
        shutil.rmtree(folder2)
    except:
        pass


def list_anime():
    """liste les different anime ainsi que les dossier correspondant"""
    log(f"[{time_log()}] DATABASE: SCANNING LIBRARY")
    dic = {}
    for dir in anime_dir:
        for file in os.listdir(dir):
            if os.path.isdir(f"{dir}/{file}"):
                try:
                    title = Anime(file).title
                    if title in dic.keys():
                        dic[title].append(f"{dir}/{file}")
                    else:
                        dic[title] = [f"{dir}/{file}"]
                except IndexError:
                    print(f"[WARNING] can't determine {file}")
                except requests.exceptions.JSONDecodeError:
                    print(f"[WARNING] can't determine {file}")
                except requests.exceptions.ConnectTimeout:
                    print(f"[WARNING] can't determine {file}")

    return dic


def determine_merge(dico: dict, dir) -> None:
    for keys in dico.keys():
        os.makedirs(f"{dir}/{forbiden_car(keys)}", exist_ok=True)
        print(keys, dico[keys])
        if len(dico[keys]) > 1:
            for values in dico[keys]:
                try:
                    merge(f"{dir}/{forbiden_car(keys)}", f"{values}")
                except FileNotFoundError:
                    pass
        else:
            if dico[keys][0].split("/")[-1] != forbiden_car(keys):
                try:
                    print("path changed")
                    new = "/".join(dico[keys][0].split("/")[:-1] + [forbiden_car(keys)])
                    os.rename(dico[keys][0], new)
                except FileExistsError:
                    pass


def delete_duplicate() -> None:
    # use os.path.getctime() to choose between duplicate
    ls = []
    # try:
    for dir in anime_dir:
        for anime in os.listdir(dir):
            print(anime)
            try:
                ls = list_season(f"{dir}/{anime}")[0]

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
                                    f"{elt}/{file}"):
                                ep[file.split(" - ")[1].split("E")[-1].strip()] = f"{elt}/{file}"
                            elif os.path.getctime(ep[file.split(" - ")[1].split("E")[-1].strip()]) >= os.path.getctime(
                                    f"{elt}/{file}"):
                                ep[file.split(" - ")[1].split("E")[-1].strip()] = f"{elt}/{file}"
                            else:
                                os.remove(f"{elt}/{file}")
                                print(f"del {file}")
            except IndexError:
                pass
            except FileNotFoundError:
                pass


def check_double():
    """merge anime folder and delete double episode"""
    json.dump(list_anime(), open("anime_lib.json", "w"))
    try:
        determine_merge(json.load(open("anime_lib.json", "r")), "Y:\Ext_serv\sorter\JellyFin\Anime\Airing")

    except:
        determine_merge(json.load(open("anime_lib.json", "r")),
                        "Z:\\install server v2\\sorter\\JellyFin\\Anime\\Airing")
    finally:
        delete_duplicate()
        json.dump(list_anime(), open("anime_lib.json", "w"))


def find_anime_dir(anime: str):
    anime = title_to_romaji(anime)
    for dir in anime_dir:
        for file in os.listdir(dir):
            if anime == title_to_romaji(file):
                return f"{dir}/{file}"
    return "no dir"


def get_source(anime: str):
    """return sources if in file name else return None"""
    if "/" not in anime or "\\" not in anime:
        dir, r = find_anime_dir(anime), None
        if dir == "no dir":
            return
    else:
        dir = anime
    print(dir)
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


def store_nyaa(result: dict):
    database = json.load(open("nyaa.json", "r"))
    for keys in result.keys():
        if not keys in database.keys():
            database[keys] = result[keys]
    json.dump(database, open("nyaa.json", "w"), indent=4)


def find_anime_id(title):
    anime_id = json.load(open("anime_id.json", 'r'))
    anime = title_to_romaji(title)

    if anime not in anime_id.keys():
        anime_id[anime] = Anime(anime).id
        json.dump(anime_id, open("anime_id.json", "w"), indent=4)
        return anime_id[anime]
    else:
        for keys in anime_id:
            if keys == anime:
                return anime_id[keys]


def find_alternative_title(title):
    id = str(find_anime_id(title))
    anime_titles_database = json.load(open("anime_titles_database.json", "r"))
    if id not in anime_titles_database.keys():
        anime_titles_database[id] = [i for i in tmdb.tv.TV(id).alternative_titles()["results"] if
                                     i["iso_3166_1"] in ["JP", "MX", "PL", "US"]]
        json.dump(anime_titles_database, open("anime_titles_database.json", "w"), indent=4)
        return anime_titles_database[id]
    else:
        for keys in anime_titles_database:
            if keys == id:
                return anime_titles_database[keys]


def prepare_url(search):
    ban = "+".join([f"-{i}" for i in banned_words])
    sel = "+".join(select_words)
    return f"{search}+{ban}+{sel}"


def database_check():
    dic = json.load(open("anime_lib.json", "r"))
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
            log(f"[{time_log()}] DATABASE: (WARNING) {anime.title} episode missing")
            print(f"Missing ep are: " + ",".join(ls))
            missing[anime.title] = ls

    json.dump(missing, open("missing.json", "w"), indent=4)


def download_torrent(url: str, file_name) -> None:
    if f"{forbiden_car(file_name)}.torrent" not in os.listdir("torrent"):
        torrent = requests.request("GET", url)
        os.makedirs("torrent", exist_ok=True)
        open(f"torrent/{forbiden_car(file_name)}.torrent", "wb").write(torrent.content)
        time.sleep(1)


def check_nyaa_database(anime: str, season, ep_number: list) -> tuple:
    database = json.load(open("nyaa.json", "r"))
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


def search_ep(anime: str, season: str, ep_number: list):
    check, file = check_nyaa_database(anime, season, ep_number)
    if check != None:
        download_torrent(check, file_name=file)
        log(f"[{time_log()}] DATABASE: {file} downloaded via nyaa.json")
        return
    elif ep_number == []:
        return
    else:
        anime_source, anime_list = sources, find_alternative_title(anime) + [{"title": anime}]
        prefered_source = get_source(anime_list[0]["title"])
        if prefered_source != None:
            anime_source = [i for i in open("sources.txt", "r").read().split("\n") if prefered_source in i]
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

                        log(f"[{time_log()}] DATABASE: {keys} downloaded via nyaa.si")

                elif ep_number != [] and file.title == title_to_romaji(
                        anime["title"]) and file.episode in ep_number and file.season == season:
                    download_torrent(r.ep[keys], file_name=keys)
                    ep_number.pop(ep_number.index(file.episode))
                    log(f"[{time_log()}] DATABASE: {keys} downloaded via nyaa.si")
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
                        log(f"[{time_log()}] DATABASE: {keys} downloaded via nyaa.si")


def download_missing_ep(missing: dict):
    log(f"[{time_log()}] DATABASE: Searching missing episode")
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


def already_in_folder(file: str, dir: list | None | str = None):
    if dir == None:
        t = title_to_romaji(File(file).title)
        ls_lib = json.load(open("anime_lib.json", "r"))
        try:
            dir = [ls_lib[anime] for anime in ls_lib if t == anime][-1]
        except IndexError:
            print("here")
            os.makedirs(f"{anime_dir[0]}/{LightFile(file).title}")
            json.dump(list_anime(),open("anime_lib.json","w"))

            return already_in_folder(file, dir)
    ls=[]
    try:
        ep=file.split(" - ")[1]
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


if __name__ == '__main__':
    test_mode()
