import os,time,subprocess
from file_analyse_lib import *


def main():
    print(f"[{time_log()}] MAIN: SERVER STARTED")
    subprocess.run("start python API.py",shell=True)
    print(f"[{time_log()}] MAIN: API STARTED")
    minute=time.time()//60
    date=datetime.datetime.now()
    h=date.strftime("%H")
    
    print(f"[{time_log()}] MAIN: WAITING FOR EVENTS")
    while True:
        if minute!=time.time()//60:
            minute=time.time()//60
            subprocess.Popen("python downloader.py",shell=True)
            for dir in download_dir:
                if os.listdir(dir)!=[]:
                    subprocess.Popen("python sorter.py")
        if date.strftime('%H')=="04":
            t = subprocess.Popen("python check_integrity.py")
            t.wait()
            t = subprocess.Popen("python fakedatabase.py")
            t.wait()
            t = subprocess.Popen("python theme.py")
            t.wait()
            os.system("shutdown /r")
            break
        
            








if __name__=='__main__':
    main()