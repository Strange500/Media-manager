from base64 import encode
from file_analyse_lib import *
import shutil



def already_in_folder(file:str,dir:str):
    ls=[]
    ep=file.split(" - ")[1]
    for episode in dir:
        if ep==episode.split(" - "):
            ls.append(f"{dir}/{episode}")
    return ls



def main():
    get_anime()
    for dir in sorter_dir:
        if "E" in dir:
            move_dir=anime_dir[1]
        else:
            move_dir=anime_dir[0]
        for file in os.listdir(dir):
            if ".mkv" in file or ".mp4" in file:
                sorting=File(f'{dir}/{file}')
                title=forbiden_car(sorting.title)
                os.makedirs(f"{anime_dir[0]}/{title}/Season {sorting.season}",exist_ok=True)
                for file in already_in_folder(file,f"{anime_dir[0]}/{title}/Season {sorting.season}"):
                    os.remove(file)
                try:
                    shutil.move(f"{dir}/{file}",f"{move_dir}/{title}/Season {sorting.season}/{forbiden_car(sorting.__str__())}")


                except FileExistsError:
                    os.remove(f"{move_dir}/{title}/Season {sorting.season}/{forbiden_car(sorting.__str__())}")
                    print(f"{file} already in so replaced by the newer one")
                    shutil.move(f"{dir}/{file}",f"{move_dir}/{title}/Season {sorting.season}/{forbiden_car(sorting.__str__())}")
                finally:
                    open("log.txt","a",encoding="utf-8").write(f"{file} ---> {move_dir}/{title}/Season {sorting.season}/{sorting.__str__()}\n")
                    print(f"{file} ---> {move_dir}/{title}/Season {sorting.season}/{sorting.__str__()}\n")







if __name__=='__main__':
    main()