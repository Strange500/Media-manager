import datetime
import json
import os
import platform
import shutil
import subprocess
import threading
import time
from typing import Dict

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
FEED_STORAGE = os.path.join("lib", "feed_storage.json")
RSS_ANIME = "rss_anime.dat"
RSS_MOVIE = "rss_movie.dat"
RSS_SHOW = "rss_show.dat"
QUERY_SHOW = "query_show.dat"
QUERY_MOVIE = "guery_movie.dat"
GGD_LIB = os.path.join("lib", "ggd_lib.json")
list_language = ["french"]
SUB_LIST = {"VOSTFR": "fre", "OmdU": "ger"}


def list_all_files(directory: str) -> list:
    """
    Recursively lists all files within a directory.

    Args:
        directory (str): The directory path.

    Returns:
        list: A list of file paths found within the directory.

    Raises:
        None

    Example:
        >>> list_all_files('/path/to/directory')
        ['/path/to/directory/file1.txt', '/path/to/directory/file2.jpg', ...]
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

    Example:
        >>> safe_move('/path/to/source/file.mp4', '/path/to/destination/file.mp4')
        True
    """
    if not os.path.isfile(src):
        raise FileNotFoundError(f"{src} is not a file")

    if not is_video(src):  # Assuming there's a separate function called 'is_video' to check if it's a video file
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

    Example:
        >>> extract_files('/path/to/source', '/path/to/destination')
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

    Example:
        >>> get_free_space('/path/to/directory')
        123456789
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

    Example:
        >>> get_directory_size('/path/to/directory')
        123456789
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

    Example:
        >>> get_dir_and_free('/path/to/directory')
        {'used': 123456789, 'free': 987654321}
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

    Example:
        >>> get_total_free_and_used('/path/to/directory')
        {'used': 123456789, 'free': 987654321}

        >>> get_total_free_and_used(['/path/to/directory1', '/path/to/directory2'])
        {'used': 246801579, 'free': 1975308642}
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

    Example:
        >>> get_path_with_most_free_space('/path/to/directory')
        '/path/to/directory'

        >>> get_path_with_most_free_space(['/path/to/directory1', '/path/to/directory2'])
        '/path/to/directory2'
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

    Example:
        >>> time_log()
        '12:34:56'
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

    Example:
        >>> log("This is a log message.")
    """
    if isinstance(to_log, str):
        log_message = ""

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

    Example:
        >>> check_json("data.json")
        True
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


class Server():
    tmdb_title: dict
    tmdb_db: dict
    conf: dict

    list_file = [ANIME_LIB, QUERY_MOVIE, QUERY_SHOW, MOVIES_LIB, SHOWS_LIB, CONF_FILE, TMDB_TITLE, TMDB_DB,
                 RSS_SHOW, RSS_ANIME,
                 RSS_MOVIE, GGD_LIB, FEED_STORAGE]
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
    tmdb_title = json.load(open(os.path.join(VAR_DIR, TMDB_TITLE), "r", encoding="utf-8"))

    def load_config(lib: str | None = VAR_DIR) -> dict:
        """
        List of all elements contained in the config:
        - shows_dir
        - movie_dir
        - serv_dir
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
                    config.pop("GGD_dir", None)
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
                    config.pop("torrent_dir", None)
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
        if enable:
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
        list_file = [ANIME_LIB, QUERY_MOVIE, QUERY_SHOW, MOVIES_LIB, SHOWS_LIB, CONF_FILE, TMDB_TITLE, TMDB_DB,
                     RSS_SHOW, RSS_ANIME, RSS_MOVIE, GGD_LIB]
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

    def get_tmdb_title(determined_title: str):
        """Retrieves the corresponding TMDB title for a determined title from the TMDB title database.

        This method looks up the TMDB title associated with a determined title in the TMDB title database stored
        in the `tmdb_title` attribute of the Server class.

        Args:
            determined_title (str): The determined title for which to retrieve the TMDB title.

        Returns:
            str or None: The corresponding TMDB title if found, or None if not found.
        """
        if not isinstance(determined_title, str):
            raise TypeError(f"determined_title is not a string: {determined_title}")
        return Server.tmdb_title.get(determined_title, None)

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
            info = s.info(append_to_response="seasons")
            t = "name"
        elif movie:
            s = tmdb.Movies(id)
            info = s.info()
            t = "title"
        else:
            raise ValueError("You have to specify either show or movie")
        if compare_dictionaries(info, {}):
            raise ValueError(f"No information found for ID: {id}")
        self.update_tmdb_db(info[t], info)
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
                if info.get("seasons") is None:
                    self.store_tmdb_info(info["id"], show=True, movie=False)
                    info = Server.tmdb_db.get(title, None)
                return info
            if movie:
                return info
        else:
            found_title = self.find_tmdb_title(title, shows=True)
            info = Server.tmdb_db.get(found_title, None)
            if info is False:
                return None
            return info

    def find_tmdb_title(self, title: str, anime=False, shows=False, movie=False):
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
            raise TypeError("title is not a string")
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
            self.store_tmdb_info(self.search.results[0]["id"], shows=(shows or anime), movie=movie)
            Server.add_tmdb_title(title, self.search.results[0][t])
            return self.tmdb_db.get(self.search.results[0][t])
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


