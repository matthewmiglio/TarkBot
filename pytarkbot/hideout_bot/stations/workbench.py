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
from pytarkbot.utils.logger import Logger


def handle_workbench(logger: Logger):
    logger.add_station_visited()

    if not get_to_hideout():
        return "restart"

    logger.change_status("Handling workbench")
    if not get_to_workbench():
        return "restart"

    print("Doing workbench checks")
    do_workbench_checks(logger)

    return "water"


def do_workbench_checks(logger: Logger):
    if check_for_workbench_get_items():
        logger.change_status("Collecting items from workbench")

        # click get items
        click(x=1091, y=713, clicks=2)
        click(x=1092, y=697, clicks=2)
        time.sleep(3)

        logger.add_workbench_collect()
        logger.add_profit(70746)

    if check_for_workbench_start():
        logger.change_status("Starting workbench craft")

        # click start button
        click(x=1100, y=711, clicks=2, interval=0.5)
        click(x=1092, y=697, clicks=2, interval=0.5)
        time.sleep(1)

        # click handover button
        click(x=654, y=672, clicks=2, interval=0.5)
        time.sleep(3)

        logger.add_workbench_start()

    return True


def check_if_at_workbench():
    iar = numpy.asarray(screenshot())

    pixels = [
        iar[353][728],
        iar[350][742],
        iar[350][808],
        iar[349][823],
        iar[455][1229],
        iar[351][1233],
        iar[351][1246],
    ]
    colors = [
        [181, 180, 163],
        [226, 224, 204],
        [95, 94, 86],
        [204, 203, 185],
        [0, 0, 0],
        [64, 7, 7],
        [63, 7, 7],
    ]

    for i, pixel in enumerate(pixels):
        if not pixel_is_equal(pixel, colors[i], tol=35):
            return False
    return True


def check_for_workbench_start():
    current_image = screenshot()
    reference_folder = "workbench_start"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return check_for_location(locations)


def check_for_workbench_get_items():
    current_image = screenshot()
    reference_folder = "workbench_get_items"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return check_for_location(locations)


def get_to_workbench() -> bool:
    print("Getting to workbench")

    start_time = time.time()

    if not check_if_in_hideout_cycle_mode():
        print("Not in hideout cycle mode. entering cycle mode...")
        for x_coord in range(700, 1200, 100):
            click(x_coord, 930)

    time.sleep(4)

    while not check_if_at_workbench():
        time_taken = time.time() - start_time
        if time_taken > 120:
            print("Took too long to get to workbench")
            return False
        cycle_hideout_tab()
        time.sleep(1.5)

    time_taken = time.time() - start_time
    print(f"made it to workbench in {str(time_taken)[:4]}")
    return True


def find_workbench_icon():
    current_image = screenshot()
    reference_folder = "workbench_icon"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return get_first_location(locations)


