from file_analyse_lib import *


def main():
    banned_words, select_words = open("banned_words.txt", "r", encoding="utf-8").read().split("\n"), open(
        "select_words.txt", "r", encoding="utf-8").read().split("\n")
    for url in open("rss.txt", "r", encoding="utf-8").read().split("\n"):
        feed = FeedAnime(url, banned_words, select_words)

        for episode in feed.ep:
            try:
                file_name = LightFile(episode).__str__()
            except:
                pass
            if file_name in open("already_download.txt", "r", encoding="utf-8").read().split("\n"):
                pass

            elif already_in_folder(file_name) not in [[], None]:
                open("already_download.txt", "a", encoding="utf-8").write(f'{file_name}\n')
            else:
                open("already_download.txt", "a", encoding="utf-8").write(f'{file_name}\n')
                r = requests.request("GET", feed.ep[episode])
                open(f"torrent/{forbiden_car(episode)}.torrent", "wb").write(r.content)
                print(f"{episode} downloaded")
                log(f"[{time_log()}] DOWNLOADER: {episode} ADDED")


if __name__ == "__main__":
    main()
