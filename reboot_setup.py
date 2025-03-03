import sys
from pivideo_manager import PiVideoManager

try:
    setupname = sys.argv[1]
except:
    print("No setupname argument detected")
    sys.exit()

print("Rebooting setup with name: ",setupname)
manager = PiVideoManager()
manager.reboot_setup(setupname)