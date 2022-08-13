


import time
import keyboard
from os.path import join

import pyautogui
from pytarkbot.client import exit_printout, intro_printout

from pytarkbot.configuration import load_user_settings
from pytarkbot.flee import check_first_price, get_to_flee_tab, get_to_flee_tab_from_my_offers_tab, get_to_my_offers_tab, open_add_offer_tab, post_item, remove_offers, select_random_item_to_flee, set_flea_filters, wait_till_can_add_another_offer
from pytarkbot.hideout import manage_hideout
from pytarkbot.launcher import restart_tarkov, wait_for_tarkov_to_close
from pytarkbot.logger import Logger
from pytarkbot.graphics_config import set_tarkov_settings_to_default_config



user_settings = load_user_settings()
launcher_path = user_settings["launcher_path"]

tarkov_graphics_settings_path = user_settings["graphics_setting_path"]
saved_user_settings_path = join(".\config","user_default_config","Graphics.ini") 
preset_graphics_for_bot_path = join(".\config","config_for_bot","Graphics.ini") 



logger=Logger()

def main():
    intro_printout(logger)
    
    state="intro"
    
    try:
        while True:
            if state=="intro":
                state=state_intro()
            if state=="restart":
                state=state_restart()
            if state=="flee_mode":
                state=state_flee_mode()
            if state=="remove_flee_offers":
                state=state_remove_flee_offers()
            if state=="manage_hideout_mode":
                state=state_hideout_management()
            if state=="help":
                state=state_user_help_printout()
            
    finally:
        #wait for clean close
        wait_for_tarkov_to_close(logger)

        #revert settings to user default
        set_tarkov_settings_to_default_config(logger,src=saved_user_settings_path,dst=tarkov_graphics_settings_path)
        
        #program tag
        exit_printout(logger)
        
    
def state_user_help_printout():
    blank_line="////////////////////////////////////////////////////"
    logger.log("")
    logger.log(blank_line)
    logger.log("State==user_help_printout")
    logger.log(blank_line)
    logger.log("")
    logger.log("lol good luck.")
    return "restart"
    2
    
def state_intro():
    blank_line="////////////////////////////////////////////////////"
    logger.log("")
    logger.log(blank_line)
    logger.log("State==Intro")
    logger.log(blank_line)
    logger.log("")
    
    restart_tarkov(logger,launcher_path,tarkov_graphics_settings_path,saved_user_settings_path,preset_graphics_for_bot_path)
    
    logger.log("Select a mode for the TarkBot")
    logger.log("[1] flee items")
    logger.log("[2] hideout management")
    logger.log("[3] help")
    
    waiting_for_key=True
    while waiting_for_key:
        if keyboard.is_pressed('1'):  # if key 'q' is pressed 
            return "flee_mode"
        if keyboard.is_pressed('2'):  # if key 'q' is pressed 
            return "manage_hideout_mode"
        if keyboard.is_pressed('3'):  # if key 'q' is pressed 
            return "help"

    
def state_remove_flee_offers():
    blank_line="////////////////////////////////////////////////////"
    logger.log("")
    logger.log(blank_line)
    logger.log("State==Remove flee offers")
    logger.log(blank_line)
    logger.log("")
    
    
    logger.log("STATE=remove_flee_offers")
      
    logger.log("Getting to the flea tab.")
    if get_to_flee_tab(logger)=="restart":
        return "restart"
    
    logger.log("Getting to my offers tab")
    if get_to_my_offers_tab(logger)=="restart":
        return "restart"
    
    logger.log("Starting remove offers alg.")
    remove_offers(logger)
    
    logger.log("Returning to browse page in the flea.")
    get_to_flee_tab_from_my_offers_tab(logger)
    
    return "flee_mode"
    
      
def state_flee_mode():
    blank_line="////////////////////////////////////////////////////"
    logger.log("")
    logger.log(blank_line)
    logger.log("State==flee mode")
    logger.log(blank_line)
    logger.log("")
    
    
    logger.log("STATE=flee_mode")
    #open flea
    if get_to_flee_tab(logger)=="restart":
        return "restart"
    time.sleep(0.33)
              
    while True:
        pyautogui.press('n')
        
        #wait for add offer
        if wait_till_can_add_another_offer(logger)=="remove_flee_offers":
            return "remove_flee_offers"
        
        #click add offer button on top of screen
        open_add_offer_tab(logger)
        
        #fbi for random item
        if select_random_item_to_flee(logger)=="restart":
            logger.log("Issue selecting random item to flee.")
            return "restart"
        
        #set search 
        set_flea_filters(logger)
        time.sleep(1)
        
        #if current price passes check, post this item up. else skip
        post_price=check_first_price(logger)
        if post_price is not False:
            logger.log("Post price passed all checks. Posting this item.")
            post_item(logger,post_price)                   
        

def state_restart():
    blank_line="////////////////////////////////////////////////////"
    logger.log("")
    logger.log(blank_line)
    logger.log("State==Restart")
    logger.log(blank_line)
    logger.log("")
    
    
    #add to logegr
    logger.add_restart()
    
    #if tark open close it
    logger.log("STATE=RESTART")
    restart_tarkov(logger,launcher_path,tarkov_graphics_settings_path, saved_user_settings_path,preset_graphics_for_bot_path)
    
    return "flee_mode"


def state_hideout_management():
    blank_line="////////////////////////////////////////////////////"
    logger.log("")
    logger.log(blank_line)
    logger.log("State==hideout management")
    logger.log(blank_line)
    logger.log("")
    
    
    if manage_hideout(logger)=="restart":
        return "restart"
    return "restart"

if __name__ == "__main__":
    main() 
