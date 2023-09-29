"""
This module contains functions for removing offers from the flea market in Escape from Tarkov.
"""

import itertools
import random
import time

import numpy
import pyautogui

from pytarkbot.detection import (
    check_for_location,
    find_references,
    get_first_location,
    pixel_is_equal,
)
from pytarkbot.detection.image_rec import make_reference_image_list
from pytarkbot.tarkov import click, screenshot
from pytarkbot.tarkov.client import get_to_flea_tab, open_filters_window

pyautogui.FAILSAFE = False
RANDOM_ITEM_SELECTION_TIMEOUT = 30  # S


def remove_offers(logger):
    """
    Removes offers from the flea market page.

    Args:
        logger: A logger object that tracks the number of offers removed.

    Returns:
        None
    """
    # Begins on MY OFFERS tab on the flea market page

    logger.change_status("Removing offers.")
    for _ in range(10):
        # click random tab on left side
        for _ in range(4):
            logger.change_status("Clicking random category of offer on left side.")
            click(x=227, y=random.randint(131, 311))
        time.sleep(0.33)

        # check the top slot for a remove offer button
        if check_if_remove_offer_button_exists_for_item_index_1():
            logger.change_status("Found a remove offer button in the first slot")
            click(1200, 150)
            time.sleep(0.33)
            pyautogui.press("y")

            # increment logger
            logger.add_offer_removed()
            logger.change_status(f"Incremented offers removed to {logger.offers_removed}")

        # check the next slot for a remove offer button
        elif check_if_remove_offer_button_exists_for_item_index_2():
            logger.change_status("Found a remove offer button in the second slot")
            click(1185, 200)
            time.sleep(0.33)
            pyautogui.press("y")

            # increment logger
            logger.add_offer_removed()
            logger.change_status("Incremented offers removed to", logger.offers_removed)

        else:
            logger.change_status("No remove offer button found.")


def get_color_list_of_current_price(image):
    """
    Returns a list of English color names for the pixels
    in the current price area of the given image.

    Args:
        image (PIL.Image): The image to analyze.

    Returns:
        list: A list of English color names for the pixels
        in the current price area of the given image.
    """
    # make numpy iar
    iar = numpy.asarray(image)

    # get pixel RGB list
    rgb_pix_list = []
    y_coord = 150
    for x_coord in range(907, 987):
        current_pix = iar[y_coord][x_coord]
        current_pix = [current_pix[0], current_pix[1], current_pix[2]]
        rgb_pix_list.append(current_pix)

    # replace RGB list with english color list
    english_color_list = []
    for rgb in rgb_pix_list:
        red_content = rgb[0]
        if red_content > 100:
            english_color_list.append("tan")
        else:
            english_color_list.append(None)

    return english_color_list


def count_digits2():
    """
    Counts the number of digits in the current price area of the screen.

    Returns:
        int: The number of digits in the current price area of the screen.
    """
    ####get pix list of pixels from (900,141) -> (1000,141)
    pixel_list = []
    iar = numpy.asarray(screenshot())
    # show_image(screenshot([900,138,100,6]))
    y_coord = 141
    for x_coord in range(900, 1000):
        pixel = iar[y_coord][x_coord]
        pixel_list.append(pixel)

    ####Turn pix list into english list
    # color_tan = [196, 193, 173]
    # color_black = [37, 36, 31]
    color_white = [190, 196, 193]
    english_list = []
    for pixel in pixel_list:
        if pixel_is_equal(pixel, color_white, tol=40):
            english_list.append("white")
        else:
            english_list.append("black")

    ####Remove dupes in english list
    short_english_list = []
    for color in english_list:
        if (
            short_english_list
            and short_english_list[-1] != color
            or not short_english_list
        ):
            short_english_list.append(color)

    ####count whites
    white_count = 0
    for color in short_english_list:
        if color == "white":
            white_count = white_count + 1

    return white_count - 2


def count_digits():
    """
    Counts the number of digits in the current price area of the screen.

    Returns:
        int: The number of digits in the current price area of the screen.
    """
    image = screenshot()

    color_list = get_color_list_of_current_price(image)
    spliced_color_list = splice_color_list_for_count_digits(color_list=color_list)

    tan_count = 0
    for color in spliced_color_list:
        if color == "tan":
            tan_count = tan_count + 1

    return tan_count - 1