class Show(Server):

    def __init__(self, path: str, title: str, is_show=True):
        """
        Initializes a Show object.

        Args:
            path (str): The path of the show.
            title (str): The title of the show.
            is_show (bool, optional): Flag indicating whether the title corresponds to a TV show. Defaults to True.

        Raises:
            Exception: If the show with the given title is not found.
            Exception: If no information is found for the show with the given title.
        """
        super().__init__()
        self.path = path
        self.is_show = is_show
        self.title = self.find_tmdb_title(title, shows=is_show, anime=(not is_show), movie=False)
        if self.title is False:
            raise Exception(f"Show {title} not found")
        self.info = super().get_tmdb_info(title, show=True)
        if self.info is None:
            raise Exception(f"Show {title} no information found")
        self.id = self.info["name"]
        self.seasons_created = self.list_season()
        self.seasons_theoric = self.info["seasons"]

    def list_season(self):
        """
        Retrieves the list of seasons for the show.

        Returns:
            Union[list, None]: The list of seasons for the show if available, None otherwise.
        """
        if self.is_show:
            result = DataBase.shows.get(str(self.id), None)
            if result is None:
                return None
            return DataBase.shows[str(self.id)]["seasons"]
        else:
            result = DataBase.animes.get(str(self.id), None)
            if result is None:
                return None
            return DataBase.animes[str(self.id)]["seasons"]

    def update_data(self):
        """
        Updates the data for the show in the TMDB database.

        This method calls the parent class's `update_tmdb_db` method to update the TMDB database with the latest information
        for the show. It retrieves the show's information using the TMDB API and appends the "seasons" data to the request.
        The updated data is then stored in the TMDB database using the show's title as the key.

        Raises:
            Exception: If the update of the TMDB database fails.
        """
        try:
            super().update_tmdb_db(self.title, tmdb.TV(self.id).info(append_to_response="seasons"))
        except Exception:
            raise Exception("Failed to update TMDB database for the show.")

    def delete(self):
        """
        Deletes the show or movie data.

        This method deletes the show or movie data associated with the object. It removes the directory specified by
        the `path` attribute using `shutil.rmtree`. It also deletes the corresponding item from the TMDB database
        using the `delete_tmdb_db_item` method of the `Server` class.

        Raises:
            NotADirectoryError: If the `path` attribute does not represent a valid directory.
        """
        if os.path.isdir(self.path):
            shutil.rmtree(self.path)
            Server.delete_tmdb_db_item(self.title)
        else:
            raise NotADirectoryError("Invalid directory path")

    def delete_ep(self, season_number: int, ep_number: int) -> bool:
        """
        Deletes an episode from the Show object.

        Args:
            season_number (int): The season number of the episode.
            ep_number (int): The episode number.

        Returns:
            bool: True if the episode is successfully deleted, False otherwise.

        Raises:
            TypeError: If the episode_number or season_number parameters are not of type int.
        """
        if not isinstance(ep_number, int):
            raise TypeError("Episode number should be of type int")
        if not isinstance(season_number, int):
            raise TypeError("Season number should be of type int")

        elt = self.seasons_created.get(str(season_number).zfill(2), None)
        if elt is None:
            return False
        else:
            nb = str(ep_number).zfill(2)
            ep = elt["current_episode"].get(nb, None)
            if ep is None:
                nb = str(ep_number).zfill(3)
                ep = elt["current_episode"].get(nb, None)
                if ep is None:
                    nb = str(ep_number).zfill(4)
                    ep = elt["current_episode"].get(nb, None)
                    if ep is None:
                        return False

            e = Episode(Season(self, elt['path'], elt), ep["path"])
            e.delete()
            DataBase.delete_episode(self.id, ep_number, season_number, show=self.is_show, anime=(not self.is_show))
            return True

    def delete_season(self, season_number: int) -> bool:
        """
        Deletes a season from the show object.

        Args:
            season_number (int): The season number to delete.

        Returns:
            bool: True if the season is successfully deleted, False otherwise.

        Raises:
            TypeError: If the season_number parameter is not of type int.
        """
        if not isinstance(season_number, int):
            raise TypeError("Season number should be of type int")

        season = self.seasons_created.get(str(season_number).zfill(2), None)
        if season is None:
            return False
        else:
            for file in os.listdir(season["path"]):
                if os.path.isfile(os.path.join(season["path"], file)):
                    os.remove(os.path.join(season["path"], file))
                elif os.path.isdir(os.path.join(season["path"], file)):
                    shutil.rmtree(os.path.join(season["path"], file))
            DataBase.delete_season(self.id, season_number, show=self.is_show, anime=(not self.is_show))
            return True

    def __str__(self):
        dic = {}
        dic[self.title] = [s.__str__() for s in self.list_season()]
        return dic.__str__()


