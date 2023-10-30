import os.path
import subprocess
import time

from bs4 import BeautifulSoup
import feedparser, re
from thefuzz import fuzz
from thefuzz import process
from operator import itemgetter
from common import *


class SorterCommon(Server):

    def __init__(self, file_path, file_reachable=True):
        super().__init__()
        self.path = file_path
        self.file_reachable = file_reachable
        self.file_name = self.path
        self.clean_file_name = self.path
        self.make_clean_file_name()
        self.file_name = self.clean_file_name
        self.file_name = os.path.basename(self.file_name)
        self.clean_file_name = os.path.splitext(self.file_name)[0].replace(".", " ").replace("_",
                                                                                             " ")  # get file name with no extension
        self.ext = os.path.splitext(self.file_name)[1]
        self.make_clean_file_name()
        if self.file_reachable:
            self.spec = self.video_spec()
            try:
                self.codec = self.spec["video"]["codec"]
            except KeyError:
                self.codec = "Unknown_codec"
            self.lang = self.determine_language()
            self.list_subs_lang = self.spec["subtitles"]["language"]
            self.list_audio_lang = self.spec["audio"]["language"]
            self.resolution = f'{self.spec["video"]["height"]}p'
        else:
            self.spec = {
                'audio': {'codec': ['Unknown'], 'language': ['Unknown']},
                'subtitles': {'codec': ['Unknown'], 'language': ['Unknown']},
                'video': {'codec': 'Unknown', 'height': -1}
            }
            self.codec = "Unknown_codec"
            self.lang = "unknown_language"
            self.list_subs_lang = []
            self.list_audio_lang = []
            self.resolution = "Unknownp"

    def make_clean_file_name(self):
        """
        Removes banned characters from the clean file name.

        This method removes all characters between banned characters, such as '[', ']', '{', '}', '(', and ')' from the clean file name attribute
        stored in the `clean_file_name` property of the object.

        Returns:
            None
        """
        banned_chars = [("[", "]"), ("{", "}"), ("(", ")")]
        for banned_char in banned_chars:
            char1, char2 = banned_char
            while char1 in self.clean_file_name and char2 in self.clean_file_name:
                self.clean_file_name = delete_from_to(self.clean_file_name, char1, char2)

    def determine_language(self):
        """
        Determine the language of a video file based on its file name and specifications.

        Returns:
            str: The determined language.

        Example:
        --------
        >>> video = SorterCommon("Attack on Titan S01E12 [VOSTFR] .mp4", file_reachable=False)
        >>> video.spec = {
        ...     "subtitles": {"language": ["fre"]},
        ...     "audio": {"language": ["jpn"]}
        ... }
        >>> video.determine_language()
        'VOSTFR'
        """

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

    def video_spec(self) -> dict[str, dict[str, list[str]] | dict[str, list[str]] | dict[str, int]]:
        """
        Retrieve the specifications of a video file using ffprobe.

        Returns:
            dict[str, dict[str, list[str]] | dict[str, list[str]] | dict[str, int]]: The video specifications.

        Example:
        --------
        >>> video = SorterCommon("path/to/video.mp4", file_reachable=False)
        >>> video_spec = video.spec
        >>> print(video_spec)
        {'audio': {'codec': ['Unknown'], 'language': ['Unknown']}, 'subtitles': {'codec': ['Unknown'], 'language': ['Unknown']}, 'video': {'codec': 'Unknown', 'height': -1}}
        """

        track_info = {'audio': {"codec": [], "language": []},
                      'subtitles': {"codec": [], "language": []},
                      'video': {"codec": None, "height": None}}

        # Run the ffprobe command and capture the output
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", self.path]
        result = subprocess.check_output(cmd, universal_newlines=True, errors="ignore")

        # Parse the JSON output to extract the subtitle languages
        data = json.loads(result)
        for streams in data["streams"]:
            stream_type = streams["codec_type"].lower()
            if stream_type == "video":
                try:
                    track_info["video"]["height"] = streams["height"]
                except KeyError:
                    pass
                try:
                    track_info["video"]["codec"] = streams["codec_name"].upper()
                except KeyError:
                    pass
            elif stream_type == "audio":
                try:
                    track_info["audio"]["codec"].append(streams["codec_name"].upper())
                except KeyError:
                    pass
                try:
                    track_info["audio"]["language"].append(streams["tags"]["language"].lower())
                except KeyError:
                    pass
            elif stream_type == "subtitle":
                try:
                    track_info["subtitles"]["codec"].append(streams["codec_name"].upper())
                except KeyError:
                    pass
                try:
                    track_info["subtitles"]["language"].append(streams["tags"]["language"].lower())
                except KeyError:
                    pass

        return track_info


class SorterShows(SorterCommon):
    def __init__(self, file_path: str, file_reachable=True, is_anime=False):
        super().__init__(file_path, file_reachable)
        self.season = self.determine_season()
        self.original_title = self.determine_title()
        self.title = self.original_title
        temp = super().find_tmdb_title(self.title, anime=is_anime, shows=(not is_anime))
        if not temp:
            raise ValueError(f"{file_path}, cannot determine the show")
        if is_anime:
            self.show = Anime("ok", temp)
        else:
            self.show = Show("ok", temp)
        self.tmdb_info = self.show.info
        self.id = self.show.id
        self.title = self.show.title
        self.ep = self.determine_ep()
        self.source = self.determine_source()

    def determine_title(self) -> str:
        """
        Determines the title of the video.

        This method analyzes the clean file name attribute stored in the `clean_file_name` property of the object
        and extracts the title of the video based on certain patterns and conventions. The determined title is returned.

        Returns:
            str: The determined title of the video.
        """
        file = self.clean_file_name
        file = delete_unwanted_words(file)
        file = split_on_season_word(file)
        if " - " in file:
            file = file.split(" - ")[0]
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

        if index is not None:
            return file[:index].strip()

        for char in file:
            if char.isnumeric():
                return file.split(char)[0].strip()

        return file.split(" ")[0]

    def determine_season(self) -> str:
        """
        Return the season of a video file from its title.

        Example:
        --------
        >>> video = SorterShows("Tokyo Ghoul S01E02 .mp4", file_reachable=False)
        >>> video.determine_season()
        '01'
        """

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
        except IndexError:
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
            temp_file, example = file.split(elt)[0], "Season "
            while temp_file[-1] == example[-1] and len(example) > 1 and len(temp_file) > 1:
                temp_file, example = temp_file[:-1], example[:-1]
            if example == "S":
                return f"{int(elt):02}"

        return "01"

    def determine_ep(self) -> str:
        """
        Return the episode number of a video file from its title.

        Returns:
            str: The episode number.

        Example:
        --------
        >>> video = SorterShows("My Hero Academia S01E02 .mp4", file_reachable=False)
        >>> video.determine_ep()
        '02'
        """

        file, ls, temp = self.clean_file_name, [], None
        if self.original_title in file:
            file = file.split(self.original_title)[-1]

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

            if temp is not None:
                return f"{int(temp):02}"
            elif ls != []:
                ep = str(max([int(i) for i in ls]))
                if len(ep) <= 2:
                    return f"{int(ep):02}"
                elif len(ep) == 3:
                    return f"{int(ep):03}"
                elif len(ep) == 4:
                    return f"{int(ep):04}"

    def determine_source(self) -> str | None:
        """
        Return the source of a video from its file name.

        Returns:
            str: The video source.

        Example:
        --------
        >>> video = SorterShows("[Source] Oshi no Ko S01E7 .mkv", file_reachable=False)
        >>> video.determine_source()
        'Source'
        """

        title, source = self.file_name, ""

        if "[" == title[0] and "]" in title:
            while title[0] != "[":
                title = title[1:]
            title = title[1:]
            while title[0] != "]":
                source = source + title[0]
                title = title[1:]
            return source

        if "-" in title:
            file = os.path.splitext(title)[0][::-1].strip()
            if "-" in file[:15]:
                return "-".join(file[:15].split("-")[:-1])[::-1]
        return None

    def __str__(self):
        if not self.file_reachable:
            if self.source == None:
                return forbidden_car(
                    f"{self.title} - S{self.season}E{self.ep} {self.ext}")
            return forbidden_car(
                f"{self.title} - S{self.season}E{self.ep} - {self.source} {self.ext}")
        if self.source == None:
            return forbidden_car(
                f"{self.title} - S{self.season}E{self.ep} - [{self.lang} {self.resolution} {self.codec}] {self.ext}")
        return forbidden_car(
            f"{self.title} - S{self.season}E{self.ep} - [{self.lang} {self.resolution} {self.codec}] -{self.source} {self.ext}")


class SorterMovie(SorterCommon):

    def __init__(self, file_path, file_reachable=True):
        super().__init__(file_path, file_reachable=file_reachable)
        self.title = self.determine_title()
        temp = super().find_tmdb_title(self.title, movie=True)
        if temp == False:
            raise ValueError(f"{file_path}, cannot determine the movie")
        self.movie = Movie("ok", temp)
        self.tmdb_info = self.movie.info
        self.id = self.movie.id
        self.title = self.movie.title

    def determine_title(self):
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

    def __str__(self):
        if not self.file_reachable:
            return forbidden_car(
                f"{self.title} - {self.ext}")
        return forbidden_car(
            f"{self.title} - [{self.lang} {self.resolution} {self.codec}] {self.ext}")


