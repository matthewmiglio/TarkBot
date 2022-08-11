from client import click, screenshot
import pyautogui
import time
import numpy

from image_rec import pixel_is_equal
from image_rec import find_references, get_first_location

#movement
def get_to_hideout(logger):
    logger.log("Getting to hideout")
    at_hideout=check_if_in_hideout()
    while not(at_hideout):
        click(143,979)
        pyautogui.moveTo(99,99,duration=0.33)
        time.sleep(3.33)
        at_hideout=check_if_in_hideout()
    logger.log("At hideout.")
    pyautogui.keyDown('a')
    logger.log("Moving to the left side of hideout to help image recognition.")
    pyautogui.keyUp('a')
    
def open_hideout_interface():
    pyautogui.click(800,934)

def scroll_left_in_hideout():
    pyautogui.click(38,934)

def scroll_right_in_hideout():
    pyautogui.click(1255,934)
    

    
#checks and looks

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



def look_for_booze_generator_symbol():
    current_image = screenshot()
    reference_folder = "look_for_booze_generator_symbol"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "4.png",
        
        
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )

    coords= get_first_location(locations)
    if coords is None:
        return None
    return [coords[1],coords[0]]

def look_for_water_collector_symbol():
    current_image = screenshot()
    reference_folder = "look_for_water_collector_symbol"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "4.png",
        
        
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )

    coords= get_first_location(locations)
    if coords is None:
        return None
    return [coords[1],coords[0]]

def look_for_lavatory_symbol():
    current_image = screenshot()
    reference_folder = "look_for_lavatory_symbol"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "4.png",
        
        
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )

    coords= get_first_location(locations)
    if coords is None:
        return None
    return [coords[1],coords[0]]

def look_for_nutrition_unit_symbol():
    current_image = screenshot()
    reference_folder = "look_for_nutrition_unit_symbol"
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

    coords= get_first_location(locations)
    if coords is None:
        return None
    return [coords[1],coords[0]]

def look_for_workbench_symbol():
    current_image = screenshot()
    reference_folder = "look_for_workbench_symbol"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "4.png",
        
        
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )

    coords= get_first_location(locations)
    if coords is None:
        return None
    return [coords[1],coords[0]]

def look_for_intelligence_center_symbol():
    current_image = screenshot()
    reference_folder = "look_for_intelligence_center_symbol"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "4.png",
        
        
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )

    coords= get_first_location(locations)
    if coords is None:
        return None
    return [coords[1],coords[0]]

def look_for_medstation_symbol():
    current_image = screenshot()
    reference_folder = "look_for_medstation_symbol"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "4.png",
        
        
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )

    coords= get_first_location(locations)
    if coords is None:
        return None
    return [coords[1],coords[0]]

def look_for_scav_case_symbol():
    current_image = screenshot()
    reference_folder = "look_for_scav_case_symbol"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "4.png",
        
        
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )

    coords= get_first_location(locations)
    if coords is None:
        return None
    return [coords[1],coords[0]]





#expanded movement

def get_to_water_collector():
    pass

def get_to_lavatory():
    pass

def get_to_nutrition_unit():
    pass

def get_to_workbench():
    pass

def get_to_intelligence_center():
    pass

def get_to_booze_generator():
    pass

def get_to_medstation():
    pass

def get_to_scav_case():
    pass












