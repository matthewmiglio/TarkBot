

import random
import time

import numpy
from matplotlib import pyplot as plt


import numpy
import pyautogui

from pytarkbot.client import (calculate_avg_pixel, check_quit_key_press, click,
                              find_all_pixel_coords, find_all_pixels,
                              find_all_pixels_not_equal_to, img_to_txt, img_to_txt_numbers_only,
                              screenshot)
from pytarkbot.image_rec import (check_for_location, find_references,
                                 get_first_location, pixel_is_equal)


def get_color_list_of_current_price(image):
    # make numpy iar
    iar = numpy.asarray(image)

    #get pixel RGB list
    rgb_pix_list=[]
    y_coord=150
    for x_coord in range(907,987):
        current_pix=iar[y_coord][x_coord]
        current_pix=[current_pix[0],current_pix[1],current_pix[2]]
        rgb_pix_list.append(current_pix)
    #print(rgb_pix_list)
        
        
    #replace RGB list with english color list
    english_color_list=[]
    for rgb in rgb_pix_list:
        red_content=rgb[0]
        if (red_content>100):
            english_color_list.append("tan")
        else:
            english_color_list.append(None)
            
    return english_color_list
        

def count_digits():
    # region = [896, 126, 115, 47]
    image = screenshot()

    color_list = get_color_list_of_current_price(image)
    


    spliced_color_list=splice_color_list_for_count_digits(color_list=color_list)
    
    tan_count=0
    for color in spliced_color_list:
        if color=="tan":
            tan_count=tan_count+1
    
    return tan_count-1
    

def splice_color_list_for_count_digits(color_list):
    returnPixlist=[None]
    
    for pixel in color_list:
        if (returnPixlist[-1] is not None)and(pixel is None):
            returnPixlist.append(pixel)
        if (returnPixlist[-1]!="tan")and(pixel=="tan"):
            returnPixlist.append(pixel)
            
            
    return returnPixlist
        

def check_price_string(price_string):
    index = 0
    for element in price_string:
        # print(f"index{index}||element{element}")
        index = index + 1
        if not (
            (element == "1") or (
                element == "2") or (
                element == "3") or (
                element == "4") or (
                    element == "5") or (
                        element == "6") or (
                            element == "7") or (
                                element == "8") or (
                                    element == "9") or (
                                        element == "0")):
            return None


def adjust_price_string(price_string):
    output_string = ""
    for element in price_string:
        if (
            element == "0") or (
            element == "1") or (
            element == "2") or (
                element == "3") or (
                    element == "4") or (
                        element == "5") or (
                            element == "6") or (
                                element == "7") or (
                                    element == "8") or (
                                        element == "9"):
            output_string = output_string + element
        if (element == "s"):
            output_string = output_string + "8"
        elif (element=="o"):
            output_string = output_string + "0"
        elif (element=="@"):
            output_string = output_string + "0"

    #checks
    if len(output_string)<3:
        return None
    
    second_char_string=output_string[1]
    second_char_int=int(second_char_string)

    if second_char_string==5:
        print("Treertet")


    return output_string


def get_current_price():
    # get image
    region = [910,137,82,19]

    price_image = screenshot(region)

    # plt.imshow(numpy.asarray(price_image))
    # plt.show()

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
    if undercut_option_2 < undercut_option_1:
        return undercut_option_1
    return undercut_option_2


def get_value_to_post_item():
    price = get_current_price()

    print(f"The price the bot read is: {price}")

    return [get_price_undercut(price), price]


def find_coords_of_item_to_flee():
    region = [16,509,407,427]

    # plt.imshow(numpy.asarray(screenshot(region)))
    # plt.show()

    color_black = [20, 20, 20]
    coords_list = find_all_pixels_not_equal_to(region, color=color_black)

    # return one of the coords at random that aren't the background's black
    # color.
    coord = coords_list[random.randint(0, len(coords_list))]
    coord[0] = coord[0] + 11
    coord[1] = coord[1] + 470

    return coord


