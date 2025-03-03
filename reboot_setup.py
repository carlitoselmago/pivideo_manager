import sys
from pivideo_manager import PiVideoManager

try:
    setupname = sys.argv[1]
except:
    print("No setupname argument detected")
    sys.exit()

manager = PiVideoManager()
manager.reboot_setup(setupname)