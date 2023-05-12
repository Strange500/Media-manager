
from pymediainfo import MediaInfo
import os
import subprocess
from encode_API import *
import time
import psutil



class episode:
    def codec_id(self):
        media_info = MediaInfo.parse(self.path)
        for track in media_info.tracks:
            if track.track_type == "Video":
                return track.to_data()["codec_id"]
        
            

    def tracks(self):
        media_info = MediaInfo.parse(self.path)
        tracks_list_subs=[]
        tracks_list_audio=[]
        for track in media_info.tracks:
            
            if track.track_type == "Audio":
                try:
                    tracks_list_audio.append(track.to_data()["language"])
                except KeyError:
                    tracks_list_audio.append("ja")

        
            if track.track_type == "Text":

                try:
                    tracks_list_subs.append(track.to_data()["language"])
                except KeyError:
                    try:
                        tracks_list_subs=tracks_list_subs+track.to_data()["other_language"]
                    except KeyError:
                        try:
                            if "FR" in track.to_data()["title"] or "fr" in track.to_data()["title"] or "Fr" in track.to_data()["title"] or "francais" in track.to_data()["title"] or "français" in track.to_data()["title"] or "Français" in track.to_data()["title"] or "french" in track.to_data()["title"] or "French" in track.to_data()["title"]:
                                tracks_list_subs.append("fr")
                        except:
                            pass



                    

            if track.track_type == "Menu":

                try:
                    tracks_list_subs.append(track.to_data()["language"])
                except KeyError:
                    pass




        return {"subs":tracks_list_subs,"audio":tracks_list_audio}

    def extension(self):
        if ".mp4" in self.path:
            return "mp4"
        elif ".mkv" in self.path:
            return "mkv"


    def __init__(self,path) -> None:
        self.path=path
        self.track=self.tracks()
        self.ext=self.extension()
        self.codec=self.codec_id()
        self.title=self.path.split("/")[-1]



    def __repr__(self) -> str:
        
        return self.path

    def info(self):
        dic={
            "path":self.path
            ,"track":self.track,
            "extension":self.ext,
            "codec":self.codec}
        return dic

def join_txt(file):
    r=open(file,"r",encoding="utf-8")
    list=r.read()
    r.close()
    list=list.split("\n")
    return list

class liste_attente:
    def __init__(self) -> None:
        self.liste=join_txt("liste_conversion.txt")
    def avancer(self):
        self.liste.pop(0)

    def passer_liste(self,elt):
        self.liste.insert(0,elt)
    def ajouter(self,elt):
        self.liste.append(elt)
    def stock_list(self,):
    
        liste="\n".join(self.liste)
        r=open("liste_conversion.txt","w",encoding="utf-8")
        r.write(liste)
        r.close()
        return liste

    



    
def is_vf_or_vostfr(list_track):
    sub=list_track["subs"]
    aud=list_track["audio"]
    if "fr" in aud:
        return "vf"
    elif "fr" in sub and "ja" in aud:
        return "vostfr"
    elif "ja" in aud and sub==[]:
        return "VOHardsub"
    elif aud==[] and sub==[]:
        return "delete"
    else:
        return "unknown"

def conv_specification(file):
    ep=episode(file)
    spec_conv={}
    if ep.ext=="mkv":
        spec_conv["ext"]="mkv"
    else:
        spec_conv["ext"]="mp4"
    if ep.codec not in ["hvc1","hevc","V_MPEGH/ISO/HEVC"]:
        spec_conv["codec"]="wrong"
    else:
        spec_conv["codec"]="hvc1"
    spec_conv["sub_mode"]=is_vf_or_vostfr(ep.track)
    return spec_conv

