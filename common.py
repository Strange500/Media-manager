import ctypes
import datetime
import json
import os
import platform
import shutil
import socket
import time
from typing import Dict, Union
from urllib.parse import urlparse, quote
import appdirs
import requests
import tmdbsimple as tmdb
from copy import deepcopy

if platform.system() == "Linux":
    import psutil
elif platform.system() == "Windows":
    import wmi
hostname = socket.gethostname()
IP = socket.gethostbyname(hostname)

APP_NAME = "Media-Manager"
APP_AUTHOR = "Strange"
VAR_DIR = appdirs.user_cache_dir(appname=APP_NAME, appauthor=APP_AUTHOR)
CONF_DIR = appdirs.user_config_dir(appname=APP_NAME, appauthor=APP_AUTHOR)
CONF_FILE = "server.conf"
TMDB_TITLE = os.path.join("data", "tmdb_tile.json")
ANIME_LIB = os.path.join("lib", "anime.json")
SHOWS_LIB = os.path.join("lib", "shows.json")
MOVIES_LIB = os.path.join("lib", "movie.json")
TMDB_DB = os.path.join("data", "tmdb_db.json")
FEED_STORAGE = os.path.join("data", "feed_storage.json")
RSS_ANIME = os.path.join("rss", "rss_anime.dat")
RSS_MOVIE = os.path.join("rss", "rss_movie.dat")
RSS_SHOW = os.path.join("rss", "rss_show.dat")
QUERY_SHOW = os.path.join("data", "query_show.dat")
QUERY_ANIME = os.path.join("data", "query_anime.dat")
QUERY_MOVIE = os.path.join("data", "guery_movie.dat")
GGD_LIB = os.path.join("data", "ggd_lib.json")
list_language = ["french"]
SUB_LIST = {"VOSTFR": "fre", "OmdU": "ger"}

os.makedirs(VAR_DIR, exist_ok=True)
os.makedirs(CONF_DIR, exist_ok=True)


def delete_empty_dictionnaries(dic: dict) -> dict:
    temp = deepcopy(dic)
    for key in temp:
        if dic[key] == {}:
            dic.pop(key)
    return dic


def remove_non_ascii(chaine):
    chaine_encodee = chaine.encode('ascii', 'ignore')
    chaine_decodee = chaine_encodee.decode('ascii')
    return chaine_decodee


def list_all_files(directory: str) -> list:
    """
    Recursively lists all files within a directory.

    Args:
        directory (str): The directory path.

    Returns:
        list: A list of file paths found within the directory.

    Raises:
        None

    """
    if not os.path.isdir(directory):
        return []

    list_files = []
    for root, directories, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            list_files.append(file_path)

    return list_files


def is_movie(path_file):
    if not os.path.isfile(path_file):
        raise ValueError("Not a file")
    file_name = os.path.basename(path_file).lower()
    return "movie" in file_name


def compare_dictionaries(dict1, dict2):
    """
    Compares two dictionaries and returns True if they are equal.

    Args:
        dict1 (dict): The first dictionary.
        dict2 (dict): The second dictionary.

    Returns:
        bool: True if the dictionaries are equal, False otherwise.

    Raises:
        ValueError: If either dict1 or dict2 is not a dictionary.

    Example:
        >>> compare_dictionaries({'a': 1, 'b': 2}, {'b': 2, 'a': 1})
        True
        >>> compare_dictionaries({'a': 1, 'b': 2}, {'a': 1, 'b': 3})
        False
    """
    if type(dict1) != dict or type(dict2) != dict:
        raise ValueError("Both arguments must be dictionaries.")

    return sorted(dict1.items()) == sorted(dict2.items())


def delete_unwanted_words(title: str) -> str:
    keywords = ["2nd Season", "1st Season", "3rd Season", "Cour 2", "INTEGRAL", "integrale", "intégrale", "INTEGRALE"]
    for keyword in keywords:
        title = title.replace(keyword, "")
    return title


