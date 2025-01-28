# pivideo_manager
Raspberry video player manager
To use alongside with
https://github.com/carlitoselmago/raspberry-sync

Can control via web GUI status of players like cpu temperature, raspberry model, RAM, available storage space or lag to main player

You can control remotely via vpn a video installation from home (vpn settings not included)  

# Usage


```
sudo python GUI.py
```

and access via http://localhost:5000/pimanager


To deploy as production:
```
gunicorn --workers 4 --bind 0.0.0.0:5000 GUI:app
```
