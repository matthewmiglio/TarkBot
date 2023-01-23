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
from pytarkbot.tarkov import click, screenshot

pyautogui.FAILSAFE = False


# digit count methods
def get_color_list_of_current_price(image):
    # make numpy iar
    iar = numpy.asarray(image)

    # get pixel RGB list
    rgb_pix_list = []
    y_coord = 150
    for x_coord in range(907, 987):
        current_pix = iar[y_coord][x_coord]
        current_pix = [current_pix[0], current_pix[1], current_pix[2]]
        rgb_pix_list.append(current_pix)
    # print(rgb_pix_list)

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
    image = screenshot()

    color_list = get_color_list_of_current_price(image)
    spliced_color_list = splice_color_list_for_count_digits(color_list=color_list)

    tan_count = 0
    for color in spliced_color_list:
        if color == "tan":
            tan_count = tan_count + 1

    return tan_count - 1


def splice_color_list_for_count_digits(color_list):
    pix_list = [None]

    for pixel in color_list:
        if (pix_list[-1] is not None) and (pixel is None):
            pix_list.append(pixel)
        if (pix_list[-1] != "tan") and (pixel == "tan"):
            pix_list.append(pixel)

    return pix_list


# item interaction methods
def find_coords_of_item_to_flea(rows_to_target):

    positive_pixel_list = []
    iar = numpy.asarray(screenshot())
    y_pixel_maximum = int(520 + (rows_to_target - 1) * 42)
    if y_pixel_maximum > 915:
        y_pixel_maximum = 915

    empty_color = [45, 45, 45]
    for x, y in itertools.product(range(15, 420, 3), range(510, y_pixel_maximum, 3)):
        this_pixel = iar[y][x]
        if not pixel_is_equal(this_pixel, empty_color, tol=45):
            positive_pixel_list.append([x, y])
    # return a random pixel from the list

    if positive_pixel_list == []:
        return None
    return random.choice(positive_pixel_list)


def find_fbi_button():
    current_image = screenshot()
    reference_folder = "filter_by_item_button"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png",
        "6.png",
        "7.png",
        "8.png",
        "9.png",
        "10.png",
        "11.png",
        "12.png",
        "13.png",
        "14.png",
        "15.png",
        "16.png",
        "17.png",
        "18.png",
        "19.png",
        "20.png",
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return get_first_location(locations)


def click_fbi_button():

    # logger.change_status("Checking whether or not the fbi button shows for the selected item.")
    fbi_coords = find_fbi_button()
    if fbi_coords is None:
        # logger.change_status("Found no fbi button for the selected item. Returning restart.")
        return "restart"

    # click fbi button

    # logger.change_status("clicking fbi button for the selected item.")
    click(fbi_coords[1], fbi_coords[0])
    time.sleep(0.33)
    return "continue"


def select_random_item_to_flea(logger, rows_to_target, loops=0):
    # ROWS TO TARGET MUST BE AN INT 1-11 THAT WILL BE GIVEN THRUGH THE GUI
    # Rows just means the amt of rows it'll attempt to target when selecting an item to flea in the
    # add offer tab

    # if this method recursively looped too many times,
    # then the flea pile is (probably) empty
    if loops > 3:
        logger.change_status(
            "Selected a non-FIR item more than 3 times in a row. Stopping sell algorithm..."
        )
        return "Done"

    logger.change_status("Selecting another random item to flea.")
    has_item_to_flea = False
    while not has_item_to_flea:
        # clicks the random item's FBI button
        # click item to flea

        item_coords = find_coords_of_item_to_flea(rows_to_target)
        if item_coords is None:
            logger.change_status("No items found in region stopping sell algorithm...")
            return "Done"
        if item_coords is None:
            return
        click(item_coords[0], item_coords[1])
        time.sleep(0.17)
        click(item_coords[0], item_coords[1], button="right")
        time.sleep(0.5)

        # click this item's FBI button
        if click_fbi_button() != "restart":
            logger.change_status("Found item to flea.")
            has_item_to_flea = True
            logger.change_status("Found a satisfactory item to flea.")
        else:
            logger.change_status(
                "This item's filter by item button was unreadable this go-around. Finding another item."
            )
        time.sleep(1)

        # if an item isn't selected by now then return
        if not check_if_has_item_to_flea_selected():
            logger.change_status(
                "Selected a non-FIR item. Recursively redoing select_random_item_to_flea()"
            )
            return select_random_item_to_flea(logger, rows_to_target, loops=loops + 1)