class Movie(Server):

    def __init__(self, path: str, title: str):
        """
        Initialize a Movie object.

        Args:
            path (str): The path to the movie file.
            title (str): The title of the movie.

        Raises:
            Exception: If the movie title is not found or no information is found.

        """

        super().__init__()
        self.path = path
        self.title = self.find_tmdb_title(title, movie=True)

        if self.title is False:
            raise Exception(f"Movie {title} not found")

        self.info = super().get_tmdb_info(title, movie=True)

        if self.info is None:
            raise Exception(f"Movie {title} no information found")

        self.id = self.info["id"]

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
            DataBase.delete(self.id, movie=True)
        else:
            raise NotADirectoryError("Invalid directory path")

    def add_movie(self, file: SorterShows):
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
        if self.title is None:
            raise Exception(f"Show {title} not found")
        self.info = super().get_tmdb_info(self.title, show=True)
        if self.info is None:
            raise Exception(f"Show {title} no information found")
        self.id = self.info["id"]
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
            self.store_tmdb_info(self.id, show=self.is_show, anime=(not self.is_show))
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
            DataBase.delete(self.id, shows=self.is_show, anime=(not self.is_show))
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


class Season(Server):
    def __init__(self, parent: Show | Anime, path: str, season_number: int):
        if not isinstance(parent, Show):
            raise TypeError("Parent of a season can only be a Show or an Anime")
        if not isinstance(season_number, int):
            raise TypeError("season_number must be an int")
        super().__init__()
        self.parent = parent
        self.path = path
        self.season_number = str(season_number).zfill(2)
        self.info_theoric = self.parent.seasons_theoric[int(season_number) - 1]
        try:
            self.info_current = DataBase.get_season_info(self.parent.id, self.season_number,
                                                         show=(type(self.parent) == Show),
                                                         anime=(type(self.parent) == Anime))
        except ValueError:
            self.info_current = None
        if self.info_theoric is None:
            raise ValueError(f"Cannot find season {self.season_number} of {self.parent.title}")
        self.number_of_episode = self.info_theoric.get("episode_count", None)
        if self.number_of_episode is None:
            raise ValueError(f"Cannot find episode_count on season {self.season_number} of {self.parent.title}")
        self.current_episode = self.list_episode()
        self.is_completed = self.info_theoric["episode_count"] == len(self.current_episode)

    def list_episode(self) -> Union[dict, None]:
        """
        Retrieve the list of current episodes for the parent entity (Anime or Show).

        Returns:
            Union[dict, None]: A dictionary containing the current episodes for the parent entity,
                              or None if the parent is not an Anime or Show.

        """
        if type(self.parent) == Anime:
            return DataBase.get_season_info(self.parent.id, season_number=self.season_number, anime=True)[
                "current_episode"]
        if type(self.parent) == Show:
            return DataBase.get_season_info(self.parent.id, season_number=self.season_number, show=True)[
                "current_episode"]

    def add_ep(self, file: SorterShows) -> bool:
        """
        Ajoute un épisode à la saison en cours de la série.

        Args:
            file (SorterShows): L'objet représentant le fichier de l'épisode à ajouter.

        Returns:
            bool: True si l'épisode a été ajouté avec succès, False sinon.

        """
        if os.path.isfile(file.path) and int(file.season) == int(self.season_number):
            DataBase.add_file(file)
            return True
        else:
            return False

    def __str__(self):
        dic = {}
        dic[f"Season {str(self.season_number).zfill(2)}"] = [ep.path for ep in self.current_episode]
        return dic.__str__()


################################################
class Episode(Server):
    def __init__(self, season: Season, path):
        super().__init__()
        self.path = path
        self.parent = season
        self.file_name = os.path.splitext(os.path.basename(path))[0]
        self.season = self.parent.season_number
        self.ep = int(self.file_name.split(" - ")[1].split("E")[-1])
        self.codec = self.file_name.split(" - ")[2].split(" ")[-1].split("]")[0]
        self.resolution = self.file_name.split(" - ")[2].split(" ")[1]
        self.lang = self.file_name.split(" - ")[2].split(" ")[0]
        self.source = self.file_name[::-1].split("- ")[0]

    def delete(self):
        os.remove(self.path)


class ConnectorShowBase(Server):
    connector_conf_dir = os.path.join(CONF_DIR, "connectors")
    connector_conf_file = "common.conf"
    os.makedirs(connector_conf_dir, exist_ok=True)
    wanted_nfo_specification = ["format", "codec id", "duration", "width",
                                "height", "language", "resolution", "hauteur", "largeur", "duree"]
    wanted_nfo_title = ["text", "video", "audio", "mkv"]

    if not os.path.isfile(os.path.join(connector_conf_dir, connector_conf_file)):
        with open(os.path.join(connector_conf_dir, connector_conf_file), "w") as f:
            ...

    def __init__(self, id: int, movie=False):
        super().__init__()
        self.connector_name = "common"
        self.is_movie = movie

        # should add config for connector
        self.target_title_lang = ["de", "en", "fr", "ja", "ko", "DE", "JP", 'EN', 'FR', 'GB', 'gb', 'US']
        self.alt_titles = list(set(self.get_titles(id)))

    def get_titles(self, id: int) -> list[str] | None:
        is_anime = self.is_anime_by_id(id)
        title = self.get_tmdb_info_by_id(id, anime=is_anime, show=(not self.is_movie and not is_anime), movie=self.is_movie)
        if self.is_movie:
            text = "title"
        else:
            text = "name"
        if title is None:
            raise ValueError(f"No show found for id {id}")
        else:
            if title.get("translations", None) is None:
                raise Exception(f"cannot find all titles for the show {id}")
            else:
                if title.get('translations', None).get("translations", None) is None:
                    raise Exception(f"cannot find all titles for the show {id}")
                else:
                    alt = tmdb.TV(id=title["id"]).alternative_titles()["results"]
                    alt = [i['title'] for i in alt if i["iso_3166_1"] in self.target_title_lang ]
                    return [ *[t["data"][text] for t in title.get("translations").get("translations") if
                            t["data"][text] != "" and t["iso_639_1"] in self.target_title_lang] , *alt]
    
    

    def parse_conf(self, conf_file_path: str):
        conf = {}
        with open(conf_file_path, "r") as f:
            for lines in f:
                if not lines[0] in ["#", "\n", ""]:
                    if not " = " in lines:
                        raise Exception(f"{conf_file_path} malformed at line {lines}")
                    lines = lines.split(" = ")
                    key = lines[0]
                    if lines[1].replace("\n", "") == "FALSE":
                        value = False
                    elif lines[1].replace("\n", "") == "TRUE":
                        value = True
                    elif lines[1].replace("\n", "") == "NONE":
                        value = []
                    else:
                        value = lines[1].replace("\n", "").split(" ")

                    conf[key] = value
        return conf

    def exclude_zero_seeders(self, dic: list):
        temp = deepcopy(dic)
        for key in dic:
            if int(key["seeders"]) == 0:
                temp.remove(key)
        return deepcopy(temp)

    def prepare_dict_sort(self, result: dict) -> dict:
        result = self.exclude_zero_seeders(result)
        r = []
        temp = {}
        for ep in result:
            temp.clear()
            temp = {}
            for title in ConnectorShowBase.wanted_nfo_title:
                if ep["nfo"].get(title, None) is None:
                    continue
                for key in ConnectorShowBase.wanted_nfo_specification:

                    if temp.get(key, None) != -1 and temp.get(key, None) is not None:
                        continue
                    if ep["nfo"][title].get(key, None) is None:
                        temp[key] = -1
                    else:
                        if key in ["width", "height", "hauteur", "largeur"]:
                            n_key = key
                            if key == "hauteur":
                                n_key = "height"
                            if key == "largeur":
                                n_key = "width"
                            temp[n_key] = convert_str_to_int(ep["nfo"][title][key])
                        elif key == "resolution" and "x" in ep["nfo"][title][key]:
                            temp["width"] = convert_str_to_int(ep["nfo"][title][key].split("x")[0])
                            temp["height"] = convert_str_to_int(ep["nfo"][title][key].split("x")[1])
                        else:
                            temp[key] = ep["nfo"][title][key]
            if temp != {}:
                temp['id'] = ep["torrent_id"]
                r.append(deepcopy(temp))
        return r

    def extract_better_version(self, results) -> dict | None:
        sorted_result = deepcopy(self.prepare_dict_sort(results))
        sorted_result = sorted(sorted_result, key=itemgetter('width', 'largeur'), reverse=True)
        try:
            results = [i for i in results if i["torrent_id"] == sorted_result[0]['id']][0]
        except IndexError:
            return None
        return results