def split_on_season_word(title: str) -> str:
    keywords = ["Season", "season", "Saison", "saison"]
    for keyword in keywords:
        if keyword in title:
            title = title.split(keyword)[0]
            return title
    return title


def safe_move(src, dst, max_retries=2, retry_delay=1):
    """
    Safely moves a file from the source to the destination path.

    Args:
        src (str): The source file path.
        dst (str): The destination file path.
        max_retries (int, optional): Maximum number of retries in case of PermissionError or RuntimeError. Defaults to 2.
        retry_delay (int, optional): Delay in seconds between retries. Defaults to 1.

    Returns:
        bool: True if the file was successfully moved and removed from the source, False otherwise.

    Raises:
        FileNotFoundError: If the source file does not exist.
        ValueError: If the source file is not a video file.

    """
    if not os.path.isfile(src):
        raise FileNotFoundError(f"{src} is not a file")

    if is_video(src):
        retries = 0
        while retries < max_retries:
            try:
                shutil.move(src, dst)
                if os.path.isfile(src):
                    os.remove(src)
                return True
            except (PermissionError, RuntimeError):
                retries += 1
                time.sleep(retry_delay)

    return False


def extract_files(source_dir, dest_dir) -> None:
    """
    Extracts files from a source directory and moves them to a destination directory.

    Args:
        source_dir (str): The source directory path.
        dest_dir (str): The destination directory path.

    Returns:
        None

    Raises:
        NotADirectoryError: If either the source directory or the destination directory does not exist.

    """
    if not (os.path.isdir(source_dir) and os.path.isdir(dest_dir)):
        raise NotADirectoryError("Both source_dir and dest_dir must be valid directory paths.")

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
    """
    Retrieves the amount of free disk space available in bytes for the specified path.

    Args:
        path (str): The path to the directory or file.

    Returns:
        int: The amount of free disk space in bytes.

    Raises:
        OSError: If the specified path is invalid or inaccessible.

    """
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
    """
    Calculates the total size of a directory in bytes.

    Args:
        directory (str): The path to the directory.

    Returns:
        int: The total size of the directory in bytes.

    Raises:
        NotADirectoryError: If the specified path is not a directory.

    """
    if not os.path.isdir(directory):
        raise NotADirectoryError(f"{directory} is not a directory.")

    total_size = 0

    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            total_size += os.path.getsize(filepath)

    return total_size


def get_dir_and_free(dir: str) -> Dict[int, int]:
    """
    Retrieves the used and free disk space of a directory.

    Args:
        dir (str): The path to the directory.

    Returns:
        dict: A dictionary containing the used and free disk space in bytes.

    Raises:
        NotADirectoryError: If the specified path is not a directory.

    """
    if not os.path.isdir(dir):
        raise NotADirectoryError(f"{dir} is not a directory.")

    dic = {
        "used": get_directory_size(dir),
        "free": get_free_space(dir)
    }
    return dic


def get_total_free_and_used(list_dir):
    """
    Retrieves the total used and free disk space of a directory or a list of directories.

    Args:
        list_dir (str or list): Either a single directory path or a list of directory paths.

    Returns:
        dict: A dictionary containing the total used and free disk space in bytes.

    Raises:
        NotADirectoryError: If any of the specified paths is not a directory.

    """
    dic = {"used": 0, "free": 0}

    if isinstance(list_dir, str):
        if not os.path.isdir(list_dir):
            raise NotADirectoryError(f"{list_dir} is not a directory.")
        return get_dir_and_free(list_dir)
    else:
        for dir in list_dir:
            if not os.path.isdir(dir):
                raise NotADirectoryError(f"{dir} is not a directory.")
            d = get_dir_and_free(dir)
            dic["used"] += d["used"]
            dic["free"] += d["free"]
        return dic