# flea interaction methods
def get_to_flea_tab(logger):
    logger.change_status("Getting to flea tab")
    on_flea = check_if_on_flea_page()
    loops = 0
    while not on_flea:
        # logger.change_status("Didnt find flea tab. Clicking flea tab.")
        if loops > 10:
            return "restart"
        loops = loops + 1

        click(829, 977)
        time.sleep(2)
        on_flea = check_if_on_flea_page()
    logger.change_status("Made it to flea tab.")


def check_if_on_flea_page():
    # sourcery skip: assign-if-exp, boolean-if-exp-identity, reintroduce-else, swap-if-expression
    iar = numpy.asarray(screenshot())

    pix1 = iar[984][813]
    pix2 = iar[972][810]
    pix3 = iar[976][883]
    pix4 = iar[984][883]

    COLOR_TAN = [159, 157, 144]

    if not pixel_is_equal(pix1, COLOR_TAN, tol=25):
        return False
    if not pixel_is_equal(pix2, COLOR_TAN, tol=25):
        return False
    if not pixel_is_equal(pix3, COLOR_TAN, tol=25):
        return False
    if not pixel_is_equal(pix4, COLOR_TAN, tol=25):
        return False
    return True


def check_if_can_add_offer():
    pix_list = []
    iar = numpy.asarray(screenshot())
    positive_pixel = [220, 215, 190]
    for x, y in itertools.product(range(780, 870), range(75, 90)):
        current_pix = iar[y][x]
        if pixel_is_equal(current_pix, positive_pixel, tol=35):
            pix_list.append(current_pix)
    return len(pix_list) > 25


def close_add_offer_window(logger):
    # logger.change_status("Closing add offer window.")
    orientate_add_offer_window(logger)
    click(732, 471)


def find_add_offer_window():

    current_image = screenshot()
    reference_folder = "find_add_offer_window"
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

    coords = get_first_location(locations)
    return None if coords is None else [coords[1], coords[0] - 13]


def wait_till_can_add_another_offer(logger, remove_offers_timer):
    # calculate how long to wait for
    time_in_seconds = convert_remove_offers_timer_to_int_in_seconds(remove_offers_timer)
    max_loops = time_in_seconds / 2

    # wait until limit or has_another_offer
    has_another_offer = check_if_can_add_offer()
    loops = 0
    while not has_another_offer:
        # if past loop: return
        if loops > max_loops:
            return "remove_flea_offers"

        loops = loops + 1
        logger.change_status(f"Waiting for another offer: {loops}")

        # close add offer window that may be obstructing the bot right now
        close_add_offer_window(logger)
        time.sleep(1)

        # refresh current flea page
        pyautogui.press("f5")
        time.sleep(1)

        # get to flea tab if not already there
        get_to_flea_tab(logger)
        logger.change_status(f"Waiting for another offer: {loops}")

        # check if has_another_offer
        has_another_offer = check_if_can_add_offer()

    logger.change_status("Done waiting for another offer.")


def convert_remove_offers_timer_to_int_in_seconds(remove_offers_timer):
    if remove_offers_timer == "1m":
        return 60
    if remove_offers_timer == "2m":
        return 120
    if remove_offers_timer == "5m":
        return 300
    if remove_offers_timer == "10m":
        return 600


def write_post_price(logger, post_price):
    # open rouble input region

    click(1162, 501)

    # write post_price
    logger.change_status(f"Writing price of {post_price}.")
    type_string = str(post_price)
    pyautogui.typewrite(type_string, interval=0.02)
    time.sleep(0.17)


