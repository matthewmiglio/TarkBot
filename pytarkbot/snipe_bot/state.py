import random
import time

from pytarkbot.snipe_bot.ruble_snipe_data import RUBLE_SNIPE_DATA
from pytarkbot.tarkov.client import (
    buy_this_offer,
    get_to_flea_tab,
    orientate_tarkov_client,
    reset_filters,
    search_for_item,
    set_specific_snipe_flea_filters,
)
from pytarkbot.tarkov.launcher import restart_tarkov

LOOPS_PER_STATE = 6


def snipebot_state_tree(state, logger, job_list, snipe_data):
    # joblist = [
    #     "ruble_sniping",
    #     "item_sniping",
    # ]

    # snipe_data = [
    #     ("item_name 1", "item_price 1"),
    #     ("item_name 2", "item_price 2"),
    #     ("item_name 3", "item_price 3"),
    #     ("item_name 4", "item_price 4"),
    # ]

    if state == "restart":
        restart_state(logger)
        state = "item_snipe"

    if state == "ruble_snipe":
        if "ruble_sniping" in job_list:
            state = ruble_snipe_main(logger)
        else:
            state = "item_snipe"

    if state == "item_snipe":
        if "item_sniping" in job_list:
            state = specific_item_snipe_main(logger, snipe_data)
        else:
            state = "ruble_snipe"

    return state


def specific_item_snipe_main(logger, snipe_data):
    # for each item in snipe_data, check for snipe

    item_index = 0
    for item in snipe_data:
        item_name = item[0]
        item_price = item[1]

        logger.change_status(
            f"Looking for {item_index}th item: [{item_name}] w/ offers below {item_price}"
        )

        # get to flea
        print("Getting to flea tab")
        orientate_tarkov_client()
        if get_to_flea_tab(logger, print_mode=False) == "restart":
            logger.change_status("#8435683 Failure with getting to flea tab")
            return "restart"

        # reset existing filters
        reset_filters(logger)

        # search for name
        if search_for_item(item_name) == "no results":
            logger.change_status(f"no results for {item_name}")
            continue

        # apply filters for this item
        set_specific_snipe_flea_filters(logger, item_price, print_mode=False)
        time.sleep(2)

        # if offer exists, buy, else continue
        if buy_this_offer(logger):
            logger.add_specific_snipe()

        item_index += 1

    return "ruble_snipe"


def restart_state(logger):
    # close all of tarkov, start launcher, then tarkov, then get to main menu
    logger.change_status("Entered restart state")

    restart_tarkov(logger)

    logger.add_restart()


def ruble_snipe_main(logger):
    # loop LOOPS_PER_STATE times, then run state_tree again
    for loop_index in range(LOOPS_PER_STATE):
        logger.change_status(f"Starting ruble snipe loop {loop_index}")

        # pick random item
        this_item = random.choice(RUBLE_SNIPE_DATA)

        # unpack name and price from tuple
        item_name = this_item[0]
        item_price = this_item[1] - 100

        logger.change_status(f"Looking for {item_name} offers below {item_price}")

        # get to flea
        if get_to_flea_tab(logger, print_mode=False) == "restart":
            logger.change_status("#235987 Failure with getting to flea tab")
            return "restart"

        # reset existing filters
        reset_filters(logger)

        # search for name
        if search_for_item(item_name) == "no results":
            logger.change_status(f"no results for {item_name}")
            continue

        # apply filters for this item
        set_specific_snipe_flea_filters(logger, item_price, print_mode=False)
        time.sleep(2)

        # if offer exists, buy, else continue
        logger.add_ruble_snipe()
        buy_this_offer(logger)

    return "item_snipe"
