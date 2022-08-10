from client import click, screenshot
import pyautogui
import time
import numpy

from image_rec import pixel_is_equal

def get_to_hideout(logger):
    logger.log("Getting to hideout")
    at_hideout=check_if_in_hideout()
    while not(at_hideout):
        click(143,979)
        pyautogui.moveTo(99,99,duration=0.33)
        time.sleep(3.33)
        at_hideout=check_if_in_hideout()
    logger.log("At hideout.")
    

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