def post_item(logger, post_price):
    orientate_add_offer_window(logger)

    click_add_requirements_in_add_requirements_window(logger)

    orientate_add_requirement_window(logger)

    write_post_price(logger, post_price)

    # click add in add requirements window

    logger.change_status("Adding this offer.")
    click(1169, 961, clicks=2)
    time.sleep(1)
    click(1169, 961, clicks=2)
    time.sleep(1)

    # click place offer in add offer window
    click(596, 954)
    time.sleep(1)

    # handle post/purchase confirmation popup
    handle_post_confirmation_popup(logger)
    handle_purchase_confirmation_popup(logger)
    pyautogui.press("n")

    # logger stats stuff
    logger.add_roubles_made(post_price)
    logger.add_item_sold()

    # refresh page to see ur own offer
    pyautogui.press("f5")
    time.sleep(0.17)


def check_for_post_confirmation_popup():

    current_image = screenshot()
    reference_folder = "check_for_post_confirmation_popup"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png",
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return check_for_location(locations)


def handle_post_confirmation_popup(logger):

    if check_for_post_confirmation_popup():
        logger.change_status("Handling post confirmation popup")
        click(50, 50, clicks=2)

        pyautogui.press("n")
        time.sleep(0.33)


def check_for_purchase_confirmation_popup():

    current_image = screenshot()
    reference_folder = "check_for_purchase_confirmation_popup"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png",
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return check_for_location(locations)


def handle_purchase_confirmation_popup(logger):

    if check_for_purchase_confirmation_popup():
        logger.change_status("Handling purchase confirmation popup")
        click(50, 50, clicks=2)
        pyautogui.press("n")
        time.sleep(0.33)


# flea add offer window
def orientate_add_offer_window(logger):

    orientated = check_add_offer_window_orientation()
    loops = 0
    while not orientated:
        # logger.change_status(f"Orientating add offer window: {loops}.")
        if loops > 10:
            return "restart"
        loops = loops + 1

        coords = find_add_offer_window()
        if coords is None:
            # logger.change_status("Trouble orientating add offer window. Restarting.")
            return "restart"
        origin = pyautogui.position()
        pyautogui.moveTo(coords[0], coords[1], duration=0.4)
        time.sleep(1)
        pyautogui.dragTo(0, 980, duration=0.33)
        pyautogui.moveTo(origin[0], origin[1])
        orientated = check_add_offer_window_orientation()
    logger.change_status("Orientated add offer window.")
    time.sleep(0.17)


def check_add_offer_window_orientation():
    coords = find_add_offer_window()
    if coords is None:
        return False
    value1 = abs(coords[0] - 20)
    value2 = abs(coords[1] - 471)
    return value1 <= 3 and value2 <= 3


def find_add_requirement_window():

    current_image = screenshot()
    reference_folder = "find_add_requirement_window"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png",
        "6.png",
        "7.png",
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    coords = get_first_location(locations)
    return None if coords is None else [coords[1], coords[0]]


def orientate_add_requirement_window(logger):
    orientated = check_add_requirement_window_orientation()
    loops = 0
    while not orientated:
        logger.change_status(f"Orientating add requirement window {loops}")
        loops = loops + 1
        window_coords = find_add_requirement_window()
        if window_coords is None:
            logger.change_status(
                "Trouble orientating add requirement window. Restarting."
            )
            return "restart"
        window_coords = [window_coords[0] + 10, window_coords[1]]
        origin = pyautogui.position()
        pyautogui.moveTo(window_coords[0], window_coords[1], duration=0.33)
        pyautogui.mouseDown(button="left")
        time.sleep(0.33)
        pyautogui.dragTo(1300, 1000, duration=0.33)
        pyautogui.moveTo(origin[0], origin[1])
        time.sleep(0.33)
        pyautogui.mouseUp(button="left")
        orientated = check_add_requirement_window_orientation()
    logger.change_status("Orientated add requirement window.")
    time.sleep(0.17)


