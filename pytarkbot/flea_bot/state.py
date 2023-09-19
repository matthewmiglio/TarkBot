"""
This module contains the state machine for the flea bot. It
includes functions for removing flea offers and adding new ones.
"""

import sys
import time

from pytarkbot.flea_bot.flea import (
    get_price_of_first_seller_in_flea_items_table,
    get_price_undercut,
    get_to_flea_tab_from_my_offers_tab,
    get_to_my_offers_tab,
    orientate_add_offer_window,
    post_item,
    remove_offers,
    select_random_item_to_flea,
    set_flea_sell_mode_filters,
    wait_till_can_add_another_offer,
)
from pytarkbot.tarkov.client import click, get_to_flea_tab
from pytarkbot.tarkov.launcher import restart_tarkov

POST_REMOVE_OFFER_SLEEP_TIME = 30


def flea_sell_mode_state_tree(logger, state, number_of_rows, remove_offers_timer):
    """
    This function represents the state machine for the flea bot.
    It takes in a logger object, the current state, the number of rows,
    and the remove offers timer. It returns the new state of the machine.

    Args:
        logger (Logger): The logger object used to log messages.
        state (str): The current state of the machine.
        number_of_rows (int): The number of rows in the flea market.
        remove_offers_timer (int): The timer for removing offers.

    Returns:
        str: The new state of the machine.
    """
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
    """
    This function removes flea offers. It takes in a logger object and returns None.

    Args:
        logger (Logger): The logger object used to log messages.

    Returns:
        None
    """
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

    for second in range(POST_REMOVE_OFFER_SLEEP_TIME):
        if second % 5 == 0:
            logger.change_status(
                f"Waiting {POST_REMOVE_OFFER_SLEEP_TIME-second}s to restart after removing offers."
            )
        time.sleep(1)
    return None


def state_flea_mode(logger, number_of_rows, remove_offers_timer):
    """
    This function represents the flea mode state. It takes in a logger
    object, the number of rows, and the remove offers timer. It returns
    the new state of the machine.

    Args:
        logger (Logger): The logger object used to log messages.
        number_of_rows (int): The number of rows in the flea market.
        remove_offers_timer (int): The timer for removing offers.

    Returns:
        str: The new state of the machine.
    """
    logger.change_status("Beginning flea alg.\n")

    # get to flea
    logger.change_status("Getting to flea")
    if get_to_flea_tab(logger) == "restart":
        return "restart"

    while True:
        # open flea
        logger.change_status("Getting to flea")
        if get_to_flea_tab(logger) == "restart":
            return "restart"

        # wait for another add offer
        logger.change_status("Waiting for another flea offer slot.")

        if not wait_till_can_add_another_offer(logger, remove_offers_timer):
            return "remove_flea_offers"

        # click add offer
        logger.change_status("Adding another offer.")
        click(837, 82)
        time.sleep(0.33)

        logger.change_status("Orientating add offer window.")
        orientate_add_offer_window(logger)

        select_random_item_to_flea(logger, number_of_rows)
        time.sleep(1)

        # set flea filter
        logger.change_status("Setting the flea filters to only RUB/players only.")
        set_flea_sell_mode_filters(logger)
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
    """
    This function represents the restart state of the flea bot. It
    takes in a logger object and returns the new state of the machine.

    Args:
        logger (Logger): The logger object used to log messages.

    Returns:
        str: The new state of the machine.
    """
    logger.change_status("\n\nState==Restart")

    # add to logger
    logger.add_restart()

    restart_tarkov(logger)

    return "flea_mode"
