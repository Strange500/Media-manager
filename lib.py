import datetime
import os
import platform
from pprint import pprint

if platform.system() == "Windows":
    PYTHON = "python"
    NTERM = "start"
    REBOOT = "shutdown /r"
    VAR_DIR = "C:\\Users\\benja\\AppData\\Local\\my-server"
    VAR_DIR = ""
elif platform.system() == "Linux":
    PYTHON = "python3"
    NTERM = "gnome-terminal --"
    REBOOT = "reboot"
    VAR_DIR = "/var/lib/my-server"


def time_log():
    # Get the current time
    current_time = datetime.datetime.now()
    datetime.datetime.now().strftime("%H")

    # Format the time as a string with the hour, minute, and second
    return current_time.strftime("%H:%M:%S")


def log(to_log: str, warning=False, error=False) -> None:
    if type(to_log) == str:
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


def load_config(lib: str | None = VAR_DIR):
    try:
        config = {}
        with open(os.path.join(lib, "server.conf"), "r", encoding="utf-8") as f:
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
                            f"some values are not set in server.conf, please make sure you have all set here is the line where's the issue : {lines}")
                        quit()
                    config[arg1] = arg2

        if config["GGD_Judas"]:
            if config["GGD_Judas"] == "FALSE":
                config.pop("Judas_dir")
            elif config["GGD_Judas"] == "TRUE":
                pass
            else:
                raise ValueError(
                    f"The value of GGD_Judas in {os.path.join(VAR_DIR, 'server.conf')} have to be TRUE or FALSE")
        if config["Clip"]:
            if config["Clip"] == "FALSE":
                config.pop("clip_load")
                config.pop("clip_lib")
            elif config["Clip"] == "TRUE":
                pass
            else:
                raise ValueError(
                    f"The value of Clip in {os.path.join(VAR_DIR, 'server.conf')} have to be TRUE or FALSE")

        for key in config:
            if "dir" in key:
                if not os.path.isdir(config[key]):
                    raise NotADirectoryError(
                        f"The directory in {os.path.join(VAR_DIR, 'server.conf')} specified as {config[key]} does not exist")
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


class Episode():
    def __init__(self, path: str, is_light=True):
        if path:
            self.path = path
        else:
            raise ValueError("The episode you try to create have no path")
        self.file_name = os.path.basename(self.path)
        self.clean_file_name = os.path.splitext(self.file_name)[0]  # get file name with no extension
        self.ext = os.path.splitext(self.file_name)[1]
        self.make_clean_file_name()
        self.title = None
        self.season = None

    def make_clean_file_name(self):
        for banned_car in [("[", "]"), ("{", "}"), ("(", ")")]:
            car1, car2 = banned_car
            while car1 in self.clean_file_name and car2 in self.clean_file_name:
                self.clean_file_name = delete_from_to(self.clean_file_name, car1, car2)

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


def main():
    pprint(load_config())
    print(Episode("Anime S01E09 1080p .mkv"))


if __name__ == "__main__":
    main()
