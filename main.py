from Downloader import *
from API import *
from GGD import *


import threading

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

            while True:
                if len(self.web_api.cpu_temp_list) > 120:
                    self.web_api.cpu_temp_list = []
                self.web_api.update_cpu_temp()
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


def main():

    server = deployServ()
    server.start()

if __name__ == "__main__":
    main()
