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
from pytarkbot.tarkov import (
    calculate_avg_pixel,
    check_quit_key_press,
    click,
    find_all_pixel_coords,
    find_all_pixels,
    img_to_txt,
    img_to_txt_numbers_only,
    screenshot,
)


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


def count_digits3():
    # show_image(screenshot([900,147,100,6]))
    # show_image(screenshot())

    iar = numpy.asarray(screenshot())

    ####get pix list from (900,150) -> (1000,150)
    pixel_list = []
    y_coord = 151
    for x_coord in range(900, 1000):
        pixel = iar[y_coord][x_coord]
        pixel_list.append(pixel)

    ####Turn pix list into english list
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

    return white_count - 1


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
    # region = [896, 126, 115, 47]
    image = screenshot()

    color_list = get_color_list_of_current_price(image)
    spliced_color_list = splice_color_list_for_count_digits(color_list=color_list)

    tan_count = 0
    for color in spliced_color_list:
        if color == "tan":
            tan_count = tan_count + 1

    return tan_count - 1


def splice_color_list_for_count_digits(color_list):
    returnPixlist = [None]

    for pixel in color_list:
        if (returnPixlist[-1] is not None) and (pixel is None):
            returnPixlist.append(pixel)
        if (returnPixlist[-1] != "tan") and (pixel == "tan"):
            returnPixlist.append(pixel)

    return returnPixlist


def adjust_price_string(price_string):
    output_string = ""
    for element in price_string:
        if element in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            output_string = output_string + element
        if element == "s":
            output_string = f"{output_string}8"
        elif element in ["o", "@"]:
            output_string = f"{output_string}0"
    # checks
    if len(output_string) < 3:
        return None

    second_char_string = output_string[1]
    # second_char_int = int(second_char_string)

    if second_char_string == 5:
        print("Treertet")

    return output_string


def get_current_price():
    # get image
    region = [910, 137, 82, 19]

    price_image = screenshot(region)

    # get text
    text = img_to_txt_numbers_only(price_image)
    print(text)

    # give adjusted price
    return adjust_price_string(text)


def get_price_undercut(found_price):
    if (found_price is None) or (found_price == ""):
        return None
    found_price = int(found_price)

    undercut_option_1 = found_price - 2700
    undercut_option_2 = int(found_price * 0.75)
    return max(undercut_option_2, undercut_option_1)


def get_value_to_post_item():
    price = get_current_price()

    print(f"The price the bot read is: {price}")

    return [get_price_undercut(price), price]


def find_coords_of_item_to_flee():
    region = [16, 509, 407, 427]
    iar = numpy.asarray(screenshot(region))
    coords_list = [
        [x_coord, y_coord]
        for x_coord, y_coord in itertools.product(range(407), range(427))
        if (x_coord % 4 == 0) and (y_coord % 4 == 0)
    ]

    has_item = False
    while not has_item:
        # select one of those random coords
        random_coord_index = random.randint(0, len(coords_list) - 1)
        coord = coords_list[random_coord_index]

        # get this coord's color
        color = iar[coord[1]][coord[0]]

        # color check to see if its not black or wahtever
        color_total = int(color[0]) + int(color[1]) + int(color[2])
        if color_total > 100:
            coord[0] = coord[0] + 16
            coord[1] = coord[1] + 509

            return coord


def check_first_price(logger):
    # get avg pixel across left side
    region = [904, 135, 1, 26]
    avg_pix = calculate_avg_pixel(find_all_pixels(region))
    wrong_background_color = [29, 28, 21]
    if pixel_is_equal(wrong_background_color, avg_pix, tol=5):
        logger.log("Top price failed availability check. Returning false for price.")
        return False

    # look for euro symbol near price
    if look_for_euro_symbol():
        logger.log("Top price failed EURO check. Returning False for price.")
        return False
    # look for usd symbol near price
    if look_for_usd_symbol():
        logger.log("Top price failed USD check. Returning False for price.")
        return False
    if check_if_item_to_flee_is_trader_item(logger):
        logger.log("Top price failed TRADER check. Returning False for price.")
        return False

    # digit check
    prices = get_value_to_post_item()
    post_price = prices[0]
    detected_price = prices[1]
    # compare against digit count
    digit_counter_count = count_digits()
    digit_counter_count2 = count_digits2()
    image_rec_count = len(str(detected_price))
    # checks
    if post_price is None:
        logger.log("Price read failed. Skipping")
        return False

    if image_rec_count != digit_counter_count:
        logger.log("Image rec price read failed digit check #1")

    if image_rec_count != digit_counter_count2:
        logger.log("Image rec price read failed digit check #2")

    logger.log(f"Found price: {post_price}")
    return post_price


