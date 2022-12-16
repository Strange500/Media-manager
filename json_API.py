import os,json,shutil,wmi,urllib.parse
import psutil


user_list = ["admin","Lester","La mom","Apo","Antoine","DrazZ"]

def alive()->json:
    
    return  json.dumps({"alive" : True},indent=4)

def space():
    list_disk,json_list= [f"{i}:\\" for i in [chr(k) for k in range(ord("A"),ord("Z")+1)]],{}
    for disk in list_disk:
        if disk == "G:\\":
            pass
        else:
            try:
                total, used, free = shutil.disk_usage(disk)
                json_list[disk]={"total" : total,"used" : used,"free" : free}
            except:
                pass

    return json.dumps(json_list,indent=5)

def restart():
    os.system("shutdown /r")
    return json.dumps({"status" : "ok"}, indent=5)


def is_user(req:str):
    req=urllib.parse.unquote(req)
    user= req.split("/")[-1].split("u=")[-1]
    if user in user_list:
        return json.dumps({"is_user" : True})
    else:
        return json.dumps({"is_user" : False})

def cpu_temp():
    w = wmi.WMI(namespace="root\OpenHardwareMonitor")
    temperature_infos = w.Sensor()
    for sensor in temperature_infos:
        
        if sensor.SensorType==u'Temperature' and sensor.name == "CPU Package":
            return json.dumps({"value" : sensor.value})

def serv_log():
    with open("log.txt","r") as f:
        n,dic=0,{}
        for line in f:
            dic[n] = line.replace("\n","")
            n+=1
    return json.dumps(dic,indent=5)






