


import time
import pyautogui
from client import exit_printout, intro_printout
from configuration import load_user_settings



from flee import check_first_price, get_to_flee_tab, get_to_flee_tab_from_my_offers_tab, get_to_my_offers_tab, open_add_offer_tab, post_item, remove_offers, select_random_item_to_flee, set_flea_filters, wait_till_can_add_another_offer
from graphics_config import set_tarkov_settings_to_default_config

               

from launcher import restart_tarkov, wait_for_tarkov_to_close, wait_for_tarkov_to_open
from logger import Logger

user_settings = load_user_settings()
launcher_path = user_settings["launcher_path"]
graphics_settings_path = user_settings["graphics_setting_path"]


logger=Logger()

def main():
    intro_printout(logger)
    
    state="restart"
    
    try:
        while True:
            if state=="restart":
                state=state_restart()
            if state=="flee_mode":
                state=state_flee_mode()
            if state=="remove_flee_offers":
                state=state_remove_flee_offers()
    finally:
        #wait for clean close
        wait_for_tarkov_to_close(logger)

        #revert settings to user default
        set_tarkov_settings_to_default_config(logger)
        
        #program tag
        exit_printout(logger)
        
    
def state_remove_flee_offers():
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
    #add to logegr
    logger.add_restart()
    
    #if tark open close it
    logger.log("STATE=RESTART")
    restart_tarkov(logger,launcher_path)
    return "flee_mode"


def state_hideout_management():
    pass


if __name__ == "__main__":
    main() 