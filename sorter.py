import shutil

from file_analyse_lib import *


def main():
    get_anime()
    print(sorter_dir)
    for dir in sorter_dir:
        if "" in dir:  #remplacer par une fonction qui evalue la place restante
            move_dir = anime_dir[0]
        elif len(anime_dir) > 1:
            move_dir = anime_dir[1]
        print(os.listdir(dir))
        for file in os.listdir(dir):
            if ".mkv" in file or ".mp4" in file:
                sorting = File(f'{dir}/{file}')
                title = forbiden_car(sorting.title)
                os.makedirs(f"{move_dir}/{title}/Season {sorting.season}", exist_ok=True)
                for file_dup in already_in_folder(file):
                    os.remove(file_dup)
                    log(f"DATABASE: {file_dup} REMOVED (duplicate)")
                try:
                    
                    shutil.move(f"{dir}/{file}",
                                f"{move_dir}/{title}/Season {sorting.season}/{forbiden_car(sorting.__str__())}")


                except FileExistsError:
                    os.remove(f"{move_dir}/{title}/Season {sorting.season}/{forbiden_car(sorting.__str__())}")
                    print(f"{file} already in so replaced by the newer one")
                    shutil.move(f"{dir}/{file}",
                        f"{move_dir}/{title}/Season {sorting.season}/{forbiden_car(sorting.__str__())}")
                except FileNotFoundError:
                    log(f"SORTER [WARNING]: {file} error while moving")
                finally:
                    logs = f"SORTER: {sorting.__str__()} ADDED TO LIBRARY"
                    log(logs)
                
            elif os.path.isdir(f"{dir}/{file}"):
                extract(f"{dir}/{file}")


if __name__ == '__main__':
    main()
