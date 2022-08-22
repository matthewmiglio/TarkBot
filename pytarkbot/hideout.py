from distutils.command.install_egg_info import to_filename
import time

import numpy
import pyautogui
from matplotlib import pyplot as plt

from pytarkbot.client import (check_quit_key_press, click,
                              find_all_pixel_coords, img_to_txt, screenshot, string_to_chars_only)
from pytarkbot.image_rec import (check_for_location, find_references,
                                 get_first_location, pixel_is_equal)

blank_line = "//////////////////////////////////////////////////////////////////"

# navigation


def get_to_hideout(logger):
    check_quit_key_press()
    logger.log("Getting to hideout")
    at_hideout = check_if_in_hideout()
    loops = 0
    while not (at_hideout):
        if loops > 7:
            logger.log("Bot had issues getting to hideout. Restarting.")
            return "restart"
        loops = loops + 1

        click(143, 979)
        pyautogui.moveTo(99, 99, duration=0.33)
        time.sleep(6.33)
        at_hideout = check_if_in_hideout()
    logger.log("At hideout.")
    time.sleep(0.33)
    logger.log("Opening hideout interface at bottom of screen.")
    open_hideout_interface()


def open_hideout_interface():
    check_quit_key_press()
    pyautogui.click(800, 934)


def scroll_left_in_hideout():
    check_quit_key_press()
    pyautogui.click(38, 934)


def scroll_right_in_hideout():
    check_quit_key_press()
    pyautogui.click(1255, 934)


# general hideout
def manage_hideout(logger, crafts_to_farm):
    check_quit_key_press()
    logger.log(blank_line)
    logger.log(blank_line)
    logger.log("Hideout management mode.")
    logger.log(blank_line)
    logger.log(blank_line)

    if get_to_hideout(logger) == "restart":
        return "restart"

    while True:
        check_quit_key_press()

        print(crafts_to_farm)

        if "medstation" in crafts_to_farm:
            logger.log("Starting medstation management")
            manage_medstation(logger)
            time.sleep(4)

        if "booze_generator" in crafts_to_farm:
            logger.log("Starting booze generator management")
            manage_booze_generator(logger)
            time.sleep(4)

        if "workbench" in crafts_to_farm:
            logger.log("Starting workbench management")
            manage_workbench(logger)
            time.sleep(4)

        if "water_collector" in crafts_to_farm:
            logger.log("Starting water collector management")
            manage_water_collector(logger)
            time.sleep(4)

        if "scav_case" in crafts_to_farm:
            logger.log("Starting scav case management")
            manage_scav_case(logger)
            time.sleep(4)

        if "lavatory" in crafts_to_farm:
            logger.log("Starting lavatory management")
            manage_lavatory(logger)
            time.sleep(4)

        logger.add_hideout_rotation()


def check_if_in_hideout():
    check_quit_key_press()
    iar = numpy.asarray(screenshot())
    pix1 = iar[986][114]
    pix2 = iar[980][180]

    color_true = [159, 157, 144]
    color_false = [15, 14, 14]

    if not (pixel_is_equal(pix1, color_true, tol=25)):
        return False
    if not (pixel_is_equal(pix2, color_true, tol=25)):
        return False
    if pixel_is_equal(pix1, color_false, tol=25):
        return False
    if pixel_is_equal(pix2, color_false, tol=25):
        return False
    return True


def reset_station(logger):
    check_quit_key_press()
    pyautogui.press('esc')
    time.sleep(0.33)
    pyautogui.press('esc')
    get_to_hideout(logger)
    open_hideout_interface()


# checking if currently at the right station
def check_if_at_booze_generator():
    region=[700,516,200,30]
    image=screenshot(region)
    text=img_to_txt(image)
    if text.startswith('Boo'):
        return True
    return False


def check_if_at_water_collector():
    region=[698,494,189,26]
    image=screenshot(region)
    text=img_to_txt(image)
    if text.startswith('Wat'):
        return True
    return False

