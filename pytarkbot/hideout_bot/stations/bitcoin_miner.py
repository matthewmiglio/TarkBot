import time

import numpy

from pytarkbot.detection.image_rec import (
    check_for_location,
    find_references,
    get_first_location,
    make_reference_image_list,
    pixel_is_equal,
)
from pytarkbot.tarkov.client import (
    check_if_in_hideout_cycle_mode,
    click,
    cycle_hideout_tab,
    get_to_hideout,
    screenshot,
)


def handle_bitcoin_miner(logger):
    logger.add_station_visited()

    if not get_to_hideout():
        return "restart"

    logger.change_status("Handling bitcoin miner")

    if not get_to_bitcoin_miner(logger):
        return "restart"

    logger.change_status("Doing bitcoin miner checks")

    if check_for_bitcoin_miner_get_items():
        logger.change_status("Collecting bitcoin")
        click(x=1111, y=761, clicks=2)
        time.sleep(2)
        logger.add_profit(327082)
        logger.add_bitcoin_collect()

    else:
        logger.change_status("No actions for bitcoin miner yet...")

    return "workbench"


def check_if_at_bitcoin_miner():
    iar = numpy.asarray(screenshot())

    current_bonuses_text_exists = False
    for x in range(972, 984):
        pixel = iar[633][x]
        if pixel_is_equal(pixel, [222, 220, 201], tol=20):
            current_bonuses_text_exists = True

    bitcoin_farm_text_exists = False
    for x in range(720, 840):
        pixel = iar[512][x]
        if pixel_is_equal(pixel, [232, 231, 210], tol=20):
            bitcoin_farm_text_exists = True

    close_button_exists = False
    for x in range(1230, 1247):
        pixel = iar[509][x]
        if pixel_is_equal(pixel, [65, 7, 7], tol=20):
            close_button_exists = True

    if current_bonuses_text_exists and bitcoin_farm_text_exists and close_button_exists:
        return True
    return False


def get_to_bitcoin_miner(logger) -> bool:
    logger.change_status("Getting to bitcoin miner")

    start_time = time.time()

    if not check_if_in_hideout_cycle_mode():
        logger.change_status("Not in hideout cycle mode. entering cycle mode...")
        for x in range(700, 1200, 100):
            click(x, 930)

    time.sleep(4)

    while not check_if_at_bitcoin_miner():
        time_taken = time.time() - start_time

        if time_taken > 120:
            logger.change_status("Took too long to get to bitcoin miner")
            return False
        cycle_hideout_tab()
        time.sleep(1.5)

    time_taken = time.time() - start_time
    logger.change_status(f"made it to bitcoin miner in {str(time_taken)[:4]}")

    return True


def find_bitcoin_miner_icon() -> list[int] | None:
    current_image = screenshot()
    reference_folder = "bitcoin_miner_icon"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return get_first_location(locations)


def check_for_bitcoin_miner_get_items() -> bool:
    current_image = screenshot()
    reference_folder = "bitcoin_miner_get_items"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return check_for_location(locations)
