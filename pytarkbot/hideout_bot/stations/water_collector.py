import time
from typing import Literal

import numpy
from pytarkbot.detection import pixel_is_equal
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
from pytarkbot.utils.logger import Logger


def handle_water_collector(logger: Logger) -> Literal["restart", "scav_case"]:
    logger.add_station_visited()

    if get_to_hideout() == "restart":
        return "restart"

    logger.change_status("Handling water collector")

    if get_to_water_collector() == "restart":
        return "restart"

    print("doing water checks")
    do_water_collector_checks(logger)

    return "scav_case"


def do_water_collector_checks(logger: Logger):
    if check_for_water_collector_get_items():
        logger.change_status("Collecting water collector items")
        click(x=1051, y=796, clicks=2)
        time.sleep(3)

        logger.add_water_collect()
        logger.add_profit(123300)

    if not check_for_water_collector_filter():
        logger.change_status("Adding a filter to water collector")

        # click filters dropdown
        click(x=930, y=790)
        time.sleep(1)

        # click topleft most filter
        click(x=975, y=796)
        time.sleep(3)

        logger.add_water_filter()

    return True


def check_if_at_water_collector():
    iar = numpy.asarray(screenshot())

    water_collector_text_exists = False
    for x in range(790, 820):
        pixel = iar[494][x]
        if pixel_is_equal(pixel, [237, 235, 214], tol=20):
            water_collector_text_exists = True

    water_description_exists = False
    for x in range(1215, 1250):
        pixel = iar[568][x]
        if pixel_is_equal(pixel, [128, 136, 140], tol=20):
            water_description_exists = True

    close_button_exists = False
    for x in range(1232, 1247):
        pixel = iar[493][x]
        if pixel_is_equal(pixel, [65, 7, 7], tol=20):
            close_button_exists = True

    if water_collector_text_exists and water_description_exists and close_button_exists:
        return True
    return False


def find_water_collector_icon():
    current_image = screenshot()
    reference_folder = "water_collector_icon"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return get_first_location(locations)


def get_to_water_collector():
    print("Getting to water")

    start_time = time.time()

    if not check_if_in_hideout_cycle_mode():
        print("Not in hideout cycle mode. entering cycle mode...")
        for x in range(700, 1200, 100):
            click(x, 930)

    time.sleep(4)

    while not check_if_at_water_collector():
        cycle_hideout_tab()

        time_taken = time.time() - start_time
        if time_taken > 120:
            print("Waited too long getting to water. restarting")
            return "restart"

        time.sleep(1.5)

    print("made it to water in ", str(time.time() - start_time)[:4], " seconds")


def check_for_water_collector_get_items():
    current_image = screenshot()
    reference_folder = "water_collector_get_items"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return check_for_location(locations)


def check_for_water_collector_filter():
    iar = numpy.asarray(screenshot())
    pixel = iar[796][845]
    if pixel_is_equal(pixel, [116, 205, 248], tol=15):
        return True
    return False
