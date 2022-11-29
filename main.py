import os,time,subprocess
from datetime import datetime
from file_analyse_lib import *


def main():
    minute=time.time()//60
    h=datetime.now().strftime('%H')
    while True:
        if minute!=time.time()//60:
            minute=time.time()//60
            subprocess.Popen("python downloader.py",shell=True)
            for dir in download_dir:
                if os.listdir(dir)!=[]:
                    subprocess.Popen("python sorter.py")
        if datetime.now().strftime('%H')=="04":
            os.system("shutdown /r")
        if datetime.now().strftime('%H')=="20" and datetime.now().strftime('%H')!=h:
            h=datetime.now().strftime('%H')
            subprocess.Popen("python check_integrity.py")
            break





if __name__=='__main__':
    print("SERVER STARTING...")
    main()