


import time
#vars
from http.client import PROXY_AUTHENTICATION_REQUIRED
from ntpath import join
from posixpath import expandvars

import numpy
import pyautogui
from matplotlib import pyplot as plt

from logger import Logger
from pytarkbot.client import check_quit_key_press, orientate_client
from pytarkbot.hideout import find_start_symbol_in_booze_generator, get_to_booze_generator, get_to_hideout, get_to_intelligence_center, get_to_lavatory, get_to_medstation, get_to_nutrition_unit, get_to_scav_case,  get_to_water_collector, get_to_workbench

logger=Logger()

# user_settings = load_user_settings()
# launcher_path = user_settings["launcher_path"]
# tarkov_graphics_settings_path = user_settings["graphics_setting_path"]
# saved_user_settings_path = join(expandvars(f"%appdata%"),".\config","user_default_config","Graphics.ini") 
# preset_graphics_for_bot_path = join(expandvars(f"%appdata%"),".\config","config_for_bot","Graphics.ini") 




orientate_client("EscapeFromTarkov",[1280,960])
time.sleep(1)


# plt.imshow(numpy.asarray(screenshot()))
# plt.show()




# while True:
#     check_quit_key_press()
#     print(look_for_lavatory_symbol())

coords=find_start_symbol_in_booze_generator()
pyautogui.moveTo(coords[0],coords[1])