def check_add_requirement_window_orientation():
    coords = find_add_requirement_window()
    # print(coords)
    if coords is None:
        return False
    value1 = abs(coords[0] - 1008)
    value2 = abs(coords[1] - 471)
    return value1 <= 3 and value2 <= 3


def click_add_requirements_in_add_requirements_window(logger):

    logger.change_status("Adding requirements for offer..")
    click(711, 710)
    time.sleep(0.17)


# flea filters window
def find_filters_window():

    current_image = screenshot()
    reference_folder = "find_filters_tab"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png",
        "6.png",
        "7.png",
        "8.png",
        "9.png",
        "10.png",
        "11.png",
        "12.png",
        "13.png",
        "14.png",
        "15.png",
        "16.png",
        "17.png",
        "18.png",
        "19.png",
        "20.png",
        "21.png",
        "22.png",
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    coords = get_first_location(locations)
    return None if coords is None else [coords[1] + 3, coords[0] + 3]


def check_filters_window_orientation():
    coords = find_filters_window()
    # print(coords)
    if coords is None:
        return False
    value1 = abs(coords[0] - 24)
    value2 = abs(coords[1] - 35)
    return value1 <= 3 and value2 <= 3


def orientate_filters_window(logger):

    is_orientated = check_filters_window_orientation()
    while not is_orientated:
        logger.change_status("Orientating filters window.")
        coords = find_filters_window()
        if coords is not None:
            origin = pyautogui.position()
            pyautogui.moveTo(coords[0], coords[1], duration=0.33)
            time.sleep(0.33)
            pyautogui.dragTo(3, 3, duration=0.33)
            pyautogui.moveTo(origin[0], origin[1])
            time.sleep(0.33)
        is_orientated = check_filters_window_orientation()
    logger.change_status("Orientated filters window.")


def open_filters_window(logger):
    click(328, 87)
    time.sleep(0.33)
    orientate_filters_window(logger)


def set_flea_filters(logger):
    logger.change_status("Setting the flea filters for price undercut recognition")

    # open filter window
    logger.change_status("Opening the filters window")
    open_filters_window(logger)
    time.sleep(0.17)

    # click currency dropdown
    logger.change_status("Filtering by roubles.")
    click(113, 62)
    time.sleep(0.17)

    # click RUB from dropdown
    click(124, 100)
    time.sleep(0.17)

    # click 'display offers from' dropdown
    logger.change_status("Filtering by player sales only.")
    click(171, 188)
    time.sleep(0.17)

    # click players from dropdown
    click(179, 250)
    time.sleep(0.17)

    # click 'condition from:' text input box
    click(131, 123)
    time.sleep(0.17)

    # write 100 in 'condition from:' text box
    pyautogui.typewrite("100")
    time.sleep(0.17)

    # click OK
    logger.change_status("Clicking OK in filters tab.")
    click(83, 272)
    time.sleep(0.17)


# removing offers methods
def check_if_on_my_offers_tab():

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

    on_offers_tab = check_if_on_my_offers_tab()

    loops = 0
    while not on_offers_tab:
        if loops > 10:
            return "restart"
        loops = loops + 1

        click(269, 87)
        time.sleep(1)
        on_offers_tab = check_if_on_my_offers_tab()
    logger.change_status("On my offers tab.")


def remove_offers(logger):
    # Begins on MY OFFERS tab on the flea market page

    logger.change_status("Removing offers.")
    print("Starting loop")
    for remove_offer_loop_index in range(10):
        print("\nDoing remove offer loop #", remove_offer_loop_index)

        # click random tab on left side
        for _ in range(4):
            print("Clicking random category of offer on left side.")
            click(x=227, y=random.randint(131, 311))
        time.sleep(0.33)

        # check the top slot for a remove offer button
        if check_if_remove_offer_button_exists_for_item_index_1():
            print("Found a remove offer button in the top slot")
            click(1200, 150)
            time.sleep(0.33)
            pyautogui.press("y")

            # increment logger
            logger.add_offer_removed()
            print("Incremented offers removed to", logger.offers_removed)

        # check the next slot for a remove offer button
        elif check_if_remove_offer_button_exists_for_item_index_2():
            print("Found a remove offer button in the second slot")
            click(1185, 200)
            time.sleep(0.33)
            pyautogui.press("y")

            # increment logger
            logger.add_offer_removed()
            print("Incremented offers removed to", logger.offers_removed)

        else:
            print("No remove offer button found.")


