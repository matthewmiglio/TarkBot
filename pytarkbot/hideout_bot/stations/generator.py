import time
from typing import Literal

import numpy

from pytarkbot.detection.image_rec import (
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


def check_for_fuel(logger) -> Literal["restart", "no_fuel", "bitcoin"]:
    if not get_to_hideout():
        return "restart"

    logger.change_status("Checking for fuel in generator")

    # get to lavatory
    if not get_to_generator(logger):
        return "restart"

    logger.change_status("Doing fuel check")

    if check_pixels_for_no_fuel():
        logger.change_status("There is no fuel")
        logger.change_status("Moving to no fuel state")
        return "no_fuel"
    logger.change_status("There is fuel!")

    return "bitcoin"


def check_if_at_generator() -> bool:
    iar = numpy.asarray(screenshot())

    generator_icon_exists = False
    for x_coord in range(660, 690):
        pixel = iar[448][x_coord]
        if pixel_is_equal(pixel, [206, 205, 195], tol=20):
            generator_icon_exists = True
            break

    current_bonuses_text_exists = False
    for x_coord in range(880, 920):
        pixel = iar[571][x_coord]
        if pixel_is_equal(pixel, [176, 175, 159], tol=20):
            current_bonuses_text_exists = True
            break
    close_button_exists = False
    for x_coord in range(1234, 1246):
        pixel = iar[450][x_coord]
        if pixel_is_equal(pixel, [65, 7, 7], tol=20):
            close_button_exists = True
            break
    if generator_icon_exists and current_bonuses_text_exists and close_button_exists:
        return True
    return False


def check_pixels_for_no_fuel() -> bool:
    iar = numpy.asarray(screenshot())

    red_no_fuel_text_exists = False
    for x_coord in range(840, 900):
        this_pixel = iar[440][x_coord]
        if pixel_is_equal(this_pixel, [138, 25, 25], tol=20):
            red_no_fuel_text_exists = True

    generator_text_exists = False
    for x_coord in range(740, 800):
        this_pixel = iar[450][x_coord]
        if pixel_is_equal(this_pixel, [237, 235, 214], tol=20):
            generator_text_exists = True

    close_menu_icon_exists = False
    for x_coord in range(1230, 1250):
        this_pixel = iar[452][x_coord]
        if pixel_is_equal(this_pixel, [62, 6, 6], tol=20):
            close_menu_icon_exists = True

    if red_no_fuel_text_exists and generator_text_exists and close_menu_icon_exists:
        return True
    return False


def get_to_generator(logger) -> bool:
    logger.change_status("Getting to generator")

    start_time = time.time()

    if not check_if_in_hideout_cycle_mode():
        print("Not in hideout cycle mode. entering cycle mode...")
        for x_coord in range(700, 1200, 100):
            click(x_coord, 930)

    time.sleep(4)

    while not check_if_at_generator():
        time_taken = time.time() - start_time
        if time_taken > 120:
            print("Took too long to get to generator")
            return False
        cycle_hideout_tab()
        time.sleep(1.5)

    time_taken = time.time() - start_time
    print(f"made it to generator in {str(time_taken)[:4]}")
    return True


def find_generator_icon():
    current_image = screenshot()
    reference_folder = "generator_icon"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return get_first_location(locations)
