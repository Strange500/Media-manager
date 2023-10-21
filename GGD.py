from Database import *


class Gg_drive():
    dict_ep = json.load(open(os.path.join(VAR_DIR, GGD_LIB), "r", encoding="utf-8"))

    def __init__(self):
        self.d_dirs = Server.conf["GGD_dir"]

    def update_dict_ep(self):
        # add list all file and update Server.TASK_GGD_SCAN so we can track evolution
        Server.TASK_GGD_SCAN = 0
        list_files = []
        if type(self.d_dirs) == str:
            list_files = list_all_files(self.d_dirs)
        else:
            for dir in self.d_dirs:
                list_files += list_all_files(dir)
        total_file = len(list_files)
        compteur_file = 0
        dictionary_episode = {}
        for episode_path in list_files:
            if is_video(episode_path):
                try:
                    try:
                        ep_info = SorterShows(episode_path)
                    except subprocess.CalledProcessError as e:
                        try:
                            ep_info = SorterShows(episode_path)
                        except subprocess.CalledProcessError:
                            continue
                        except UnicodeError:
                            continue
                        except ValueError as e:
                            continue
                    except ValueError as e:
                        continue
                    id = str(ep_info.id)
                    season = str(ep_info.season)
                    ep = str(ep_info.ep)
                    if Gg_drive.dict_ep.get(id, None) is None:
                        Gg_drive.dict_ep[id] = {}
                    if Gg_drive.dict_ep[id].get(season, None) is None:
                        Gg_drive.dict_ep[id][season] = {}
                    if Gg_drive.dict_ep[id][season].get(ep, None) is None:
                        Gg_drive.dict_ep[id][season][ep] = {}

                    Gg_drive.dict_ep[id][season][ep][ep_info.path] = {
                        "original_filename": ep_info.file_name,
                        "renamed": ep_info.__str__(),
                        "language": ep_info.lang,
                        "list_subs_language": ep_info.list_subs_lang,
                        "list_audio_language": ep_info.list_audio_lang,
                        "title": ep_info.title,
                        "height": ep_info.resolution,
                        "codec": ep_info.codec,
                    }
                except AttributeError as e:
                    pass
            compteur_file += 1
            Server.TASK_GGD_SCAN = round((compteur_file / total_file) * 100, 2)
            json.dump(Gg_drive.dict_ep, open(os.path.join(VAR_DIR, GGD_LIB), "w", encoding="utf-8"), indent=5)
        json.dump(Gg_drive.dict_ep, open(os.path.join(VAR_DIR, GGD_LIB), "w", encoding="utf-8"), indent=5)
        return dictionary_episode

    def run(self):
        try:
            self.update_dict_ep()
            log("GGD drive(s) updated")
        except KeyboardInterrupt:
            json.dump(Gg_drive.dict_ep, open(os.path.join(VAR_DIR, GGD_LIB), "w", encoding="utf-8"), indent=5)
            json.dump(Server.tmdb_db, open(os.path.join(VAR_DIR, TMDB_DB), "w", encoding="utf-8"), indent=5)

if __name__ == '__main__':
    d = Gg_drive()
    d.run()