def get_to_flea_tab_from_my_offers_tab(logger):
    click(829, 977, clicks=2, interval=0.33)
    time.sleep(0.33)
    get_to_flea_tab(logger)


def look_for_remove_offer_button():
    # find red remove button coord on this page
    color_red = [185, 6, 7]
    iar = numpy.asarray(screenshot())
    for y_coord in range(120, 430):
        this_pixel = iar[y_coord][1190]
        if pixel_is_equal(this_pixel, color_red, tol=35):
            return [1190, y_coord]
    return None


def check_if_remove_offer_button_exists():
    red_pix_list = []
    color_red = [185, 6, 7]
    iar = numpy.asarray(screenshot())
    for x_coord in range(1160, 1225):
        this_pixel = iar[152][x_coord]
        if pixel_is_equal(this_pixel, color_red, tol=35):
            red_pix_list.append(x_coord)

    return len(red_pix_list) > 5


# price detection methods
def get_price_undercut(found_price):
    if (found_price is None) or (found_price == ""):
        return None
    found_price = int(found_price)

    undercut_option_1 = found_price - 2700
    undercut_option_2 = int(found_price * 0.75)
    return max(undercut_option_2, undercut_option_1)


def get_price_of_first_seller_in_flea_items_table():
    # returns digits and the significant figures of the price
    num = None

    digit_ch_1 = count_digits()
    digit_ch_2 = count_digits2()
    digit_ch_3 = count_digits2()

    if not digit_ch_1 == digit_ch_2 == digit_ch_3:
        print("Failed digit checking. Returning.")
        return None

    digits = digit_ch_1

    print("Digits: ", digits)
    if (digits == 0) or (digits == 1) or (digits == 2) or (digits is None):
        print("Digits are too low. Returning.")
        return None
    if digits == 3:
        image = screenshot([928, 137, 10, 16])
        num = get_number_from_image(image)
        if num is None:
            return None
        num = f"{num}50"
    if digits == 4:
        image = screenshot([918, 138, 16, 16])
        # show_image(image)
        num = get_number_from_image(image)
        if num is None:
            return None
        num = f"{num}500"
    if digits == 5:
        image_1 = screenshot([916, 137, 12, 18])
        image_2 = screenshot([926, 137, 12, 18])
        # show_image(image_1)
        # show_image(image_2)
        digit1 = get_number_from_image(image_1)
        digit2 = get_number_from_image(image_2)
        # print(digit1,digit2)
        if (digit1 is None) or (digit2 is None):
            print("One of the digits is empty.\nBot thinks this is a 5 digit number.")
            print("First two read digits: ", digit1, digit2)
            return None
        num = digit1 + digit2 + "500"
    if digits == 6:
        image1 = screenshot([909, 139, 11, 14])
        image2 = screenshot([918, 139, 11, 14])
        image3 = screenshot([928, 139, 11, 14])
        # show_image(image1)
        # show_image(image2)
        # show_image(image3)
        digit1 = get_number_from_image(image1)
        digit2 = get_number_from_image(image2)
        digit3 = get_number_from_image(image3)
        print(digit1, "|", digit2, "|", digit3)
        if (digit1 is None) or (digit2 is None) or (digit3 is None):
            print("One of the digits is empty. Bot thinkgs this is a 6 digit number.")
            print("First three read digits: ", digit1, digit2, digit3)
            return None
        num = digit1 + digit2 + digit3 + "500"

    return num


