from random import randint
from file_analyse_lib import *
from file_analyse_lib import sources
from pprint import pprint
import time
banned_words,select_words=open("banned_words.txt","r",encoding="utf-8").read().split("\n"),open("select_words.txt","r",encoding="utf-8").read().split("\n")


def find_anime_id(title):
    anime_id=json.load(open("anime_id.json",'r'))
    anime=title_to_romaji(title)
    
    if anime not in anime_id.keys():
        anime_id[anime]=Anime(anime).id
        json.dump(anime_id,open("anime_id.json","w"),indent=4)
        return anime_id[anime]
    else:
        for keys in anime_id:
            if keys == anime:
                return anime_id[keys]

def find_alternative_title(title):
    id=str(find_anime_id(title))
    anime_titles_database=json.load(open("anime_titles_database.json","r"))
    if id not in anime_titles_database.keys():
        anime_titles_database[id]=[i for i in tmdb.tv.TV(id).alternative_titles()["results"] if i["iso_3166_1"] in ["JP","MX","PL","US"]]
        json.dump(anime_titles_database,open("anime_titles_database.json","w"),indent=4)
        return anime_titles_database[id]
    else:
        for keys in anime_titles_database:
            if keys==id:
                return anime_titles_database[keys]

def prepare_url(search):
    ban="+".join([f"-{i}" for i in banned_words]) 
    sel="+".join(select_words) 
    return f"{search}+{ban}+{sel}"

def database_check():
    dic=json.load(open("anime_lib.json","r"))
    missing={}
    for keys in dic:
        ls=[]
        # for dir in dic[keys]:
        
    
    
        print(dic[keys])

        anime=Anime(keys)
        
        for nb in range(1,anime.number_of_season+1):
            for dir in dic[keys]:
                os.makedirs(f"{dir}/Season {nb:02}",exist_ok=True)
            
            #checking season and all ep
            season_info=tmdb.TV_Seasons((anime.tmbd.id),nb).info()
            if nb == anime.number_of_season:
                try:
                    last_ep=tmdb.TV(find_anime_id(keys)).info()["last_episode_to_air"]["episode_number"]
                    season_ep=[f"{k:02}" for k in [i for i in range(1,len(season_info["episodes"])+1) ] if k<=last_ep]
                except TypeError:
                    season_ep=tmdb.TV_Seasons((anime.tmbd.id),nb).info()["episodes"]
                except requests.exceptions.JSONDecodeError:
                    break
                except json.decoder.JSONDecodeError:
                    break
            else:
                season_ep=tmdb.TV_Seasons((anime.tmbd.id),nb).info()["episodes"]

            
            print(len(season_ep))
            y,z=[os.listdir(f'{k}/Season {nb:02}') for k in dic[keys]],[]
            for file in y:
                z+=file
            # os.listdir(f'{dir}/Season {nb:02}')
            current_ep=[i.split(" - ")[1].split("E")[-1] for i in z if ".mkv" in i or ".mp4" in i]
            if len(current_ep)==len(season_ep):
                pass
            elif len(current_ep)==0:
                ls.append("S"+str(nb))
            elif len(current_ep)<len(season_ep):
                
                for epi in [f"{i:02}" for i in range(1,len(season_ep)+1) ]:
                    if epi in current_ep:
                        pass
                    else:
                        ls.append(f"S{nb:02}E{epi}")
        if anime.title in missing.keys():
            missing[anime.title]=ls
        else:
            missing[anime.title]=ls
        # pprint(missing)
    json.dump(missing,open("missing.json","w"),indent=4)

def download_torrent(url:str,file_name=randint(1000,1000000))->None:
    if f"{forbiden_car(file_name)}.torrent" not in os.listdir("torrent"):
        torrent = requests.request("GET",url)
        os.makedirs("torrent",exist_ok=True)
        open(f"torrent/{forbiden_car(file_name)}.torrent","wb").write(torrent.content)
        time.sleep(1)

