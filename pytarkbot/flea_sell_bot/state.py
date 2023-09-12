import sys
import time

from pytarkbot.flea_sell_bot.flea import (
    get_price_of_first_seller_in_flea_items_table,
    get_price_undercut,
    get_to_flea_tab,
    get_to_flea_tab_from_my_offers_tab,
    get_to_my_offers_tab,
    orientate_add_offer_window,
    post_item,
    remove_offers,
    select_random_item_to_flea,
    set_flea_filters,
    wait_till_can_add_another_offer,
)
from pytarkbot.hideout_bot.stations.bitcoin_miner import handle_bitcoin_miner
from pytarkbot.hideout_bot.stations.lavatory import handle_lavatory
from pytarkbot.hideout_bot.stations.medstation import handle_medstation
from pytarkbot.hideout_bot.stations.scav_case import handle_scav_case
from pytarkbot.hideout_bot.stations.water_collector import find_water_collector_icon
from pytarkbot.hideout_bot.stations.workbench import handle_workbench
from pytarkbot.tarkov import restart_tarkov
from pytarkbot.tarkov.client import click



#flea sell mode stuff
def flea_sell_mode_state_tree(logger, state, number_of_rows, remove_offers_timer):

    if state == "restart":
        flea_mode_restart_state(logger)
        return "flea_mode"

    if state == "flea_mode":
        state = state_flea_mode(logger, number_of_rows, remove_offers_timer)
        if state == "Done":
            sys.exit()

    elif state == "remove_flea_offers":
        state_remove_flea_offers(logger)
        state = "restart"
    return state


def state_remove_flea_offers(logger):

    logger.change_status("State==Remove flea offers")

    logger.change_status("STATE=remove_flea_offers")

    logger.change_status("Getting to the flea tab.")
    if get_to_flea_tab(logger) == "restart":
        return "restart"

    logger.change_status("Getting to my offers tab")
    if get_to_my_offers_tab(logger) == "restart":
        return "restart"

    logger.change_status("Starting remove offers alg.")
    remove_offers(logger)

    logger.change_status("Returning to browse page in the flea.")
    get_to_flea_tab_from_my_offers_tab(logger)

    sleep_time = 30
    for n in range(sleep_time):
        if n % 5 == 0:
            logger.change_status(
                f"Waiting {sleep_time-n} seconds to restart after removing offers."
            )
        time.sleep(1)
    return None


def state_flea_mode(logger, number_of_rows, remove_offers_timer):
    logger.change_status("Beginning flea alg.\n")

    # get to flea
    logger.change_status("Getting to flea")
    if get_to_flea_tab(logger) == "restart":
        return "restart"
    time.sleep(1)

    # read money and set logger's starting money value

    while True:
        # open flea
        logger.change_status("Getting to flea")
        if get_to_flea_tab(logger) == "restart":
            return "restart"
        time.sleep(1)

        # wait for another add offer
        logger.change_status("Waiting for another flea offer slot.")
        if (
            wait_till_can_add_another_offer(logger, remove_offers_timer)
            == "remove_flea_offers"
        ):
            return "remove_flea_offers"
        time.sleep(1)

        # click add offer
        logger.change_status("Adding another offer.")
        click(837, 82)
        time.sleep(0.33)

        logger.change_status("Orientating add offer window.")
        orientate_add_offer_window(logger)
        time.sleep(1)
        orientate_add_offer_window(logger)
        time.sleep(1)

        if select_random_item_to_flea(logger, number_of_rows)== "restart":
            return "restart"
        time.sleep(1)

        # set flea filter
        logger.change_status("Setting the flea filters to only RUB/players only.")
        set_flea_filters(logger)
        time.sleep(1)

        # get/check price
        logger.change_status("Doing price check.")
        # logger.add_flea_sale_attempt()
        detected_price = get_price_of_first_seller_in_flea_items_table()
        if detected_price is not None:
            logger.change_status(f"Price of {detected_price} passed check.")

            # get undercut
            undercut_price = get_price_undercut(detected_price)
            logger.change_status(f"Undercut price is: {undercut_price}")

            # post this item
            post_item(logger, undercut_price)

        # read current money and set logger's current money value

        logger.add_flea_sale_attempt()


def flea_mode_restart_state(logger):
    logger.change_status("\n\nState==Restart")

    # add to logger
    logger.add_restart()

    restart_tarkov(logger)

    return "flea_mode"



#hideout bot stuff
def hideout_mode_state_tree(state, logger, jobs):  # -> check_fuel
    print("-------------------------------------\n")

    if state == "start":
        restart_tarkov(logger)

        state = "check_fuel"

    if state == "restart":  # -> check_fuel
        logger.add_restart()

        restart_tarkov(logger)

        state = "check_fuel"

    elif state == "check_fuel":  # -> no_fuel,
        # state = check_for_fuel(logger)
        return "bitcoin"

    elif state == "no_fuel":  # -> program freeze
        for _ in range(3):
            logger.change_status("Generator has no fuel!!")
        while 1:
            pass

    elif state == "autorestart":
        print("Entered autorestart state")
        logger.add_autorestart()

        restart_tarkov(logger)

        state = "check_fuel"

    # bitcoin -> workbench -> water -> scav -> medstation -> lavatory -> bitcoin

    elif state == "bitcoin":
        # if its time for autorestart, state = autorestart then return
        print('Checking for autorestart time')
        hours_string = logger.time_since_start

        print('Done checking for autorestart time')

        hours_running = int(hours_string)

        autorestarts = logger.autorestarts

        if hours_running >= autorestarts:
            state = "autorestart"
        else:
            print("Entered bitcoin state")

            if "Bitcoin" in jobs:
                state = handle_bitcoin_miner(logger)
            else:
                state = "workbench"

            print(f"State after bitcoin is {state}")

    elif state == "workbench":
        print("Entered workbench state")

        if "Workbench" in jobs:
            state = handle_workbench(logger)
        else:
            state = "water"

        print(f"State after workbench is {state}")

    elif state == "water":
        print("Entered water state")

        if "water" in jobs:
            state = find_water_collector_icon()
        else:
            state = "scav_case"

        print(f"State after water is {state}")

    elif state == "scav_case":
        print("Entered scav_case state")

        if "scav_case" in jobs:
            # unpack scav case craft type from job list

            if "15000" in jobs:
                craft_type = "15000"
            elif "95000" in jobs:
                craft_type = "95000"
            elif "Moonshine" in jobs:
                craft_type = "moonshine"
            elif "Intel" in jobs:
                craft_type = "intel"
            else:
                craft_type = "2500"

            state = handle_scav_case(logger, craft_type)
        else:
            state = "medstation"

        print(f"State after scav_case is {state}")

    elif state == "medstation":
        print("Entered medstation state")

        if "medstation" in jobs:
            state = handle_medstation(logger)
        else:
            state = "lavatory"

        print(f"State after medstation is {state}")

    elif state == "lavatory":
        print("Entered lavatory state")

        if "Lavatory" in jobs:
            state = handle_lavatory(logger)
        else:
            state = "bitcoin"

        print(f"State after lavatory is {state}")

    return state