def splice_color_list_for_count_digits(color_list):
    """
    Splices a list of English color names for the pixels in the
    current price area of the screen into a list of digits.

    Args:
        color_list (list): A list of English color names for the
        pixels in the current price area of the screen.

    Returns:
        list: A list of digits in the current price area of the screen.
    """
    pix_list = [None]

    for pixel in color_list:
        if (pix_list[-1] is not None) and (pixel is None):
            pix_list.append(pixel)
        if (pix_list[-1] != "tan") and (pixel == "tan"):
            pix_list.append(pixel)

    return pix_list


def find_coords_of_item_to_flea(rows_to_target):
    """
    Finds the coordinates of an item to sell on the flea market.

    Args:
        rows_to_target (int): The number of rows to target.

    Returns:
        list: The coordinates of the item to sell.
    """
    positive_pixel_list = []
    iar = numpy.asarray(screenshot())
    y_pixel_maximum = min(520 + (rows_to_target - 1) * 42, 915)

    empty_color = [45, 45, 45]
    for x_coord, y_coord in itertools.product(
        range(15, 420, 3), range(510, y_pixel_maximum, 3)
    ):
        this_pixel = iar[y_coord][x_coord]
        if not pixel_is_equal(this_pixel, empty_color, tol=45):
            positive_pixel_list.append([x_coord, y_coord])

    if not positive_pixel_list:
        return None

    positive_pixel_list = remove_close_coords(positive_pixel_list, threshold=5)

    return random.choice(positive_pixel_list)


def remove_close_coords(coord_list, threshold=5):
    """
    Removes coordinates from a list that are too close to each other.

    Args:
        coord_list (list): A list of coordinates.
        threshold (int, optional): The minimum distance between coordinates to keep. Defaults to 5.

    Returns:
        list: A list of coordinates with duplicates removed.
    """
    # Create a list to store the coordinates to keep
    coords_to_keep = []

    # Iterate through the list of coordinates
    for coord in coord_list:
        # Assume we want to keep this coordinate
        keep_coord = True

        # Check if this coordinate is within 'threshold' pixels of any other coordinate
        for existing_coord in coords_to_keep:
            distance = (
                (coord[0] - existing_coord[0]) ** 2
                + (coord[1] - existing_coord[1]) ** 2
            ) ** 0.5
            if distance < threshold:
                # If it is, mark it for removal
                keep_coord = False
                break

        # If we still want to keep this coordinate, add it to the list of coordinates to keep
        if keep_coord:
            coords_to_keep.append(coord)

    return coords_to_keep


def find_fbi_button():
    """
    Find the filter by item button on the screen.

    Returns:
        tuple: The coordinates of the filter by item button.
    """
    current_image = screenshot()
    reference_folder = "filter_by_item_button"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return get_first_location(locations)


def click_fbi_button():
    """
    Click the filter by item button.

    Returns:
        str: "restart" if the filter by item button is not found, "continue" otherwise.
    """
    # logger.change_status("Checking whether or not the fbi button shows for the selected item.")
    fbi_coords = find_fbi_button()
    if fbi_coords is None:
        # logger.change_status("Found no fbi button for the selected item. Returning restart.")
        return "restart"

    # click fbi button

    # logger.change_status("clicking fbi button for the selected item.")
    click(fbi_coords[1], fbi_coords[0])
    return "continue"


def select_random_item_to_flea(logger, rows_to_target) -> bool:
    """
    Select a random item to flea.

    Args:
        logger: The logger object.
        rows_to_target (int): The number of rows to target.

    Returns:
        bool: True if a satisfactory item to flea is found, False otherwise.
    """
    #click add offer button
    click(837, 82)
    time.sleep(0.33)

    # cast rows to assure its really an int
    rows_to_target = int(rows_to_target)

    logger.change_status("Selecting a random item to flea.")

    # get start time
    start_time = time.time()

    # loop forever
    while 1:
        # timeout check
        if time.time() - start_time > RANDOM_ITEM_SELECTION_TIMEOUT:
            logger.change_status(
                f"Looked for an item to flea for longer than {RANDOM_ITEM_SELECTION_TIMEOUT}s!"
            )
            break

        # find an item
        item_coords = find_coords_of_item_to_flea(rows_to_target)

        # if no items, look  again
        if item_coords is None:
            continue

        # left + right click the item
        logger.change_status("Found a potential item to sell")
        click(item_coords[0], item_coords[1], button="left")
        time.sleep(0.1)
        click(item_coords[0], item_coords[1], button="right")
        time.sleep(0.33)

        # click this item's filter by item (FBI) button
        if click_fbi_button() != "restart":
            logger.change_status("Found a satisfactory item to flea.")
            return True

    # if we get here, we timed out
    return False


