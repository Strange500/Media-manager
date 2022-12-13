import os,json,shutil,wmi


def alive()->json:
    
    return  json.dumps({"alive" : True},indent=4)

def space():
    list_disk,json_list= [f"{i}:\\" for i in [chr(k) for k in range(ord("A"),ord("Z")+1)]],{}
    for disk in list_disk:
        try:
            total, used, free = shutil.disk_usage(disk)
            json_list[disk]={"total" : total,"used" : used,"free" : free}
        except:
            pass

    return json.dumps(json_list,indent=5)

def restart():
    os.system("shutdown /r")
    return json.dumps({"status" : "ok"}, indent=5)


# def temp():
#     w_temp=wmi.WMI(namespace="root\\wmi")
#     print(w_temp.)