class Anime(Show):
    def __init__(self, path: str, title: str):
        """
        Initializes an Anime object.

        Args:
            path (str): The path of the anime.
            title (str): The title of the anime.
        """
        super().__init__(path, title, is_show=False)


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
            if temp is not None:
                self.show = Show("ok", temp, is_valid=True)
            else:
                self.show = Show("ok", self.title, is_valid=False)
            self.tmdb_info = self.show.info
            self.id = self.show.id
            self.title = self.show.title
            self.ep = self.determine_ep()

        else:
            self.title = self.det_title_movie()
            temp = Server.get_tmdb_title(self.title)
            if temp is not None:
                self.movie = Movie(self.path, temp, is_valid=True)
            else:
                self.movie = Movie(self.path, self.title, is_valid=False)
            self.tmdb_info = self.movie.info
            self.id = self.movie.id
            self.title = self.movie.title

    def make_clean_file_name(self):
        for banned_car in [("[", "]"), ("{", "}"), ("(", ")")]:
            car1, car2 = banned_car
            while car1 in self.clean_file_name and car2 in self.clean_file_name:
                self.clean_file_name = delete_from_to(self.clean_file_name, car1, car2)

    def det_title_movie(self):
        if self.file_name[-1] == ')':
            file = delete_from_to(self.path[::-1], ")", "(")[::-1]
            file = os.path.basename(file)
        else:
            file = self.file_name
        file = os.path.splitext(file)[0].replace(".", " ").replace("_", " ")
        if file[0] == "[" and "]" in file:
            file = delete_from_to(file, "[", "]").strip()
        for words in ["movie", "film", "vostfr"]:
            if words in file.lower():
                if words in file:
                    file = file.split(words)[0]
                elif words.upper() in file:
                    file = file.split(words.upper())[0]
                elif f"{words[0].upper()}{words[1:]}" in file:
                    file = file.split(f"{words[0].upper()}{words[1:]}")[0]
        if "-" in file[-3:]:
            file = "-".join(file.split("-")[:-1])

        new = file[0]
        file = file[1:]
        for language in list_language:
            if language in file:
                file = file.split(language)[0]
            elif language in file.lower():
                file = file.split(f"{language[0].upper()}{language[1:]}")[0]
        if "(" in file:
            file = file.split("(")[0]
        file += "/"
        while file[0] != "/":
            if len(file) >= 4:
                test = file[0:4]
                if test.isnumeric() and (1900 < int(test) <= datetime.datetime.now().year or int(test) in [1080, 720,
                                                                                                           480, 2160]):
                    break
                else:
                    new += file[0]
                    file = file[1:]
            else:
                new += file[0]
                file = file[1:]
        for banned_car in [("[", "]"), ("{", "}"), ("(", ")")]:
            car1, car2 = banned_car
            while car1 in new and car2 in new:
                new = delete_from_to(new, car1, car2)
        return new

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
                self.title = self.search.results[0]["title"]
                self.id = self.search.results[0]['id']
                Server.add_tmdb_title(title, self.title)
                self.info = super().store_tmdb_info(self.id, movie=True)

            except IndexError:
                log(f"Can't determine the movie named {title}", error=True)
        else:
            self.title = title
            if not self.title in Server.tmdb_db:
                self.id = self.search.movie(query=title)
                self.id = self.search.results[0]['id']
                self.info = super().store_tmdb_info(self.id, movie=True)
            else:
                self.info = Server.tmdb_db[title]
                self.id = self.info['id']

    def add(self, file: Sorter):
        if os.path.isfile(file.path):
            path = os.path.join(self.path, file.__str__())
            shutil.move(file.path, path)
            DataBase.movies[str(self.id)]["file_info"] = {
                "renamed": file.__str__(),
                "path": path,
                "language": file.lang,
                "list_subs_language": file.list_subs_lang,
                "list_audio_language": file.list_audio_lang,
                "height": file.resolution,
                "codec": file.codec,
            }
            json.dump(DataBase.movies, open(os.path.join(VAR_DIR, MOVIES_LIB), "w", encoding="utf-8"), indent=5)

    def delete(self):
        shutil.rmtree(self.path)
        DataBase.movies.pop(str(self.id))


