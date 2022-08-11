import json
import sys
from os import makedirs
from os.path import exists, expandvars, isdir, join

top_level = join(expandvars(f'%appdata%'), "py-TarkBot")
config_file = join(top_level, 'config.json')



def load_user_settings():
    try:
        return json.load(open(config_file, 'r'))
    except json.JSONDecodeError:
        print("User config file could not be loaded, is it misconfigured?")
        sys.exit()
    except OSError:
        print("Could not find config file, creating one now")
        create_config_file()
        return load_user_settings()


def create_config_file():
    if not isdir(top_level):
        makedirs(top_level)
    if not exists(config_file):
        with open(config_file, "w") as f:
            default_config = {
                #"launcher_path": ("Microsoft", "Windows", "Start Menu", "Programs", "Chrome Apps", "Twitter.lnk"), 
                "launcher_path": ("B:\BsgLauncher\BsgLauncher.exe"), # tarko launcher path
                "graphics_setting_path": join(expandvars(f"%appdata%"), "Battlestate", "Escape from Tarkov", "Settings", "Graphics.ini") #tark graphics settings file path 
                } 
            f.write(json.dumps(default_config, indent=4))
    print("Created config file for the bot @ appdata/py-TarkBot/")