class YggConnector(ConnectorShowBase):
    id_parsed_ep = []
    id_parsed_batches = []
    connector_name = "YggTorrent.conf"
    stored_data_file = "yggdata.json"
    conf_path = os.path.join(ConnectorShowBase.connector_conf_dir, connector_name)
    if not os.path.isfile(conf_path):
        with open(conf_path, "w") as f:
            f.write(f"active = FALSE\n")
            f.write(f"DOMAIN = https://yggtorrent.wtf/\n")
            f.write(f"pass_key = yourpasskey\n")
            f.write(f"trusted_sources_rss_anime = PutHereURLForEraiRSSFeed\n")
            f.write(f"trusted_sources_rss_show = PutHereURLForEraiRSSFeed\n")
            f.write(f"trusted_sources_rss_movie = PutHereURLForEraiRSSFeed\n")
            f.write(f"trusted_sources_episode_anime = putherethesearchpageforyggtorrent\n")
            f.write(f"trusted_sources_episode_show = putherethesearchpageforyggtorrent\n")
            f.write(f"trusted_sources_file_movie = putherethesearchpageforyggtorrent\n")
            f.write(f'trusted_sources_batch_anime = anime_batch_urls\n')
            f.write(f'trusted_sources_batch_show = anime_batch_urls\n')

    def __init__(self, id: int, movie=False):
        super().__init__(id, movie=movie)
        self.connector_name = "YggTorrent.conf"
        self.stored_data_file = "yggdata.json"
        self.conf_path = os.path.join(ConnectorShowBase.connector_conf_dir, self.connector_name)
        if not os.path.isfile(self.conf_path):
            with open(self.conf_path, "w") as f:
                f.write(f"active = FALSE\n")
                f.write(f"DOMAIN = https://yggtorrent.wtf/\n")
                f.write(f"pass_key = yourpasskey\n")
                f.write(f"trusted_sources_rss_anime = PutHereURLForEraiRSSFeed\n")
                f.write(f"trusted_sources_rss_show = PutHereURLForEraiRSSFeed\n")
                f.write(f"trusted_sources_rss_movie = PutHereURLForEraiRSSFeed\n")
                f.write(f"trusted_sources_episode_anime = putherethesearchpageforyggtorrent\n")
                f.write(f"trusted_sources_episode_show = putherethesearchpageforyggtorrent\n")
                f.write(f"trusted_sources_file_movie = putherethesearchpageforyggtorrent\n")
                f.write(f'trusted_sources_batch_anime = anime_batch_urls\n')
                f.write(f'trusted_sources_batch_show = anime_batch_urls\n')
        self.stored_data_path = os.path.join(ConnectorShowBase.connector_conf_dir, self.stored_data_file)
        if not (os.path.isfile(self.stored_data_path) and check_json(self.stored_data_path)):
            with open(os.path.join(ConnectorShowBase.connector_conf_dir, self.stored_data_file), "w") as f:
                f.write('{"rss": {},'
                        ' "web": {} }')
        with open(os.path.join(ConnectorShowBase.connector_conf_dir, self.stored_data_file), "r") as f:
            self.stored_data = json.load(f)
        self.conf = self.parse_conf(self.conf_path)
        self.domain = self.conf["DOMAIN"][0]
        self.pass_key = self.conf["pass_key"][0]
        self.trusted_sources_rss_anime = [self.domain + i for i in self.conf["trusted_sources_rss_anime"]]
        self.trusted_sources_rss_show = [self.domain + i for i in self.conf["trusted_sources_rss_show"]]
        self.trusted_sources_rss_movie = [self.domain + i for i in self.conf["trusted_sources_rss_movie"]]
        self.trusted_sources_episode_anime = [self.domain + i for i in self.conf["trusted_sources_episode_anime"]]
        self.trusted_sources_episode_show = [self.domain + i for i in self.conf["trusted_sources_episode_show"]]
        self.trusted_sources_episode_movie = [self.domain + i for i in self.conf["trusted_sources_file_movie"]]
        self.trusted_sources_batch_anime = [self.domain + i for i in self.conf["trusted_sources_batch_anime"]]
        self.trusted_sources_batch_show = [self.domain + i for i in self.conf["trusted_sources_batch_show"]]
        self.id = id
        self.cookies = None
        self.user_agent = None

        self.active = self.conf["active"]

    def get_cookies_user_agent(self):
        self.cookies, self.user_agent = flareSolverr_cookies_useragent(self.domain)

    def getresponse(self, url):
        response = requests.get(url, cookies=self.cookies, headers={"User-Agent": self.user_agent})
        if response.status_code == 403:
            self.get_cookies_user_agent()
            return requests.get(url, cookies=self.cookies, headers={"User-Agent": self.user_agent})
        else:
            return response

    def extract_feed_info(self, url: str):
        feed = feedparser.parse(url)
        rss_feed = {}
        for entry in feed.entries:
            if 'title' in entry and "link" in entry:
                title = " ".join(entry.title.split(" ")[:-1])
                seed_leachers = entry.title.split(" ").pop()
                seeders = seed_leachers.replace("S:", "").split("/")[0]
                size = entry["description"].split(" Taille de l'upload: ")[-1].split(" ")[0]
                link = [k["href"] for k in entry["links"] if k['rel'] == 'enclosure'][0]
                link = "/".join(link.split("/")[1:])
                if os.path.splitext(title)[1] == "":
                    title = title + ".mkv"
                try:
                    episode = SorterShows(title, file_reachable=False, is_anime=self.is_anime_by_id(int(self.id)))
                    if rss_feed.get(str(episode.id), None) is None:
                        rss_feed[str(episode.id)] = {}
                    if rss_feed[str(episode.id)].get(episode.season, None) is None:
                        rss_feed[str(episode.id)][episode.season] = {}
                    if rss_feed[str(episode.id)][episode.season].get(episode.ep, None) is None:
                        rss_feed[str(episode.id)][episode.season][episode.ep] = []
                    rss_feed[str(episode.id)][episode.season][episode.ep].append({"torrent_title": entry.title,
                                                                                  "link": link,
                                                                                  "seeders": seeders,
                                                                                  "size": size})
                except ValueError as e:
                    log(str(e), warning=True)
        self.stored_data["rss"] = {**self.stored_data["rss"], **rss_feed}
        json.dump(self.stored_data,
                  open(os.path.join(ConnectorShowBase.connector_conf_dir, self.stored_data_file), "w"), indent=5)
        return rss_feed

    def get_next_page_url(self, url_base: str, n_total_item: int):
        if not len([i for i in url_base.split("&") if "page=" in i]) > 0:
            n_item = 0
            url_base = url_base + f"&page={n_item}"
        else:
            n_item = int([i for i in url_base.split("&") if "page=" in i][0].split("=")[-1])
        if n_item > n_total_item:
            return None
        else:
            n_url = url_base.replace(f"page={n_item}", f"page={n_item + 50}")
            return n_url

    def parse_page(self, url) -> tuple[dict | None, int | None]:
        def extract_text_from_tr(html):
            matching_trs = html.find_all('tr')
            results = []
            list_trs = []
            for tr in matching_trs:
                for td in tr.find_all("td"):
                    if td.find("a", {"id": "torrent_name"}) is not None:
                        list_trs.append(tr)
            for tr in list_trs:
                tds = tr.find_all('td')
                before_last_td = tds[-2]
                text = before_last_td.get_text(strip=True)
                results.append(text)

            return results
        try:
            response = self.getresponse(url)
        except requests.exceptions.ConnectionError:
            time.sleep(5)
            self.parse_page(url)
        html = BeautifulSoup(response.content, features="html.parser")
        h2_tags_with_font = [h2_tag for h2_tag in html.find_all("h2") if h2_tag.find("font", style="float: right")]
        if len(h2_tags_with_font) == 0:
            return None, None
        text_contents = [font_tag.text.strip() for h2_tag in h2_tags_with_font for font_tag in
                         h2_tag.find_all("font")]
        total_result = int(text_contents[0].split(" ")[0])
        target_elements = html.find_all("a", id="get_nfo")
        target_values = [element["target"] for element in target_elements]
        torrent_name_elements = html.find_all("a", id="torrent_name")
        torrent_names = [element.text.strip() for element in torrent_name_elements]
        seeders = extract_text_from_tr(html)
        return {f"{name}": {"id": id, "seeders": seed} for name, id, seed in
                zip(torrent_names, target_values, seeders)}, total_result

    def get_value(self, part: str) -> tuple:
        key, value = "", ""
        while part != "" and part[0] != ":":
            key += part[0]
            part = part[1:]
        part, key = part[1:], key.replace(".", "").lower().strip()
        while part != "":
            value += part[0]
            part = part[1:]
        value = value.strip()
        return (key, value)

    def get_nfo(self, id_torrent: int):
        time.sleep(0.1)
        response = self.getresponse(f'{self.domain}engine/get_nfo?torrent={id_torrent}')
        content, result = self.prepare_nfo(str(response.content)), {}
        temp, title = {}, None
        for part in content:
            key, value = self.get_value(part)
            if key == "" and value == "":
                continue
            elif key != "" and value == "":
                if title is not None:
                    if temp != {title: {}}:
                        result = {**result, **deepcopy(temp)}
                    temp.clear()
                key = self.wanted_title(key)
                if key:
                    title = key
                    temp[title] = {}
                else:
                    key = "None"
            if title is not None and title != key and len(key) < 30 and len(value) < 60 and key != "None":

                key = self.wanted_info(key)
                if temp.get(title, None) is None:
                    temp[title] = {}
                if key:
                    temp[title][key] = value
        result = {**result, **deepcopy(temp)}
        return delete_empty_dictionnaries(result)

    def wanted_title(self, key: str) -> str | bool:
        key = remove_non_ascii(key).lower()
        for wanted in ConnectorShowBase.wanted_nfo_title:
            wanted_ori = wanted
            wanted = remove_non_ascii(wanted).lower()
            if fuzz.ratio(key, wanted) > 65:
                return wanted_ori
        return False

    def wanted_info(self, key: str) -> str | bool:
        key = remove_non_ascii(key).lower()
        for wanted in ConnectorShowBase.wanted_nfo_specification:
            wanted_ori = wanted
            wanted = remove_non_ascii(wanted).lower()
            if fuzz.ratio(key, wanted) > 80:
                return wanted_ori
        return False

    def prepare_nfo(self, nfo_content: str):
        content = bytes(str(nfo_content).replace('b"<pre>', "").replace('\n</pre>"', ""), "utf-8").decode(
            'unicode_escape', errors='ignore')
        content, result = content.split("\n"), {}
        temp, title, result = {}, None, []
        for lines in content:
            temp = ""
            for car in lines:
                if (car.isalnum() or car == " " or car == "." or car == ":") and car != "â":
                    temp += car
            result.append(temp.strip())
        return result

    def find_from_data_ep(self, season_number: int, episode_number: int) -> list | None:
        s = str(season_number).zfill(2)
        e = str(episode_number).zfill(2)
        for cat in self.stored_data:
            if self.stored_data[cat].get(str(self.id), None) is None:
                continue
            if self.stored_data[cat][str(self.id)].get(s, None) is None:
                continue
            if self.stored_data[cat][str(self.id)][s].get(e, None) is None:
                continue
            return self.stored_data[cat][str(self.id)][s][e]
        return None

    def find_from_data_batch(self, season_number: int) -> list | None:
        s = str(season_number).zfill(2)
        for cat in self.stored_data:
            if self.stored_data[cat].get(str(self.id), None) is None:
                continue
            if self.stored_data[cat][str(self.id)].get(s, None) is None:
                continue
            if self.stored_data[cat][str(self.id)][s].get("batch", None) is None:
                continue
            if len(self.stored_data[cat][str(self.id)][s]["batch"]) == 0:
                return None
            return self.stored_data[cat][str(self.id)][s]["batch"]
        return None

    def get_results(self, url: str, title: str):
        results = {}
        title = title.replace(" ", "+")
        url = url.replace("toreplace", title)
        item, n_tot = self.parse_page(url)
        if item is None:
            return None
        results = {**results, **item}
        time.sleep(1)
        url = self.get_next_page_url(url, n_tot)
        while url is not None:
            item, temp = self.parse_page(url)
            if item is not None:
                results = {**results, **item}
            time.sleep(1)
            url = self.get_next_page_url(url, n_tot)
        return results

    def scrap_ep(self, anime=False, show=False):
        if not (anime or show):
            raise ValueError("You should choose anime or show in function parameter")
        results = {}
        feed = {}
        trusted_source = None
        if anime:
            trusted_source = self.trusted_sources_episode_anime
        elif show:
            trusted_source = self.trusted_sources_episode_show
        for titles in self.alt_titles:
            for url in trusted_source:
                new_results = self.get_results(url, titles)
                if new_results is None:
                    continue
                results = {**results, **new_results}
        for torrent in results:
            orignal_name = torrent
            sort_name = torrent
            if os.path.splitext(torrent)[1] == "":
                sort_name = torrent + ".mkv"
            try:
                ep = SorterShows(sort_name, file_reachable=False, is_anime=self.is_anime_by_id(int(self.id)))
            except ValueError as e:
                continue
            id = str(ep.id)
            if feed.get(id, None) is None:
                feed[id] = {}
            if feed[id].get(ep.season, None) is None:
                feed[id][ep.season] = {"batch": []}
            if feed[id][ep.season].get(ep.ep, None) is None:
                feed[id][ep.season][ep.ep] = []
            feed[id][ep.season][ep.ep].append({"torrent_title": orignal_name,
                                               "link": f"rss/download?id={results[torrent]['id']}&passkey={self.pass_key}",
                                               "seeders": results[torrent]["seeders"],
                                               "torrent_id": results[torrent]["id"],
                                               "nfo": self.get_nfo(results[torrent]["id"])})
            self.stored_data["web"] = {**self.stored_data["web"], **feed}
            json.dump(self.stored_data, open(os.path.join(ConnectorShowBase.connector_conf_dir, self.stored_data_file), "w"), indent=5)
        return feed

    def scrap_batch(self, anime=False, show=False):
        if not (anime or show):
            raise ValueError("You should choose anime or show in function parameter")
        results = {}
        feed = {}
        trusted_source = None
        if anime:
            trusted_source = self.trusted_sources_batch_anime
        elif show:
            trusted_source = self.trusted_sources_batch_show
        for titles in self.alt_titles:
            for url in trusted_source:
                new_results = self.get_results(url, titles)
                if new_results is not None:
                    results = {**results, **new_results}
        for torrent in results:
            original_name = torrent
            sort_name = torrent

            if os.path.splitext(torrent)[1] == "":
                sort_name = torrent + ".mkv"
            try:
                ep = SorterShows(sort_name, file_reachable=False, is_anime=anime)
            except (ValueError, IndexError) as e:
                continue
            id = str(ep.id)
            if feed.get(id, None) is None:
                feed[id] = {}
            if feed[id].get(ep.season, None) is None:
                feed[id][ep.season] = {"batch": []}
            feed[id][ep.season]["batch"].append({"torrent_title": original_name,
                                                 "link": f"rss/download?id={results[torrent]['id']}&passkey={self.pass_key}",
                                                 "seed": results[torrent]['seeders'],
                                                 "torrent_id": results[torrent]["id"],
                                                 "nfo": self.get_nfo(results[torrent]["id"])})
            self.stored_data["web"] = {**self.stored_data["web"], **feed}
            json.dump(self.stored_data,
                    open(os.path.join(ConnectorShowBase.connector_conf_dir, self.stored_data_file), "w"), indent=5)
        return feed

    def scrap_movie(self):
        results, feed, trusted_source = {}, {}, self.trusted_sources_episode_movie
        for titles in self.alt_titles:
            for url in trusted_source:
                new_results = self.get_results(url, titles)
                if new_results is not None:
                    results = {**results, **new_results}
        for torrent in results:
            original_name = torrent
            sort_name = torrent
            season = None

            if os.path.splitext(torrent)[1] == "":
                sort_name = torrent + ".mkv"
            try:
                ep = SorterMovie(sort_name, file_reachable=False)
            except ValueError as e:
                continue
            id = str(ep.id)
            if feed.get(id, None) is None:
                feed[id] = []
            feed[id].append({"torrent_title": original_name,
                             "link": f"rss/download?id={results[torrent]['id']}&passkey={self.pass_key}",
                             "seed": results[torrent]['seeders'],
                             "torrent_id": results[torrent]["id"],
                             "nfo": self.get_nfo(results[torrent]["id"])})
        self.stored_data["web"] = {**self.stored_data["web"], **feed}
        json.dump(self.stored_data,
                  open(os.path.join(ConnectorShowBase.connector_conf_dir, self.stored_data_file), "w"), indent=5)
        return feed

    def find_ep(self, season_number: int, episode_number: int, anime=False, show=False):
        if not (anime or show):
            raise ValueError("You should choose anime or show in function parameter")
        db_results, choice, trusted_source = self.find_from_data_ep(season_number, episode_number), None, None
        if db_results is not None:
            choice = self.extract_better_version(db_results)
        if anime:
            trusted_source = self.trusted_sources_rss_anime
        elif show:
            trusted_source = self.trusted_sources_rss_show
        for trusted in trusted_source:
            feed = self.extract_feed_info(trusted)
            time.sleep(1)
            if self.dict_have_ep(feed, self.id, season_number, episode_number) is None:
                continue
            else:
                choice = feed[str(self.id)][str(season_number).zfill(2)].get(str(episode_number).zfill(2), None)
        if choice is None:
            try:
                if str(self.id) in YggConnector.id_parsed_ep:
                    results = self.stored_data["web"]
                else:
                    results = self.scrap_ep(anime, show)
                    YggConnector.id_parsed_ep.append(str(self.id))

                choice = self.extract_better_version(
                    results[str(self.id)][str(season_number).zfill(2)][str(episode_number).zfill(2)])
            except KeyError as e:
                log(e, debug=True)
                return None
        json.dump(self.stored_data,
                  open(os.path.join(ConnectorShowBase.connector_conf_dir, self.stored_data_file), "w"), indent=5)
        if type(choice) is not None:
            try:
                choice["link"] = self.domain + choice["link"]
            except TypeError:
                return None
        return choice

    def find_batch(self, season_number: int, anime=False, show=False):
        if not (anime or show):
            raise ValueError("You should choose anime or show in function parameter")
        db_results = self.find_from_data_batch(season_number)
        if db_results is not None:
            db_results[0]["link"] = self.domain + db_results[0]["link"]
            return db_results[0]
        choice = None
        if choice is None:
            if str(self.id) in self.id_parsed_batches:
                results = self.stored_data["web"]
            else:
                results = self.scrap_batch(anime, show)
                YggConnector.id_parsed_batches.append(str(self.id))
            try:
                for batch in results[str(self.id)][str(season_number).zfill(2)]["batch"]:
                    if int(batch["seed"]) == 0:
                        continue
                    if batch != None:
                        choice = batch
            except KeyError:
                choice = None
        json.dump(self.stored_data,
                  open(os.path.join(ConnectorShowBase.connector_conf_dir, self.stored_data_file), "w"), indent=5)
        if choice is not None:
            choice["link"] = self.domain + choice["link"]
        return choice