def check_if_item_to_flee_is_trader_item(logger):
    current_image = screenshot(region=[504, 130, 90, 45])
    reference_folder = "check_if_item_to_flee_is_trader_item"
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
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    truth = check_for_location(locations)
    if truth:
        logger.log("Item is trader item")
    return truth


def look_for_euro_symbol():
    # tells u whether or not the EURO symbol is found near the price
    region = [896, 126, 115, 48]

    euro_color = [120, 124, 192]
    euro_pixels = find_all_pixel_coords(region, euro_color, image=None)

    return len(euro_pixels) != 0


def look_for_usd_symbol():
    # tells u whether or not the EURO symbol is found near the price
    region = [896, 126, 115, 48]

    usd_color = [119, 195, 118]
    euro_pixels = find_all_pixel_coords(region, usd_color, image=None)

    return len(euro_pixels) != 0


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


def get_to_flee_tab(logger):
    on_flee = check_if_on_flee_page()
    loops = 0
    while not on_flee:
        logger.log("Didnt find flea tab. Clicking flea tab.")
        if loops > 10:
            return "restart"
        loops = loops + 1

        check_quit_key_press()
        click(829, 977)
        time.sleep(2)
        on_flee = check_if_on_flee_page()
    logger.log("Made it to flea tab.")


def check_if_on_flee_page():
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


def check_if_can_add_offer(logger):
    close_add_offer_window(logger)
    check_quit_key_press()
    # if we find pixels of this color in this region, then we can add offers
    region = [800, 75, 90, 20]
    color = [215, 209, 182]
    pix_coords = find_all_pixel_coords(region, color, tol=25)

    return pix_coords is not None and pix_coords


def close_add_offer_window(logger):
    # logger.log("Closing add offer window.")
    orientate_add_offer_window(logger)
    click(732, 471)


def find_add_offer_window():
    check_quit_key_press()
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


def wait_till_can_add_another_offer(logger):
    has_another_offer = check_if_can_add_offer(logger)
    loops = 0
    while not has_another_offer:
        if loops > 120:
            return "remove_flee_offers"

        loops = loops + 1
        if loops % 2 == 0:
            print(f"Waiting for another offer: {loops}")

        close_add_offer_window(logger)
        time.sleep(1)

        pyautogui.press("f5")
        time.sleep(1)

        get_to_flee_tab(logger)

        has_another_offer = check_if_can_add_offer(logger)

    logger.log("Done waiting for another offer.")


def orientate_add_offer_window(logger):
    check_quit_key_press()
    orientated = check_add_offer_window_orientation()
    loops = 0
    while not orientated:
        # logger.log(f"Orientating add offer window: {loops}.")
        if loops > 10:
            return "restart"
        loops = loops + 1
        check_quit_key_press()
        coords = find_add_offer_window()
        if coords is None:
            # logger.log("Trouble orientating add offer window. Restarting.")
            return "restart"
        pyautogui.moveTo(coords[0], coords[1], duration=0.4)
        time.sleep(1)
        pyautogui.dragTo(0, 980, duration=0.33)
        orientated = check_add_offer_window_orientation()
    logger.log("Orientated add offer window.")
    time.sleep(0.17)


def check_add_offer_window_orientation():
    coords = find_add_offer_window()
    if coords is None:
        return False
    value1 = abs(coords[0] - 20)
    value2 = abs(coords[1] - 471)
    return value1 <= 3 and value2 <= 3


def find_add_requirement_window():
    check_quit_key_press()
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
        logger.log(f"Orientating add requirement window {loops}")
        loops = loops + 1
        window_coords = find_add_requirement_window()
        if window_coords is None:
            logger.log("Trouble orientating add requirement window. Restarting.")
            return "restart"
        window_coords = [window_coords[0] + 10, window_coords[1]]
        pyautogui.moveTo(window_coords[0], window_coords[1], duration=0.33)
        pyautogui.mouseDown(button="left")
        time.sleep(0.33)
        pyautogui.dragTo(1300, 1000, duration=0.33)
        time.sleep(0.33)
        pyautogui.mouseUp(button="left")
        orientated = check_add_requirement_window_orientation()
    logger.log("Orientated add requirement window.")
    time.sleep(0.17)


def check_add_requirement_window_orientation():
    coords = find_add_requirement_window()
    # print(coords)
    if coords is None:
        return False
    value1 = abs(coords[0] - 1008)
    value2 = abs(coords[1] - 471)
    return value1 <= 3 and value2 <= 3