class Season(Server):
    def __init__(self, anime: Show | Anime, path: str, info: dict):
        super().__init__()
        self.anime = anime
        self.path = path
        self.info = info
        self.list_ep = self.list_episode()
        self.is_completed = self.info["season_info"]["episode_count"] == len(self.list_ep)

    def list_episode(self) -> list:
        if type(self.anime) == Anime:
            return \
                DataBase.animes[str(self.anime.id)]['seasons'][str(self.info["season_info"]["season_number"]).zfill(2)][
                    "current_episode"]
        if type(self.anime) == Show:
            return \
                DataBase.shows[str(self.anime.id)]['seasons'][str(self.info["season_info"]["season_number"]).zfill(2)][
                    "current_episode"]

    def add_ep(self, file: Sorter):
        if os.path.isfile(file.path):
            path = os.path.join(self.path, file.__str__())
            shutil.move(file.path, path)
            if self.anime.is_show:
                DataBase.shows[str(self.anime.id)]["seasons"][file.season]['current_episode'][file.ep] = {
                    "renamed": file.__str__(),
                    "path": path,
                    "language": file.lang,
                    "list_subs_language": file.list_subs_lang,
                    "list_audio_language": file.list_audio_lang,
                    "height": file.resolution,
                    "codec": file.codec,
                }
                json.dump(DataBase.shows, open(os.path.join(VAR_DIR, SHOWS_LIB), "w", encoding="utf-8"), indent=5)
            else:
                DataBase.animes[str(self.anime.id)]["seasons"][file.season]['current_episode'][file.ep] = {
                    "renamed": file.__str__(),
                    "path": path,
                    "language": file.lang,
                    "list_subs_language": file.list_subs_lang,
                    "list_audio_language": file.list_audio_lang,
                    "height": file.resolution,
                    "codec": file.codec,
                }
                json.dump(DataBase.animes, open(os.path.join(VAR_DIR, ANIME_LIB), "w", encoding="utf-8"), indent=5)

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
        self.season = str(season.info['season_info']['season_number']).zfill(2)
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
    try:
        animes = json.load(open(os.path.join(VAR_DIR, ANIME_LIB), "r", encoding="utf-8"))
    except IOError as e:
        log(f"can't acces to {ANIME_LIB}", error=True)
        quit()
    try:
        shows = json.load(open(os.path.join(VAR_DIR, SHOWS_LIB), "r", encoding="utf-8"))
    except IOError as e:
        log(f"can't acces to {SHOWS_LIB}", error=True)
        quit()
    try:
        movies = json.load(open(os.path.join(VAR_DIR, MOVIES_LIB), "r", encoding="utf-8"))
    except IOError as e:
        log(f"can't acces to {MOVIES_LIB}", error=True)
        quit()

    def __init__(self):
        super().__init__(enable=True)
        super().check_system_files()
        self.shows_dirs = Server.conf["shows_dir"]
        self.anime_dirs = Server.conf["anime_dir"]
        self.movie_dirs = Server.conf["movie_dir"]
        self.to_sort_anime = Server.conf["sorter_anime_dir"]
        self.to_sort_show = Server.conf["sorter_show_dir"]
        self.to_sort_movie = Server.conf["sorter_movie_dir"]
        self.check_database()

    def check_database(self):
        """check if all information from Database.shows/anime/movies are correct (dir exist)"""
        ls = DataBase.animes.copy()
        for media in DataBase.animes:
            if not os.path.isdir(DataBase.animes[media]["path"]):
                ls.pop(media)
        if not compare_dictionaries(DataBase.animes, ls):
            DataBase.animes = ls.copy()
            json.dump(DataBase.animes, open(os.path.join(VAR_DIR, ANIME_LIB), "w", encoding="utf-8"), indent=5)
        ls.clear()
        ls = DataBase.shows.copy()
        for media in DataBase.shows:
            if not os.path.isdir(DataBase.shows[media]['path']):
                ls.pop(media)
        if not compare_dictionaries(DataBase.shows, ls):
            DataBase.shows = ls.copy()
            json.dump(DataBase.shows, open(os.path.join(VAR_DIR, SHOWS_LIB), "w", encoding="utf-8"), indent=5)
        ls.clear()
        ls = DataBase.movies.copy()
        for media in DataBase.movies:
            if not os.path.isdir(DataBase.movies[media]['path']):
                ls.pop(media)
        if not compare_dictionaries(DataBase.movies, ls):
            DataBase.movies = ls.copy()
            json.dump(DataBase.movies, open(os.path.join(VAR_DIR, MOVIES_LIB), "w", encoding="utf-8"), indent=5)

    def var(self, anime=False, shows=False, movie=False) -> tuple[dict, Anime | Show | Movie, list, str]:
        self.check_database()
        if anime:
            dic = DataBase.animes
            r = Anime
            dirs = Server.conf["anime_dir"]
            lib = ANIME_LIB
        elif shows:
            dic = DataBase.shows
            r = Show
            dirs = Server.conf["shows_dir"]
            lib = SHOWS_LIB
        elif movie:
            dic = DataBase.movies
            r = Movie
            dirs = Server.conf["movie_dir"]
            lib = MOVIES_LIB
        return (dic, r, dirs, lib)

    def find(self, title, anime=False, shows=False, movie=False, is_valid=False,
             id=None) -> Anime | Show | Movie | bool:
        dic, r, dirs, lib = self.var(anime, shows, movie)
        try:
            if movie:
                self.search.movie(query=title)
                text = "title"
            else:
                self.search.tv(query=title)
                text = "name"
            info = super().store_tmdb_info(self.search.results[0]['id'], shows=(anime or shows), movie=movie)
            id = str(info["id"])
            path = dic.get(id, None)["path"]
            return r(path, info[text], is_valid=True)
        except KeyError:
            return False
        except IndexError:
            return False
        except TypeError:
            return False
        except requests.exceptions.ReadTimeout:
            log(f"connection to tmdb timeout", warning=True)

    def update_lib(self, n_item, value, anime=False, shows=False, movie=False, delete=False):
        dic, r, dirs, lib = self.var(anime, shows, movie)
        if anime:
            info = self.tmdb_db.get(n_item, False)
            if info == False:
                info = Anime(value, n_item, is_valid=True)
                super().update_tmdb_db(info.title,
                                       tmdb.TV(info.search.results[0]["id"]).info(append_to_response="seasons"))
                info = self.tmdb_db[info.title]
            id = str(info['id'])

            if not delete:
                if DataBase.animes.get(id, None) is None:
                    DataBase.animes[id] = {"title": info["name"],
                                           "path": value,
                                           "seasons": {}}
                for season in info["seasons"]:
                    path = os.path.join(DataBase.animes[id]['path'], f"Season {str(season['season_number']).zfill(2)}")
                    os.makedirs(path, exist_ok=True)
                    if DataBase.animes[id]["seasons"].get(str(season["season_number"]).zfill(2), None) is None:
                        DataBase.animes[id]["seasons"][str(season["season_number"]).zfill(2)] = {"season_info": season,
                                                                                                 'path': path,
                                                                                                 'current_episode': {}}
            else:
                DataBase.animes.pop(id)
            json.dump(DataBase.animes, open(os.path.join(VAR_DIR, lib), "w", encoding="utf-8"), indent=5)
        elif shows:
            info = self.tmdb_db.get(n_item, False)
            if info == False:
                info = Show(value, n_item, is_valid=True)
                super().update_tmdb_db(info.title,
                                       tmdb.TV(info.search.results[0]["id"]).info(append_to_response="seasons"))
                info = self.tmdb_db[info.title]
            id = str(info['id'])

            if not delete:
                if DataBase.shows.get(id, None) is None:
                    DataBase.shows[id] = {"title": info["name"],
                                          "path": value,
                                          "seasons": {}}
                for season in info["seasons"]:
                    path = os.path.join(DataBase.shows[id]['path'], f"Season {str(season['season_number']).zfill(2)}")
                    os.makedirs(path, exist_ok=True)
                    if DataBase.shows[id]["seasons"].get(str(season["season_number"]).zfill(2), None) is None:
                        DataBase.shows[id]["seasons"][str(season["season_number"]).zfill(2)] = {"season_info": season,
                                                                                                'path': path,
                                                                                                'current_episode': {}}
            else:
                DataBase.shows.pop(id)
            json.dump(DataBase.shows, open(os.path.join(VAR_DIR, lib), "w", encoding="utf-8"), indent=5)
        elif movie:
            info = self.tmdb_db.get(n_item, False)
            if info == False:
                info = Movie(value, n_item, is_valid=True)
                super().update_tmdb_db(info.title,
                                       tmdb.TV(info.search.results[0]["id"]).info(append_to_response="seasons"))
                info = self.tmdb_db[info.title]
            id = str(info['id'])

            if not delete:
                if DataBase.movies.get(id, None) is None:
                    DataBase.movies[id] = {"title": info["title"],
                                           "path": value,
                                           "file_info": {}}
            else:
                DataBase.shows.pop(id)
            json.dump(DataBase.movies, open(os.path.join(VAR_DIR, lib), "w", encoding="utf-8"), indent=5)

    def get_dir_freer(self, anime=False, shows=False, movie=False) -> str:
        """return the direcotires with the more free space
            choose between anime, shows and movie, it returns only one result at the time"""
        dic, r, dirs, lib = self.var(anime, shows, movie)
        max, max_dir = 0, ""
        return get_path_with_most_free_space(dirs)

    def add(self, title, anime=False, shows=False, movie=False, is_valid=False) -> bool | Anime | Show | Movie:
        dict, r, dirs, lib = self.var(anime, shows, movie)
        if not is_valid:
            title = r("path", title, is_valid).title
            test = self.find(title, anime=anime, shows=shows, movie=movie, is_valid=False)
            if test != False:
                return self.add(title, anime=anime, shows=shows, movie=movie, is_valid=True)
            else:
                return self.add(title, anime=anime, shows=shows, movie=movie, is_valid=True)
        id = str(self.tmdb_db[title]['id'])
        if id not in dict:
            dir = self.get_dir_freer(anime, shows, movie)
            try:
                path = os.path.join(dir, forbiden_car(title))
                os.makedirs(path, exist_ok=True)
                self.update_lib(title, path, anime, shows, movie)

            except OSError as e:
                print(e)
                log(e, error=True)
            return r(path, title, is_valid=True)
        else:
            return r(dict[id], title, is_valid=True)

    def add_file(self, file: Sorter, anime=False, shows=False, movie=False) -> bool:
        elt = self.add(file.title, anime, shows, movie, is_valid=True)
        if elt != False and not movie:
            season = elt.seasons[file.season]
            ep = season.get(file.ep, None)
            if ep is None:
                s = Season(elt, season['path'], season)
                s.add_ep(file)
                return
            elif choose_best_version(ep, file) == file:
                self.replace(ep, file, anime, shows, movie)
                return True
            else:
                os.remove(file.path)
                return True

            log(f"Episode is unknown for the database : {file}", error=True)
            if anime:
                st = "anime"
            elif shows:
                st = "show"
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

    def delete_episode(id: int, season_number: int, episode_number: int, show: bool = False, anime: bool = False):
        """
        Deletes an episode from the database.

        Args:
            id (int): The ID of the show or anime.
            season_number (int): The season number of the episode.
            episode_number (int): The episode number.
            show (bool, optional): Flag indicating whether the ID corresponds to a TV show. Defaults to False.
            anime (bool, optional): Flag indicating whether the ID corresponds to an anime. Defaults to False.

        Returns:
            bool: True if the episode is successfully deleted, False otherwise.

        Raises:
            ValueError: If both the show and anime flags are set to True or both are set to False.
            TypeError: If the episode_number, season_number, or id parameters are not of type int.
        """
        if (anime and show) or not (anime or show):
            raise ValueError("You should choose between show and anime")
        if not isinstance(episode_number, int):
            raise TypeError("Episode number should be of type int")
        if not isinstance(season_number, int):
            raise TypeError("Season number should be of type int")
        if not isinstance(id, int):
            raise TypeError("ID should be of type int")

        id = str(id)
        season_number = str(season_number).zfill(2)
        episode_number = str(episode_number).zfill(2)

        if anime:
            if DataBase.animes.get(id) is None:
                return False
            elif DataBase.animes[id].get(season_number) is None:
                return False
            elif DataBase.animes[id][season_number].get(episode_number) is None:
                return False
            DataBase.animes[id][season_number].pop(episode_number)
            json.dump(DataBase.animes, open(os.path.join(VAR_DIR, ANIME_LIB), "w", encoding="utf-8"), indent=5)
            return True

        if show:
            if DataBase.shows.get(id) is None:
                return False
            elif DataBase.shows[id].get(season_number) is None:
                return False
            elif DataBase.shows[id][season_number].get(episode_number) is None:
                return False
            DataBase.shows[id][season_number].pop(episode_number)
            json.dump(DataBase.shows, open(os.path.join(VAR_DIR, SHOWS_LIB), "w", encoding="utf-8"), indent=5)
            return True

    def delete_season(id: int, season_number: int, show: bool = False, anime: bool = False):
        """
        Deletes a season from the database.

        Args:
            id (int): The ID of the show or anime.
            season_number (int): The season number to delete.
            show (bool, optional): Flag indicating whether the ID corresponds to a TV show. Defaults to False.
            anime (bool, optional): Flag indicating whether the ID corresponds to an anime. Defaults to False.

        Returns:
            bool: True if the season is successfully deleted, False otherwise.

        Raises:
            ValueError: If both the show and anime flags are set to True or both are set to False.
            TypeError: If the season_number or id parameters are not of type int.
        """
        if (anime and show) or not (anime or show):
            raise ValueError("You should choose between show and anime")
        if not isinstance(season_number, int):
            raise TypeError("Season number should be of type int")
        if not isinstance(id, int):
            raise TypeError("ID should be of type int")

        id = str(id)
        season_number = str(season_number).zfill(2)

        if anime:
            if DataBase.animes.get(id) is None:
                return False
            elif DataBase.animes[id].get(season_number) is None:
                return False
            DataBase.animes[id].pop(season_number)
            json.dump(DataBase.animes, open(os.path.join(VAR_DIR, ANIME_LIB), "w", encoding="utf-8"), indent=5)
            return True

        if show:
            if DataBase.shows.get(id) is None:
                return False
            elif DataBase.shows[id].get(season_number) is None:
                return False
            DataBase.shows[id].pop(season_number)
            json.dump(DataBase.shows, open(os.path.join(VAR_DIR, SHOWS_LIB), "w", encoding="utf-8"), indent=5)
            return True

    def sort(self, anime=False, shows=False, movie=False):
        if anime:
            dir = self.to_sort_anime
        elif shows:
            dir = self.to_sort_show
        elif movie:
            dir = self.to_sort_movie
        if type(dir) == str:
            list_file = list_all_files(dir)
        elif type(dir) == list:
            list_file = []
            for directory in dir:
                list_file += list_all_files(directory)
        for file in list_file:
            if os.path.isfile(file) and is_video(file):
                try:
                    s = Sorter(file, movie)
                    print(s)
                    self.add_file(s, anime, shows, movie)
                except RuntimeError as e:
                    print(e)
                    pass
                except PermissionError as e:
                    print(e)
                    pass
                except subprocess.CalledProcessError as e:
                    print(e)
                    pass
                except IndexError as e:
                    print(e)
                    pass
                except AttributeError as e:
                    print(e)
                    pass

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
                            self.sort(movie=True)
                time.sleep(5)
        except KeyboardInterrupt:
            print("shutting down")

    def have_ep(self, file: Sorter, anime=False, shows=False, movie=False) -> bool:
        elt = self.find(file.title, anime, shows, movie)
        if elt == False:
            return False
        elif not movie:
            ep = elt.seasons[file.season]["current_episode"].get(file.ep, None)
            if ep is None:
                return False
            else:
                return True
        return False

    def save_tmdb_title(self):
        json.dump(Server.tmdb_title, open(os.path.join(VAR_DIR, TMDB_TITLE), "w", encoding="utf-8"), indent=5)