def check_if_at_lavatory():
    region=[698,338,117,31]
    image=screenshot(region)
    text=img_to_txt(image)
    if text.startswith('Lava'):
        return True
    return False

def check_if_at_nutrition_unit():
    region=[698,340,170,26]
    image=screenshot(region)
    text=img_to_txt(image)
    if text.startswith('Nutr'):
        return True
    return False


def check_if_at_workbench():
    region=[698,341,138,26]
    image=screenshot(region)
    text=img_to_txt(image)
    if text.startswith('Workb'):
        return True
    return False


def check_if_at_intelligence_center():
    region=[698,340,229,29]
    image=screenshot(region)
    text=img_to_txt(image)
    if text.startswith('Intell'):
        return True
    return False

def check_if_at_medstation():
    region=[698,340,229,29]
    image=screenshot(region)
    text=img_to_txt(image)
    if text.startswith('Meds'):
        return True
    return False
        
    

def check_if_at_scav_case():
    region=[700,357,123,27]
    image=screenshot(region)
    text=img_to_txt(image)
    if text.startswith("Scav"):
        return True
    return False


def check_if_at_lavatory():
    region=[698,341,120,30]
    image=screenshot(region)
    text=img_to_txt(image)
    if text.startswith("Lava"):
        return True


# move to each station
def get_to_water_collector(logger):
    check_quit_key_press()
    open_hideout_interface()

    at_location = check_if_at_water_collector()
    while not (at_location):
        scroll_left_in_hideout()
        time.sleep(4)
        at_location = check_if_at_water_collector()
    logger.log("Made it to water collector.")


def get_to_lavatory(logger):
    check_quit_key_press()
    open_hideout_interface()

    at_location = check_if_at_lavatory()
    while not (at_location):
        scroll_left_in_hideout()
        time.sleep(4)
        at_location = check_if_at_lavatory()
    logger.log("Made it to lavatory")


def get_to_booze_generator(logger):
    check_quit_key_press()
    logger.log("Getting to booze generator")
    open_hideout_interface()

    at_location = check_if_at_booze_generator()
    while not (at_location):
        scroll_left_in_hideout()
        time.sleep(5)
        at_location = check_if_at_booze_generator()
    logger.log("Made it to booze_generator.")


def get_to_nutrition_unit(logger):
    check_quit_key_press()
    open_hideout_interface()

    at_location = check_if_at_nutrition_unit()
    while not (at_location):
        scroll_left_in_hideout()
        time.sleep(4)
        at_location = check_if_at_nutrition_unit()
    logger.log("Made it to nutrition_unit")


def get_to_workbench(logger):
    check_quit_key_press()
    open_hideout_interface()

    at_location = check_if_at_workbench()
    while not (at_location):
        scroll_left_in_hideout()
        time.sleep(4)
        at_location = check_if_at_workbench()
    logger.log("Made it to workbench")


def get_to_intelligence_center(logger):
    check_quit_key_press()
    open_hideout_interface()

    at_location = check_if_at_intelligence_center()
    while not (at_location):
        scroll_left_in_hideout()
        time.sleep(4)
        at_location = check_if_at_intelligence_center()
    logger.log("Made it to intelligence_center")


def get_to_medstation(logger):
    check_quit_key_press()
    open_hideout_interface()

    at_location = check_if_at_medstation()
    while not (at_location):
        scroll_left_in_hideout()
        time.sleep(4)
        at_location = check_if_at_medstation()
    logger.log("Made it to medstation")


def get_to_scav_case(logger):
    check_quit_key_press()
    open_hideout_interface()

    at_location = check_if_at_scav_case()
    while not (at_location):
        scroll_left_in_hideout()
        time.sleep(4)
        at_location = check_if_at_scav_case()
    logger.log("Made it to scav_case.")