def click_fbi_button():
    check_quit_key_press()
    # logger.log("Checking whether or not the fbi button shows for the selected item.")
    fbi_coords = find_fbi_button()
    if fbi_coords is None:
        # logger.log("Found no fbi button for the selected item. Returning restart.")
        return "restart"

    # click fbi button
    check_quit_key_press()
    # logger.log("clicking fbi button for the selected item.")
    click(fbi_coords[1], fbi_coords[0])
    time.sleep(0.33)
    return "continue"


def open_add_offer_tab(logger):
    logger.log("Clicking add offer button in the top")

    # handle popups
    pyautogui.click(50, 50)
    pyautogui.press("n")

    # closing add offer window if it exists
    close_add_offer_window(logger)
    time.sleep(0.17)

    # click add offer
    check_quit_key_press()
    logger.log("Opening add offer window.")
    click(850, 85)
    time.sleep(0.17)

    # orientate add offer window
    orientate_add_offer_window(logger)

    time.sleep(3)

    # orientate add offer window
    orientate_add_offer_window(logger)


def select_random_item_to_flee(logger):
    logger.log("Selecting another random item to flea.")
    has_item_to_flee = False
    while not has_item_to_flee:
        # clicks the random item's FBI button
        # click item to flee
        check_quit_key_press()

        item_coords = find_coords_of_item_to_flee()
        if item_coords is None:
            return
        click(item_coords[0], item_coords[1])
        time.sleep(0.17)
        click(item_coords[0], item_coords[1], button="right")
        time.sleep(0.5)

        # click this item's FBI button
        if click_fbi_button() != "restart":
            logger.log("Found item to flee.")
            has_item_to_flee = True
            logger.log("Found a satisfactory item to flea.")
        else:
            logger.log(
                "This item's filter by item button was unreadable this go-around. Finding another item."
            )


def click_add_requirements_in_add_requirements_window(logger):
    check_quit_key_press()
    logger.log("Adding requirements for offer..")
    click(711, 710)
    time.sleep(0.17)


def write_post_price(logger, post_price):
    # open rouble input region
    check_quit_key_press()
    click(1162, 501)

    # write post_price
    logger.log(f"Writing price of {post_price}.")
    type_string = str(post_price)
    pyautogui.typewrite(type_string, interval=0.02)
    time.sleep(0.17)


def post_item(logger, post_price):
    orientate_add_offer_window(logger)

    click_add_requirements_in_add_requirements_window(logger)

    orientate_add_requirement_window(logger)

    write_post_price(logger, post_price)

    # click add in add requirements window
    check_quit_key_press()
    logger.log("Adding this offer.")
    click(1169, 961, clicks=2)
    time.sleep(0.17)

    # click place offer in add offer window
    click(596, 954)
    time.sleep(1)

    # handle post/purchase confirmation popup
    handle_post_confirmation_popup(logger)
    handle_purchase_confirmation_popup(logger)

    # logger stuff
    logger.add_roubles_made(post_price)
    logger.add_item_sold()

    # refresh page to see ur own offer
    pyautogui.press("f5")
    time.sleep(0.17)


def find_filters_window():
    check_quit_key_press()
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
        logger.log("Orientating filters window.")
        coords = find_filters_window()
        if coords is not None:
            pyautogui.moveTo(coords[0], coords[1], duration=0.33)
            time.sleep(0.33)
            pyautogui.dragTo(3, 3, duration=0.33)
            time.sleep(0.33)
        is_orientated = check_filters_window_orientation()
    logger.log("Orientated filters window.")


def open_filters_window(logger):
    click(328, 87)
    time.sleep(0.33)
    orientate_filters_window(logger)


def set_flea_filters(logger):  # sourcery skip: extract-duplicate-method
    logger.log("Setting the flea filters for price undercut recognition")

    # open filter window
    logger.log("Opening the filters window")
    open_filters_window(logger)
    time.sleep(0.17)

    # click currency dropdown
    logger.log("Filtering by roubles.")
    click(113, 62)
    time.sleep(0.17)

    # click RUB from dropdown
    click(124, 100)
    time.sleep(0.17)

    # click 'display offers from' dropdown
    logger.log("Filtering by player sales only.")
    click(171, 188)
    time.sleep(0.17)

    # click players from dropdown
    click(179, 250)
    time.sleep(0.17)

    # click OK
    logger.log("Clicking OK in filters tab.")
    click(83, 272)
    time.sleep(0.17)


def check_for_post_confirmation_popup():
    check_quit_key_press()
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
    check_quit_key_press()
    if check_for_post_confirmation_popup():
        logger.log("Handling post confirmation popup")
        pyautogui.click(50, 50)
        pyautogui.click(50, 50)
        pyautogui.press("n")
        time.sleep(0.33)