def check_first_price(logger):
    # get avg pixel across left side
    region = [904, 135, 1, 26]
    avg_pix = calculate_avg_pixel(find_all_pixels(region))
    wrong_background_color = [29, 28, 21]
    if pixel_is_equal(wrong_background_color, avg_pix, tol=5):
        logger.log(
            "Top price failed availability check. Returning false for price.")
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
    image_rec_count = len(str(detected_price))
    if (post_price is None) or (image_rec_count != digit_counter_count):
        logger.log(
            f"Error with digit check. \n Tried to post at {post_price} but found {digit_counter_count} digits.")
        return False

    if post_price is None:
        logger.log("Problem getting post_price. Returning false for price.")
        return False

    logger.log("Top price passed USD/EURO/TRADER/digit checks. Returning True")
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
        tolerance=0.99
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

    if len(euro_pixels) != 0:
        return True
    return False


def look_for_usd_symbol():
    # tells u whether or not the EURO symbol is found near the price
    region = [896, 126, 115, 48]

    usd_color = [119, 195, 118]
    euro_pixels = find_all_pixel_coords(region, usd_color, image=None)

    if len(euro_pixels) != 0:
        return True
    return False


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
        tolerance=0.99
    )

    return get_first_location(locations)


def get_to_flee_tab(logger):
    on_flee = check_if_on_flee_page()
    loops = 0
    while not (on_flee):
        if loops > 10:
            return "restart"
        loops = loops + 1

        check_quit_key_press()
        click(829, 977)
        time.sleep(2)
        on_flee = check_if_on_flee_page()


def check_if_on_flee_page():
    iar=numpy.asarray(screenshot())

    pix1=iar[984][813]
    pix2=iar[972][810]
    pix3=iar[976][883]
    pix4=iar[984][883]
    
    COLOR_TAN=[159,157,144]
    
    if not(pixel_is_equal(pix1,COLOR_TAN,tol=25)): return False
    if not(pixel_is_equal(pix2,COLOR_TAN,tol=25)): return False
    if not(pixel_is_equal(pix3,COLOR_TAN,tol=25)): return False
    if not(pixel_is_equal(pix4,COLOR_TAN,tol=25)): return False
    return True


def check_if_can_add_offer(logger):
    close_add_offer_window(logger)
    check_quit_key_press()
    # if we find pixels of this color in this region, then we can add offers
    region = [800, 75, 90, 20]
    color = [215, 209, 182]
    pix_coords = find_all_pixel_coords(region, color, tol=25)

    if (pix_coords is not None) and (pix_coords != []):
        return True
    return False


def close_add_offer_window(logger):
    #logger.log("Closing add offer window.")
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
        tolerance=0.99
    )

    coords = get_first_location(locations)
    if coords is None:
        return None
    return [coords[1], coords[0] - 13]


def wait_till_can_add_another_offer(logger):
    logger.log("Starting wait for another offer")
    has_another_offer=check_if_can_add_offer(logger)
    loops=0
    while not(has_another_offer):
        if loops>120:
            return "remove_flee_offers"
        
        loops=loops+1
        if (loops % 2 == 0): print(f"Waiting for another offer: {loops}")
        
        close_add_offer_window(logger)
        time.sleep(1)
        
        pyautogui.press('f5')
        time.sleep(1)
        
        get_to_flee_tab(logger)
        
        
        has_another_offer=check_if_can_add_offer(logger)
        
    logger.log("Done waiting for another offer.")
        

def orientate_add_offer_window(logger):
    check_quit_key_press()
    orientated = check_add_offer_window_orientation()
    loops = 0
    while not (orientated):
        #logger.log(f"Orientating add offer window: {loops}.")
        if loops > 10:
            return "restart"
        loops = loops + 1
        check_quit_key_press()
        coords = find_add_offer_window()
        if coords is None:
            #logger.log("Trouble orientating add offer window. Restarting.")
            return "restart"
        pyautogui.moveTo(coords[0], coords[1], duration=0.4)
        time.sleep(1)
        pyautogui.dragTo(0, 980, duration=0.33)
        orientated = check_add_offer_window_orientation()
    logger.log("Orientated add offer window.")
    time.sleep(0.17)


