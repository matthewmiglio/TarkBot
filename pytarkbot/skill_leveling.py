import pyautogui
import time
import numpy

from pytarkbot.client import screenshot, smooth_click
from pytarkbot.image_rec import check_for_location, find_references, pixel_is_equal



def skill_leveling_main():
    state=""
    while True:
        pass

def state_skill_leveling(logger):
    while True:
        logger.log("STATE=skill leveling")
        if get_to_main_menu(logger)=="restart": return "restart"
        time.sleep(1)
        if queue_into_shoreline(logger)=="restart": return "restart"
        time.sleep(1)
        
        
def wait_for_game_queue():
    waiting=True
    while waiting:
         time.sleep(1)
                


def get_to_main_menu(logger):
    logger.log("Getting to main menu.")
    on_main_menu=check_if_on_main_menu()
    loops=0
    while not(on_main_menu):
        pyautogui.click(55,980)
        time.sleep(2)
        if loops>15: return "restart"
        on_main_menu=check_if_on_main_menu()
    logger.log("Made it to main menu.")


def check_if_on_main_menu():
    iar=numpy.asarray(screenshot())
    pix_list=[
        iar[610][979],
        iar[605][294],
        iar[651][946]
    ]
    sentinel=[155,77,17]
    for pix in pix_list:
        if not(pixel_is_equal(pix,sentinel,tol=50)):return False
    return True


def queue_into_shoreline(logger):
    #click escape from tarkov
    logger.log("Clicking 'escape from tarkov' button")
    smooth_click(645,686)
    time.sleep(0.33)
    #click pmc
    logger.log("Clicking PMC")
    smooth_click(797,728)
    time.sleep(0.33)
    #click next
    logger.log("Getting to map selection page.")
    smooth_click(410,717)
    time.sleep(0.33)
    #click shoreline
    logger.log("Clicking shoreline")
    smooth_click(647,899)
    time.sleep(0.33)
    #click ready
    logger.log("Clicking ready button")
    smooth_click(851,946)
    time.sleep(5)
    if not(look_for_in_queue()):
        return "restart"
    

def look_for_in_queue():
    current_image = screenshot()
    reference_folder = "look_for_in_queue1"
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