def check_nyaa_database(anime:str,season,ep_number:list)->tuple:
    database=json.load(open("nyaa.json","r"))
    anime=title_to_romaji(anime)
    for keys in database.keys():
        try:
            info=LightFile(keys)
        except IndexError:
            break
        if info.ep in ep_number and info.season==season:
            if info.title()==anime and keys!=None:
                return database[keys],keys
    return None,None

def search_ep(anime:str,season:str,ep_number:list):
    check,file=check_nyaa_database(anime,season,ep_number)
    if check!=None:
        download_torrent(check,file_name=file)
        print(f"{file}.torrent")
        return
    elif ep_number==[]:
        return
    else:
        anime_source=sources
        anime_list=find_alternative_title(anime)
        anime_list+=[{"title":anime}]
        
        prefered_source=get_source(anime_list[0]["title"])
        
        
        print(prefered_source)
        if prefered_source !=None:
            anime_source=[i for i in open("sources.txt","r").read().split("\n") if prefered_source in i]
            
        for anime in anime_list:

                a="|".join(['"'+anime["title"].replace(" ","+")+'"' for anime in anime_list])
        for source in anime_source:
            if season=="01":
                url=source.replace("##search##",prepare_url(f"{a}"))
            else:
                s=season.replace("0","")
                url=source.replace("##search##",prepare_url(f"{a}+{s}"))
                
                
                
                    
            print(url)

            r=FeedAnime(url,banned_words,select_words)
            time.sleep(2)
            for keys in r.ep:
                file=File(keys)
                if ep_number==["S"]:
                    if file.title==title_to_romaji(anime["title"]) and  file.season==season:
                        download_torrent(r.ep[keys],file_name=keys)

                        print(f"{keys}.torrent")
                        
                elif ep_number != [] and file.title==title_to_romaji(anime["title"]) and file.episode in ep_number and file.season==season:
                    download_torrent(r.ep[keys],file_name=keys)
                    ep_number.pop(ep_number.index(file.episode))
                    print(f"{forbiden_car(keys)}.torrent")
        print(ep_number)
        if ep_number!=[]:
            for source in sources:
            
                    
                if season=="01":
                    url=source.replace("##search##",f"{a}")
                else:
                    s=season.replace("0","")
                    url=source.replace("##search##",f"{a}+{s}")
                print(url)
                r=FeedAnime(url,banned_words,select_words)
                time.sleep(2)
                for keys in r.ep:
                    file=File(keys)
                    if ep_number != [] and file.title==title_to_romaji(anime["title"]) and file.episode in ep_number and file.season==season:
                        download_torrent(r.ep[keys],file_name=keys)
                        ep_number.pop(ep_number.index(file.episode))
                        print(f"{keys}.torrent")


def download_missing_ep(missing:dict):
    n=0
    for keys in missing.keys():
        if len(missing[keys])>24:
            pass
        else:
            dic={}
            # print(keys,missing[keys])
            for ep in missing[keys]:
                if len(ep) in [3,2]:
                    dic[ep.split("S")[-1]] = ["S"]
                elif ep.split("S")[-1].split("E")[0] not in dic.keys():
                    dic[ep.split("S")[-1].split("E")[0]] = [ep.split("S")[-1].split("E")[-1]]
                elif ep.split("S")[-1].split("E")[-1] not in dic[ep.split("S")[-1].split("E")[0]]:
                    dic[ep.split("S")[-1].split("E")[0]].append(ep.split("S")[-1].split("E")[-1])
            for season in dic:
               
                # input()
                # print(keys,season,dic[season])
                search_ep(keys,season,dic[season])
                n+=1
    print(n)

def main():
    # print(check_nyaa_database("shine pos","01",["01"]))
    # json.dump(list_anime(),open("anime_lib.json","w"),indent=4)
    # database_check()
    download_missing_ep(json.load(open("missing.json","r")))
    # print([i for i in tmdb.tv.TV(204716).alternative_titles()["results"] if i["iso_3166_1"]=="JP"])






if __name__=="__main__":
    main()


