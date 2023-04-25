import subprocess, platform

from file_analyse_lib import *

if platform.system() == "Windows" :
    PYTHON = "python"
    NTERM = "start"
    REBOOT = "shutdown /r"
elif platform.system() == "Linux" :
    PYTHON = "/bin/python3"
    NTERM = "gnome-terminal --"
    REBOOT = "reboot"

def main():







    print(f"[{time_log()}] MAIN: SERVER STARTED")
    subprocess.Popen(f"{PYTHON} API.py", shell=True)
    print(f"[{time_log()}] MAIN: API STARTED")
    minute = time.time() // 60
    date = datetime.datetime.now()
    h = date.strftime("%H")

    print(f"[{time_log()}] MAIN: WAITING FOR EVENTS")
    while True:
        date = datetime.datetime.now()

        if minute != time.time() // 60:
            minute = time.time() // 60
            subprocess.Popen(f"{PYTHON} downloader.py", shell=True)
            for dir in download_dir:
                if os.listdir(dir) != []:
                    subprocess.Popen(f"{PYTHON} sorter.py")
        if date.strftime('%H') == "16":
            t = subprocess.Popen(f"'{PYTHON}' '{os.path.join(install_dir,'check_integrity.py')}'", shell=True)
            t.wait()
            t = subprocess.Popen(f"'{PYTHON}' '{os.path.join(install_dir,'fakedatabase.py')}'")
            t.wait()
            t = subprocess.Popen(f"'{PYTHON}' '{os.path.join(install_dir,'theme.py')}'")
            t.wait()
            os.system(REBOOT)
            break


if __name__ == '__main__':
    print(f'gnome-terminal -- python3 {os.path.join(install_dir, "api.py")}')
    #subprocess.run(f'gnome-terminal -- /bin/python3 "{os.path.join(install_dir, "api.py")}"', shell=True)
    main()

