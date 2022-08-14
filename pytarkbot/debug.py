


import time
#vars
from http.client import PROXY_AUTHENTICATION_REQUIRED
from ntpath import join
from posixpath import expandvars

from unittest.mock import NonCallableMagicMock

import numpy
import PySimpleGUI as sg
import pyautogui
from matplotlib import pyplot as plt

from logger import Logger
from pytarkbot.__main__ import show_donate_gui, state_intro
from pytarkbot.client import check_quit_key_press, click, find_all_pixel_coords, img_to_txt, orientate_client, screenshot
from pytarkbot.hideout import add_filter_to_water_collector, check_booze_generator, check_for_water_collector_collect_icon, check_for_workbench_producing_icon, check_if_at_booze_generator, check_if_water_collector_has_filter, check_state_of_medstation, check_water_collector, check_workbench, find_add_filter_dropdown_arrow_in_water_collector, find_green_gunpowerder_icon_in_workbench, find_start_symbol_in_booze_generator, find_water_filter_in_dropdown_in_water_collector, get_image_of_green_gunpowder_surroundings, get_to_booze_generator, get_to_green_gunpowder_craft, get_to_hideout, get_to_intelligence_center, get_to_lavatory, get_to_medstation, get_to_nutrition_unit, get_to_scav_case,  get_to_water_collector, get_to_workbench, manage_booze_generator, manage_medstation, manage_scav_case, manage_water_collector, manage_workbench, reset_station, start_green_gunpowder_craft_in_workbench
from pytarkbot.image_rec import check_for_location, find_references, get_first_location, pixel_is_equal

logger=Logger()

# user_settings = load_user_settings()
# launcher_path = user_settings["launcher_path"]
# tarkov_graphics_settings_path = user_settings["graphics_setting_path"]
# saved_user_settings_path = join(expandvars(f"%appdata%"),".\config","user_default_config","Graphics.ini") 
# preset_graphics_for_bot_path = join(expandvars(f"%appdata%"),".\config","config_for_bot","Graphics.ini") 




# orientate_client("EscapeFromTarkov",[1280,960])
# time.sleep(1)

# plt.imshow(numpy.asarray(screenshot()))
# plt.show()

show_donate_gui()