class NyaaConnector(ConnectorShowBase):

    connector_name = "Nyaa.conf"
    conf_path = os.path.join(ConnectorShowBase.connector_conf_dir, connector_name)
    if not os.path.isfile(conf_path):
        with open(conf_path, "w") as f:
            f.write(f"active = FALSE\n")
            f.write(f"trusted_sources_rss_url = PutHereURLForNyaaRSSFeed\n")
            f.write(f"words = write words specific to nyaa search engine\n")

    def __init__(self, id: int):
        super().__init__(id)
        self.connector_name = "Nyaa.conf"
        self.conf_path = os.path.join(ConnectorShowBase.connector_conf_dir, self.connector_name)
        if not os.path.isfile(self.conf_path):
            with open(self.conf_path, "w") as f:
                f.write(f"active = FALSE\n")
                f.write(f"trusted_sources_rss_url = PutHereURLForNyaaRSSFeed\n")
                f.write(f"words = write words specific to nyaa search engine\n")
        self.conf = self.parse_conf(self.conf_path)
        self.trusted_sources_rss_url = self.conf["trusted_sources_rss_url"]
        self.words = self.conf["words"]
        self.id = id
        self.active = self.conf["active"]

    def make_url(self, source: str, *arg):
        text = '(' + ') | ('.join(self.alt_titles) + ')'.replace(" ", "+")
        title_req = f'({text})'
        if list(arg) != []:
            word_req = "+" + "+".join(list(arg))
        else:
            word_req = ""
        req = source.replace("toreplace", f"{title_req}{word_req}").replace(" ", "+")
        if check_url_syntax(req):
            return req
        else:
            return None

    def extract_feed_info(self, url: str):
        feed = feedparser.parse(url)
        rss_feed = {}
        for entry in feed.entries:
            if 'title' in entry and "link" in entry:
                if os.path.splitext(entry.title)[1] == "":
                    filename = f"{entry.title}.mkv"

                else:
                    filename = entry.title
                try:
                    seeders = entry["nyaa_seeders"]
                    size = entry["nyaa_size"]
                    episode = SorterShows(filename, file_reachable=False, is_anime=True)
                    if rss_feed.get(str(episode.id), None) is None:
                        rss_feed[str(episode.id)] = {}
                    if rss_feed[str(episode.id)].get(episode.season, None) is None:
                        rss_feed[str(episode.id)][episode.season] = {}
                    if rss_feed[str(episode.id)][episode.season].get(episode.ep, None) is None:
                        rss_feed[str(episode.id)][episode.season][episode.ep] = []
                    rss_feed[str(episode.id)][episode.season][episode.ep].append({"torrent_title": entry.title,
                                                                                  "link": entry.link,
                                                                                  "seeders": seeders,
                                                                                  "size": size})
                except ValueError as e:
                    log(str(e), warning=True)

        return rss_feed

    def find_ep(self, season_number: int, episode_number: int, anime=False, show=False) -> dict | None:
        if show and not anime:
            return None
        for trusted in self.trusted_sources_rss_url:
            url = self.make_url(trusted, *self.words)
            feed = self.extract_feed_info(url)
            time.sleep(1)
            if feed.get(str(self.id), None) is None:
                continue
            if feed[str(self.id)].get(str(season_number).zfill(2), None) is None:
                continue
            if feed[str(self.id)][str(season_number).zfill(2)].get(str(episode_number).zfill(2), None) is None:
                continue
            else:
                choice = None
                for ep in feed[str(self.id)][str(season_number).zfill(2)].get(str(episode_number).zfill(2), None):
                    if int(ep["seeders"]) > 0:
                        choice = ep
                return choice


