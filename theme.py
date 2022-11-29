import os
from youtubesearchpython import VideosSearch
from pytube import *
from file_analyse_lib import *


def dl_theme(dir):
    if "theme.mp3" in os.listdir(dir):
        return
    research=dir.split("/")[-1]+" opening"
    print(research)
    videosSearch = VideosSearch(research, limit = 2)
    re=videosSearch.result()["result"][0]["link"]
    print(re)
    dl(re,dir)


def dl(url,dir):
    
    yt = YouTube(url)

    yt.title=forbiden_car(yt.title)
    yt.author=forbiden_car(yt.author)
    try:
        if list(yt.title)[0]=="":
            yt.title=yt.title.replace(" ","",1)
        if list(yt.title)[-1]=="":
            yt.title=list(yt.title)
            yt.title.pop()
            yt.title="".join(yt.title)
    except:
        pass
    # audio="theme."+yt.streams.filter(progressive=False,is_dash=True,type="audio").order_by("abr")#.last().mime_type.split("/")[-1]
    audio=yt.streams.filter(progressive=False,is_dash=True,type="audio").order_by("abr").all()
    audio.pop(0)
    for aud in audio:
        if aud.mime_type=="audio/mp4":
            aud.download(dir,filename="theme."+"mp3")


    

    
   

for file in os.listdir("Z:\install server v2\sorter\JellyFin\Anime\Airing"):
    dl_theme("Z:\install server v2\sorter\JellyFin\Anime\Airing"+"/"+file)