def get_number_from_image(image):
    # sourcery skip: assign-if-exp, reintroduce-else
    if check_for_1_in_image_for_selling_price(image):
        return "1"
    if check_for_2_in_image_for_selling_price(image):
        return "2"
    if check_for_3_in_image_for_selling_price(image):
        return "3"
    if check_for_4_in_image_for_selling_price(image):
        return "4"
    if check_for_5_in_image_for_selling_price(image):
        return "5"
    if check_for_6_in_image_for_selling_price(image):
        return "6"
    if check_for_7_in_image_for_selling_price(image):
        return "7"
    if check_for_8_in_image_for_selling_price(image):
        return "8"
    if check_for_9_in_image_for_selling_price(image):
        return "9"
    if check_for_0_in_image_for_selling_price(image):
        return "0"

    return None


def check_for_1_in_image_for_selling_price(current_image):
    reference_folder = "check_for_1_in_image"
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


def check_for_2_in_image_for_selling_price(current_image):
    reference_folder = "check_for_2_in_image"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png",
        "6.png",
        "7.png",
        "8.png",
        "9.png",
        "10.png",
        "11.png",
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )
    return check_for_location(locations)


def check_for_3_in_image_for_selling_price(current_image):
    # show_image(current_image)
    reference_folder = "check_for_3_in_image"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png",
        "6.png",
        "7.png",
        "8.png",
        "9.png",
        "10.png",
        "11.png",
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )
    return check_for_location(locations)


def check_for_4_in_image_for_selling_price(current_image):
    # show_image(current_image)
    reference_folder = "check_for_4_in_image"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png",
        "6.png",
        "7.png",
        "8.png",
        "9.png",
        "10.png",
        "11.png",
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )
    return check_for_location(locations)


def check_for_5_in_image_for_selling_price(current_image):
    # show_image(current_image)
    reference_folder = "check_for_5_in_image"
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


def check_for_6_in_image_for_selling_price(current_image):
    # show_image(current_image)
    reference_folder = "check_for_6_in_image"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png",
        "6.png",
        "7.png",
        "8.png",
        "9.png",
        "10.png",
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )
    return check_for_location(locations)


def check_for_7_in_image_for_selling_price(current_image):
    # show_image(current_image)
    reference_folder = "check_for_7_in_image"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png",
        "6.png",
        "7.png",
        "8.png",
        "9.png",
        "10.png",
        "11.png",
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )
    return check_for_location(locations)


def check_for_8_in_image_for_selling_price(current_image):
    # show_image(current_image)
    reference_folder = "check_for_8_in_image"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png",
        "6.png",
        "7.png",
        "8.png",
        "9.png",
        "10.png",
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )
    return check_for_location(locations)


def check_for_9_in_image_for_selling_price(current_image):
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


###TO SORT


def check_if_remove_offer_button_exists_for_item_index_1():
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
    # if this is true click (1185,200)

    red_pix_list = []
    color_red = [185, 6, 7]
    iar = numpy.asarray(screenshot())
    for x_coord in range(1160, 1225):
        this_pixel = iar[200][x_coord]
        if pixel_is_equal(this_pixel, color_red, tol=35):
            red_pix_list.append(x_coord)

    return len(red_pix_list) > 5


def check_if_has_item_to_flea_selected():
    iar = numpy.asarray(screenshot())

    requirements_text_exists = False
    for x in range(460, 500):
        this_pixel = iar[680][x]
        if pixel_is_equal(this_pixel, [165, 163, 149], tol=45):
            requirements_text_exists = True

    expires_in_text_exists = False
    for x in range(460, 480):
        this_pixel = iar[820][x]
        if pixel_is_equal(this_pixel, [180, 179, 163], tol=45):
            expires_in_text_exists = True

    fee_text_exists = False
    for x in range(455, 480):
        this_pixel = iar[910][x]
        if pixel_is_equal(this_pixel, [190, 188, 171], tol=45):
            fee_text_exists = True

    # print('requirements_text_exists',requirements_text_exists)
    # print('expires_in_text_exists',expires_in_text_exists)
    # print('fee_text_exists',fee_text_exists)

    if requirements_text_exists and expires_in_text_exists and fee_text_exists:
        return True
    return False