def prepare_encode(file, temp_file="encoding", any=False):
    os.makedirs(temp_file, exist_ok=True)
    dic, temp_file = conv_specification(file), temp_file+"/"
    ep=episode(file)
    if any==True:
        ori = file
        output_file=ep.title
        temp_file=temp_file+output_file
        file=ori 
        return " ".join(["HandBrakeCLI.exe", "-v", "--preset-import-file","any.json", "-i", '"'+file+'"', "-o", '"'+temp_file+'"' ])
    elif dic["ext"]=="mkv" and dic["codec"]=="hvc1" and dic["sub_mode"]=="VOHardsub":
        pass 
    elif dic["ext"]=="mkv" and dic["codec"]=="wrong" and dic["sub_mode"]=="vf":
        output_file=ep.title
        temp_file=temp_file+output_file
        file=ori 
        return " ".join(["HandBrakeCLI.exe", "-v", "--preset-import-file","vf.json", "-i", '"'+file+'"', "-o", '"'+temp_file+'"' ])
    elif dic["ext"]=="mp4" and dic["codec"]=="wrong" and dic["sub_mode"]=="vf":
        ori=file
        titre=ep.title.split(".")
        titre[-1]="mkv"
        output_file=".".join(titre)
        temp_file=temp_file+output_file
        return " ".join(["HandBrakeCLI.exe", "-v", "--preset-import-file","vf.json", "-i", '"'+file+'"', "-o", '"'+temp_file+'"' ])
    elif dic["ext"]=="mp4" and dic["codec"]!="hvc1" and dic["sub_mode"]!="vf" and dic["sub_mode"]!="unknown":
        ori=file
        titre=ep.title.split(".")
        titre[-1]="mkv"
        output_file=".".join(titre)
        temp_file=temp_file+output_file
        return " ".join(["HandBrakeCLI.exe", "-v", "--preset-import-file","vostfr.json", "-i", '"'+file+'"', "-o", '"'+temp_file+'"' ])
    elif dic["ext"]=="mkv" and dic["codec"]!="hvc1" and dic["sub_mode"]!="vf" and dic["sub_mode"]!="unknown":
        output_file=ep.title
        temp_file=temp_file+output_file
        return " ".join(["HandBrakeCLI.exe", "-v", "--preset-import-file","vostfr.json", "-i", '"'+file+'"', "-o", '"'+temp_file+'"' ])
    elif dic["ext"]=="mp4" and dic["codec"]=="hvc1" and dic["sub_mode"]=="VOHardsub":
        ori=file
        titre=ep.title.split(".")
        titre[-1]="mkv"
        output_file=".".join(titre)
        temp_file=temp_file+output_file
        return 'ffmpeg.exe -i '+'"'+file+'"'+' -codec copy '+'"'+temp_file+'"'

    elif dic["ext"]=="mp4" and dic["codec"]=="hvc1" and dic["sub_mode"]=="vf":
        return
    elif dic["ext"]=="mkv" and dic["codec"]=="wrong" and dic["sub_mode"]=="vf":
        output_file=ep.title
        temp_file=temp_file+output_file
        return " ".join(["HandBrakeCLI.exe", "-v", "--preset-import-file","vf.json", "-i", '"'+file+'"', "-o", '"'+temp_file+'"' ])
    elif dic["ext"]=="mkv" and dic["codec"]=="hvc1" and dic["sub_mode"]=="vostfr":
        output_file=ep.title
        temp_file=temp_file+output_file 
        return " ".join(["HandBrakeCLI.exe", "-v", "--preset-import-file","vostfr.json", "-i", '"'+file+'"', "-o", '"'+temp_file+'"' ])
    elif dic["ext"]=="mp4" and dic["codec"]=="hvc1" and dic["sub_mode"]=="vostfr":
        ori=file
        titre=ep.title.split(".")
        titre[-1]="mkv"
        output_file=".".join(titre)
        temp_file=temp_file+output_file
        return " ".join(["HandBrakeCLI.exe", "-v", "--preset-import-file","vostfr.json", "-i", '"'+file+'"', "-o", '"'+temp_file+'"' ])
    elif dic["ext"]=="mkv" and dic["codec"]=="hvc1" and dic["sub_mode"]=="vostfr":
        output_file=ep.title
        temp_file=temp_file+output_file 
        return " ".join(["HandBrakeCLI.exe", "-v", "--preset-import-file","vostfr.json", "-i", '"'+file+'"', "-o", '"'+temp_file+'"' ])
    elif dic["ext"]=="mkv" and dic["codec"]=="hvc1" and dic["sub_mode"]=="vf":
        pass

    

    else:
        return prepare_encode(file, any=True)
    



    







def encode(commande:str):
    if commande != None and commande != "ok" and commande != "unknonw":
        try:
            filename = commande.split('"')[3].split("/")[-1]
            path = commande.split('"')[3]
            os.makedirs("encoding/log", exist_ok=True)
            os.makedirs("web_download", exist_ok=True)
            f = open(f"encoding/log/{filename}.txt","w")
            p = subprocess.Popen(f'{commande}', shell=False, stdout=f)
            with open("encoding.json", "r") as f:
                try:
                    dic = json.load(f)
                except json.decoder.JSONDecodeError:
                    dic = {}
                dic[f"{p.pid}"] = path
                CURRENT_CONV[commande.split('"')[1]] = p
                f.close()
            with open("encoding.json", "w") as f:
                json.dump(dic, f, indent=5)

            ## bug 
            
        except FileNotFoundError:
            pass
        except KeyboardInterrupt:
            os.remove(commande.split('"')[3])
            os.remove(f"encoding/log/{filename}.txt")
    else: 
        pass



if __name__ == "__main__":
    CURRENT_CONV = {}
    CONVERTER_DIR = "server/upload"
    while True:
        for file in os.listdir(CONVERTER_DIR):
            print(prepare_encode(f"{CONVERTER_DIR}/{file}"))
            encode(prepare_encode(f"{CONVERTER_DIR}/{file}"))
        while CURRENT_CONV != {}:
            try:
                for file in CURRENT_CONV:
                    print("waiting")
                    CURRENT_CONV[file].wait()
                    print("finish")
                    CURRENT_CONV.pop(file)
                    print(file)
                    os.remove(file)
            except RuntimeError:
                pass
            except FileExistsError:
                pass
        
            