from pprint import pprint

from file_analyse_lib import *


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
                open("judas_not_vostfr.txt", "a").write(path_to_anime_dir + "\n")
            else:
                open("judas_vostfr.txt", "a").write(path_to_anime_dir + "\n")
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
    json.dump(dic, open("judas_anime_lib.json", "w"), indent=4)


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
    json.dump(list_anime(), open("anime_lib.json", "w"), indent=4)
    dic = json.load(open("anime_lib.json"))
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

        # for dir in dic[anime]:
        #     for elt in os.listdir(dir):
        #         if "Season" in elt and os.path.isdir(f"{dir}/{elt}"):
        #             for file in os.listdir(f"{dir}/{elt}"):
        #                 if ("mkv" in file or "mp4" in file) and "Judas" in file:
        #                     ep=File(file).__str__().split(" - ")[1]
        #                     if ep not in liste_ep:
        #                         liste_ep.append(ep)
        #                     else:
        #                         print("remove "+file)
        #                         os.remove(f"{dir}/{elt}/{file}")
        #     for elt in os.listdir(dir):
        #         if "Season" in elt and os.path.isdir(f"{dir}/{elt}"):
        #             for file in os.listdir(f"{dir}/{elt}"):
        #                 if ("mkv" in file or "mp4" in file) and "Judas" not in file:
        #                     ep=File(file).__str__().split(" - ")[1]
        #                     if ep not in liste_ep:
        #                         liste_ep.append(ep)
        #                     else:
        #                         print("remove "+file)
        #                         os.remove(f"{dir}/{elt}/{file}")


def main() -> None:
    delete_duplicate()

    # json.dump(list_anime(),open("anime_lib.json","w"),indent=4)

    anime_lib = json.load(open("anime_lib.json", "r"))

    list_judas_anime()
    judas_lib = json.load(open("judas_anime_lib.json", "r"))

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


def test():
    pprint(global_dir([
        "E:\\JellyFin\\Anime\\Airing/SPY x FAMILY",
        "D:\\JellyFin\\Anime\\Airing/SPY x FAMILY"
    ]))


if __name__ == "__main__":
    main()
    delete_duplicate()
