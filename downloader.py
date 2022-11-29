from file_analyse_lib import *
import requests
from pprint import pprint

def main():
    banned_words,select_words=open("banned_words.txt","r",encoding="utf-8").read().split("\n"),open("select_words.txt","r",encoding="utf-8").read().split("\n")
    for url in open("rss.txt","r",encoding="utf-8").read().split("\n"):
        print("Scanning feed ...")
        feed=FeedAnime(url,banned_words,select_words)

        for episode in feed.ep:
            print(episode)
            if episode in open("already_download.txt","r").read().split("\n"):
                print("pass")
                pass
            else:
                print("select")
                open("already_download.txt","a").write(f'{episode}\n')
                r = requests.request("GET",feed.ep[episode])
                open(f"torrent/{forbiden_car(episode)}.torrent","wb").write(r.content)
                print(f"{episode} downloaded")
                log(f"DOWNLOADER : {episode} downloading")

    # # print("Downloader succesfuly exited")
    # rss=open("rss.txt","r",encoding="utf-8").read().split("\n")[0]
    # pprint(FeedAnime(rss,banned_words,select_words).ep)
    # print("Akiba Maid War - S01E05 - [VOSTFR h264 1080p] -Tsundere-Raws .mkv" in open("already_download.txt","r").read().split("\n"))
if __name__=="__main__":
    main()