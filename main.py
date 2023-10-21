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

            fetched = False
            fetch_requets = False
            folder_sorted = False
            temp_checked = False
            ggd_scanned = False
            dl_done = False

            fetch_thr = threading.Thread(target=self.db.fetch_request)
            fetch = threading.Thread(target=self.db.fetch_missing_ep)
            sort = threading.Thread(target=self.db.check_sorter_folder)
            dl = threading.Thread(target=self.dl.run)

            second_old = 0
            minute_old = 0
            hour_old = 0
            log("Server Started")
            while True:

                while not is_connected():
                    time.sleep(2)
                second = datetime.now().strftime("%S")
                minute = int(datetime.now().strftime("%M")) 
                hour = datetime.now().strftime("%H")

                if int(datetime.now().strftime("%M")) % 1 == 0:

                    if not temp_checked:
                        log("Checking temp", debug=True)
                        if len(self.web_api.cpu_temp_list) > 120:
                            self.web_api.cpu_temp_list = []
                        Server.CPU_TEMP = get_temp()
                        self.web_api.cpu_temp_list.append(Server.CPU_TEMP)
                        self.web_api.update_cpu_avg()
                        temp_checked = True

                    if not folder_sorted and not sort.is_alive():
                        log("Sorting folders", debug=True)
                        sort = threading.Thread(target=self.db.check_sorter_folder())
                        sort.start()
                        folder_sorted = True

                    elif minute_old != minute:
                        temp_checked = False
                        folder_sorted = False
                    
                if minute % 5 == 0:
                    ...   
                if minute % 10 == 0:
                    if Server.conf["Downloader"] and not dl_done and not dl.is_alive():
                        log("Downloading", debug=True)
                        dl = threading.Thread(target=self.dl.run)
                        dl.start()
                        dl_done = True
                    elif minute_old != minute:
                        dl_done = False

                if minute % 15 == 0:
                    ...
                if minute % 30 == 0:
                    if not fetch_requets and not fetch_thr.is_alive():
                        log("fetching requested shows", debug=True)
                        fetch_thr = threading.Thread(target=self.db.fetch_request)
                        fetch_thr.start()
                        fetch_requets = True

                if hour == 11:
                    
                    if not fetched and not fetch.is_alive():
                        log("fetching missing episodes", debug=True)
                        fetch = threading.Thread(target=self.db.fetch_missing_ep)
                        fetch.start()
                        fetched = True
            
                
                if Server.conf["GGD"] and hour == 1:
                    if not ggd_scanned:
                        log("scanning GGD", debug=True)
                        ggd_scan = threading.Thread(target=self.GGD.run())
                        ggd_scan.start()
                        ggd_scanned = True

                second_old = second
                minute_old = minute
                hour_old = hour
                time.sleep(1)
        except KeyboardInterrupt:

            log("wait before closing saving data", warning=True)
            log("saving GGD_lib", warning=True)
            json.dump(Gg_drive.dict_ep, open(os.path.join(VAR_DIR, GGD_LIB), "w", encoding="utf-8"), indent=5)
            log("saving tmdb_title ...", warning=True)
            self.db.save_tmdb_title()
            log("saving tmdb_db ...", warning=True)
            json.dump(Server.tmdb_db, open(os.path.join(VAR_DIR, TMDB_DB), "w", encoding="utf-8"), indent=5)
            log("Saving feed storage ...", warning=True)
            json.dump(Feed.feed_storage, open(os.path.join(VAR_DIR, FEED_STORAGE), "w", encoding="utf-8"), indent=5)
            log("Shutting down", warning=True)
            quit()

def test():
    
    # ls_anime = ["86 Eighty-Six S01E02 CUSTOM MULTi 1080p 10bits BluRay x265 AAC -Punisher694.mkv",
    #             "KonoSuba.An.Explosion.on.This.Wonderful.World.S01E11.SUBFRENCH.1080p.WEB.x264.AAC-Tsundere-Raws.mkv",
    #             "Konosuba.An.Explosion.on.this.Wonderful.World.S01E11.SUBFRENCH.1080p.WEB.x264-T3KASHi.mkv",
    #             "Iseleve S01E11 VOSTFR WebRip 1080p x265 10bit AAC.mkv",
    #             "Dragons Rescue Riders.S01E02.MULTI.1080p.WEB.x264-FTMVHD.mkv",
    #             "[Raze] Kono Subarashii Sekai ni Bakuen wo! - 11 x265 10bit 1080p 143.8561fps.mkv",
    #             "[ASW] Kaminaki Sekai no Kamisama Katsudou - 10 [1080p HEVC][504C7F1D].mkv",
    #             "[Trix] Vinland Saga - S02E23 - (1080p AV1 E-AC3)[Multi Subs].mkv",
    #             "[Judas] Vinland Saga - S02E23.mkv",
    #             "[Judas] Rougo ni Sonaete Isekai de 8-manmai no Kinka o Tamemasu - S01E01v2.mkv",
    #             "Saving 80,000 Gold in Another World for my Retirement - S01E12 (1080p CR WEB-DL -KS-).mkv"
    #             "Butareba -The Story of a Man Who Turned into a Pig- S01E02 VOSTFR 1080p WEB x264 AAC -Tsundere-Raws (CR) (Buta no Liver wa Kanetsu Shiro).mkv"
    #             "The iDOLMASTER Million Live! S01E02 VOSTFR 1080p WEB x264 AAC -Tsundere-Raws (CR).mkv",
    #             "Bocchi the Rock! S01 VOSTFR 1080p BluRay x265 FLAC -Tsundere-Raws.mkv"]
    ls_anime = []
    ls_anime = [*ls_anime, *[remove_non_ascii(i.strip()) for i in open("/home/strange/install/shared/media/list_filename")]]
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

def test_bis():
    from pprint import pprint
    pprint(delete_empty_dictionnaries({"prout" : {},
                                      "bonjour": {"bibn": "prout"}}))
def main():
    import time

    server = deployServ()
    server.start()


if __name__ == "__main__":
    main()
    # st = time.process_time()


    # test()

    # et = time.process_time()

    # print("execution time : " + str(et - st) + "seconds" )


    #test_bis()