def get_to_lavatory(logger):
    check_quit_key_press()
    open_hideout_interface()

    at_location = check_if_at_lavatory()
    while not (at_location):
        scroll_left_in_hideout()
        time.sleep(4)
        at_location = check_if_at_lavatory()
    logger.log("Made it to lavatory")

# booze generator station
def manage_booze_generator(logger):
    check_quit_key_press()
    logger.log("")
    logger.log("Managing booze_generator craft.")
    logger.log("")

    #logger.log("Getting to booze generator.")
    get_to_hideout(logger)

    get_to_booze_generator(logger)

    time.sleep(3)

    logger.log("Checking state of booze generator.")
    state = check_booze_generator()
    logger.log(f"Booze generator state: {state}")

    if state == "start":
        logger.log("Starting moonshine craft.")
        start_moonshine_craft(logger)
        time.sleep(3)
    if state == "get items":
        logger.add_craft_completed()
        logger.log("Collecting items.")
        click(1070, 795)
        time.sleep(3)
        reset_station()

def check_booze_generator():
    check_quit_key_press()
    # get image1
    region1 = [1010, 780, 120, 50]
    image1 = screenshot(region1)
    text1 = img_to_txt(image1)
    if text1.startswith("GET"):
        return "get items"
    if text1.startswith("START"):
        return "start"

    # get image2
    region2 = [1020, 745, 85, 40]
    image2 = screenshot(region2)
    text2 = img_to_txt(image2)
    if text2.startswith("GET"):
        return "get items"
    if text2.startswith("START"):
        return "start"


def find_start_symbol_in_booze_generator():
    check_quit_key_press()
    current_image = screenshot()
    reference_folder = "booze_generator_start_icon"
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
    coords = get_first_location(locations)
    return [coords[1], coords[0]]


def start_moonshine_craft(logger):
    check_quit_key_press()
    start_coords = find_start_symbol_in_booze_generator()
    if start_coords is None:
        logger.log(
            "Start button coords weren't found so start craft alg cannot continue.")
        return

    click(start_coords[0], start_coords[1])
    time.sleep(0.5)

    click(647, 674)
    time.sleep(0.5)

    logger.log("Started moonshine craft.")
    reset_station(logger)


# workbench
def manage_workbench(logger):
    check_quit_key_press()
    logger.log("")
    logger.log("Managing workbench crafts.")
    logger.log("")

    logger.log("Getting to workbench")
    get_to_hideout(logger)
    get_to_workbench(logger)

    logger.log("Checking workbench state.")
    if check_for_workbench_producing_icon():
        state = "Producing"
    else:
        state = check_workbench(logger)

    logger.log(f"Workbench state is {state}")

    if state == "start":
        start_green_gunpowder_craft_in_workbench(logger)
    if state == "Get items":
        logger.add_craft_completed()
        get_items_from_workbench()

    reset_station(logger)


def start_green_gunpowder_craft_in_workbench(logger):
    check_quit_key_press()
    logger.log("Starting green gunpowder craft.")
    # click first start
    click_green_gunpowder_start_icon(logger)

    # click handover
    click(650, 675)
    time.sleep(1)
    logger.log("Started craft for green_gunpowder.")
    reset_station(logger)


def get_items_from_workbench():
    check_quit_key_press()
    coords = find_green_gunpowerder_icon_in_workbench()
    get_items_coord = [coords[0] + 80, coords[1] + 25]
    click(get_items_coord[0], get_items_coord[1])


def check_workbench(logger):
    check_quit_key_press()
    # get to green gunpowder craft
    get_to_green_gunpowder_craft(logger)

    if check_for_get_items_in_workbench():
        return "Get items"
    if check_for_start_in_workbench():
        return "start"
   

def check_for_start_in_workbench():
    green_gunpowder_coords=find_green_gunpowerder_icon_in_workbench()
    region=[green_gunpowder_coords[0]+76,green_gunpowder_coords[1]+14,40,15]
    
    image=screenshot(region)
    text = img_to_txt(image)
    
    # print(text)
    # plt.imshow(numpy.asarray(image))
    # plt.show()
    
    if text.startswith("START"): return True
    if text.startswith("start"): return True
    return False


