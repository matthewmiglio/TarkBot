


#vars
from http.client import PROXY_AUTHENTICATION_REQUIRED
from logger import Logger
from ntpath import join
from posixpath import expandvars

from configuration import load_user_settings
from client import orientate_client, screenshot
import time
import numpy
import pyautogui
from matplotlib import pyplot as plt

from hideout import get_to_booze_generator, get_to_hideout
from image_rec import find_references, get_first_location
from image_rec import check_for_location

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

def check_if_at_booze_generator():
    current_image = screenshot()
    reference_folder = "check_if_at_booze_generator"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png", 
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )

    return check_for_location(locations)

def check_if_at_water_collector():
    current_image = screenshot()
    reference_folder = "check_if_at_water_collector"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png", 
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )
    return check_for_location(locations)

def check_if_at_lavatory():
    current_image = screenshot()
    reference_folder = "check_if_at_lavatory"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png", 
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )
    return check_for_location(locations)

def check_if_at_nutrition_unit():
    current_image = screenshot()
    reference_folder = "check_if_at_nutrition_unit"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png", 
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )
    return check_for_location(locations)

def check_if_at_workbench():
    current_image = screenshot()
    reference_folder = "check_if_at_workbench"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png", 
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )
    return check_for_location(locations)

def check_if_at_intelligence_center():
    current_image = screenshot()
    reference_folder = "check_if_at_intelligence_center"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png", 
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )
    return check_for_location(locations)

def check_if_at_medstation():
    current_image = screenshot()
    reference_folder = "check_if_at_medstation"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png", 
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )
    return check_for_location(locations)

def check_if_at_scav_case():
    current_image = screenshot()
    reference_folder = "check_if_at_scav_case"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png", 
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )
    return check_for_location(locations)


for n in range(1,4):
    t=check_if_at_booze_generator()
    print(t)
    time.sleep(0.33)