def check_add_offer_window_orientation():
    iar = numpy.asarray(screenshot())

    pix1 = iar[485][24]
    pix2 = iar[485][33]
    pix3 = iar[491][34]
    pix4 = iar[492][42]

    pix5 = iar[492][23]
    pix6 = iar[490][30]
    pix7 = iar[490][48]
    pix8 = iar[487][61]

    if not(pixel_is_equal(pix1,[143, 141,129],tol=25)): return False
    if not(pixel_is_equal(pix2, [143 ,141 ,129],tol=25)): return False
    if not(pixel_is_equal(pix3,[0 ,0, 0],tol=25)): return False
    if not(pixel_is_equal(pix4,[137 ,136 ,124],tol=25)): return False
    
    if not(pixel_is_equal(pix5,[0, 0, 0],tol=25)): return False
    if not(pixel_is_equal(pix6,[0 ,0, 0],tol=25)): return False
    if not(pixel_is_equal(pix7,[0, 0, 0],tol=25)): return False
    if not(pixel_is_equal(pix8,[0, 0 ,0],tol=25)): return False
    
    return True
    


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
        tolerance=0.99
    )

    coords = get_first_location(locations)
    if coords is None:
        return None
    return [coords[1], coords[0]]


def orientate_add_requirement_window(logger):
    orientated = check_add_requirement_window_orientation()
    loops = 0
    while not (orientated):
        logger.log(f"Orientating add requirement window {loops}")
        loops = loops + 1
        window_coords = find_add_requirement_window()
        if window_coords is None:
            logger.log(
                "Trouble orientating add requirement window. Restarting.")
            return "restart"
        window_coords=[window_coords[0]+10,window_coords[1]]
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
    iar = numpy.asarray(screenshot())

    pix1 = iar[476][1009]
    pix3 = iar[473][1021]
    pix4 = iar[476][1030]

    pix5 = iar[475][1027]
    pix6 = iar[476][1006]
    pix7 = iar[475][1100]
    pix8 = iar[476][1126]

    if not(pixel_is_equal(pix1,[130 ,138 ,142],tol=15)): return False
    if not(pixel_is_equal(pix3,[162 ,171 ,177],tol=15)): return False
    if not(pixel_is_equal(pix4,[116 ,122, 125],tol=15)): return False
    
    if not(pixel_is_equal(pix5,[25 ,27 ,27],tol=15)): return False
    if not(pixel_is_equal(pix6,[25 ,27, 27],tol=15)): return False
    if not(pixel_is_equal(pix7,[25, 27 ,27],tol=15)): return False
    if not(pixel_is_equal(pix8,[25, 27, 27],tol=15)): return False
    
    return True


def click_fbi_button():
    check_quit_key_press()
    #logger.log("Checking whether or not the fbi button shows for the selected item.")
    fbi_coords = find_fbi_button()
    if fbi_coords is None:
        #logger.log("Found no fbi button for the selected item. Returning restart.")
        return "restart"

    # click fbi button
    check_quit_key_press()
    #logger.log("clicking fbi button for the selected item.")
    click(fbi_coords[1], fbi_coords[0])
    time.sleep(0.33)


def open_add_offer_tab(logger):
    # handle popups
    pyautogui.click(50,50)
    pyautogui.press('n')

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
    has_item_to_flee = False
    while not (has_item_to_flee):
        # clicks the random item's FBI button
        # click item to flee
        check_quit_key_press()

        item_coords = find_coords_of_item_to_flee()
        click(item_coords[0], item_coords[1])
        time.sleep(0.17)
        click(item_coords[0], item_coords[1], button="right")
        time.sleep(0.5)

        # click this item's FBI button
        if click_fbi_button() != "restart":
            logger.log('Found item to flee.')
            has_item_to_flee = True


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
    pyautogui.press('f5')
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
        tolerance=0.99
    )

    coords = get_first_location(locations)
    if coords is None:
        return None
    return [coords[1] + 3, coords[0] + 3]