def check_for_get_items_in_workbench():
    green_gunpowder_coords=find_green_gunpowerder_icon_in_workbench()
    region=[green_gunpowder_coords[0]+50,green_gunpowder_coords[1]+2,80,20]
    
    
    image=screenshot(region)
    text = img_to_txt(image)
    
    # print(text)
    # plt.imshow(numpy.asarray(image))
    # plt.show()
    
    if text.startswith("GET"): return True
    if text.startswith("get"): return True
    return False
    


def check_for_workbench_producing_icon():
    check_quit_key_press()
    current_image = screenshot()
    reference_folder = "check_for_workbench_producing_icon"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )
    return check_for_location(locations)


def find_green_gunpowerder_icon_in_workbench():
    region = [970, 385, 230, 465]
    current_image = screenshot(region)

    # plt.imshow(numpy.asarray(current_image))
    # plt.show()

    reference_folder = "find_green_gunpowerder_icon_in_workbench"
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

    coord = get_first_location(locations)
    if coord is None:
        return None
    return [coord[1] + 970, coord[0] + 385]


def get_image_of_green_gunpowder_surroundings():
    coord = find_green_gunpowerder_icon_in_workbench()
    region = [coord[0] + 55, coord[1] - 20, 75, 60]

    green_gunpowder_image = screenshot(region)

    # plt.imshow(numpy.asarray(image))
    # plt.show()

    return green_gunpowder_image


def get_to_green_gunpowder_craft(logger):
    check_quit_key_press()
    logger.log("Getting to green gunpowder craft.")
    at_green_gunpowder_craft = False
    if find_green_gunpowerder_icon_in_workbench() is not None:
        at_green_gunpowder_craft = True
    loops = 0
    while not (at_green_gunpowder_craft):
        if loops > 50:
            logger.log("Had issues finding green gunpowder. Returning")
            return "restart"
        loops = loops + 1
        check_quit_key_press()
        click(900, 700)
        pyautogui.scroll(-400)
        time.sleep(1)
        if find_green_gunpowerder_icon_in_workbench() is not None:
            at_green_gunpowder_craft = True
    logger.log("Found green gunpowder craft in workbench.")


def click_green_gunpowder_start_icon(logger):
    logger.log("Looking for green gunpowder's start icon.")
    green_gunpowder_coords = find_green_gunpowerder_icon_in_workbench()
    x_coord_range = range(
        green_gunpowder_coords[0] + 50,
        green_gunpowder_coords[0] + 150)
    y_coord = green_gunpowder_coords[1] + 15
    iar = numpy.asarray(screenshot())
    color_tan = [158, 156, 144]
    for x_coord in x_coord_range:
        current_pix = iar[y_coord][x_coord]
        current_coord = [x_coord, y_coord]
        if pixel_is_equal(current_pix, color_tan, tol=50):
            click(current_coord[0], current_coord[1])
            logger.log("Clicking green gunpowder start icon.")


# water collector
def manage_water_collector(logger):
    check_quit_key_press()
    logger.log("")
    logger.log("Managing water_collector craft.")
    logger.log("")

    logger.log("Getting to water_collector")
    get_to_hideout(logger)
    get_to_water_collector(logger)

    logger.log("Checking water_collector state.")
    state = check_water_collector()

    logger.log(f"State of water collector: {state}")

    if state == "add filter":
        logger.log("Adding filter to water collector.")
        add_filter_to_water_collector()

    if state == "collect":
        click(1060, 790)
        time.sleep(1)
        logger.add_craft_completed()

    reset_station(logger)


def check_water_collector():
    if not (check_if_water_collector_has_filter()):
        return "add filter"
    if check_for_water_collector_producing_icon():
        return "producing"
    if check_for_water_collector_collect_icon():
        return "collect"


