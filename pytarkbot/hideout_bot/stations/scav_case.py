import time

import numpy
import pyautogui
from pytarkbot.detection.image_rec import (
    check_for_location,
    find_references,
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


def handle_scav_case(logger, craft_type):
    logger.add_station_visited()

    logger.change_status("Handling scav case")

    if get_to_hideout() == "restart":
        return "restart"

    if get_to_scav_case() == "restart":
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


def do_scav_case_scrolling():
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


def check_for_95000_get_items():
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


def check_for_moonshine_get_items():
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


def check_for_intel_get_items():
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


def check_for_2500_get_items():
    current_image = screenshot([1000, 490, 200, 80])
    reference_folder = "scav_case_2500_get_items"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return check_for_location(locations)


def check_for_15000_get_items():
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


def check_for_moonshine_start():
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


def check_for_2500_start():
    current_image = screenshot([1010, 490, 220, 85])
    reference_folder = "scav_case_2500_start"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return check_for_location(locations)


def check_for_intel_start():
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


def check_for_95000_start():
    current_image = screenshot([1025, 675, 200, 80])
    reference_folder = "scav_case_95000_start"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return check_for_location(locations)


def check_for_15000_start():
    current_image = screenshot([1025, 750, 200, 80])
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
    print("Getting to scav case")

    start_time = time.time()

    if not check_if_in_hideout_cycle_mode():
        print("Not in hideout cycle mode. entering cycle mode...")
        for x in range(700, 1200, 100):
            click(x, 930)

    time.sleep(4)

    while not check_if_at_scav_case():
        cycle_hideout_tab()

        time_taken = time.time() - start_time

        if time_taken > 120:
            print("Took too long getting to scav case. restarting")
            return "restart"

        time.sleep(1.5)

    time_taken = time.time() - start_time
    print(f"made it to scav case in {str(time_taken)[:4]} sec")


def check_if_at_scav_case():
    iar = numpy.asarray(screenshot())

    scav_case_text_exists = False
    for x in range(710, 760):
        this_pixel = iar[354][x]
        if pixel_is_equal(this_pixel, [214, 212, 193], tol=20):
            scav_case_text_exists = True
            break

    scav_case_description_exists = False
    for x in range(1185, 1220):
        this_pixel = iar[400][x]
        if pixel_is_equal(this_pixel, [132, 140, 144], tol=20):
            scav_case_description_exists = True
            break

    current_bonuses_text_exists = False
    for x in range(1010, 1035):
        this_pixel = iar[462][x]
        if pixel_is_equal(this_pixel, [223, 221, 201], tol=20):
            current_bonuses_text_exists = True
            break

    blue_jacket_exists = False
    for x in range(550, 600):
        this_pixel = iar[223][x]
        if pixel_is_equal(this_pixel, [17, 71, 152], tol=20):
            blue_jacket_exists = True
            break
        elif pixel_is_equal(this_pixel, [38, 74, 111], tol=20):
            blue_jacket_exists = True
            break

    if (
        blue_jacket_exists
        and scav_case_text_exists
        and scav_case_description_exists
        and current_bonuses_text_exists
    ):
        return True
    return False