class Feed(DataBase):
    feed_storage: dict
    feed_storage = json.load(open(os.path.join(VAR_DIR, FEED_STORAGE), "r", encoding="utf-8"))

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
                    rss_feeds["movie_feeds"].append(lines.replace("\n", "").strip())
        with open(os.path.join(VAR_DIR, RSS_SHOW), "r", encoding="utf-8") as f:
            for lines in f:
                if not lines[0] in ["#", '', "\n"]:
                    rss_feeds["show_feeds"].append(lines.replace("\n", "").strip())
        return rss_feeds

    def get_ep_with_link(self, feed: feedparser.FeedParserDict, feed_title: str) -> dict:
        dicto = {}
        for entry in feed.entries:
            is_selected = False
            for words in Server.conf["select_words_rss"]:
                if words in entry.title:
                    is_selected = True
                    if "yggtorrent" in feed_title:
                        dicto[entry.title] = entry.enclosures[0].get("url")
                    else:
                        dicto[entry.title] = entry.link
                    break
            is_ban = False
            for words in Server.conf["banned_words_rss"]:
                if is_selected:
                    break
                if words in entry.title:
                    is_ban = True
                    break
            if not is_ban:
                if "yggtorrent" in feed_title:
                    dicto[entry.title] = entry.enclosures[0].get("url")
                else:
                    dicto[entry.title] = entry.link

        return dicto

    def sort_feed(self) -> dict:

        for feed_list in self.feed_dict:

            for feed in self.feed_dict[feed_list]:
                ls = []
                feed_link = feed
                time.sleep(2)  # avoid ban IP
                r = {}
                r.clear()
                feed = feedparser.parse(feed)
                dic = self.get_ep_with_link(feed, feed_link)
                for ep in dic:
                    title = ep
                    link = dic[ep]
                    if os.path.splitext(title)[1] == '':
                        ep += ".mkv"
                    if not "movie" in feed_list:
                        try:
                            ep = Sorter(ep, for_test=True)
                            if Feed.feed_storage.get(str(ep.id), None) is None:
                                Feed.feed_storage[str(ep.id)] = {}
                            if Feed.feed_storage[str(ep.id)].get(ep.season, None) is None:
                                Feed.feed_storage[str(ep.id)][ep.season] = {}
                            Feed.feed_storage[str(ep.id)][ep.season][ep.ep] = {
                                "torrent_title": title,
                                "link": link,
                                "origin_feed": feed_link
                            }
                        except AttributeError as e:
                            log(f"can't determine the show {ep}", error=True)
                            pass
                        if "anime" in feed_list:
                            if not self.have_ep(ep, anime=True):
                                try:
                                    r[f"{ep.title} - S{ep.season}E{ep.ep} {ep.ext}"] = link
                                except AttributeError:
                                    ...
                                except requests.exceptions.ReadTimeout:
                                    pass
                        elif "show" in feed_list:
                            if not self.have_ep(ep, shows=True):
                                try:
                                    r[f"{ep.title} - S{ep.season}E{ep.ep} {ep.ext}"] = link
                                except AttributeError:
                                    ...
                                except requests.exceptions.ReadTimeout:
                                    print("timeout")
                                    pass
                    else:
                        try:
                            mv = Sorter(ep, is_movie=True, for_test=True)
                        except AttributeError:
                            ...
                        except requests.exceptions.ReadTimeout:
                            print("timeout")
                            pass
                        Feed.feed_storage[str(mv.id)] = {
                            "torrent_title": title,
                            "link": link,
                            "origin_feed": feed_link
                        }
                        if not self.have_ep(ep, movie=True):
                            r[f"{mv.title} - {mv.ext}"] = link
                ls.append(r)
            dic.clear()
            self.feed_dict[feed_list] = ls

    def dl_torrent(self):
        for list_feed in self.feed_dict:
            for feed in self.feed_dict[list_feed]:
                if "anime" in list_feed:
                    torrent_dir = os.path.join(Server.conf['torrent_dir'], "anime")
                elif "show" in list_feed:
                    torrent_dir = os.path.join(Server.conf['torrent_dir'], "show")
                elif "movie" in list_feed:
                    torrent_dir = os.path.join(Server.conf['torrent_dir'], "movie")
                else:
                    raise ValueError
                os.makedirs(torrent_dir, exist_ok=True)
                for key in feed:
                    file_name = forbiden_car(f"{key}.torrent")
                    if file_name not in os.listdir(torrent_dir):
                        try:
                            torrent = requests.request("GET", feed[key])
                            open(os.path.join(torrent_dir, file_name), "wb").write(
                                torrent.content)
                        except requests.exceptions.ConnectTimeout:
                            log(f"connection to {feed[key]} tomeout", warning=True)
                            pass
                        time.sleep(1)  # avoid ban ip

    def run(self):
        while True:
            self.sort_feed()
            self.dl_torrent()
            time.sleep(600)


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
        self.app.run(host='0.0.0.0')

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
        self.dl = Feed()

    def start(self):
        try:
            api = threading.Thread(target=self.web_api.run)
            api.start()

            db = threading.Thread(target=self.db.serve_forever)
            db.start()
            if Server.conf["GGD"]:
                GGD = threading.Thread(target=self.GGD.run)
                GGD.start()
            if Server.conf["Downloader"]:
                dl = threading.Thread(target=self.dl.run)
                dl.start()

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
            print("Saving feed storage ...")
            json.dump(Feed.feed_storage, open(os.path.join(VAR_DIR, FEED_STORAGE), "w", encoding="utf-8"), indent=5)
            print("Shutting down")
            quit()


def main():
    server = deploy_serv()
    server.start()

    # db.serve_forever()


if __name__ == "__main__":
    main()