def check_for_purchase_confirmation_popup():
    check_quit_key_press()
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
    check_quit_key_press()
    if check_for_purchase_confirmation_popup():
        logger.log("Handling purchase confirmation popup")
        pyautogui.click(50, 50)
        pyautogui.click(50, 50)
        pyautogui.press("n")
        time.sleep(0.33)


def check_if_on_my_offers_tab():
    check_quit_key_press()
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
    check_quit_key_press()
    on_offers_tab = check_if_on_my_offers_tab()

    loops = 0
    while not on_offers_tab:
        if loops > 10:
            return "restart"
        loops = loops + 1

        click(269, 87)
        time.sleep(1)
        on_offers_tab = check_if_on_my_offers_tab()
    logger.log("On my offers tab.")


def remove_offers(logger):
    check_quit_key_press()
    for _ in range(10):
        # click red remove button
        remove_button_coords = look_for_remove_offer_button()
        if remove_button_coords is not None:
            logger.log("Removing an offer.")
            click(remove_button_coords[0], remove_button_coords[1])
            pyautogui.press("y")
            time.sleep(0.33)
        # click item filters on left to assure not systematically missing an
        # offer.
        click(174, random.randint(136, 250))
        time.sleep(0.33)
        logger.log("remove_offers alg is done.")


def get_to_flee_tab_from_my_offers_tab(logger):
    click(829, 977, clicks=2, interval=0.33)
    time.sleep(0.33)
    get_to_flee_tab(logger)


def look_for_remove_offer_button():
    # looks for red remove button in my offers tab and returns the coord
    region = [1150, 136, 90, 530]
    color_red = [185, 6, 7]
    pix_list = find_all_pixel_coords(region=region, color=color_red)

    loops = 0
    while pix_list is None:
        if loops > 10:
            return None
        loops = loops + 1
        click(x=127, y=random.randint(143, 300))
        time.sleep(1)
        pix_list = find_all_pixel_coords(region=region, color=color_red)

    return None if (pix_list is None) or (not pix_list) else pix_list[0]


def get_price_text():
    region = [909, 132, 80, 24]
    image = screenshot(region)
    text = img_to_txt(image)

    # show_image(image)
    print(f"read text: {text}")

    return text


def splice_price_text(logger, price_text):
    out_string = ""
    for digit in price_text:
        if digit.isdigit():
            out_string = out_string + digit
        if digit in ["e", "a", "o", "O", "B"]:
            out_string = f"{out_string}0"
    if len(out_string) != count_digits():
        logger.log(
            f"Price check failed. Read price: {out_string}, digits: {count_digits()}"
        )
        return "fail"
    return out_string


def get_price_2():
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
    if check_for_1_in_image(image):
        return "1"
    if check_for_2_in_image(image):
        return "2"
    if check_for_3_in_image(image):
        return "3"
    if check_for_4_in_image(image):
        return "4"
    if check_for_5_in_image(image):
        return "5"
    if check_for_6_in_image(image):
        return "6"
    if check_for_7_in_image(image):
        return "7"
    if check_for_8_in_image(image):
        return "8"
    if check_for_9_in_image(image):
        return "9"
    if check_for_0_in_image(image):
        return "0"

    return None


def check_for_1_in_image(current_image):
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


def check_for_2_in_image(current_image):
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


def check_for_3_in_image(current_image):
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


def check_for_4_in_image(current_image):
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


def check_for_5_in_image(current_image):
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


def check_for_6_in_image(current_image):
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


def check_for_7_in_image(current_image):
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


def check_for_8_in_image(current_image):
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


def check_for_9_in_image(current_image):
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


def check_for_0_in_image(current_image):
    check_quit_key_press()
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


def get_to_wishlist():
    check_quit_key_press()
    pyautogui.moveTo(164, 85)
    pyautogui.click()
    time.sleep(0.5)


def find_dorm_room_314_in_wishlist():
    check_quit_key_press()

    current_image = screenshot(region=[39, 121, 400, 600])
    reference_folder = "find_dorm_room_314_in_wishlist"
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
    ]
    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )
    coord = get_first_location(locations)
    if coord is None:
        return None

    coord = [coord[1] + 39, coord[0] + 121]
    return coord


def check_if_has_offer():
    check_quit_key_press()
    iar = numpy.asarray(screenshot())
    pix_list = [
        iar[134][605],
        iar[164][623],
        iar[139][626],
        iar[161][603],
    ]
    sentinel = [70, 70, 50]
    return any(not (pixel_is_equal(pix, sentinel, tol=50)) for pix in pix_list)


def purchase_first_offer():
    check_quit_key_press()
    pyautogui.moveTo(1193, 150)
    pyautogui.click()
    time.sleep(0.5)

    pyautogui.press("y")
    time.sleep(0.5)
