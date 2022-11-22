from time import time

import pyautogui

from pytarkbot.tarkov import restart_tarkov

from .flee import (
    get_price_2,
    get_price_undercut,
    get_to_flee_tab,
    get_to_flee_tab_from_my_offers_tab,
    get_to_my_offers_tab,
    orientate_add_offer_window,
    post_item,
    remove_offers,
    select_random_item_to_flee,
    set_flea_filters,
    wait_till_can_add_another_offer,
)


def flea_items_main(logger, bsg_launcher_path):
    state = "intro"
    while True:
        if state == "intro":
            state_intro(logger, bsg_launcher_path)
            state = "flee_mode"

        if state == "restart":
            state_restart(logger, bsg_launcher_path)
            state = "flee_mode"

        if state == "flee_mode":
            state = state_flea_mode(logger)

        if state == "remove_flee_offers":
            state = state_remove_flee_offers(logger)


def state_intro(logger, bsg_launcher_path):
    blank_line = "////////////////////////////////////////////////////"
    logger.log("")
    logger.log(blank_line)
    logger.log("State==Intro")
    logger.log(blank_line)
    logger.log("")

    restart_tarkov(logger, bsg_launcher_path)


def state_remove_flee_offers(logger):
    blank_line = "////////////////////////////////////////////////////"
    logger.log("")
    logger.log(blank_line)
    logger.log("State==Remove flee offers")
    logger.log(blank_line)
    logger.log("")

    logger.log("STATE=remove_flee_offers")

    logger.log("Getting to the flea tab.")
    if get_to_flee_tab(logger) == "restart":
        return "restart"

    logger.log("Getting to my offers tab")
    if get_to_my_offers_tab(logger) == "restart":
        return "restart"

    logger.log("Starting remove offers alg.")
    remove_offers(logger)

    logger.log("Returning to browse page in the flea.")
    get_to_flee_tab_from_my_offers_tab(logger)

    return "flee_mode"


def state_flea_mode(logger):
    logger.log("Beginning flea alg.\n")
    while True:
        # open flea
        logger.log("Getting to flea")
        if get_to_flee_tab(logger) == "restart":
            return "restart"
        time.sleep(1)

        # wait for another add offer
        logger.log("Waiting for another flea offer slot.")
        if wait_till_can_add_another_offer(logger) == "remove_flee_offers":
            return "remove_flee_offers"
        time.sleep(1)

        # click add offer
        logger.log("Adding another offer.")
        pyautogui.moveTo(837, 82, duration=0.33)
        pyautogui.click()
        time.sleep(0.33)

        logger.log("Orientating add offer window.")
        orientate_add_offer_window(logger)
        time.sleep(1)
        orientate_add_offer_window(logger)
        time.sleep(1)

        select_random_item_to_flee(logger)
        time.sleep(1)

        # set flea filter
        logger.log("Setting the flea filters to only RUB/players only.")
        set_flea_filters(logger)
        time.sleep(1)

        # get/check price
        logger.log("Doing price check.")
        # logger.add_flea_sale_attempt()
        detected_price = get_price_2()
        if detected_price is not None:
            logger.log(f"Price of {detected_price} passed check.")

            # get undercut
            undercut_price = get_price_undercut(detected_price)
            logger.log(f"Undercut price is: {undercut_price}")

            # post this item
            post_item(logger, undercut_price)
        logger.add_flea_sale_attempt()


def state_restart(logger, bsg_launcher_path):
    blank_line = "////////////////////////////////////////////////////"
    for _ in range(5):
        logger.log(blank_line)
    logger.log("\n\nState==Restart")

    # add to logger
    logger.add_restart()

    restart_tarkov(logger, bsg_launcher_path)

    return "flee_mode"