def check_if_water_collector_has_filter():
    iar = numpy.asarray(screenshot())
    pix = iar[795][844]

    color_black = [22, 22, 23]
    color_blue = [122, 214, 254]

    if pixel_is_equal(pix, color_black, tol=50):
        return False
    if pixel_is_equal(pix, color_blue, tol=50):
        return True


def check_for_water_collector_producing_icon():
    current_image = screenshot()
    reference_folder = "check_for_water_collector_producing_icon"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )
    return check_for_location(locations)


def check_for_water_collector_collect_icon():
    region = [1008, 782, 80, 20]
    image = screenshot(region)
    
    # plt.imshow(numpy.asarray(image))
    # plt.show()
    
    text = img_to_txt(image)
    
    # print(text)
    
    if text.startswith("GET"):
        return True
    return False


def add_filter_to_water_collector():
    #click dropdown coord to show filters on standby
    dropdown_arrow_coord=[927,791]
    pyautogui.moveTo(dropdown_arrow_coord[0],dropdown_arrow_coord[1],duration=0.2)
    time.sleep(1)
    pyautogui.click()
    time.sleep(1)
    
    #click next filter
    click(971,797)
    time.sleep(1)
    
    
    

def find_add_filter_dropdown_arrow_in_water_collector():
    region = [910, 773, 35, 50]
    current_image = screenshot(region)
    reference_folder = "find_add_filter_dropdown_arrow_in_water_collector"
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
    coord = get_first_location(locations)
    if coord is None:
        return None
    return [coord[1] + 910, coord[0] + 773]


def find_water_filter_in_dropdown_in_water_collector():
    region = [825, 734, 328, 197]
    color_blue = [123, 219, 255]

    coords_list = find_all_pixel_coords(region=region, color=color_blue)

    if len(coords_list) == 0:
        return None
    return coords_list[0]


# scav case
def manage_scav_case(logger):
    check_quit_key_press()
    logger.log("")
    logger.log("Managing scav_case craft.")
    logger.log("")

    logger.log("Getting to scav_case")
    get_to_hideout(logger)
    get_to_scav_case(logger)

    logger.log("Checking scav_case state.")
    state = check_scav_case()

    logger.log(f"Scav case state is: {state}")

    if state == "get items":
        collect_scav_case()
        logger.add_craft_completed()
    if state == "start":
        start_scav_case()

    logger.log("Done managing scav case.")

    reset_station(logger)


def check_scav_case():
    region = [1006, 711, 90, 35]
    image = screenshot(region)
    text = img_to_txt(image)

    if text.startswith("GET"):
        return "get items"
    if check_for_scav_case_progress():
        return "collecting"
    return "start"


def collect_scav_case():
    # click get items
    click(1055, 729)
    time.sleep(0.33)

    # click recieve
    coords = find_receive_icon_in_scav_case()
    if coords is not None:
        click(coords[0], coords[1])
    time.sleep(0.33)


def find_receive_icon_in_scav_case():
    current_image = screenshot()
    reference_folder = "find_receive_icon_in_scav_case"
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
    coord = get_first_location(locations)
    return [coord[1], coord[0]]


def start_scav_case():
    click(1050, 730)
    time.sleep(1)


def check_for_scav_case_progress():
    current_image = screenshot()
    reference_folder = "check_for_scav_case_progress"
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
        tolerance=0.99
    )
    truth= check_for_location(locations)
    
    region=[1022,673,58,12]
    image=screenshot(region)
    text=img_to_txt(image)
    print(text)
    if text.startswith("Coll"):
        truth = True

    return truth


# medstation
def manage_medstation(logger):
    logger.log("Managing medstation")

    get_to_hideout(logger)
    get_to_medstation(logger)

    state = check_state_of_medstation()

    logger.log(f"State of medstation is: {state}")

    if state == "start":
        logger.log("Starting the craft for pile of meds in the medstation.")
        start_pile_of_meds_craft_in_medstation()

    if state == "get items":
        logger.log("Getting pile of meds craft from medstation.")
        collect_pile_of_meds_craft_from_medstation()
        logger.add_craft_completed()


