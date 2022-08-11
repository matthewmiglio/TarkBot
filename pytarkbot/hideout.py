import time

import numpy
import pyautogui

from pytarkbot.client import check_quit_key_press, click, screenshot
from pytarkbot.image_rec import check_for_location, find_references, get_first_location, pixel_is_equal


#navigation
def get_to_hideout(logger):
    logger.log("Getting to hideout")
    at_hideout=check_if_in_hideout()
    while not(at_hideout):
        click(143,979)
        pyautogui.moveTo(99,99,duration=0.33)
        time.sleep(3.33)
        at_hideout=check_if_in_hideout()
    logger.log("At hideout.")
    time.sleep(0.33)
    logger.log("Opening hideout interface at bottom of screen.")
    open_hideout_interface()
    
def open_hideout_interface():
    pyautogui.click(800,934)

def scroll_left_in_hideout():
    pyautogui.click(38,934)

def scroll_right_in_hideout():
    pyautogui.click(1255,934)
    

    
##checks and looks

#general hideout
def check_if_in_hideout():
    iar=numpy.asarray(screenshot())
    pix1=iar[986][114]
    pix2=iar[980][180]
    
    color_true=[159,157,144]
    color_false=[15,14,14]
    
    if not(pixel_is_equal(pix1,color_true,tol=25)):
        return False
    if not(pixel_is_equal(pix2,color_true,tol=25)):
        return False
    if pixel_is_equal(pix1,color_false,tol=25):
        return False
    if pixel_is_equal(pix2,color_false,tol=25):
        return False
    return True


#checking if currently at the right station
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

#checking the state of stations
def check_booze_generator():
    pass



#move to each station
def get_to_water_collector(logger):
    open_hideout_interface()
    
    at_location=check_if_at_water_collector()
    while not(at_location):
        scroll_left_in_hideout()
        time.sleep(2)
        at_location=check_if_at_water_collector()
    logger.log("Made it to water collector.")

def get_to_lavatory(logger):
    open_hideout_interface()
    
    at_location=check_if_at_lavatory()
    while not(at_location):
        scroll_left_in_hideout()
        time.sleep(2)
        at_location=check_if_at_lavatory()
    logger.log("Made it to lavatory")

def get_to_booze_generator(logger):
    open_hideout_interface()
    
    at_location=check_if_at_booze_generator()
    while not(at_location):
        scroll_left_in_hideout()
        time.sleep(2)
        at_location=check_if_at_booze_generator()
    logger.log("Made it to booze_generator.")

def get_to_nutrition_unit(logger):
    open_hideout_interface()
    
    at_location=check_if_at_nutrition_unit()
    while not(at_location):
        scroll_left_in_hideout()
        time.sleep(2)
        at_location=check_if_at_nutrition_unit()
    logger.log("Made it to nutrition_unit")

def get_to_workbench(logger):
    open_hideout_interface()
    
    at_location=check_if_at_workbench()
    while not(at_location):
        scroll_left_in_hideout()
        time.sleep(2)
        at_location=check_if_at_workbench()
    logger.log("Made it to workbench")

def get_to_intelligence_center(logger):
    open_hideout_interface()
    
    at_location=check_if_at_intelligence_center()
    while not(at_location):
        scroll_left_in_hideout()
        time.sleep(2)
        at_location=check_if_at_intelligence_center()
    logger.log("Made it to intelligence_center")

def get_to_medstation(logger):
    open_hideout_interface()
    
    at_location=check_if_at_medstation()
    while not(at_location):
        scroll_left_in_hideout()
        time.sleep(2)
        at_location=check_if_at_medstation()
    logger.log("Made it to medstation")

def get_to_scav_case(logger):
    open_hideout_interface()
    
    at_location=check_if_at_scav_case()
    while not(at_location):
        scroll_left_in_hideout()
        time.sleep(2)
        at_location=check_if_at_scav_case()
    logger.log("Made it to scav_case.")


#aux definitions
def find_start_symbol_in_booze_generator():
    current_image = screenshot()
    reference_folder = "booze_generator_start_icon"
    references = [
        "1.png",
        "2.png",
        "3.png",
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )
    return get_first_location(locations)