def get_path_with_most_free_space(paths):
    """
    Retrieves the path with the most free disk space from a single path or a list of paths.

    Args:
        paths (str or list): Either a single path or a list of paths.

    Returns:
        str: The path with the most free disk space.

    """
    if isinstance(paths, str):
        return paths

    max_free_space = 0
    path_with_max_free_space = ''

    for path in paths:
        free_space = get_free_space(path)
        if free_space > max_free_space:
            max_free_space = free_space
            path_with_max_free_space = path

    return path_with_max_free_space


def time_log():
    """
    Retrieves the current time and returns it as a formatted string.

    Returns:
        str: The current time in the format "HH:MM:SS".

    """
    # Get the current time
    current_time = datetime.datetime.now()

    # Format the time as a string with the hour, minute, and second
    return current_time.strftime("%H:%M:%S")


def log(to_log, warning=False, error=False):
    """
    Writes a log message to a log file.

    Args:
        to_log (str): The message to be logged.
        warning (bool, optional): Indicates if the log message is a warning. Defaults to False.
        error (bool, optional): Indicates if the log message is an error. Defaults to False.

    Returns:
        None

    """
    if isinstance(to_log, str):
        log_message = ""
        print(to_log)

        if error:
            log_message = f"[{time_log()}] ERROR: {to_log}\n"
        elif warning:
            log_message = f"[{time_log()}] WARNING: {to_log}\n"

        with open(os.path.join(VAR_DIR, "log.txt"), "a", encoding="utf-8") as log_file:
            log_file.write(log_message)


def forbidden_car(name):
    """
    Removes forbidden characters from a file name.

    Args:
        name (str): The file name to be processed.

    Returns:
        str: The processed file name with forbidden characters removed.

    Example:
        >>> forbidden_car("file?name")
        'filename'
    """
    for car in ["?", '"', "/", "\\", "*", ":", "<", ">", "|"]:
        name = name.replace(car, "")
    return name


def delete_from_to(string, fromm, to):
    """
    Deletes a substring from the given string, starting from the specified 'from' substring
    and ending at the specified 'to' substring (both inclusive).

    Args:
        string (str): The original string.
        fromm (str): The starting substring to be deleted.
        to (str): The ending substring to be deleted.

    Returns:
        str: The modified string after deleting the specified substring.

    Raises:
        ValueError: If the 'from' or 'to' substrings are not found in the original string.

    Example:
        >>> delete_from_to("Hello [world], how are you?", "[", "]")
        'Hello , how are you?'
    """
    if fromm not in string:
        raise ValueError(f"'{fromm}' not found in '{string}'")
    if to not in string:
        raise ValueError(f"'{to}' not found in '{string}'")

    result = ""
    while string[0] != fromm:
        result += string[0]
        string = string[1:]

    while string[0] != to:
        string = string[1:]

    string = string[1:]
    return result + string


def isolate_numbers(temp_file):
    """
    Retrieves a list of all numbers present in the given string.

    Args:
        temp_file (str): The input string.

    Returns:
        list: A list of all numbers found in the string.

    Example:
        >>> isolate_numbers("abc 123 xyz 456")
        ['123', '456']
    """
    numbers = []
    current_number = ""

    while temp_file != "":
        if temp_file[0].isnumeric():
            current_number += temp_file[0]
            temp_file = temp_file[1:]
            while temp_file != "" and temp_file[0].isnumeric():
                current_number += temp_file[0]
                temp_file = temp_file[1:]
            numbers.append(current_number)
            current_number = ""
        else:
            temp_file = temp_file[1:]

    return numbers