def collect_pile_of_meds_craft_from_medstation():
    # click first start button
    coords = find_pile_of_meds_icon()
    get_items_coord = [coords[0] + 75, coords[1] + 30]
    click(get_items_coord[0], get_items_coord[1]-20)
    time.sleep(1.0)


def start_pile_of_meds_craft_in_medstation():
    # click first start button
    coords = find_pile_of_meds_icon()
    start_button_coord = [coords[0] + 75, coords[1] + 20]
    click(start_button_coord[0], start_button_coord[1])
    time.sleep(1.0)

    # click handover button
    click(644, 674)
    time.sleep(0.33)


def check_if_medstation_is_producing():
    check_quit_key_press()
    current_image = screenshot()
    reference_folder = "check_if_medstation_is_producing"
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


def get_to_pile_of_meds_craft_in_medstation():
    at_pile_of_meds = False
    if find_pile_of_meds_icon() is not None:
        at_pile_of_meds = True

    while not (at_pile_of_meds):
        pyautogui.click(700, 700)
        pyautogui.scroll(-400)
        time.sleep(0.22)
        if find_pile_of_meds_icon() is not None:
            at_pile_of_meds = True

    pyautogui.click(700, 700)
    pyautogui.scroll(-400)

def find_pile_of_meds_icon():
    region = [972, 387, 75, 557]
    check_quit_key_press()
    current_image = screenshot(region)
    
    # plt.imshow(numpy.asarray(current_image))
    # plt.show()
    
    
    reference_folder = "find_pile_of_meds_icon"
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
        
        

    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )
    coord = get_first_location(locations)
    if coord is None:
        return None
    return [coord[1] + 972, coord[0] + 387]


def check_state_of_medstation():
    if check_if_medstation_is_producing():
        return "producing"

    get_to_pile_of_meds_craft_in_medstation()
    image = get_image_of_pile_of_meds_craft_in_medstation()
    text=img_to_txt(image)
    
    # print(text)
    # plt.imshow(numpy.asanyarray(image))
    # plt.show()
    
    
    if image is None:
        return

    if text.startswith("STAR"):
        return "start"

    if text.startswith("GET"):
        return "get items"


def get_image_of_pile_of_meds_craft_in_medstation():
    pile_of_meds_coords = find_pile_of_meds_icon()
    if pile_of_meds_coords is None:
        return
    region = [
        pile_of_meds_coords[0] +
        40,
        pile_of_meds_coords[1] -
        20,
        140,
        70]

    return screenshot(region)



#lavatory
def manage_lavatory(logger):
    logger.log("Managing lavatory")

    get_to_hideout(logger)
    get_to_lavatory(logger)
    
    state=check_lavatory()
    logger.log(f"Lavatory state: {state}")
    
    if state=="start":
        buy_slings_for_cordura_craft(logger)
        
        start_cordura_craft_in_hideout()
    if state=="get items":
        coords=find_cordura_craft_in_lavatory()
        click(coords[0],coords[1],clicks=3,interval=0.2)
    reset_station(logger)
    
    
def find_cordura_craft_in_lavatory():
    region = [845,313,50,520]
    check_quit_key_press()
    current_image = screenshot(region)
    reference_folder = "find_cordura_craft_in_lavatory"
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
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )
    coord = get_first_location(locations)
    if coord is None:
        return None
    return [coord[1]+1045, coord[0]+323]


def get_to_cordura_craft_in_lavatory():
    at_craft=False
    if find_cordura_craft_in_lavatory() is not None: at_craft=True
    
    while not(at_craft):
        pyautogui.click(700, 700)
        pyautogui.scroll(-400)
        time.sleep(0.33)
        if find_cordura_craft_in_lavatory() is not None: at_craft=True
        
        