def choose_best_version(v_cur: Episode, v_new: SorterShows) -> SorterShows | Episode:
    if not os.path.isfile(v_cur.path):
        return v_new
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
        self.cookies = None
        self.user_agent = None
        self.ban_ids = open(BAN_ID_FILE, "r").read().split("\n")
    
    def get_cookies_user_agent(self, url :str):
        self.cookies, self.user_agent = flareSolverr_cookies_useragent(url=url)

    def getresponse(self, url :str):
        response = requests.get(url, cookies=self.cookies, headers={"User-Agent": self.user_agent})
        if response.status_code == 403:
            self.get_cookies_user_agent(f"{urlparse(url).scheme}://{urlparse(url).netloc}/")
            return requests.get(url, cookies=self.cookies, headers={"User-Agent": self.user_agent})
        return response


    def check_database(self):
        """check if all information from Database.shows/anime/movies are correct (dir exist)"""
        ls = DataBase.animes.copy()
        for media in DataBase.animes:
            if not os.path.isdir(DataBase.animes[media]["path"]):
                ls.pop(media)
            if media in self.ban_ids:
                DataBase.delete(int(media), anime=True)
        if not compare_dictionaries(DataBase.animes, ls):
            DataBase.animes = ls.copy()
            json.dump(DataBase.animes, open(os.path.join(VAR_DIR, ANIME_LIB), "w", encoding="utf-8"), indent=5)
        ls.clear()
        ls = DataBase.shows.copy()
        for media in DataBase.shows:
            if not os.path.isdir(DataBase.shows[media]['path']):
                ls.pop(media)
            if media in self.ban_ids:
                DataBase.delete(int(media), shows=True)
        if not compare_dictionaries(DataBase.shows, ls):
            DataBase.shows = ls.copy()
            json.dump(DataBase.shows, open(os.path.join(VAR_DIR, SHOWS_LIB), "w", encoding="utf-8"), indent=5)
        ls.clear()
        ls = DataBase.movies.copy()
        for media in DataBase.movies:
            if not os.path.isdir(DataBase.movies[media]['path']):
                ls.pop(media)
            if media in self.ban_ids:
                DataBase.delete(int(media), movie=True)
        if not compare_dictionaries(DataBase.movies, ls):
            DataBase.movies = ls.copy()
            json.dump(DataBase.movies, open(os.path.join(VAR_DIR, MOVIES_LIB), "w", encoding="utf-8"), indent=5)


    def var(self, anime=False, shows=False, movie=False) -> tuple[
        dict | None, Anime | Show | Movie | None, list | None, str | None]:
        self.check_database()
        dic = None
        r = None
        dirs = None
        lib = None
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

    def find(title: str, anime=False, shows=False, movie=False) -> Union[Anime, Show, Movie, bool]:
        """
        Find a media (anime, show, or movie) based on the title.

        Args:
            title (str): The title of the media.
            anime (bool, optional): Whether to search for anime. Defaults to False.
            shows (bool, optional): Whether to search for shows. Defaults to False.
            movie (bool, optional): Whether to search for movies. Defaults to False.

        Raises:
            ValueError: If the title is not a string.
            ValueError: If neither anime, shows, nor movie flags are set.

        Returns:
            Anime or Show or Movie or bool: The found media object or False if not found.
        """

        if not isinstance(title, str):
            raise ValueError(f"title should be a string, not {type(title)}")
        serv = Server()
        tmdb_title = serv.find_tmdb_title(title, anime, shows, movie)

        if not tmdb_title:
            return False
        info = serv.get_tmdb_info(tmdb_title, anime=anime, show=shows, movie=movie)
        if info is None:
            return False

        identifier = str(info["id"])

        if anime:
            if DataBase.animes.get(identifier, None) is None:
                return False
            else:
                path = DataBase.animes[identifier]["path"]
                return Anime(path, tmdb_title)
        elif shows:
            if DataBase.shows.get(identifier, None) is None:
                return False
            else:
                path = DataBase.shows[identifier]["path"]
                return Show(path, tmdb_title)
        elif movie:
            if DataBase.movies.get(identifier, None) is None:
                return False
            else:
                path = DataBase.movies[identifier]["path"]
                return Movie(path, tmdb_title)
        else:
            raise ValueError("You should choose between anime, show, or movie")

    def get_dir_freer(self, anime=False, shows=False, movie=False) -> str:
        """return the direcotires with the more free space
            choose between anime, shows and movie, it returns only one result at the time"""
        dic, r, dirs, lib = self.var(anime, shows, movie)
        return get_path_with_most_free_space(dirs)

    def add(self, title: str, anime=False, shows=False, movie=False) -> bool:
        if not isinstance(title, str):
            raise ValueError(f"Title argument must be str not {type(title)}")
        tmdb_title = super().find_tmdb_title(title, anime, shows, movie)
        if not tmdb_title:
            raise ValueError(f"Can't find the show corresponding to {title}")
        if anime:
            title_info = "name"
            dic, file = deepcopy(DataBase.animes), ANIME_LIB
        elif shows:
            title_info = "name"
            dic, file = deepcopy(DataBase.shows), SHOWS_LIB
        elif movie:
            title_info = "title"
            dic, file = deepcopy(DataBase.movies), MOVIES_LIB
        else:
            raise ValueError("You have to choose between anime|shows|movie")
        info = super().get_tmdb_info(tmdb_title, show=shows, anime=anime, movie=movie)
        if info is None:
            return False
        try:
            path = os.path.join(self.get_dir_freer(anime, shows, movie), forbidden_car(info[title_info]))
        except KeyError:
            try :
                path = os.path.join(self.get_dir_freer(anime, shows, movie), forbidden_car(info["name"]))
                title_info = "name"
            except KeyError:
                path = os.path.join(self.get_dir_freer(anime, shows, movie), forbidden_car(info["title"]))
                title_info = "title"


        os.makedirs(path, exist_ok=True)
        season_dict = {}
        if anime or shows:
            for season in info["seasons"]:
                season_path = os.path.join(path, f"Season {str(season['season_number']).zfill(2)}")
                os.makedirs(season_path, exist_ok=True)
                season_dict[str(season["season_number"]).zfill(2)] = {"season_info": season,
                                                                      "path": season_path,
                                                                      "current_episode": {}
                                                                      }
        identifier = str(info["id"])
        if dic.get(identifier, None) is not None:
            return True
        else:
            dic[identifier] = {
                "title": info[title_info],
                "path": path,
                "seasons": season_dict
            }
            if season_dict == {}:
                dic[identifier].pop("seasons")
                dic[identifier]["file_info"] = {}
            if anime:
                DataBase.animes = deepcopy(dic)
            elif shows:
                DataBase.shows = deepcopy(dic)
            elif movie:
                DataBase.movies = deepcopy(dic)
            json.dump(dic, open(os.path.join(VAR_DIR, file), "w", encoding="utf-8"), indent=5)
            if anime:
                DataBase.animes = dic
            elif shows:
                DataBase.shows = dic
            elif movie:
                DataBase.movies = dic
            return True

    def add_file(file: SorterShows | SorterMovie, anime=False, shows=False, movie=False) -> bool:
        """if successful return the new path of the file"""
        elt = DataBase.find(file.title, anime, shows, movie)
        if elt is not False and not movie and type(file) == SorterShows:
            season = elt.seasons_created.get(file.season, None)
            if season is None:
                raise ValueError(f"Cannot add file because no season is associated with the show/anime {file.title}")
            if season["current_episode"].get(file.ep, None) is None:
                ep = None
            else:
                ep = Episode(Season(elt, season["path"], season["season_info"]["season_number"]),
                             os.path.join(season["path"], file.__str__()))
            if ep is None:
                save_path = DataBase.add_ep_database(file)
                try:
                    safe_move(file.path, save_path)
                except OSError:
                    log(f"No more space on {save_path}", error=True)
                    DataBase().balance_media()
                    DataBase.add_file(file, anime, shows, movie)
                    
                return True
            elif choose_best_version(ep, file) == file:
                save_path = DataBase.add_ep_database(file)
                delete_path = DataBase.delete_episode(file.id, int(file.season), int(file.ep), show=file.show.is_show,
                                                      anime=(not file.show.is_show))
                if delete_path is not False and os.path.isfile(delete_path):
                    os.remove(delete_path)
                safe_move(file.path, save_path)
                return True
            else:
                os.remove(file.path)
                return True
        elif movie and type(file) == SorterMovie:
            path = DataBase.add_movie_databse(file)
            shutil.move(file.path, path)
        else:
            raise ValueError(f"You should choose between anime|show|movie")

    def add_ep_database(file: SorterShows) -> str:
        """Add an episode to the database for a given file.

        Args:
            file (SorterShows): The file object representing the episode.

        Returns:
            str: The path where the episode is added in the database.

        Raises:
            ValueError: If the file is not of type SorterShows.
            ValueError: If the file is not reachable.
            ValueError: If trying to add an episode to an unexisting show or anime.
            Exception: If there is a database error.
            ValueError: If the season for the show or anime is not found.
            Exception: If there is no current episode associated with the show or anime season.

        """

        if not isinstance(file, SorterShows):
            raise ValueError("file must be SorterShows type")

        if not file.file_reachable:
            raise ValueError("The file you want to add is not reachable")

        id = str(file.id)
        season = file.season
        ep = file.ep

        if file.show.is_show:
            path = os.path.join(DataBase.get_season_info(file.id, season, show=True)["path"], file.__str__())

            if DataBase.shows.get(id, None) is None:
                raise ValueError("You can't add an episode to an unexisting show")

            if DataBase.shows[id].get("seasons", None) is None:
                raise Exception("Database error: no seasons associated with the show {id}, please check JSON")

            if DataBase.shows[id]["seasons"].get(season, None) is None:
                raise ValueError(f"No season {season} for show {id}")

            if DataBase.shows[id]["seasons"][season].get("current_episode", None) is None:
                raise Exception(
                    f"Database error: no current_episode associated with the show {id} season {season}, please check JSON")

            DataBase.shows[id]["seasons"][season]["current_episode"][ep] = {
                "renamed": file.__str__(),
                "path": path,
                "language": file.lang,
                "list_subs_language": file.list_subs_lang,
                "list_audio_language": file.list_audio_lang,
                "height": file.resolution,
                "codec": file.codec,
            }

            json.dump(DataBase.shows, open(os.path.join(VAR_DIR, SHOWS_LIB), "w", encoding="utf-8"), indent=5)

            return path

        elif not file.show.is_show:
            path = os.path.join(DataBase.get_season_info(file.id, season, anime=True)["path"], file.__str__())

            if DataBase.animes.get(id, None) is None:
                raise ValueError("You can't add an episode to an unexisting anime")

            if DataBase.animes[id].get("seasons", None) is None:
                raise Exception(f"Database error: no seasons associated with the anime {id}, please check JSON")

            if DataBase.animes[id]["seasons"].get(season, None) is None:
                raise ValueError(f"No season {season} for anime {id}")

            if DataBase.animes[id]["seasons"][season].get("current_episode", None) is None:
                raise Exception(
                    f"Database error: no current_episode associated with the anime {id} season {season}, please check JSON")

            DataBase.animes[id]["seasons"][season]["current_episode"][ep] = {
                "original_filename": file.file_name,
                "renamed": file.__str__(),
                "path": path,
                "language": file.lang,
                "list_subs_language": file.list_subs_lang,
                "list_audio_language": file.list_audio_lang,
                "height": file.resolution,
                "codec": file.codec,
            }

            json.dump(DataBase.animes, open(os.path.join(VAR_DIR, ANIME_LIB), "w", encoding="utf-8"), indent=5)

            return path

    def add_movie_databse(file: SorterMovie) -> str:
        if not isinstance(file, SorterMovie):
            raise ValueError("file must be SorterMovie type")

        if not file.file_reachable:
            raise ValueError("The file you want to add is not reachable")
        id = str(file.id)
        folder_path = DataBase.movies.get(id, None)
        if folder_path is None:
            raise ValueError(f"{file.title} not in movie database")
        folder_path = DataBase.movies[id].get("path", None)
        path = os.path.join(folder_path, file.__str__())

        DataBase.movies[id]["file"] = {
            "original_filename": file.file_name,
            "renamed": file.__str__(),
            "path": path,
            "language": file.lang,
            "list_subs_language": file.list_subs_lang,
            "list_audio_language": file.list_audio_lang,
            "height": file.resolution,
            "codec": file.codec,
        }

        json.dump(DataBase.movies, open(os.path.join(VAR_DIR, MOVIES_LIB), "w", encoding="utf-8"), indent=5)

        return path

    def replace(self, ep: Episode, new_file: SorterShows, anime=False, shows=False, movie=False):
        ep.parent.parent.delete_ep(int(ep.season), ep.ep)
        DataBase.add_file(new_file, anime, shows, movie)

    def get_season_info(identifier: int, season_number: str, show=False, anime=False) -> dict:
        """
        Get season information based on the ID and season number.

        Args:
            identifier (int): The ID of the show or anime.
            season_number (str): The season number in the format '02'.
            show (bool, optional): Whether the ID corresponds to a show. Defaults to False.
            anime (bool, optional): Whether the ID corresponds to an anime. Defaults to False.

        Raises:
            ValueError: If the ID is not an integer or if both show and anime flags are False.
            TypeError: If the season number is not a string in the correct format.
            ValueError: If the show or anime with the given ID is not found in the database.
            ValueError: If the specified season number is not found for the show or anime.

        Returns:
            dict: The season information.
        """

        if not isinstance(identifier, int):
            raise ValueError("id must be an integer")

        if not isinstance(season_number, str):
            raise TypeError(f"season number must be a string formatted like '02', not {season_number}")

        identifier = str(identifier)

        if show:
            if DataBase.shows.get(identifier, None) is None:
                raise ValueError(f"Cannot find the show with ID {identifier} in the database")
            elif DataBase.shows[identifier].get("seasons", None) is None:
                raise Exception(f"Database error: no seasons associated with the show {identifier}, please check JSON")
            elif DataBase.shows[identifier]["seasons"].get(season_number, None) is None:
                raise ValueError(f"No season {season_number} for show {identifier}")
            return DataBase.shows[identifier]["seasons"][season_number]
        elif anime:
            if DataBase.animes.get(identifier, None) is None:
                raise ValueError(f"Cannot find the anime with ID {identifier} in the database")
            elif DataBase.animes[identifier].get("seasons", None) is None:
                raise Exception(f"Database error: no seasons associated with the anime {identifier}, please check JSON")
            elif DataBase.animes[identifier]["seasons"].get(season_number, None) is None:
                raise ValueError(f"No season {season_number} for anime {identifier}")
            return DataBase.animes[identifier]["seasons"][season_number]
        else:
            raise ValueError("You should choose between anime and show")

    def delete(id: int, anime: bool = False, shows: bool = False, movie: bool = False) -> bool:
        """
        Deletes a show, anime, or movie from the database.

        Args:
            id (int): The ID of the show, anime, or movie.
            anime (bool, optional): Flag indicating whether the ID corresponds to an anime. Defaults to False.
            shows (bool, optional): Flag indicating whether the ID corresponds to a TV show. Defaults to False.
            movie (bool, optional): Flag indicating whether the ID corresponds to a movie. Defaults to False.

        Returns:
            bool: True if the show, anime, or movie is successfully deleted, False otherwise.

        Raises:
            ValueError: If more than one flag is set to True or no flag is set to True.
            TypeError: If the ID parameter is not of type int.
        """
        valid_flags = [anime, shows, movie]
        if sum(valid_flags) != 1:
            raise ValueError("You should choose only one among anime, shows, and movie")
        if not isinstance(id, int):
            raise TypeError("ID should be of type int")

        id = str(id)

        if anime:
            if DataBase.animes.get(id) is None:
                return False
            DataBase.animes.pop(id)
            json.dump(DataBase.animes, open(os.path.join(VAR_DIR, ANIME_LIB), "w", encoding="utf-8"), indent=5)
            return True

        if shows:
            if DataBase.shows.get(id) is None:
                return False
            DataBase.shows.pop(id)
            json.dump(DataBase.shows, open(os.path.join(VAR_DIR, SHOWS_LIB), "w", encoding="utf-8"), indent=5)
            return True

        if movie:
            if DataBase.movies.get(id) is None:
                return False
            DataBase.movies.pop(id)
            json.dump(DataBase.movies, open(os.path.join(VAR_DIR, MOVIES_LIB), "w", encoding="utf-8"), indent=5)
            return True

    def delete_episode(id: int, season_number: int, episode_number: int, show: bool = False, anime: bool = False) -> \
            Union[bool, str]:
        """
        Deletes an episode from the database.

        Args:
            id (int): The ID of the show or anime.
            season_number (int): The season number of the episode.
            episode_number (int): The episode number.
            show (bool, optional): Flag indicating whether the ID corresponds to a TV show. Defaults to False.
            anime (bool, optional): Flag indicating whether the ID corresponds to an anime. Defaults to False.

        Returns:
            bool: path of the episode is successfully deleted, False otherwise.

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

        id, dic, file = str(id), None, None
        season_number = str(season_number).zfill(2)
        episode_number = str(episode_number).zfill(2)

        if anime:
            dic, file = deepcopy(DataBase.animes), ANIME_LIB
        elif show:
            dic, file = deepcopy(DataBase.shows), SHOWS_LIB
        if dic.get(id) is None:
            return False
        elif dic[id].get(season_number) is None:
            return False
        elif dic[id][season_number].get(episode_number) is None:
            return False
        path = dic[id][season_number][episode_number]["path"]
        dic[id][season_number].pop(episode_number)
        json.dump(dic, open(os.path.join(VAR_DIR, file), "w", encoding="utf-8"), indent=5)
        if anime:
            DataBase.animes = deepcopy(dic)
        elif show:
            DataBase.shows = deepcopy(dic)
        return path

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

    def list_missing_episodes(self):
        missing, temp = {"anime": {}, "show": {}}, {}
        for name, lib in [("anime", self.animes), ("show", self.shows)]:
            for shows in lib:
                for seasons in lib[shows]["seasons"]:
                    for i in range(1, lib[shows]["seasons"][seasons]["season_info"]["episode_count"] + 1):
                        if lib[shows]["seasons"][seasons]["current_episode"].get(str(i).zfill(2), None) is None:
                            if temp.get(shows, None) is None:
                                temp[shows] = {}
                            if temp[shows].get(seasons, None) is None:
                                temp[shows][seasons] = []
                            temp[shows][seasons].append(str(i).zfill(2))
                    try:
                        if len(temp[shows][seasons]) == 1:
                            if temp[shows][seasons][0] == "00":
                                temp[shows][seasons] = []
                    except KeyError:
                        pass
            missing[name] = deepcopy(temp)
            temp.clear()
        return missing

    def search_episode_source(self, anime_id: int, season_number: int, episode_number: int, anime=False,
                              show=False) -> dict | None:
        if not (anime or show):
            raise ValueError("You should choose anime or show in function parameter")
        show_info = self.get_tmdb_info_by_id(anime_id, anime=anime, show=show, movie=False)
        seasons = show_info["seasons"]
        season = [s for s in seasons if s["season_number"] == season_number]
        if not season:
            raise ValueError(f"The season {season_number} does not exist for show {anime_id}")
        else:
            season = season[0]
        if season["episode_count"] < episode_number:
            raise ValueError(f"The episode {episode_number} does not exist for show {anime_id} season {season_number}")
        if self.dict_have_ep(Server.feed_storage, anime_id, season_number, episode_number) is None:
            pass
        else:
            return Server.feed_storage.get(str(anime_id)).get(str(season_number).zfill(2)).get(
                str(episode_number).zfill(2))
        for connector in ConnectorShowBase.__subclasses__():
            con = connector(anime_id)
            if not isinstance(con, ConnectorShowBase):
                raise Exception(f"Malformed connector {connector}")
            else:
                if con.active:
                    result = con.find_ep(season_number, episode_number, anime, show)
                    if result is not None:
                        return result
        return None

    def search_season_source(self, show_id: int, season_number: int, anime=False, show=False) -> dict | None:
        if not (anime or show):
            raise ValueError("You should choose anime or show in function parameter")
        anime = self.get_tmdb_info_by_id(show_id, anime=anime, show=(not anime), movie=False)
        seasons = anime["seasons"]
        season = [s for s in seasons if s["season_number"] == season_number]
        if season == []:
            raise ValueError(f"The season {season_number} does not exist for show {show_id}")
        else:
            season = season[0]
        for connector in ConnectorShowBase.__subclasses__():
            con = connector(show_id)
            if not isinstance(con, ConnectorShowBase):
                raise Exception(f"Malformed connector {connector}")
            else:
                if con.active and hasattr(connector, "find_batch"):
                    result = con.find_batch(season_number, anime, show)
                    if result is not None:
                        return result
        return None

    def dl_torrent(self, url: str, name: str, show=False, anime=False, movie=False):
        target_directory = None
        if anime:
            target_directory = os.path.join(Server.conf['torrent_dir'], "anime")
        elif show:
            target_directory = os.path.join(Server.conf['torrent_dir'], "show")
        elif movie:
            target_directory = os.path.join(Server.conf['torrent_dir'], "movie")
        else:
            raise ValueError("You should choose show, anime or movie in function parameter")
        torrent_content = self.getresponse(url).content
        if os.path.splitext(name)[1] != ".torrent":
            name = name + ".torrent"
        os.makedirs(target_directory, exist_ok=True)
        with open(os.path.join(target_directory, forbidden_car(name)), "wb") as f:
            f.write(torrent_content)

    def get_episode(self, list_ep: list, season: int, identifier: int, anime=False, show=False) -> bool:
        if not (show or anime):
            raise ValueError("You should choose between show and anime in function parameter")
        find = False
        for ep in list_ep:
            episode = self.search_episode_source(int(identifier), int(season), int(ep), anime=anime, show=show)
            if episode is None:
                continue
            find = True
            self.dl_torrent(episode["link"], episode["torrent_title"], anime=anime, show=show, movie=False)
        return find

    def get_batch(self, season: int, identifier: int, anime=False, show=False) -> bool:
        if not (show or anime):
            raise ValueError("You should choose between show and anime in function parameter")
        find = False
        batch = self.search_season_source(int(identifier), int(season), anime=anime, show=show)
        if batch is not None:
            find = True
            self.dl_torrent(batch["link"], batch["torrent_title"], anime=anime, show=show, movie=False)

        return find

    def fetch_missing_ep(self):
        list_missing = self.list_missing_episodes()
        for target in list_missing:
            anime = target == "anime"
            show_status = not anime
            for show in list_missing[target]:
                info = self.get_tmdb_info_by_id(int(show), anime=anime, show=show_status)
                if info is None:
                    continue
                for season in list_missing[target][show]:
                    if info["last_episode_to_air"] is not None:
                        if info["last_episode_to_air"]["season_number"] != int(season) or info["last_episode_to_air"][
                            "episode_number"] == info["seasons"][int(season) - 1]["episode_count"]:
                            log(f"searching batch season {season} for {info['name']}")
                            if self.get_batch(int(season), int(show), anime=anime, show=show):
                                log(f"Found batch for Season {season} of {info['name']}")
                                continue
                    log(f"searching batch ep  {season} for {info['name']}")
                    if self.get_episode(list_missing[target][show][season], int(season), int(show), anime=anime,
                                        show=show_status):
                        log(f"episodes found for {info['name']} season {season}")

    def fetch_requested_shows(self, show=False, anime=False):
        if not (show or anime):
            raise ValueError("You should choose between show and anime in function parameter")
        list_missing, show_status, file = [''], show, None
        if show:
            list_missing, file = Server.query_show, QUERY_SHOW
        elif anime:
            list_missing, file = Server.query_anime, QUERY_ANIME,
        if list_missing == ['']:
            return
        for show in list_missing:
            info = self.get_tmdb_info_by_id(int(show), anime=anime, show=show)
            if info is None or DataBase.find(info["name"], anime=True) or DataBase.find(info["name"], shows=True):
                continue
            for season in info["seasons"]:
                season_number = season["season_number"]
                if info["last_episode_to_air"] is None:
                    continue
                season_ended = info["last_episode_to_air"]["season_number"] != int(season_number) or \
                               info["last_episode_to_air"][
                                   "episode_number"] == info["seasons"][int(season_number) - 1]["episode_count"]
                if season_ended and self.get_batch(int(season_number), int(show), anime=anime, show=show_status):
                    log(f"Found batch for Season {season} of {info['name']}")
                    Server.delete_query(int(show), anime=anime, show=show_status)
                    continue
                else:
                    list_ep = [i for i in range(info["seasons"][season_number]["episode_count"] + 1)]
                    if self.get_episode(list_ep, season_number, int(show), anime=anime, show=show_status):
                        log(f"episodes found for {info['name']} season {season_number}")
                        Server.delete_query(int(show), anime=anime, show=show_status)

    def fetch_request(self):
        self.fetch_requested_shows(anime=True)
        self.fetch_requested_shows(show=True)

        
    def sort(self, anime=False, shows=False, movie=False):
        directory, list_file, sorter, arg = None, None, None, {"file_reachable": True}
        if anime:
            sorter, arg = SorterShows, {"file_reachable": True, "is_anime": True}
            directory = self.to_sort_anime
        elif shows:
            sorter, arg = SorterShows, {"file_reachable": True}
            directory = self.to_sort_show
        elif movie:
            sorter, arg = SorterMovie, {"file_reachable": True}
            directory = self.to_sort_movie
        if type(directory) == str:
            list_file = list_all_files(directory)
        elif type(directory) == list:
            list_file = []
            for directory in directory:
                list_file += list_all_files(directory)
        for file in list_file:
            if os.path.isfile(file) and is_video(file):
                try:
                    s = sorter(file, **arg)
                    if self.add(s.title, anime, shows, movie):
                        log(f"Adding {s.title} --> {s}")
                        DataBase.add_file(s, anime, shows, movie)
                    else:
                        log("Something went wrong when adding media to Database in sort method", debug=True)
                except (RuntimeError, PermissionError, subprocess.CalledProcessError, ValueError, IndexError) as e:
                    log(f"{e} ---> {file}", debug=True)
                    pass


    def check_sorter_folder(self):
        conf_list = [(self.to_sort_anime, True, False, False),
                     (self.to_sort_show, False, True, False),
                     (self.to_sort_movie, False, False, True)]
        for path, anime, show, movie in conf_list:
            if type(path) == str and os.listdir(path) != []:
                self.sort(anime=anime, shows=show, movie=movie)
            elif type(self.to_sort_anime) == list:
                for directory in self.to_sort_anime:
                    if os.listdir(directory):
                        self.sort(anime=anime, shows=show, movie=movie)

    def have_ep(self, file: SorterShows, anime=False, shows=False, movie=False) -> bool:
        elt = DataBase.find(file.title, anime, shows, movie)
        if elt == False:
            return False
        elif not movie:
            if elt.seasons_created.get(file.season, None) is None:
                return False
            else:
                ep = elt.seasons_created[file.season]["current_episode"].get(file.ep, None)
            if ep is None:
                return False
            else:
                return True
        return False
    
    def move_media(self, id : int, path: str, anime=False, show=False, movie=False) -> bool:
        if not os.path.isdir(path):
            return False
        if (anime or show) and movie:
            return False
        if anime:
            media_info = self.animes.get(str(id), None)
        if show:
            media_info = self.shows.get(str(id), None)
        if movie:
            media_info = self.movies.get(str(id), None)

        if media_info is None:
            return False
        original_path = media_info["path"]
        media_info["path"] = os.path.join(path, os.path.basename(original_path))
        log(f"Moving {original_path} --> {path}")
        safe_move_dir(original_path, path, max_retries=10)
        if (anime or show):
            for season in media_info["seasons"]:
                media_info["seasons"][season]["path"] = str(media_info["seasons"][season]["path"]).replace(original_path, media_info["path"])
                for episodes in media_info["seasons"][season]["current_episode"]:
                    media_info["seasons"][season]["current_episode"][episodes]["path"] = str(media_info["seasons"][season]["current_episode"][episodes]["path"]).replace(original_path, media_info["path"])
        if os.path.isdir(os.path.join(path, os.path.basename(original_path))):
            if anime:
                self.animes[str(id)] = media_info
                json.dump(DataBase.animes, open(os.path.join(VAR_DIR, ANIME_LIB), "w", encoding="utf-8"), indent=5)
            elif movie:
                self.movies[str(id)] = media_info
                json.dump(DataBase.movies, open(os.path.join(VAR_DIR, MOVIES_LIB), "w", encoding="utf-8"), indent=5)
            elif show:
                self.shows[str(id)] = media_info
                json.dump(DataBase.shows, open(os.path.join(VAR_DIR, SHOWS_LIB), "w", encoding="utf-8"), indent=5)
            return True
        else:
            return False 
        
    
    def find_id_by_path(self,path: str, anime=False, show=False, movie=False) -> int | None:
        if anime:
            dic = self.animes
        elif show:
            dic = self.shows
        elif movie:
            dic = self.movies
        for ids in dic:
            if dic[ids]["path"] == path:
                return int(ids)
        return None

    def adjust_directories(self, dic : dict, anime=False, show=False, movie=False):
        max_free = [i for i in dic if dic[i]["free_space"] == max([dic[k]["free_space"] for k in dic])][0]
        dic_id_dst = {}
        compteur = 0
        for dirs in dic:
            if dic[dirs]["free_space"]/dic[max_free]["free_space"] < 0.9:
                while dic[dirs]["free_space"]/dic[max_free]["free_space"] < 0.9:
                    if compteur > 25:
                        break
                    directory = [i for i in dic[max_free] if i != "free_space" and dic[max_free][i][0] == min([dic[max_free][k][0] for k in dic[max_free] if k != "free_space" ])][0]
                    min_media_max_free = dic[max_free][directory]
                    dic[max_free]["free_space"] -= min_media_max_free[0]
                    dic_id_dst[min_media_max_free[1]] = dirs
                    compteur+=1
                max_free = [i for i in dic if dic[i]["free_space"] == max([dic[k]["free_space"] for k in dic])][0]

        for ids in dic_id_dst:
            if ids is not None:
                self.move_media(int(ids), dic_id_dst[ids], anime, show, movie)
            
    def balance_media(self):
        dic_media_size = {}
        total_size = 0
        temp = self.anime_dirs
        if isinstance(self.anime_dirs, str):
            temp = [self.anime_dirs]

        for dirs in temp:
            dic_media_size[dirs] = {"free_space" : get_free_space(dirs)}
            for directory in os.listdir(dirs):
                path = os.path.join(dirs, directory)
                size = get_dir_size(path)
                dic_media_size[dirs][path] = [size, self.find_id_by_path(path, anime=True)]
        self.adjust_directories(dic_media_size, anime=True)
        temp = self.shows_dirs
        if isinstance(self.shows_dirs, str):
            temp = [self.shows_dirs]
        dic_media_size.clear()
        for dirs in temp:
            dic_media_size[dirs] = {"free_space" : get_free_space(dirs)}
            for directory in os.listdir(dirs):
                path = os.path.join(dirs, directory)
                size = get_dir_size(path)
                dic_media_size[dirs][path] = [size, self.find_id_by_path(path, show=True)]
        self.adjust_directories(dic_media_size, show=True)
        dic_media_size.clear()
        temp = self.movie_dirs
        if isinstance(self.movie_dirs, str):
            temp = [self.movie_dirs]
        for dirs in temp:
            dic_media_size[dirs] = {"free_space" : get_free_space(dirs)}
            for directory in os.listdir(dirs):
                path = os.path.join(dirs, directory)
                size = get_dir_size(path)
                dic_media_size[dirs][path] = [size, self.find_id_by_path(path, movie=True)]
        self.adjust_directories(dic_media_size, movie=True)

                
    def update_tmdb(self):
        ids_to_update = [[self.tmdb_db[i]["id"], i] for i in self.tmdb_db]
        for id in ids_to_update:
            is_movie = False
            is_anime = [] != [i for i in self.tmdb_db[id[1]]["genres"] if i["name"] == "Animation" and self.tmdb_db[id[1]].get("seasons", None) is not None]
            if not is_anime:
                is_movie = self.tmdb_db[id[1]].get("seasons", None) is None
            self.store_tmdb_info(id[0], show=(not is_anime), anime=is_anime, movie=is_movie)
            log(f"{id} updated in tmdb_db")
            
    def save_tmdb_title(self):
        json.dump(Server.tmdb_title, open(os.path.join(VAR_DIR, TMDB_TITLE), "w", encoding="utf-8"), indent=5)


if __name__ == "__main__":
    
    print(get_dir_size("/home/strange/install/shared/media/anime"))
    d = DataBase()
    d.fetch_missing_ep()
    pass