def check_if_can_add_offer():
    """
    Check if an offer can be added.

    Returns:
        bool: True if an offer can be added, False otherwise.
    """
    pix_list = []
    iar = numpy.asarray(screenshot())
    positive_pixel = [220, 215, 190]
    for x_coord, y_coord in itertools.product(range(780, 870), range(75, 90)):
        current_pix = iar[y_coord][x_coord]
        if pixel_is_equal(current_pix, positive_pixel, tol=35):
            pix_list.append(current_pix)
    return len(pix_list) > 25


def close_add_offer_window(logger):
    """
    Close the add offer window.

    Args:
        logger: The logger object.
    """
    # logger.change_status("Closing add offer window.")
    orientate_add_offer_window(logger)
    click(732, 471)


def check_for_close_add_offer_window():
    """
    Check if the add offer window can be closed.

    Returns:
        bool: True if the add offer window can be closed, False otherwise.
    """
    iar = numpy.asarray(screenshot())

    white_x_exists = False
    for x_coord in range(730, 738):
        if pixel_is_equal(iar[470][x_coord], [184, 193, 199], tol=35):
            white_x_exists = True
            break

    grey_refresh_button_exists = False
    for x_coord in range(710, 722):
        if pixel_is_equal(iar[470][x_coord], [61, 64, 65], tol=35):
            grey_refresh_button_exists = True
            break

    red_background_exists = False
    for x_coord in range(727, 742):
        if pixel_is_equal(iar[470][x_coord], [72, 13, 13], tol=35):
            red_background_exists = True
            break

    if white_x_exists and grey_refresh_button_exists and red_background_exists:
        return True
    return False


def find_add_offer_window():
    """
    Find the add offer window.

    Returns:
        list: A list containing the x and y coordinates of
        the add offer window, or None if it cannot be found.
    """
    current_image = screenshot()
    reference_folder = "find_add_offer_window"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    coords = get_first_location(locations)
    return None if coords is None else [coords[1], coords[0] - 13]


def wait_till_can_add_another_offer(logger, remove_offers_timer) -> bool:
    """
    Wait until another offer can be added.

    Args:
        logger: The logger object.
        remove_offers_timer: The time to wait before removing offers.

    Returns:
        bool: True if another offer can be added, False otherwise.
    """
    # False = waited too long so should remove offers

    # calculate how long to wait for
    time_in_seconds = convert_remove_offers_timer_to_int_in_seconds(remove_offers_timer)
    time_per_loop = 1
    max_loops = time_in_seconds / time_per_loop

    # wait until limit or has_another_offer
    has_another_offer = check_if_can_add_offer()
    loops = 0
    while not has_another_offer:
        # if past loop: return
        if loops > max_loops:
            return False

        loops = loops + 1
        logger.change_status(f"Waiting for another offer: {loops}")

        # close add offer window that may be obstructing the bot right now
        if check_for_close_add_offer_window():
            close_add_offer_window(logger)

        # refresh current flea page
        click(65, 50)
        time.sleep(0.2)
        pyautogui.press("f5")
        time.sleep(0.8)

        # get to flea tab if not already there
        get_to_flea_tab(logger, print_mode=False)
        logger.change_status(f"Waiting for another offer: {loops}")

        # check if has_another_offer
        has_another_offer = check_if_can_add_offer()

    logger.change_status("Done waiting for another offer.")

    return True


def convert_remove_offers_timer_to_int_in_seconds(remove_offers_timer):
    """
    Convert the remove offers timer to an integer in seconds.

    Args:
        remove_offers_timer: The time to wait before removing offers.

    Returns:
        int: The time in seconds.
    """
    if remove_offers_timer == "1m":
        return 60
    if remove_offers_timer == "2m":
        return 120
    if remove_offers_timer == "5m":
        return 300
    if remove_offers_timer == "10m":
        return 600
    return 60


def write_post_price(logger, post_price):
    """
    Write the post price.

    Args:
        logger: The logger object.
        post_price: The price to write.
    """
    # open rouble input region

    click(507, 709)

    # write post_price
    logger.change_status(f"Writing price of {post_price}.")
    type_string = str(post_price)
    pyautogui.typewrite(type_string, interval=0.02)