def check_lavatory():
    ###first check if lavatory is producing
    if check_if_lavatory_is_producing():
        return "producing"
    
    get_to_cordura_craft_in_lavatory()
    time.sleep(0.33)
    
    craft_coords=find_cordura_craft_in_lavatory()
    region=[craft_coords[0]-20,craft_coords[1]-10,100,30]
    image=screenshot(region)
    
    # plt.imshow(numpy.asarray(image))
    # plt.show()
    
    
    text=img_to_txt(image)
    print(text)
    
    if (text.startswith("STA"))or(text.startswith("sta"))or(text.startswith("SO")):
        return "start"
    
    if (text.startswith("GE"))or(text.startswith("ge"))or(text.startswith("Ge")):
        return "get items"
    
    
def check_if_lavatory_is_producing():
    region=[831,345,80,16]
    image=screenshot(region)
    text=img_to_txt(image)
    
    if (text.startswith("Pro"))or(text.startswith("pro")):
        return True
    return False

    
def start_cordura_craft_in_hideout():
    #click start
    coord=find_cordura_craft_in_lavatory()
    pyautogui.moveTo(coord[0],coord[1],duration=0.2)
    time.sleep(0.2)
    pyautogui.click()
    time.sleep(0.33)
    
    #click handover
    click(640,674)
    time.sleep(0.33)
    
        
def buy_slings_for_cordura_craft(logger):
    #start method when you can see the craft in the lavatory
    logger.log("Buying 4 slings for cordura craft.")
    
    #right click sling
    logger.log("Getting to filter by item of sling bags")
    sling_coords=find_sling_in_lavatory_craft_menu()
    pyautogui.moveTo(sling_coords[0],sling_coords[1],duration=0.2)
    time.sleep(0.33)
    pyautogui.click(button='right')
    time.sleep(1)
    
    #click FBI button for sling
    pyautogui.moveRel(20,22)
    time.sleep(0.22)
    pyautogui.click()
    time.sleep(2)
    
    #set filters to ragman only 
    set_filters_to_only_ragman()
    time.sleep(2)
    
    #click purchase
    click(1197,150)
    time.sleep(0.33)    
    
    #set buy to 4 and buy 4
    click(693,475)
    time.sleep(0.33)
    pyautogui.press('4')
    time.sleep(0.33)
    pyautogui.press('y')
    time.sleep(1)
    
    #get back to lavatory
    pyautogui.press('esc')
    time.sleep(1)
    
    #get back to cordura
    get_to_cordura_craft_in_lavatory()
    time.sleep(1)
    

def find_sling_in_lavatory_craft_menu():
    region = [845,313,50,520]
    check_quit_key_press()
    current_image = screenshot(region)
    reference_folder = "find_cordura_craft_in_lavatory"
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
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )
    coord = get_first_location(locations)
    if coord is None:
        return None
    return [coord[1]+845, coord[0]+313]

        
def set_filters_to_only_ragman():
    #open filter cog button
    click(326,87)
    time.sleep(1)
    
    #open+orientate filters window
    coord=find_filters_window_for_sling_purchase()
    pyautogui.moveTo(coord[0],coord[1],duration=0.2)
    
    #click 'Display offers from' dropdown
    display_offers_from_coord=[coord[0]+120,coord[1]+150]
    click(display_offers_from_coord[0],display_offers_from_coord[1],duration=0.2)
    time.sleep(1)
    
    #click traders
    traders_coord=[coord[0]+120,coord[1]+190]
    click(traders_coord[0],traders_coord[1],duration=0.2)
    time.sleep(1)
    
    #click OK
    ok_coord=[coord[0]+60,coord[1]+237]
    click(ok_coord[0],ok_coord[1],duration=0.2)
    time.sleep(1)
    
   
def find_filters_window_for_sling_purchase():
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

