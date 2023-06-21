import feedparser

from Database import *


class Feed(DataBase):


    def __init__(self):
        super().__init__()
        self.feed_dict = self.get_feed()

    def get_feed(self) -> dict:
        rss_feeds = {"anime_feeds": [], "movie_feeds": [], "show_feeds": []}
        with open(os.path.join(VAR_DIR, RSS_ANIME), "r", encoding="utf-8") as f:
            for lines in f:
                if not lines[0] in ["#", '', "\n"]:
                    rss_feeds["anime_feeds"].append(lines.replace("\n", "").strip())
        with open(os.path.join(VAR_DIR, RSS_MOVIE), "r", encoding="utf-8") as f:
            for lines in f:
                if not lines[0] in ["#", '', "\n"]:
                    rss_feeds["movie_feeds"].append(lines.replace("\n", "").strip())
        with open(os.path.join(VAR_DIR, RSS_SHOW), "r", encoding="utf-8") as f:
            for lines in f:
                if not lines[0] in ["#", '', "\n"]:
                    rss_feeds["show_feeds"].append(lines.replace("\n", "").strip())
        return rss_feeds

    def get_ep_with_link(self, feed: feedparser.FeedParserDict, feed_title: str) -> dict:
        if not isinstance(feed, feedparser.FeedParserDict):
            raise ValueError(f"feed should be feedparser.FeedParserDict not {type(feed)}")
        dicto = {}
        for entry in feed.entries:
            is_selected = False
            for words in Server.conf["select_words_rss"]:
                if words in entry.title:
                    is_selected = True
                    if "yggtorrent" in feed_title:
                        dicto[entry.title] = entry.enclosures[0].get("url")
                    else:
                        dicto[entry.title] = entry.link
                    break
            is_ban = False
            for words in Server.conf["banned_words_rss"]:
                if is_selected:
                    break
                if words in entry.title:
                    is_ban = True
                    break
            if not is_ban:
                if "yggtorrent" in feed_title:
                    dicto[entry.title] = entry.enclosures[0].get("url")
                else:
                    dicto[entry.title] = entry.link

        return dicto

    def sort_feed(self) -> dict:
        dic = {}
        ls = []
        for feed_list in self.feed_dict:

            for feed in self.feed_dict[feed_list]:
                ls = []
                feed_link = feed
                time.sleep(2)  # avoid ban IP
                r = {}
                r.clear()
                feed = feedparser.parse(feed)
                dic = self.get_ep_with_link(feed, feed_link)
                for ep in dic:
                    title = ep
                    link = dic[ep]
                    if os.path.splitext(title)[1] == '':
                        ep += ".mkv"
                    if not "movie" in feed_list:
                        try:
                            if "anime" in feed_list:
                                ep = SorterShows(ep, file_reachable=False, is_anime=True)
                            elif "show" in feed_list:
                                ep = SorterShows(ep, file_reachable=False)
                            if Server.feed_storage.get(str(ep.id), None) is None:
                                Server.feed_storage[str(ep.id)] = {}
                            if Server.feed_storage[str(ep.id)].get(ep.season, None) is None:
                                Server.feed_storage[str(ep.id)][ep.season] = {}
                            Server.feed_storage[str(ep.id)][ep.season][ep.ep] = {
                                "torrent_title": title,
                                "link": link,
                                "origin_feed": feed_link
                            }
                        except AttributeError as e:
                            log(f"can't determine the show {ep}", error=True)
                            continue
                        except ValueError as e:
                            log(e, warning=True)
                            continue
                        if "anime" in feed_list:
                            if not self.have_ep(ep, anime=True):
                                try:
                                    r[f"{ep.title} - S{ep.season}E{ep.ep} {ep.ext}"] = link
                                except AttributeError:
                                    ...
                                except requests.exceptions.ReadTimeout:
                                    pass
                        elif "show" in feed_list:
                            if not self.have_ep(ep, shows=True):
                                try:
                                    r[f"{ep.title} - S{ep.season}E{ep.ep} {ep.ext}"] = link
                                except AttributeError:
                                    ...
                                except requests.exceptions.ReadTimeout:
                                    print("timeout")
                                    pass
                    else:
                        try:
                            mv = SorterMovie(ep, file_reachable=False)
                        except AttributeError:
                            ...
                        except requests.exceptions.ReadTimeout:
                            print("timeout")
                            pass
                        Server.feed_storage[str(mv.id)] = {
                            "torrent_title": title,
                            "link": link,
                            "origin_feed": feed_link
                        }
                        if not self.have_ep(ep, movie=True):
                            r[f"{mv.title} - {mv.ext}"] = link
                ls.append(r)
            dic.clear()
            self.feed_dict[feed_list] = ls

    def dl_torrent(self):
        for list_feed in self.feed_dict:
            for feed in self.feed_dict[list_feed]:
                if "anime" in list_feed:
                    torrent_dir = os.path.join(Server.conf['torrent_dir'], "anime")
                elif "show" in list_feed:
                    torrent_dir = os.path.join(Server.conf['torrent_dir'], "show")
                elif "movie" in list_feed:
                    torrent_dir = os.path.join(Server.conf['torrent_dir'], "movie")
                else:
                    raise ValueError
                os.makedirs(torrent_dir, exist_ok=True)
                for key in feed:
                    file_name = forbidden_car(f"{key}.torrent")
                    if file_name not in os.listdir(torrent_dir):
                        try:
                            torrent = requests.request("GET", feed[key])
                            open(os.path.join(torrent_dir, file_name), "wb").write(
                                torrent.content)
                        except requests.exceptions.ConnectTimeout:
                            log(f"connection to {feed[key]} tomeout", warning=True)
                            pass
                        time.sleep(1)  # avoid ban ip

    def run(self):
        while True:
            self.sort_feed()
            self.dl_torrent()
            time.sleep(600)
