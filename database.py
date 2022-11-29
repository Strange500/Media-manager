from file_analyse_lib import *
from pprint import pprint
# anime_dir=["Z:\install server v2\sorter\JellyFin\Anime\Airing","Y:\Ext_serv\sorter\JellyFin\Anime\Airing"]

# def ep_file(file):
#     print(file)
#     return file.split(" - ")[1]


# def merge(folder1,folder2):
#     """move folder 2 to folder 1"""
#     list_folder1=os.listdir(folder1)
#     list_folder2=os.listdir(folder2)
#     for file in list_folder2:
       
#         if file in list_folder1 and not os.path.isdir(folder2+"/"+file) and "mkv" not in file and "mp4" not in file:
#             print("not ep"+" "+file)
#             os.remove(folder2+"/"+file)
#         elif file not in list_folder1 and not os.path.isdir(folder2+"/"+file) and "mkv" not in file and "mp4" not in file:
#             print(folder2+"/"+file+" -----> "+folder1+"/"+file)
#             shutil.move(folder2+"/"+file,folder1+"/"+file)
#         elif os.path.isdir(folder2+"/"+file) and file not in list_folder1 :
#             print(folder2+"/"+file+" -----> "+folder1+"/"+file)
#             try:
#                 shutil.move(folder2+"/"+file,folder1+"/"+file)
#             except:
#                 pass
#             print("dossier "+file)
#         elif os.path.isdir(folder2+"/"+file) and file in list_folder1 :
#             merge(folder1+"/"+file,folder2+"/"+file)
#         elif  "mkv" in file or "mp4" in file :
#             liste_ep_folder1={}
#             liste_ep_folder2={}
#             for filee in list_folder1:
#                 if "mkv" in filee or "mp4" in filee:
#                     liste_ep_folder1[ep_file(filee)]=filee
#             for fileee in list_folder2:
#                 if "mkv" in fileee or "mp4" in fileee:
#                     liste_ep_folder2[ep_file(fileee)]=fileee
#             for ep in liste_ep_folder2:
#                 if ep in liste_ep_folder1:
#                     try:
#                         print(liste_ep_folder2[ep]+" remove")
#                         os.remove(folder2+"/"+liste_ep_folder2[ep])
#                     except FileNotFoundError:
#                         pass
#                     except:
#                         pass
                        
#                 else:
#                     try:
#                         print(folder2+"/"+liste_ep_folder2[ep]+" -----> "+folder1+"/"+liste_ep_folder2[ep])
#                         shutil.move(folder2+"/"+liste_ep_folder2[ep],folder1+"/"+liste_ep_folder2[ep])
#                     except FileNotFoundError:
#                         pass
#     try:              
#         shutil.rmtree(folder2)
#     except:
#         pass


# def delete_duplicate()->None:
#     #use os.path.getctime() to choose between duplicate
#     ls=[]
#     # try:
#     for dir in anime_dir:
#             for anime in os.listdir(dir):
#                     print(anime)
#                     try:
#                         ls=list_season(f"{dir}/{anime}")[0]

#                         ep={}
#                         for elt in ls:
                                

#                                     for file in ls[elt]:
#                                         if " -  -Strange" in file :
#                                                 os.remove(f"{elt}/{file}")
#                                                 pass
#                                         elif  " - SEhe - " in ls:
#                                             os.remove()
#                                             pass
                                        
                                        
#                                         elif  not file.split(" - ")[1].split("E")[-1].strip() in ep.keys():
#                                             ep[file.split(" - ")[1].split("E")[-1].strip()]=f"{elt}/{file}"
#                                         else :
#                                             if os.path.getsize(ep[file.split(" - ")[1].split("E")[-1].strip()])<= os.path.getsize(f"{elt}/{file}"):
#                                                 ep[file.split(" - ")[1].split("E")[-1].strip()]=f"{elt}/{file}"
#                                             elif os.path.getctime(ep[file.split(" - ")[1].split("E")[-1].strip()]) >= os.path.getctime(f"{elt}/{file}") :
#                                                 ep[file.split(" - ")[1].split("E")[-1].strip()]=f"{elt}/{file}"
#                                             else:
#                                                 os.remove(f"{elt}/{file}")
#                                                 print(f"del {file}")
#                     except IndexError:
#                         pass
#                     except FileNotFoundError:
#                         pass
#     # except Exception as error:
#     #                             input(f"waiting {error}")
#     print("####TEST####")


# def determine_merge(dir):
#     ls=[]
#     for direct in os.listdir(dir):
#         for car in [str(i) for i in range(10)]:
#             if car in direct and direct[direct.index(car)-1]=="S"  and direct[direct.index(car)-2]==" "  :
#                 pass
#                 # shutil.rmtree(f"{dir}/{direct}")
#                 # try:
#                 #     if direct[direct.index(car)+1] in [str(i) for i in range(10)]:
#                 #         direct=direct.split(f" S{car}{direct[direct.index(car)+1]}")[0]
#                 # except IndexError:
#                 #     pass

                
#                 # direct=direct.split(f" S{car}")[0]
#             elif f" part {car}" in direct.lower():
#                 pass                # shutil.rmtree(f"{dir}/{direct}")
#             else:
#                 ls.append(direct)
#     dict={}
#     for file in ls:
#         anime =title_to_romaji(file)
#         if anime in dict.keys():
#             if file not in dict[anime]:
#                 dict[anime].append(file)
#         else:
#             dict[anime]=[file]

#     for keys in dict.keys():
#         print(dict[keys])

            
            
        # direct=direct.replace()
        # anime=title_to_romaji(direct)
        

file='[Judas] Kakkou no Iinazuke (A Couple of Cuckoos) (Season 1) [1080p][HEVC x265 10bit][Multi-Subs]'

