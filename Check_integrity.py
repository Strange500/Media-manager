from random import randint
from file_analyse_lib import *
from file_analyse_lib import sources
from pprint import pprint
import time

banned_words, select_words = open("banned_words.txt", "r", encoding="utf-8").read().split("\n"), open(
    "select_words.txt", "r", encoding="utf-8").read().split("\n")


def main():
    json.dump(list_anime(), open("anime_lib.json", "w"), indent=4)
    database_check()
    download_missing_ep(json.load(open("missing.json", "r")))


if __name__ == "__main__":
    main()
