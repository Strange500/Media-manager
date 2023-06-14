from common import *

import subprocess
class SorterCommon(Server):

    def __init__(self, file_path, file_reachable=True):
        super().__init__()
        self.path = file_path
        self.file_reachable = file_reachable
        self.file_name = os.path.basename(self.path)
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


class SorterShows(SorterCommon):
    def __init__(self, file_path: str, file_reachable=True, is_anime=False):
        super().__init__(file_path, file_reachable)
        self.season = self.determine_season()
        self.title = self.determine_title()
        temp = super().find_tmdb_title(self.title, shows=True)
        if temp == False:
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
        season_keywords = ["2nd Season", "1st Season", "3rd Season", "Cour 2"]
        for keyword in season_keywords:
            file = file.replace(keyword, "")

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

    def determine_source(self) -> str:
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

        try:
            r = title.split(" -")[-1].strip()
            return r
        except IndexError:
            return "NoSource"

    def __str__(self):
        if not self.file_reachable:
            return forbidden_car(
                f"{self.title} - S{self.season}E{self.ep} - {self.source} {self.ext}")
        return forbidden_car(
            f"{self.title} - S{self.season}E{self.ep} - [{self.lang} {self.resolution} {self.codec}] {self.ext}")


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
        if self.title is False:
            raise Exception(f"Show {title} not found")
        self.info = super().get_tmdb_info(title, show=True)
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

        if tmdb_title == False:
            return False
        serv = Server()
        info = serv.get_tmdb_info(tmdb_title, show=(anime or shows), movie=movie)

        if info is None:
            return False

        id = str(info["id"])

        if anime:
            if DataBase.animes.get(id, None) is None:
                return False
            else:
                path = DataBase.animes[id]["path"]
                return Anime(path, tmdb_title)
        elif shows:
            if DataBase.shows.get(id, None) is None:
                return False
            else:
                path = DataBase.shows[id]["path"]
                return Show(path, tmdb_title)
        elif movie:
            if DataBase.movies.get(id, None) is None:
                return False
            else:
                path = DataBase.movies[id]["path"]
                return Movie(path, tmdb_title)
        else:
            raise ValueError("You should choose between anime, show, or movie")

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

    def add(self, title: str, anime=False, shows=False, movie=False) -> bool:
        if not isinstance(title, str):
            raise ValueError(f"Title argument must be str not {type(title)}")
        tmdb_title = super().find_tmdb_title(title, anime, shows, movie)
        if tmdb_title == False:
            raise ValueError(f"Can't find the show corresponding to {title}")

        if (anime or shows):
            title_info = "name"
        elif movie:
            title_info = "title"
        else:
            raise ValueError("You have to choose between anime|shows|movie")

        info = super().get_tmdb_info(tmdb_title, show=(shows or anime), movie=movie)

        if info is None:
            return False

        path = os.path.join(self.get_dir_freer(anime, shows, movie), forbidden_car(info[title_info]))
        os.makedirs(path, exist_ok=True)
        if (anime or shows):
            season_dict = {}
            for season in info["seasons"]:
                season_path = os.path.join(path, f"Season {str(season['season_number']).zfill(2)}")
                os.makedirs(season_path, exist_ok=True)
                season_dict[str(season["season_number"]).zfill(2)] = {"season_info": season,
                                                                      "path": season_path,
                                                                      "current_episode": {}
                                                                      }
        id = str(info["id"])
        if anime:
            if DataBase.animes.get(id, None) is not None:
                return True
            else:
                DataBase.animes[id] = {
                    "title": info[title_info],
                    "path": path,
                    "seasons": season_dict
                }
                json.dump(DataBase.animes, open(os.path.join(VAR_DIR, ANIME_LIB), "w", encoding="utf-8"), indent=5)
                return True
        elif shows:
            if DataBase.shows.get(info["id"], None) is not None:
                return True
            else:
                DataBase.shows[id] = {
                    "title": info[title_info],
                    "path": path,
                    "seasons": season_dict
                }
                json.dump(DataBase.shows, open(os.path.join(VAR_DIR, SHOWS_LIB), "w", encoding="utf-8"), indent=5)
                return True
        elif movie:
            if DataBase.movies.get(info["id"], None) is not None:
                return True
            else:
                DataBase.movies[id] = {
                    "title": info[title_info],
                    "path": path,
                    "file_info": {}
                }
                json.dump(DataBase.movies, open(os.path.join(VAR_DIR, MOVIES_LIB), "w", encoding="utf-8"), indent=5)
                return True
        else:
            raise ValueError("You have to choose between anime|shows|movie")

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
                safe_move(file.path, save_path)
                return True
            elif choose_best_version(ep, file) == file:
                save_path = DataBase.add_ep_database(file)
                delete_path = DataBase.delete_episode(file.id, int(file.season), int(file.ep), show=file.show.is_show, anime=(not file.show.is_show))
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
        folder_path = DataBase.movies[id]["path"]
        if folder_path is None:
            raise ValueError(f"{file.title} not in movie database")
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
        ep.s.anime.delete_ep(int(ep.season), ep.ep)
        self.add_file(new_file, anime, shows, movie)

    def get_season_info(id: int, season_number: str, show=False, anime=False) -> dict:
        """
        Get season information based on the ID and season number.

        Args:
            id (int): The ID of the show or anime.
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

        if not isinstance(id, int):
            raise ValueError("id must be an integer")

        if not isinstance(season_number, str):
            raise TypeError(f"season number must be a string formatted like '02', not {season_number}")

        id = str(id)

        if show:
            if DataBase.shows.get(id, None) is None:
                raise ValueError(f"Cannot find the show with ID {id} in the database")
            elif DataBase.shows[id].get("seasons", None) is None:
                raise Exception(f"Database error: no seasons associated with the show {id}, please check JSON")
            elif DataBase.shows[id]["seasons"].get(season_number, None) is None:
                raise ValueError(f"No season {season_number} for show {id}")
            return DataBase.shows[id]["seasons"][season_number]
        elif anime:
            if DataBase.animes.get(id, None) is None:
                raise ValueError(f"Cannot find the anime with ID {id} in the database")
            elif DataBase.animes[id].get("seasons", None) is None:
                raise Exception(f"Database error: no seasons associated with the anime {id}, please check JSON")
            elif DataBase.animes[id]["seasons"].get(season_number, None) is None:
                raise ValueError(f"No season {season_number} for anime {id}")
            return DataBase.animes[id]["seasons"][season_number]
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
            path = DataBase.animes[id][season_number][episode_number]["path"]
            DataBase.animes[id][season_number].pop(episode_number)
            json.dump(DataBase.animes, open(os.path.join(VAR_DIR, ANIME_LIB), "w", encoding="utf-8"), indent=5)
            return path

        if show:
            if DataBase.shows.get(id) is None:
                return False
            elif DataBase.shows[id].get(season_number) is None:
                return False
            elif DataBase.shows[id][season_number].get(episode_number) is None:
                return False
            path = DataBase.shows[id][season_number][episode_number]["path"]
            DataBase.shows[id][season_number].pop(episode_number)
            json.dump(DataBase.shows, open(os.path.join(VAR_DIR, SHOWS_LIB), "w", encoding="utf-8"), indent=5)
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
                    if shows:
                        s = SorterShows(file, file_reachable=True)
                    if anime:
                        s = SorterShows(file, file_reachable=True, is_anime=True)
                    elif movie:
                        s = SorterMovie(file, file_reachable=True)
                    if self.add(s.title, anime, shows, movie):
                        DataBase.add_file(s, anime, shows, movie)
                    else:
                        print("warnings")
                except RuntimeError as e:
                    print(e)
                    pass
                except PermissionError as e:
                    print(e)
                    pass
                except subprocess.CalledProcessError as e:
                    print(e)
                    pass
                except  ValueError as e :
                    log(e, warning=True)

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

    def have_ep(self, file: SorterShows, anime=False, shows=False, movie=False) -> bool:
        elt = self.find(file.title, anime, shows, movie)
        if elt == False:
            return False
        elif not movie:
            ep = elt.seasons_created[file.season]["current_episode"].get(file.ep, None)
            if ep is None:
                return False
            else:
                return True
        return False

    def save_tmdb_title(self):
        json.dump(Server.tmdb_title, open(os.path.join(VAR_DIR, TMDB_TITLE), "w", encoding="utf-8"), indent=5)