def post_item(logger, post_price):
    """
    Post an item.

    Args:
        logger: The logger object.
        post_price: The price to post.
    """
    operation_delay = 0.17

    orientate_add_offer_window(logger)

    write_post_price(logger, post_price)
    time.sleep(operation_delay)

    # click place offer
    click(590, 960)
    time.sleep(operation_delay)

    # if the game asks any questions at this point, the answer is always NO!
    if check_for_post_confirmation_popup():
        pyautogui.press("n")
        time.sleep(operation_delay)
    else:
        # logger stats stuff
        logger.add_roubles_made(post_price)
        logger.add_item_sold()

    # refresh page to see ur own offer
    pyautogui.press("f5")
    time.sleep(operation_delay)


def check_for_post_confirmation_popup() -> bool:
    """
    Check if there is a post confirmation popup.

    Returns:
        bool: True if there is a post confirmation popup, False otherwise.
    """
    current_image = screenshot()
    reference_folder = "check_for_post_confirmation_popup"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return check_for_location(locations)


def orientate_add_offer_window(logger) -> bool:
    """
    Orientate the add offer window.

    Args:
        logger: The logger object.

    Returns:
        bool: True if the add offer window is orientated, False otherwise.
    """
    orientated = check_add_offer_window_orientation()
    loops = 0
    while not orientated:
        if loops > 10:
            return False
        loops = loops + 1

        coords = find_add_offer_window()
        if coords is None:
            return False
        origin = pyautogui.position()
        pyautogui.moveTo(coords[0], coords[1], duration=0.1)
        time.sleep(0.1)
        pyautogui.dragTo(0, 980, duration=0.7)
        pyautogui.moveTo(origin[0], origin[1])
        orientated = check_add_offer_window_orientation()
    logger.change_status("Orientated add offer window.")
    return True


def check_add_offer_window_orientation() -> bool:
    """
    Check if the add offer window is orientated.

    Returns:
        bool: True if the add offer window is orientated, False otherwise.
    """
    coords = find_add_offer_window()
    if coords is None:
        return False
    value1 = abs(coords[0] - 20)
    value2 = abs(coords[1] - 471)
    return value1 <= 3 and value2 <= 3


def find_add_requirement_window() -> list[int] | None:
    """
    Find the add requirement window.

    Returns:
        list[int] | None: The coordinates of the add requirement window, or None if it is not found.
    """
    current_image = screenshot()
    reference_folder = "find_add_requirement_window"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    coords = get_first_location(locations)
    return None if coords is None else [coords[1], coords[0]]


def set_flea_sell_mode_filters(logger):
    """
    Set the flea sell mode filters.

    Args:
        logger: The logger object.
    """
    start_time = time.time()
    operation_delay = 0.01

    # open filter window
    open_filters_window(logger)
    time.sleep(operation_delay)

    # click currency dropdown
    click(113, 62)
    time.sleep(operation_delay)

    # click RUB from dropdown
    click(124, 100)
    time.sleep(operation_delay)

    # click 'display offers from' dropdown
    click(171, 188)
    time.sleep(operation_delay)

    # click players from dropdown
    click(179, 250)
    time.sleep(operation_delay)

    # click 'condition from:' text input box
    click(131, 123)
    time.sleep(operation_delay)

    # write 100 in 'condition from:' text box
    pyautogui.typewrite("100")
    time.sleep(operation_delay)

    # click OK
    click(83, 272)
    time.sleep(operation_delay)

    logger.change_status(
        f"Took {str(time.time() - start_time)[:5]}s to set flea sell mode filters."
    )


def check_if_on_my_offers_tab():
    """
    Check if the user is on the 'My Offers' tab.

    Returns:
        bool: True if the user is on the 'My Offers' tab, False otherwise.
    """
    iar = numpy.asarray(screenshot())

    pix1 = iar[77][255]
    pix2 = iar[94][251]
    pix3 = iar[82][309]

    pixel_totals = [
        int(pix1[0]) + int(pix1[1]) + int(pix1[2]),
        int(pix2[0]) + int(pix2[1]) + int(pix2[2]),
        int(pix3[0]) + int(pix3[1]) + int(pix3[2]),
    ]

    return all(total >= 500 for total in pixel_totals)


