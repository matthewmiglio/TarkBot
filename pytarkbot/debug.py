from ntpath import join
from posixpath import expandvars
import time


from matplotlib import pyplot as plt
from client import img_to_txt, orientate_client, screenshot
from configuration import load_user_settings
from graphics_config import set_tarkov_settings_to_bot_config, set_tarkov_settings_to_default_config

from image_filtering import  look_for_ruble_symbol
from image_rec import check_for_location, find_references, get_first_location, pixel_is_equal

from logger import Logger





logger=Logger()
user_settings = load_user_settings()
launcher_path = user_settings["launcher_path"]

tarkov_graphics_settings_path = user_settings["graphics_setting_path"]
saved_user_settings_path = join(expandvars(f"%appdata%"),".\config","user_default_config","Graphics.ini") 
preset_graphics_for_bot_path = join(expandvars(f"%appdata%"),".\config","config_for_bot","Graphics.ini") 


print(saved_user_settings_path)

# orientate_client("EscapeFromTarkov",[1280,960])
# time.sleep(1)


# plt.imshow(numpy.asarray(screenshot()))
# plt.show()


set_tarkov_settings_to_bot_config(logger,src=preset_graphics_for_bot_path,dst=tarkov_graphics_settings_path)

# set_tarkov_settings_to_default_config(logger,src=saved_user_settings_path,dst=tarkov_graphics_settings_path)