def check_json(path):
    """
    Checks if the given file is a valid JSON file.

    Args:
        path (str): The path to the file.

    Returns:
        bool: True if the file is a valid JSON file, False otherwise.

    Raises:
        FileNotFoundError: If the file does not exist.

    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"{path} does not exist")

    if "json" not in path:
        return True

    try:
        with open(path, "r", encoding="utf-8") as file:
            json.load(file)
        return True
    except json.decoder.JSONDecodeError:
        return False


def get_temp():
    if platform.system() == "Linux":
        try:
            return psutil.sensors_temperatures()["k10temp"][0].current
        except:
            return -1
    else:
        w = wmi.WMI(namespace="root\OpenHardwareMonitor")
        temperature_infos = w.Sensor()
        for sensor in temperature_infos:
            if sensor.SensorType == u'Temperature' and sensor.name == "CPU Package":
                return sensor.value


def check_url_syntax(url):
    parsed_url = urlparse(url)
    return all([parsed_url.scheme, parsed_url.netloc])


def correct_and_encode_url(url):
    corrected_url = quote(url, safe=':/?=&')  # Encode special characters
    return corrected_url


class Server():
    tmdb_title: dict
    tmdb_db: dict
    conf: dict
    CPU_TEMP: int
    feed_storage: dict
    connectors: list

    connectors = []

    list_file = [ANIME_LIB, QUERY_MOVIE, QUERY_SHOW, MOVIES_LIB, SHOWS_LIB, CONF_FILE, TMDB_TITLE, TMDB_DB,
                 RSS_SHOW, RSS_ANIME,
                 RSS_MOVIE, GGD_LIB, FEED_STORAGE, QUERY_ANIME, os.path.join(CONF_DIR, CONF_FILE)]
    for file in list_file:
        path = os.path.join(VAR_DIR, file)
        if os.path.isfile(path) and check_json(path):
            pass
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if "json" in file:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                json.dump({}, open(path, "w"))
            else:
                open(path, "w")

    tmdb_db = json.load(open(os.path.join(VAR_DIR, TMDB_DB), "r", encoding="utf-8"))
    tmdb_title = json.load(open(os.path.join(VAR_DIR, TMDB_TITLE), "r", encoding="utf-8"))
    feed_storage = json.load(open(os.path.join(VAR_DIR, FEED_STORAGE), "r", encoding="utf-8"))
    query_anime = open(os.path.join(VAR_DIR, QUERY_ANIME), "r").read().split("\n")
    query_show = open(os.path.join(VAR_DIR, QUERY_SHOW), "r").read().split("\n")
    query_movie = open(os.path.join(VAR_DIR, QUERY_ANIME), "r").read().split("\n")

    CPU_TEMP = get_temp()
    TASK_GGD_SCAN = 100

    def load_config(lib: str | None = CONF_DIR) -> dict:
        """
        List of all elements contained in the config:
        - shows_dir
        - movie_dir
        - download_dir
        - sorter_anime_dir
        - clip_load
        - clip_lib
        - temp_dir
        - Judas_dir
        - GGD_Judas
        - Clip
        """
        try:
            config = {}
            with open(os.path.join(lib, CONF_FILE), "r", encoding="utf-8") as f:
                for line in f:
                    if line[0] in ["#", "\n", ""]:
                        continue
                    line = line.replace("\n", "").split(" = ")
                    try:
                        if "," in line[1]:
                            line[1] = [elt.strip() for elt in line[1].split(",")]
                        else:
                            line[1] = line[1].strip()
                        arg1, arg2 = line[0].strip(), line[1]
                    except IndexError as e:
                        print(
                            f"Some values are not set in {CONF_FILE}, please make sure you have all set. Here is the line where the issue occurred: {line}")
                        quit()
                    config[arg1] = arg2

            if config.get("GGD"):
                if config["GGD"] == "FALSE":
                    pass
                elif config["GGD"] == "TRUE":
                    pass
                else:
                    raise ValueError(
                        f"The value of GGD_Judas in {os.path.join(VAR_DIR, CONF_FILE)} must be TRUE or FALSE")
            if config.get("Clip"):
                if config["Clip"] == "FALSE":
                    config.pop("clip_load", None)
                    config.pop("clip_lib", None)
                elif config["Clip"] == "TRUE":
                    pass
                else:
                    raise ValueError(f"The value of Clip in {os.path.join(VAR_DIR, CONF_FILE)} must be TRUE or FALSE")
            if config.get("Downloader"):
                if config["Downloader"] == "FALSE":
                    config.pop("download_dir", None)
                elif config["Downloader"] == "TRUE":
                    pass
                else:
                    raise ValueError(
                        f"The value of Downloader in {os.path.join(VAR_DIR, CONF_FILE)} must be TRUE or FALSE")

            for key, value in config.items():
                if "dir" in key:
                    if isinstance(value, list):
                        for directory in value:
                            if not os.path.isdir(directory):
                                raise NotADirectoryError(f"The directory specified as '{directory}' does not exist")
                    else:
                        if not os.path.isdir(value):
                            raise NotADirectoryError(f"The directory specified as '{value}' does not exist")
                else:
                    if value == "FALSE":
                        config[key] = False
                    elif value == "TRUE":
                        config[key] = True

            return config
        except IOError as e:
            print(e)
            quit()

    conf = load_config()

    def __init__(self, enable=True):

        tmdb.API_KEY = Server.conf["TMDB_API_KEY"]
        tmdb.REQUESTS_TIMEOUT = 10
        self.search = tmdb.Search()

    def check_system_files(self):
        """Checks the system files and ensures their existence or creates them if missing.

        This method checks a list of system files and ensures that they exist in the specified directory. If a file is
        missing or does not pass the JSON validation, it creates an empty file or a JSON file with an empty dictionary.

        Args:
            self: The Server instance.

        Returns:
            None
        """
        list_file = Server.list_file
        for file in list_file:
            path = os.path.join(VAR_DIR, file)
            if os.path.isfile(path) and check_json(path):
                continue
            else:
                if "json" in file:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w") as f:
                        json.dump({}, f)
                else:
                    open(path, "w")

    def update_tmdb_db(self, title: str, info: dict):
        """Updates the TMDB database with the provided title and information.

        This method updates the TMDB database stored in the `tmdb_db` attribute of the Server class. It takes a title as a
        string and information as a dictionary, and adds or updates the entry in the database with the provided title.

        Args:
            self: The Server instance.
            title (str): The title to be added or updated in the TMDB database.
            info (dict): The information associated with the title.

        Returns:
            None
        """
        if not isinstance(title, str):
            raise TypeError(f"title is not a string: {title}")
        if not isinstance(info, dict):
            raise TypeError(f"info is not a dictionary: {info}")
        Server.tmdb_db[title] = info

    def add_tmdb_title(determined_title: str, tmdb_title: str):
        """Adds a TMDB title mapping to the TMDB title database.

        This method adds a mapping between a determined title and its corresponding TMDB title in the TMDB title database
        stored in the `tmdb_title` attribute of the Server class.

        Args:
            determined_title (str): The determined title to be mapped.
            tmdb_title (str): The corresponding TMDB title.

        Returns:
            None
        """
        if not isinstance(determined_title, str):
            raise TypeError(f"determined_title is not a string: {determined_title}")
        if not isinstance(tmdb_title, str):
            raise TypeError(f"tmdb_title is not a string: {tmdb_title}")
        Server.tmdb_title[determined_title] = tmdb_title

    def get_tmdb_title(determined_title: str) -> str | None:
        """
        Retrieves the corresponding TMDB title for a determined title from the TMDB title database.

        This method looks up the TMDB title associated with a determined title in the TMDB title database stored
        in the `tmdb_title` attribute of the Server class.

        Args:
            determined_title (str): The determined title for which to retrieve the TMDB title.

        Return:
            str or None: The corresponding TMDB title if found, or None if not found.

        Raises:
            TypeError: If determined_title is not a string.
        """
        if not isinstance(determined_title, str):
            raise TypeError(f"determined_title is not a string: {determined_title}")
        if Server.tmdb_db.get(determined_title, None) is None:
            return None
        if Server.tmdb_db.get(determined_title, None).get("name", None) is None:
            return Server.tmdb_db.get(determined_title, None).get("title", None)
        return Server.tmdb_db.get(determined_title, None).get("name", None)

    def store_tmdb_info(self, id: int, show=False, movie=False):
        """Stores TMDB information for a given ID in the TMDB database.

        This method retrieves information from TMDB for a specified ID and stores it in the TMDB database (`tmdb_db`)
        of the Server class. The type of information retrieved depends on the `show` and `movie` flags.

        Args:
            id (int): The TMDB ID for which to retrieve and store information.
            show (bool, optional): Flag indicating whether the ID corresponds to a TV show. Defaults to False.
            movie (bool, optional): Flag indicating whether the ID corresponds to a movie. Defaults to False.

        Returns:
            dict: The retrieved TMDB information.

        Raises:
            TypeError: If the provided ID is not an integer.
            ValueError: If both `show` and `movie` flags are True or both are False, or if no information is found for the ID.
        """
        if not isinstance(id, int):
            raise TypeError(f"id is not an integer: {id}")
        if (show and movie) or not (show or movie):
            raise ValueError("You have to specify either show or movie")
        if show:
            s = tmdb.TV(id)
            info = s.info(append_to_response="seasons,translations")
            t = "name"
        elif movie:
            s = tmdb.Movies(id)
            info = s.info(append_to_response="translations")
            t = "title"
        else:
            raise ValueError("You have to specify either show or movie")
        if compare_dictionaries(info, {}):
            raise ValueError(f"No information found for ID: {id}")
        self.update_tmdb_db(info[t], info)
        return info

    def get_tmdb_info_by_id(self, id: int, show: int | None = False, movie: bool | None = False):
        if not isinstance(id, int):
            raise TypeError(f"id should be int not {type(id)}")
        else:
            for keys in Server.tmdb_db:
                if Server.tmdb_db[keys]["id"] == id:
                    return Server.tmdb_db[keys]
            info = self.store_tmdb_info(id, show=show, movie=movie)
            return info

    def get_tmdb_info(self, title: str, show=False, movie=False):
        """Retrieves the TMDB information for a given title from the TMDB database.

        This method retrieves the TMDB information associated with a given title from the TMDB database (`tmdb_db`).
        The `title` argument should be a string representing the title to retrieve the information for. The `show` and `movie`
        arguments specify whether the title corresponds to a TV show or a movie, respectively.

        If the `show` flag is True, it checks if the retrieved information includes "seasons" data. If not, it calls the
        `store_tmdb_info` method to update the information by fetching the TMDB data for the corresponding show ID.
        After updating the information, it retrieves the updated data from the TMDB database.

        If the title is not found in the TMDB database, it attempts to find a TMDB title using the `find_tmdb_title` method.
        If the `find_tmdb_title` method returns `None` or `False`, indicating that no title was found, it returns `None`.
        Otherwise, it retrieves the TMDB information for the found title.

        Args:
            title (str): The title for which to retrieve the TMDB information.
            show (bool, optional): Flag indicating whether the title corresponds to a TV show. Defaults to False.
            movie (bool, optional): Flag indicating whether the title corresponds to a movie. Defaults to False.

        Returns:
            Union[dict, None]: The TMDB information for the given title if found in the TMDB database, None otherwise.

        Raises:
            TypeError: If the provided title is not a string.
            ValueError: If both the `show` and `movie` flags are set to True or both are set to False.
        """
        if not isinstance(title, str):
            raise TypeError("title is not a string")
        if (show and movie) or not (show or movie):
            raise ValueError("You have to specify either show or movie")
        info = Server.tmdb_db.get(title, None)
        if info is not None:
            if show:
                if info.get("seasons", None) is None:
                    self.store_tmdb_info(info["id"], show=True, movie=False)
                    info = Server.tmdb_db.get(title, None)
                    print(Server.tmdb_db)
                return info
            if movie:
                return info
        else:
            info = self.get_tmdb_title(title, show=show, movie=movie)
            print(info)
            return info

    def find_tmdb_title(self, title: str, anime=False, shows=False, movie=False) -> str | bool:
        """Finds the TMDB title for a given title and stores it in the TMDB database if not already present. Also using this function add all related information tmdb_db

        This method searches for a TMDB title based on the given title. If the TMDB title is already present in the
        TMDB database (`tmdb_db`), it is returned. Otherwise, if the `anime` or `shows` flags are set to True, it performs
        a TV show search using the `search.tv` method. If the `movie` flag is set to True, it performs a movie search
        using the `search.movie` method. The first result from the search is used to store the TMDB information in the
        TMDB database and associate it with the given title.

        Args:
            title (str): The title for which to find the TMDB title.
            anime (bool, optional): Flag indicating whether the title corresponds to an anime. Defaults to False.
            shows (bool, optional): Flag indicating whether the title corresponds to a TV show. Defaults to False.
            movie (bool, optional): Flag indicating whether the title corresponds to a movie. Defaults to False.

        Returns:
            Union[str, False]: The TMDB title if found and stored in the TMDB database, False if no title is found.

        Raises:
            TypeError: If the provided title is not a string.
        """
        if not isinstance(title, str):
            raise TypeError(f"{title} is not a string")
        tmdb_title = Server.get_tmdb_title(title)
        if tmdb_title is not None:
            return tmdb_title
        elif anime or shows:
            self.search.tv(query=title)
            t = "name"
        else:
            self.search.movie(query=title)
            t = "title"
        try:
            self.store_tmdb_info(self.search.results[0]["id"], show=(shows or anime), movie=movie)
            Server.add_tmdb_title(title, self.search.results[0][t])
            return self.search.results[0][t]
        except IndexError:
            log(f"No title found for {title}", warning=True)
            return False
        except requests.exceptions.ReadTimeout:
            log("Connection timeout to tmdb", warning=True)
            return False

    def delete_tmdb_db_item(self, title: str) -> bool:
        """
        Deletes an item from the TMDB database.

        This method removes an item with the given title from the TMDB database (`tmdb_db`). If the item is found
        in the database, it is removed from the database and the method returns True. If the item is not found,
        the method returns False.

        Args:
            title (str): The title of the item to be deleted from the TMDB database.

        Returns:
            bool: True if the item was successfully deleted, False if the item was not found in the TMDB database.
        """
        item = Server.tmdb_db.get(title, None)
        if item is None:
            return False
        else:
            Server.tmdb_db.pop(title)
            return True

    def dict_have_ep(self, dic: dict, identifier: int, season: int, episode: int) -> None | bool:
        if dic.get(str(identifier), None) is None:
            return None
        if dic[str(identifier)].get(str(season).zfill(2), None) is None:
            return None
        if dic[str(identifier)][str(season).zfill(2)].get(str(episode).zfill(2), None) is None:
            return None
        return True

    def delete_query(identifier: int, anime=False, show=False, movie=False):
        if not (anime or show or movie):
            raise ValueError("should choose between anime,show or movie")
        file, text = None, None
        if anime and str(identifier) in Server.query_anime:
            Server.query_anime.remove(str(identifier))
            file, text = QUERY_ANIME, "\n".join(Server.query_anime)
        elif show and str(identifier) in Server.query_show:
            Server.query_show.remove(str(identifier))
            file, text = QUERY_ANIME, "\n".join(Server.query_anime)
        elif movie and str(identifier) in Server.query_movie:
            Server.query_movie.remove(str(identifier))
            file, text = QUERY_ANIME, "\n".join(Server.query_anime)
        if file is not None and text is not None:
            with open(os.path.join(VAR_DIR, file), "w") as f:
                f.write(text)