def get_to_my_offers_tab(logger):
    """
    Navigate to the 'My Offers' tab.

    Args:
        logger: The logger object.

    Returns:
        str: "restart" if the function needs to be restarted, None otherwise.
    """
    on_offers_tab = check_if_on_my_offers_tab()
    loops = 0
    while not on_offers_tab:
        if loops > 25:
            return "restart"
        loops = loops + 1

        click(269, 87)
        time.sleep(0.17)
        on_offers_tab = check_if_on_my_offers_tab()
    logger.change_status("On my offers tab.")


def get_to_flea_tab_from_my_offers_tab(logger):
    """
    Navigate to the flea market tab from the 'My Offers' tab.

    Args:
        logger: The logger object.
    """
    click(829, 977, clicks=2, interval=0.33)
    time.sleep(0.33)
    get_to_flea_tab(logger)


def get_price_undercut(found_price):
    """
    Calculates the undercut price based on the found price.

    Args:
        found_price (str): The price found in the image.

    Returns:
        int: The undercut price.
    """
    if (found_price is None) or (found_price == ""):
        return None
    found_price = int(found_price)

    undercut_option_1 = found_price - 2100
    undercut_option_2 = int(found_price * 0.8)
    return max(undercut_option_2, undercut_option_1)


def get_price_of_first_seller_in_flea_items_table():
    """
    Gets the price of the first seller in the flea items table.

    Returns:
        str: The price of the first seller in the flea items table.
    """
    # returns digits and the significant figures of the price
    num = None

    digit_ch_1 = count_digits()
    digit_ch_2 = count_digits2()
    digit_ch_3 = count_digits2()

    if not digit_ch_1 == digit_ch_2 == digit_ch_3:
        return None

    digits = digit_ch_1

    if (digits == 0) or (digits == 1) or (digits == 2) or (digits is None):
        return None
    if digits == 3:
        image = screenshot([928, 137, 10, 16])
        num = get_number_from_image(image)
        if num is None:
            return None
        num = f"{num}50"
    elif digits == 4:
        image = screenshot([918, 138, 16, 16])
        # show_image(image)
        num = get_number_from_image(image)
        if num is None:
            return None
        num = f"{num}500"
    elif digits == 5:
        image_1 = screenshot([916, 137, 12, 18])
        image_2 = screenshot([926, 137, 12, 18])
        digit1 = get_number_from_image(image_1)
        digit2 = get_number_from_image(image_2)
        if (digit1 is None) or (digit2 is None):
            return None
        num = digit1 + digit2 + "500"
    elif digits == 6:
        image1 = screenshot([909, 139, 11, 14])
        image2 = screenshot([918, 139, 11, 14])
        image3 = screenshot([928, 139, 11, 14])
        digit1 = get_number_from_image(image1)
        digit2 = get_number_from_image(image2)
        digit3 = get_number_from_image(image3)
        if (digit1 is None) or (digit2 is None) or (digit3 is None):
            return None
        num = digit1 + digit2 + digit3 + "500"

    return num


def get_number_from_image(image):
    """
    Gets the number from the given image.

    Args:
        image (PIL.Image): The image to get the number from.

    Returns:
        str: The number found in the image.
    """
    # sourcery skip: assign-if-exp, reintroduce-else
    if check_for_1_in_image_for_selling_price(image):
        return "1"
    elif check_for_2_in_image_for_selling_price(image):
        return "2"
    elif check_for_3_in_image_for_selling_price(image):
        return "3"
    elif check_for_4_in_image_for_selling_price(image):
        return "4"
    elif check_for_5_in_image_for_selling_price(image):
        return "5"
    elif check_for_6_in_image_for_selling_price(image):
        return "6"
    elif check_for_7_in_image_for_selling_price(image):
        return "7"
    elif check_for_8_in_image_for_selling_price(image):
        return "8"
    elif check_for_9_in_image_for_selling_price(image):
        return "9"
    elif check_for_0_in_image_for_selling_price(image):
        return "0"

    return None


def check_for_1_in_image_for_selling_price(current_image):
    """
    Checks if the given image contains the number 1.

    Args:
        current_image (PIL.Image): The image to check.

    Returns:
        bool: True if the image contains the number 1, False otherwise.
    """
    reference_folder = "check_for_1_in_image"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )
    return check_for_location(locations)


