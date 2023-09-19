"""
This module contains the code for handling the scav
case station in the TarkBot hideout bot.
"""

import time
from typing import Literal

import numpy
import pyautogui

from detection.image_rec import (
    check_for_location,
    find_references,
    make_reference_image_list,
    pixel_is_equal,
)
from tarkov.client import (
    check_if_in_hideout_cycle_mode,
    click,
    cycle_hideout_tab,
    get_to_hideout,
    screenshot,
)


def handle_scav_case(logger, craft_type) -> Literal["restart", "medstation"]:
    """
    Handles the scav case station by collecting items and starting a craft.

    Args:
        logger: The logger object to use for logging.
        craft_type: The type of craft to start.

    Returns:
        A string indicating whether to restart the bot or move on to the next station.
    """
    logger.add_station_visited()

    logger.change_status("Handling scav case")

    if not get_to_hideout():
        return "restart"

    if not get_to_scav_case():
        return "restart"

    # scroll to the bottom of the list
    do_scav_case_scrolling()

    # collect any type of craft from this station
    if check_for_moonshine_get_items():
        logger.change_status("Collecting moonshine scav case items...")
        click(1049, 440, clicks=2)
        logger.add_scav_case_collect()
        time.sleep(3)
        pyautogui.press("esc")
        time.sleep(5)

    elif check_for_intel_get_items():
        logger.change_status("Collecting intel scav case items...")
        click(1048, 612, clicks=2)
        logger.add_scav_case_collect()

        time.sleep(3)
        pyautogui.press("esc")
        time.sleep(5)

    elif check_for_15000_get_items():
        logger.change_status("Collecting 15000 scav case items...")
        click(1066, 784, clicks=2)
        logger.add_scav_case_collect()

        time.sleep(3)
        pyautogui.press("esc")
        time.sleep(5)

    elif check_for_2500_get_items():
        logger.change_status("Collecting 2500 scav case items...")
        click(1059, 528, clicks=2)
        logger.add_scav_case_collect()

        time.sleep(3)
        pyautogui.press("esc")
        time.sleep(5)

    elif check_for_95000_get_items():
        logger.change_status("Collecting 95000 scav case items...")
        click(1071, 699)
        logger.add_scav_case_collect()
        time.sleep(3)
        pyautogui.press("esc")
        time.sleep(5)

    # start the selected craft
    if craft_type == "moonshine":
        if check_for_moonshine_start():
            logger.change_status("Starting moonshine scav case...")
            click(1050, 440, clicks=2)
            time.sleep(2)
            logger.add_scav_case_start()

    elif craft_type == "intel":
        if check_for_intel_start():
            logger.change_status("Starting intel scav case...")
            click(1051, 613, clicks=2)
            time.sleep(2)
            logger.add_scav_case_start()

    elif craft_type == "95000":
        if check_for_95000_start():
            logger.change_status("Starting 95000 scav case...")
            click(1070, 699, clicks=2)
            time.sleep(2)
            logger.add_scav_case_start()

    elif craft_type == "15000":
        if check_for_15000_start():
            logger.change_status("Starting 15000 scav case...")
            click(1068, 785, clicks=2)
            time.sleep(2)
            logger.add_scav_case_start()

    elif craft_type == "2500":
        if check_for_2500_start():
            logger.change_status("Starting 2500 scav case...")
            click(1062, 527, clicks=2)
            time.sleep(2)
            logger.add_scav_case_start()

    return "medstation"


def do_scav_case_scrolling() -> None:
    """
    Scrolls to the bottom of the scav case list.
    """
    print("Doing scav case scrolling")
    coord_list = [
        [1267, 410],
        [1271, 410],
        [1269, 410],
        [1270, 410],
        [1273, 410],
    ]

    wait_time = 0.5

    for coord in coord_list:
        # first scroll
        pyautogui.moveTo(x=coord[0], y=coord[1])
        time.sleep(wait_time)
        pyautogui.dragTo(x=coord[0], y=750)
        time.sleep(wait_time)

        # second scroll
        pyautogui.moveTo(x=coord[0], y=650)
        time.sleep(wait_time)
        pyautogui.dragTo(x=coord[0], y=750)
        time.sleep(wait_time)


def check_for_95000_get_items() -> bool:
    """
    Checks if there are 95000 scav case items available.

    Returns:
        True if 95000 scav case items are available, False otherwise.
    """
    current_image = screenshot([995, 670, 160, 70])
    reference_folder = "scav_case_95000_get_items"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return check_for_location(locations)