def isolate_quote(file)->list:
    contain,ls="",[]
    while file[0]!="(":
        print(file)
        file=file[1:]
    while file[0]!=")":
        contain+=file[0]
        file=file[1:]
    ls.append(contain)
    if "(" in file and ")" in file:
        return ls+isolate_quote(file)
    else:
        return ls

def judas_season(file):
    file=[i for i in isolate_quote(file) if "Season " in i or "Saison " in i]
    return [car for car in "".join(file) if car in [str(i) for i in range(0,10)]]

def judas_is_vostfr(path_to_anime_dir):
    for file in os.listdir(path_to_anime_dir):
        if "mkv" in file:
            judas_download_ep(f"{path_to_anime_dir}/{file}",f"test")
            statut=Episode(f"{path_to_anime_dir}/{file}").is_vostfr()
            os.remove(f"{path_to_anime_dir}/{file}")
            return statut


def judas_download_ep(src,dest):
    
        os.makedirs(dest,exist_ok=True)
        dest_name=src.split("/")[-1]
        with open(src,"rb") as f:
            open(f"{dest}/{dest_name}","wb").write(f.read())
        


def download_judas_anime(title):
    title,judas=title_to_romaji(title),"G:\Drive partagés\Judas - DDL 1\Judas - DDL"
    for dir in os.listdir(judas):
        for anime in os.listdir(f'{judas}/{dir}'):
            if "Movie" in anime:
                pass
            else:
                temp=anime
                for banned_car in [("[","]"),("{","}"),("(",")")]:
                    car1,car2=banned_car
                    try:
                        temp=car_to_car(temp,car1,car2)
                    except:
                        pass
                print(temp)
                if title==title_to_romaji(temp):
                    for file in os.listdir(f'{judas}/{dir}/{anime}'):
                        judas_download_ep(f'{judas}/{dir}/{anime}/{file}',)
                    break

def judas_google_drive():
    print(os.listdir("G:\Drive partagés\Judas - DDL 1\Judas - DDL\[Judas] Webrip batches"))

def list_judas_anime(path="G:\Drive partagés\Judas - DDL 1\Judas - DDL"):
    dic={}
    for dir in os.listdir(path):
        for file in os.listdir(f"{path}/{dir}"):
            temp=file
            for banned_car in [("[","]"),("{","}"),("(",")")]:
                car1,car2=banned_car
                try:
                    temp=car_to_car(temp,car1,car2)
                except:
                    pass
            t=title_to_romaji(temp)
            print(t)
            if t in dic.keys():
                dic[t].append(f"{path}/{dir}/{file}")
            else:
                dic[t]=[f"{path}/{dir}/{file}"]
    json.dump(dic,open("judas_anime_lib.json","w"),indent=4)


def delete_duplicate():
    json.dump(list_anime(),open("anime_lib.json","w"),indent=4)
    dic=json.load(open("anime_lib.json"))
    for anime in dic.keys():
        liste_ep=[]
        for dir in dic[anime]:
            for elt in os.listdir(dir):
                if "Season" in elt and os.path.isdir(f"{dir}/{elt}"):
                    for file in os.listdir(f"{dir}/{elt}"):
                        if "mkv" in file or "mp4" in file:
                            ep=File(file).__str__().split(" - ")[1]
                            if ep not in liste_ep:
                                liste_ep.append(ep)
                            else:
                                print("remove "+file)
                                os.remove(f"{dir}/{elt}/{file}")





def main()->None:
    # print(judas_is_vostfr("G:\Drive partagés\Judas - DDL 1\Judas - DDL\[Judas] Webrip batches\[Judas] 86 (Eighty Six) (2021) (Season 01pt02 + Specials) [1080p][HEVC x265 10bit][Multi-Subs]"))
    # print(search_judas_anime("a couple of cuckoos"))
    # print(judas_google_drive())
    # f=open("G:\Drive partagés\Judas - DDL 1\Judas - DDL\[Judas] Webrip batches\[Judas] Overlord (Season 4) [1080p][HEVC x265 10bit][Dual-Audio][Multi-Subs]\[Judas] Overlord - S04E12v2.mkv","rb")
    # open("test.mkv","wb").write(f.read())
    # shutil.copy("G:\Drive partagés\Judas - DDL 1\Judas - DDL\[Judas] Webrip batches\[Judas] Overlord (Season 4) [1080p][HEVC x265 10bit][Dual-Audio][Multi-Subs]","D:\anime")
    # check_double()
    # json.dump(list_anime(),open("anime_lib.json","w"),indent=4)
    # list_anime()
    delete_duplicate()
    anime_lib=json.load(open("anime_lib.json","r"))
    # list_judas_anime()
    judas_lib=json.load(open("judas_anime_lib.json","r"))
    for anime in anime_lib:
        if anime in judas_lib.keys():
            print(f"{anime} matching")
            if get_source(anime)!="Judas":
                liste_ep=[]
                for dir in judas_lib[anime]:
                    if "Movie" in dir:
                        pass
                    else:
                        try:
                            if judas_is_vostfr(dir)==True:
                                print("begin download")
                                for file in os.listdir(dir):
                                    if ("mp4" in file or "mkv" in file) and liste_ep.append(File(file).__str__().split(" - ")[1]) not in liste_ep:
                                        try:
                                            judas_download_ep(f"{dir}/{file}",temp_dir)
                                            shutil.move(f"{temp_dir}/{file}",download_dir[0])
                                            print(f"{file} downloaded")
                                            liste_ep.append(File(file).__str__().split(" - ")[1])
                                        except OSError:
                                            pass
                        except:
                            pass
    








if __name__=="__main__":
    main()