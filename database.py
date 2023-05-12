from file_analyse_lib import *
from pprint import pprint


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
    for file in os.listdir(path_to_anime_dir):
        if "mkv" in file:
            judas_download_ep(f"{path_to_anime_dir}/{file}", f"test")
            statut = Episode(f"{path_to_anime_dir}/{file}").is_vostfr()
            os.remove(f"{path_to_anime_dir}/{file}")
            return statut


def judas_download_ep(src, dest):
    os.makedirs(dest, exist_ok=True)
    dest_name = src.split("/")[-1]
    with open(src, "rb") as f:
        open(f"{dest}/{dest_name}", "wb").write(f.read())


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
            print(t)
            if t in dic.keys():
                dic[t].append(f"{path}/{dir}/{file}")
            else:
                dic[t] = [f"{path}/{dir}/{file}"]
    json.dump(dic, open("judas_anime_lib.json", "w"), indent=4)


def delete_duplicate():
    json.dump(list_anime(), open("anime_lib.json", "w"), indent=4)
    dic = json.load(open("anime_lib.json"))
    for anime in dic.keys():
        liste_ep = []
        for dir in dic[anime]:
            for elt in os.listdir(dir):
                if "Season" in elt and os.path.isdir(f"{dir}/{elt}"):
                    for file in os.listdir(f"{dir}/{elt}"):
                        if "mkv" in file or "mp4" in file:
                            ep = File(file).__str__().split(" - ")[1]
                            if ep not in liste_ep:
                                liste_ep.append(ep)
                            else:
                                print("remove " + file)
                                os.remove(f"{dir}/{elt}/{file}")


def main() -> None:
    delete_duplicate()
    anime_lib = json.load(open("anime_lib.json", "r"))
    list_judas_anime()
    judas_lib = json.load(open("judas_anime_lib.json", "r"))
    for anime in anime_lib:
        if anime in judas_lib.keys():
            print(f"{anime} matching")
            if get_source(anime) != "Judas":
                liste_ep = []
                for dir in judas_lib[anime]:
                    if "Movie" in dir:
                        pass
                    else:
                        try:
                            if judas_is_vostfr(dir):
                                print("begin download")
                                for file in os.listdir(dir):
                                    if ("mp4" in file or "mkv" in file) and liste_ep.append(
                                            File(file).__str__().split(" - ")[1]) not in liste_ep:
                                        try:
                                            judas_download_ep(f"{dir}/{file}", temp_dir)
                                            shutil.move(f"{temp_dir}/{file}", download_dir[0])
                                            print(f"{file} downloaded")
                                            liste_ep.append(File(file).__str__().split(" - ")[1])
                                        except OSError:
                                            pass
                        except:
                            pass


if __name__ == "__main__":
    main()