def check_for_2_in_image_for_selling_price(current_image):
    """
    Checks if the given image contains the number 2.

    Args:
        current_image (PIL.Image): The image to check.

    Returns:
        bool: True if the image contains the number 2, False otherwise.
    """
    reference_folder = "check_for_2_in_image"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )
    return check_for_location(locations)


def check_for_3_in_image_for_selling_price(current_image):
    """
    Checks if the given image contains the number 3.

    Args:
        current_image (PIL.Image): The image to check.

    Returns:
        bool: True if the image contains the number 3, False otherwise.
    """
    # show_image(current_image)
    reference_folder = "check_for_3_in_image"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )
    return check_for_location(locations)


def check_for_4_in_image_for_selling_price(current_image):
    """
    Checks if the given image contains the number 4.

    Args:
        current_image (PIL.Image): The image to check.

    Returns:
        bool: True if the image contains the number 4, False otherwise.
    """
    # show_image(current_image)
    reference_folder = "check_for_4_in_image"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )
    return check_for_location(locations)


def check_for_5_in_image_for_selling_price(current_image):
    """
    Checks if the given image contains the number 5.

    Args:
        current_image (PIL.Image): The image to check.

    Returns:
        bool: True if the image contains the number 5, False otherwise.
    """
    # show_image(current_image)
    reference_folder = "check_for_5_in_image"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )
    return check_for_location(locations)


def check_for_6_in_image_for_selling_price(current_image):
    """
    Checks if the given image contains the number 6.

    Args:
        current_image (PIL.Image): The image to check.

    Returns:
        bool: True if the image contains the number 6, False otherwise.
    """
    # show_image(current_image)
    reference_folder = "check_for_6_in_image"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )
    return check_for_location(locations)


def check_for_7_in_image_for_selling_price(current_image):
    """
    Checks if the given image contains the number 7.

    Args:
        current_image (PIL.Image): The image to check.

    Returns:
        bool: True if the image contains the number 7, False otherwise.
    """
    # show_image(current_image)
    reference_folder = "check_for_7_in_image"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )
    return check_for_location(locations)


def check_for_8_in_image_for_selling_price(current_image):
    """
    Checks if the given image contains the number 8.

    Args:
        current_image (PIL.Image): The image to check.

    Returns:
        bool: True if the image contains the number 8, False otherwise.
    """
    # show_image(current_image)
    reference_folder = "check_for_8_in_image"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )
    return check_for_location(locations)


def check_for_9_in_image_for_selling_price(current_image):
    """
    Checks if the given image contains the number 9.

    Args:
        current_image (PIL.Image): The image to check.

    Returns:
        bool: True if the image contains the number 9, False otherwise.
    """
    # show_image(current_image)
    reference_folder = "check_for_9_in_image"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png",
        "6.png",
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )
    return check_for_location(locations)


def check_for_0_in_image_for_selling_price(current_image):
    """
    Checks if the given image contains the number 0.

    Args:
        current_image (PIL.Image): The image to check.

    Returns:
        bool: True if the image contains the number 0, False otherwise.
    """
    # show_image(current_image)
    reference_folder = "check_for_0_in_image"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png",
        "6.png",
        "7.png",
        "8.png",
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )
    return check_for_location(locations)


def check_if_remove_offer_button_exists_for_item_index_1():
    """
    Checks if the remove offer button exists for item index 1.

    Returns:
        bool: True if the remove offer button exists, False otherwise.
    """
    # if this is true click (1200,150)

    red_pix_list = []
    color_red = [185, 6, 7]
    iar = numpy.asarray(screenshot())
    for x_coord in range(1160, 1225):
        this_pixel = iar[152][x_coord]
        if pixel_is_equal(this_pixel, color_red, tol=35):
            red_pix_list.append(x_coord)

    return len(red_pix_list) > 5


def check_if_remove_offer_button_exists_for_item_index_2():
    """
    Checks if the remove offer button exists for item index 2.

    Returns:
        bool: True if the remove offer button exists, False otherwise.
    """
    # if this is true click (1185,200)

    red_pix_list = []
    color_red = [185, 6, 7]
    iar = numpy.asarray(screenshot())
    for x_coord in range(1160, 1225):
        this_pixel = iar[200][x_coord]
        if pixel_is_equal(this_pixel, color_red, tol=35):
            red_pix_list.append(x_coord)

    return len(red_pix_list) > 5
