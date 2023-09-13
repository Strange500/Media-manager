import threading

from API import *
from Downloader import *
from GGD import *
from datetime import datetime


class deployServ():

    def __init__(self):
        self.db = DataBase()
        self.web_api = web_API(self.db)
        self.GGD = Gg_drive()
        self.dl = Feed()

    def start(self):
        try:
            api = threading.Thread(target=self.web_api.run)
            api.start()

            db = threading.Thread(target=self.db.serve_forever)
            db.start()
            if Server.conf["GGD"]:
                GGD = threading.Thread(target=self.GGD.run)
                GGD.start()
            if Server.conf["Downloader"]:
                dl = threading.Thread(target=self.dl.run)
                dl.start()

            fetch = None
            while True:
                if datetime.now().strftime("%H") == "11" and fetch is None:
                    fetch = threading.Thread(target=self.db.fetch_missing_ep)
                    fetch.start()
                if len(self.web_api.cpu_temp_list) > 120:
                    self.web_api.cpu_temp_list = []
                Server.CPU_TEMP = get_temp()
                self.web_api.cpu_temp_list.append(Server.CPU_TEMP)
                self.web_api.update_cpu_avg()
                self.db.fetch_requested_shows(anime=True)
                self.db.fetch_requested_shows(show=True)
                time.sleep(30)
        except KeyboardInterrupt:

            print("wait before closing saving data")
            print("saving GGD_lib")
            json.dump(Gg_drive.dict_ep, open(os.path.join(VAR_DIR, GGD_LIB), "w", encoding="utf-8"), indent=5)
            print("saving tmdb_title ...")
            self.db.save_tmdb_title()
            print("saving tmdb_db ...")
            json.dump(Server.tmdb_db, open(os.path.join(VAR_DIR, TMDB_DB), "w", encoding="utf-8"), indent=5)
            print("Saving feed storage ...")
            json.dump(Feed.feed_storage, open(os.path.join(VAR_DIR, FEED_STORAGE), "w", encoding="utf-8"), indent=5)
            print("Shutting down")
            quit()

def test():
    from pprint import pprint
    ls_anime = ["86 Eighty-Six S01E02 CUSTOM MULTi 1080p 10bits BluRay x265 AAC -Punisher694.mkv",
                "KonoSuba.An.Explosion.on.This.Wonderful.World.S01E11.SUBFRENCH.1080p.WEB.x264.AAC-Tsundere-Raws.mkv",
                "Konosuba.An.Explosion.on.this.Wonderful.World.S01E11.SUBFRENCH.1080p.WEB.x264-T3KASHi.mkv",
                "Iseleve S01E11 VOSTFR WebRip 1080p x265 10bit AAC.mkv",
                "Dragons Rescue Riders.S01E02.MULTI.1080p.WEB.x264-FTMVHD.mkv",
                "[Raze] Kono Subarashii Sekai ni Bakuen wo! - 11 x265 10bit 1080p 143.8561fps.mkv",
                "[ASW] Kaminaki Sekai no Kamisama Katsudou - 10 [1080p HEVC][504C7F1D].mkv",
                "[Trix] Vinland Saga - S02E23 - (1080p AV1 E-AC3)[Multi Subs].mkv",
                "[Judas] Vinland Saga - S02E23.mkv",
                "[Judas] Rougo ni Sonaete Isekai de 8-manmai no Kinka o Tamemasu - S01E01v2.mkv",
                "Saving 80,000 Gold in Another World for my Retirement - S01E12 (1080p CR WEB-DL -KS-).mkv"]
    ls_show = ["law.and.order.svu.s23e10.french.720p.hdtv.x264-obstacle.mkv",
               "Les Feux De L'amour The Young and The Restless S48E0113.mp4",
               "The.Full.Monty.The.Serie.S01E08.FiNAL.MULTi.HDR.2160p.DSNP.WEB-DL.DDP5.1.H.265-FCK.mkv",
               "Youre.the.Worst.S03E01.MULTi.1080p.WEB.H264-FW.mkv",
               "Greys.Anatomy.S19E16.MULTi.1080p.AMZN.WEB-DL.DDP5.1.H.264-FCK.mkv",
               'Une mauvaise mère __S01E12_2023.VOSTFR.WEB-DL.1080.h264.eac3.kimiko.mkv']

    for file in ls_anime:
        print(SorterShows(file, file_reachable=False, is_anime=True))
    print("###################")
    for file in ls_show:
        print(SorterShows(file, file_reachable=False, is_anime=False))
    db = DataBase()
    pprint(db.list_missing_episodes())
def main():
    server = deployServ()
    server.start()


if __name__ == "__main__":
    main()
    #test()