def check_for_moonshine_get_items() -> bool:
    """
    Checks if there are moonshine scav case items available.

    Returns:
        True if moonshine scav case items are available, False otherwise.
    """
    current_image = screenshot([1000, 411, 150, 65])
    reference_folder = "scav_case_moonshine_get_items"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return check_for_location(locations)


def check_for_intel_get_items() -> bool:
    """
    Checks if there are intel scav case items available.

    Returns:
        True if intel scav case items are available, False otherwise.
    """
    current_image = screenshot([980, 580, 220, 70])
    reference_folder = "scav_case_intel_get_items"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return check_for_location(locations)


def check_for_2500_get_items() -> bool:
    """
    Checks if there are 2500 scav case items available.

    Returns:
        True if 2500 scav case items are available, False otherwise.
    """
    current_image = screenshot([1019, 667, 109, 63])
    reference_folder = "scav_case_2500_get_items"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return check_for_location(locations)


def check_for_15000_get_items() -> bool:
    """
    Checks if there are 15000 scav case items available.

    Returns:
        True if 15000 scav case items are available, False otherwise.
    """
    current_image = screenshot([1020, 760, 140, 80])
    reference_folder = "scav_case_15000_get_items"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return check_for_location(locations)


def check_for_moonshine_start() -> bool:
    """
    Checks if there are moonshine scav case items available.

    Returns:
        True if moonshine scav case items are available, False otherwise.
    """
    current_image = screenshot([1000, 413, 200, 65])
    reference_folder = "scav_case_moonshine_start"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return check_for_location(locations)


def check_for_2500_start() -> bool:
    """
    Checks if there are 2500 scav case items available.

    Returns:
        True if 2500 scav case items are available, False otherwise.
    """
    current_image = screenshot([1022, 673, 112, 57])
    reference_folder = "scav_case_2500_start"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return check_for_location(locations)


def check_for_intel_start() -> bool:
    """
    Checks if there are intel scav case items available.

    Returns:
        True if intel scav case items are available, False otherwise.
    """
    current_image = screenshot([1005, 585, 125, 80])
    reference_folder = "scav_case_intel_start"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return check_for_location(locations)


def check_for_95000_start() -> bool:
    """
    Checks if there are 95000 scav case items available.

    Returns:
        True if 95000 scav case items are available, False otherwise.
    """
    current_image = screenshot([1033, 545, 119, 54])
    reference_folder = "scav_case_95000_start"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return check_for_location(locations)


def check_for_15000_start() -> bool:
    """
    Checks if there are 15000 scav case items available.

    Returns:
        True if 15000 scav case items are available, False otherwise.
    """
    current_image = screenshot([1032, 638, 137, 53])
    reference_folder = "scav_case_15000_start"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return check_for_location(locations)


def get_to_scav_case():
    """
    Navigates to the scav case in the hideout.

    Returns:
        True if successfully navigated to the scav case, False otherwise.
    """
    print("Getting to scav case")

    start_time = time.time()

    if not check_if_in_hideout_cycle_mode():
        print("Not in hideout cycle mode. entering cycle mode...")
        for x_coord in range(700, 1200, 100):
            click(x_coord, 930)

    time.sleep(4)

    while not check_if_at_scav_case():
        cycle_hideout_tab()

        time_taken = time.time() - start_time

        if time_taken > 120:
            print("Took too long getting to scav case. restarting")
            return False

        time.sleep(1.5)

    time_taken = time.time() - start_time
    print(f"made it to scav case in {str(time_taken)[:4]} sec")
    return True


def check_if_at_scav_case():
    """
    Checks if the player is currently at the scav case in the hideout.

    Returns:
        True if the player is at the scav case, False otherwise.
    """
    iar = numpy.asarray(screenshot())

    blue_jacket_exists = True
    for x_coord in range(70, 135):
        pixel = iar[278][x_coord]
        if pixel_is_equal(pixel, [44, 99, 83], tol=15):
            blue_jacket_exists = True
    if not blue_jacket_exists:
        return False

    green_wall_exists = True
    for x_coord in range(609, 650):
        pixel = iar[115][x_coord]
        if pixel_is_equal(pixel, [109, 105, 17], tol=15):
            green_wall_exists = True
    if not green_wall_exists:
        return False

    green_jacket_photo_exists = True
    for x_coord in range(847, 883):
        pixel = iar[181][x_coord]
        if pixel_is_equal(pixel, [21, 88, 21], tol=15):
            green_jacket_photo_exists = True
    if not green_jacket_photo_exists:
        return False

    return True