def check_filters_window_orientation():
    iar = numpy.asarray(screenshot())

    pix1 = iar[35][25]
    pix2 = iar[168][78]
    pix4 = iar[168][78]

    pix5 = iar[37][77]
    pix6 = iar[52][62]
    pix7 = iar[36][70]
    pix8 = iar[189][230]

    
    
    if not(pixel_is_equal(pix1,[90, 96, 98],tol=20)): return False
    if not(pixel_is_equal(pix2,[224, 223, 211],tol=20)): return False
    if not(pixel_is_equal(pix4,[224, 223, 211],tol=20)): return False
    
    if not(pixel_is_equal(pix5,[26, 28, 28],tol=20)): return False
    if not(pixel_is_equal(pix6,[1, 1, 1],tol=20)): return False
    if not(pixel_is_equal(pix7,[27, 29, 29],tol=20)): return False
    if not(pixel_is_equal(pix8,[3, 3 ,1],tol=20)): return False
    
    return True
    

def orientate_filters_window(logger):
    is_orientated = check_filters_window_orientation()
    while not (is_orientated):
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


def set_flea_filters(logger):
    logger.log("Filtering by roubles")

    # open filter window
    open_filters_window(logger)
    time.sleep(0.17)

    # click currency dropdown
    click(113, 62)
    time.sleep(0.17)

    # click RUB from dropdown
    click(124, 100)
    time.sleep(0.17)

    # click 'display offers from' dropdown
    click(171, 188)
    time.sleep(0.17)

    # click players from dropdown
    click(179, 250)
    time.sleep(0.17)

    # click OK
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
        tolerance=0.99
    )

    return check_for_location(locations)


def handle_post_confirmation_popup(logger):
    if check_for_post_confirmation_popup():
        logger.log("Handling post confirmation popup")
        pyautogui.click(50,50)
        pyautogui.click(50,50)
        pyautogui.press('n')
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
        tolerance=0.99
    )

    return check_for_location(locations)


def handle_purchase_confirmation_popup(logger):
    if check_for_purchase_confirmation_popup():
        logger.log("Handling purchase confirmation popup")
        pyautogui.click(50, 50)
        pyautogui.click(50,50)
        pyautogui.press('n')
        time.sleep(0.33)


def check_if_on_my_offers_tab():
    iar = numpy.asarray(screenshot())

    pix1 = iar[77][255]
    pix2 = iar[94][251]
    pix3 = iar[82][309]

    pixel_totals = []
    pixel_totals.append(int(pix1[0]) + int(pix1[1]) + int(pix1[2]))
    pixel_totals.append(int(pix2[0]) + int(pix2[1]) + int(pix2[2]))
    pixel_totals.append(int(pix3[0]) + int(pix3[1]) + int(pix3[2]))

    for total in pixel_totals:
        if total < 500:
            return False
    return True


def get_to_my_offers_tab(logger):
    on_offers_tab = check_if_on_my_offers_tab()

    loops = 0
    while not (on_offers_tab):
        if loops > 10:
            return "restart"
        loops = loops + 1

        click(269, 87)
        time.sleep(1)
        on_offers_tab = check_if_on_my_offers_tab()
    logger.log("On my offers tab.")


def remove_offers(logger):
    # starts on my offers tab
    # removes all your offers that you've posted. Usually all of them.

    loops = 0
    while loops < 10:
        # incremenet
        loops = loops + 1
        # click red remove button
        remove_button_coords = look_for_remove_offer_button()
        if remove_button_coords is not None:
            logger.log("Removing an offer.")
            click(remove_button_coords[0], remove_button_coords[1])
            pyautogui.press('y')
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
            return
        loops = loops + 1
        click(x=127, y=random.randint(143, 300))
        time.sleep(1)
        pix_list = find_all_pixel_coords(region=region, color=color_red)

    if (pix_list is None) or (pix_list == []):
        return None
    return pix_list[0]
