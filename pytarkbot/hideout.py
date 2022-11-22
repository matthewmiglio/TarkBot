import time

import numpy
import pyautogui
from matplotlib import pyplot as plt

from pytarkbot.client import (check_quit_key_press, click,
                              find_all_pixel_coords, img_to_txt, screenshot,
                              show_image)
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

    logger.log("Entering cyclical hideout interface mode.")
    open_hideout_interface()
    time.sleep(2)

    while True:
        check_quit_key_press()

        #what station is this
        this_station_name=check_this_station_name(logger)

        logger.log(f"This station is: {this_station_name}")

        #if we're at medstation and medstation is selected in crafts to farm...
        if (this_station_name=="medstation")and("medstation" in crafts_to_farm):
            logger.log("Starting medstation management")
            manage_medstation(logger)
            time.sleep(4)

        #if we're at lavatory and lavatory is selected in crafts to farm...
        if (this_station_name=="lavatory")and("lavatory" in crafts_to_farm):
            logger.log("Starting lavatory management")
            manage_lavatory(logger)
            time.sleep(4)

        #if we're at workbench and workbench is selected in crafts to farm...
        if (this_station_name=="workbench")and("workbench" in crafts_to_farm):
            logger.log("Starting workbench management")
            manage_workbench(logger)
            time.sleep(4)

        #if we're at water_collector and water_collector is selected in crafts to farm...
        if (this_station_name=="water_collector")and("water_collector" in crafts_to_farm):
            logger.log("Starting water_collector management")
            manage_water_collector(logger)
            time.sleep(4)

        #if we're at scav_case and scav_case is selected in crafts to farm...
        if (this_station_name=="scav_case")and("scav_case" in crafts_to_farm):
            logger.log("Starting scav_case management")
            manage_scav_case(logger)
            time.sleep(4)


        scroll_left_in_hideout()
        time.sleep(3)


def check_if_in_hideout():
    check_quit_key_press()
    iar = numpy.asarray(screenshot())
    pix1 = iar[986][114]
    pix2 = iar[980][180]

    color_true = [159, 157, 144]
    if not (pixel_is_equal(pix1, color_true, tol=25)):
        return False
    if not (pixel_is_equal(pix2, color_true, tol=25)):
        return False
    color_false = [15, 14, 14]

    return False if pixel_is_equal(pix1, color_false, tol=25) else not pixel_is_equal(pix2, color_false, tol=25)


def check_this_station_name(logger):
    if check_if_at_booze_generator(logger): return "booze_generator"
    if check_if_at_water_collector(logger): return "water_collector"
    if check_if_at_lavatory(logger): return "lavatory"
    if check_if_at_nutrition_unit(logger): return "nutrition_unit"
    if check_if_at_workbench(logger): return "workbench"
    if check_if_at_intelligence_center(logger): return "intelligence_center"
    if check_if_at_medstation(logger): return "medstation"
    if check_if_at_scav_case(logger): return "scav_case"
    else:
        return "unk"



# checking if currently at the right station
def check_if_at_booze_generator():
    t=time.time()
    region=[650,475,350,150]
    current_image = screenshot(region)
    reference_folder = "check_if_at_booze_generator"
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
    print(f"Search took {'{:06.4f}'.format(time.time()-t)} seconds")
    return check_for_location(locations)


def check_if_at_water_collector():
    t=time.time()
    region=[650,475,350,150]
    current_image = screenshot(region)
    reference_folder = "check_if_at_water_collector"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "4.png",
    ]
    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )
    print(f"Search took {'{:06.4f}'.format(time.time()-t)} seconds")
    return check_for_location(locations)


def check_if_at_lavatory():
    t=time.time()
    region=[660,306,250,179]
    current_image = screenshot(region)
    reference_folder = "check_if_at_lavatory"
    references = [
        "1.png",
        "2.png",
        "3.png",
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
    print(f"Search took {'{:06.4f}'.format(time.time()-t)} seconds")
    return check_for_location(locations)


def check_if_at_nutrition_unit(logger):
    region = [698, 340, 170, 26]
    image = screenshot(region)
    text = img_to_txt(image)

    # print(text)
    # show_image(image)


    return bool(text.startswith('Nutr'))


def check_if_at_workbench():
    t=time.time()
    region=[660,306,250,179]
    current_image = screenshot(region)
    reference_folder = "check_if_at_workbench"
    references = [
        "1.png",
        "2.png",
        "3.png",
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
    print(f"Search took {'{:06.4f}'.format(time.time()-t)} seconds")
    return check_for_location(locations)


def check_if_at_intelligence_center(logger):
    region = [698, 340, 229, 29]
    image = screenshot(region)
    text = img_to_txt(image)
    #logger.log(f"check_if_at_intelligence_center text readout: {text}")

    return bool(text.startswith('Intell'))


def check_if_at_medstation():
    t=time.time()
    region=[660,306,250,179]
    current_image = screenshot(region)
    reference_folder = "check_if_at_medstation"
    references = [
        "1.png",
        "2.png",
        "3.png",
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
    print(f"Search took {'{:06.4f}'.format(time.time()-t)} seconds")
    return check_for_location(locations)


def check_if_at_scav_case():
    t=time.time()
    region=[660,306,250,179]
    current_image = screenshot(region)
    reference_folder = "check_if_at_scav_case"
    references = [
        "1.png",
        "2.png",
        "3.png",
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
    print(f"Search took {'{:06.4f}'.format(time.time()-t)} seconds")
    return check_for_location(locations)


# move to each station
def get_to_water_collector(logger):
    check_quit_key_press()
    open_hideout_interface()

    at_location = check_if_at_water_collector(logger)
    while not (at_location):
        scroll_left_in_hideout()
        time.sleep(4)
        at_location = check_if_at_water_collector(logger)
    logger.log("Made it to water collector.")


def get_to_lavatory(logger):
    check_quit_key_press()
    open_hideout_interface()

    at_location = check_if_at_lavatory(logger)
    while not (at_location):
        scroll_left_in_hideout()
        time.sleep(4)
        at_location = check_if_at_lavatory(logger)
    logger.log("Made it to lavatory")


def get_to_booze_generator(logger):
    check_quit_key_press()
    logger.log("Getting to booze generator")
    open_hideout_interface()

    at_location = check_if_at_booze_generator(logger)
    while not (at_location):
        scroll_left_in_hideout()
        time.sleep(5)
        at_location = check_if_at_booze_generator(logger)
    logger.log("Made it to booze_generator.")


def get_to_nutrition_unit(logger):
    check_quit_key_press()
    open_hideout_interface()

    at_location = check_if_at_nutrition_unit(logger)
    while not (at_location):
        scroll_left_in_hideout()
        time.sleep(4)
        at_location = check_if_at_nutrition_unit(logger)
    logger.log("Made it to nutrition_unit")


def get_to_workbench(logger):
    check_quit_key_press()
    open_hideout_interface()

    at_location = check_if_at_workbench(logger)
    while not (at_location):
        scroll_left_in_hideout()
        time.sleep(4)
        at_location = check_if_at_workbench(logger)
    logger.log("Made it to workbench")


def get_to_intelligence_center(logger):
    check_quit_key_press()
    open_hideout_interface()

    at_location = check_if_at_intelligence_center(logger)
    while not (at_location):
        scroll_left_in_hideout()
        time.sleep(4)
        at_location = check_if_at_intelligence_center(logger)
    logger.log("Made it to intelligence_center")


def get_to_medstation(logger):
    check_quit_key_press()
    open_hideout_interface()

    at_location = check_if_at_medstation(logger)
    while not (at_location):
        scroll_left_in_hideout()
        time.sleep(4)
        at_location = check_if_at_medstation(logger)
    logger.log("Made it to medstation")


def check_for_water_collector_collect_icon():
    region = [1008, 782, 80, 20]
    image = screenshot(region)
    text = img_to_txt(image)
    return bool(text.startswith("GET") or text.startswith("GETITE") or text.startswith("GE") or text.startswith("GGE") or text.startswith("-GET"))

# booze generator station
def manage_booze_generator(logger):
    check_quit_key_press()
    logger.log("")
    logger.log("Managing booze_generator craft.")
    logger.log("")

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


def find_water_filter_in_dropdown_in_water_collector():
    region = [825, 734, 328, 197]
    color_blue = [123, 219, 255]
    coords_list = find_all_pixel_coords(region=region, color=color_blue)
    return None if len(coords_list) == 0 else coords_list[0]

# workbench
def manage_workbench(logger):
    check_quit_key_press()
    logger.log("")
    logger.log("Managing workbench crafts.")
    logger.log("")


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


def check_scav_case():
    region = [1006, 711, 90, 35]
    image = screenshot(region)
    text = img_to_txt(image)
    if text.startswith("GET"):
        return "get items"
    return "collecting" if check_for_scav_case_progress() else "start"


def get_items_from_workbench():
    check_quit_key_press()
    coords = find_green_gunpowerder_icon_in_workbench()
    get_items_coord = [coords[0] + 80, coords[1] + 25]
    click(get_items_coord[0], get_items_coord[1])


def check_workbench(logger):
    check_quit_key_press()
    check_for_get_items_in_workbench()


def check_for_get_items_in_workbench():
    t=time.time()
    region=[800,336,150,40]
    current_image = screenshot(region)
    #show_image(current_image)
    reference_folder = "check_for_get_items_in_workbench"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "3.png",
        "4.png",
    ]
    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )
    print(f"Check_for_get_items_in_workbench search took {'{:06.4f}'.format(time.time()-t)} seconds")
    return check_for_location(locations)



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
    region = [970, 385, 100, 400]
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

    coord = get_first_location(locations)
    return None if coord is None else [coord[1] + 970, coord[0] + 385]


def get_image_of_green_gunpowder_surroundings():
    coord = find_green_gunpowerder_icon_in_workbench()
    region = [coord[0] + 55, coord[1] - 20, 75, 60]

    # plt.imshow(numpy.asarray(image))
    # plt.show()

    return screenshot(region)


def get_to_green_gunpowder_craft(logger):
    check_quit_key_press()
    logger.log("Getting to green gunpowder craft.")
    at_green_gunpowder_craft = find_green_gunpowerder_icon_in_workbench() is not None

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


# water collector
def manage_water_collector(logger):
    check_quit_key_press()
    logger.log("")
    logger.log("Managing water_collector craft.")
    logger.log("")


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





def add_filter_to_water_collector():
    # click dropdown coord to show filters on standby
    dropdown_arrow_coord = [927, 791]
    pyautogui.moveTo(
        dropdown_arrow_coord[0], dropdown_arrow_coord[1], duration=0.2)
    time.sleep(1)
    pyautogui.click()
    time.sleep(1)

    # click next filter
    click(971, 797)
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
    return None if coord is None else [coord[1] + 910, coord[0] + 773]





# scav case
def manage_scav_case(logger):
    check_quit_key_press()
    logger.log("")
    logger.log("Managing scav_case craft.")
    logger.log("")



    logger.log("Checking scav_case state.")
    state = check_scav_case()

    logger.log(f"Scav case state is: {state}")

    if state == "get items":
        collect_scav_case()
        logger.add_craft_completed()
    if state == "start":
        start_scav_case()

    logger.log("Done managing scav case.")



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
    truth = check_for_location(locations)

    region = [1022, 673, 58, 12]
    image = screenshot(region)
    text = img_to_txt(image)
    print(text)
    if text.startswith("Coll"):
        truth = True

    return truth


# medstation
def manage_medstation(logger):
    logger.log("Managing medstation")

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
    at_pile_of_meds = find_pile_of_meds_icon() is not None
    while not (at_pile_of_meds):
        pyautogui.click(700, 700)
        pyautogui.scroll(-400)
        time.sleep(0.22)
        if find_pile_of_meds_icon() is not None:
            at_pile_of_meds = True

    pyautogui.click(700, 700)
    pyautogui.scroll(-400)


def find_pile_of_meds_icon():
    region = [992, 415, 50, 350]
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
        "9.png"
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )
    coord = get_first_location(locations)
    return None if coord is None else [coord[1] + 992, coord[0] + 415]


def check_state_of_medstation():
    if check_if_medstation_is_producing():
        return "producing"

    get_to_pile_of_meds_craft_in_medstation()

    if check_for_start_in_medstation():
        return "start"

    if check_for_get_items_in_medstation():
        return "get items"


def check_for_get_items_in_medstation():
    coord = find_pile_of_meds_icon()
    region = [coord[0]+62, coord[1]+12, 65, 17]
    image = screenshot(region)
    text = img_to_txt(image)

    # print(text)
    # show_image(image)

    return bool((text.startswith("GET")) or (text.startswith("GE")) or (text.startswith("get")))


def check_for_start_in_medstation():
    coords = find_pile_of_meds_icon()
    region = [coords[0]+75, coords[1]+13, 40, 15]
    image = screenshot(region)
    text = img_to_txt(image)

    # print(text)
    # show_image(image)

    return bool((text.startswith("START")) or (text.startswith("STA")) or (text.startswith("SST")) or (text.startswith("SSST")))


def get_image_of_pile_of_meds_craft_in_medstation():
    coords = find_pile_of_meds_icon()
    region = [coords[0]+60, coords[1]+12, 67, 19]
    # show_image(image)

    return screenshot(region)


# lavatory
def manage_lavatory(logger):
    logger.log("Managing lavatory")
    state = check_lavatory()
    logger.log(f"Lavatory state: {state}")

    if state == "start":
        get_to_cordura_craft_in_lavatory()
        buy_slings_for_cordura_craft(logger)
        start_cordura_craft_in_hideout()

    if state == "get items":
        get_items_from_lavatory()


def get_items_from_lavatory():
    get_to_cordura_craft_in_lavatory()
    coords = find_cordura_craft_in_lavatory()
    pyautogui.moveTo(coords[0]+205, coords[1]+20, duration=0.33)
    time.sleep(0.33)
    pyautogui.click(clicks=2, interval=0.2)
    time.sleep(1)


def find_cordura_craft_in_lavatory():
    region = [845, 453, 50, 300]
    check_quit_key_press()
    current_image = screenshot(region)

    # show_image(current_image)

    reference_folder = "find_cordura_craft_in_lavatory"
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
    coord = get_first_location(locations)
    return None if coord is None else [coord[1]+845, coord[0]+453]


def get_to_cordura_craft_in_lavatory():
    at_craft = find_cordura_craft_in_lavatory() is not None
    while not (at_craft):
        pyautogui.click(700, 700)
        pyautogui.scroll(-400)
        time.sleep(0.33)
        if find_cordura_craft_in_lavatory() is not None:
            at_craft = True


def check_lavatory():
    time.sleep(1)
    # check for get items
    if check_for_lavatory_get_items():
        return "get items"
    return "producing" if look_for_producing_in_lavatory() else "start"


def look_for_producing_in_lavatory():
    t=time.time()
    for _ in range(33, 0, -1):
        if check_for_producing_icon_in_lavatory():
            print(f"Spent {'{:06.4f}'.format(time.time()-t)} looking for producing icon in lavatory.")
            return True
    print(f"Spent {'{:06.4f}'.format(time.time()-t)} looking for producing icon in lavatory.")
    return False


def check_for_producing_icon_in_lavatory():
    iar=numpy.asarray(screenshot())
    pix=iar[330][688]
    return pixel_is_equal(pix,[184, 183, 171],tol=35)


def check_for_lavatory_get_items():
    t=time.time()
    region=[800,336,150,40]
    current_image = screenshot(region)
    #show_image(current_image)
    reference_folder = "check_for_lavatory_get_items"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "3.png",
        "4.png",

    ]
    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )
    print(f"Search took {'{:06.4f}'.format(time.time()-t)} seconds")
    return check_for_location(locations)


def start_cordura_craft_in_hideout():  # sourcery skip: extract-duplicate-method
    # click start
    coord = find_cordura_craft_in_lavatory()
    pyautogui.moveTo(coord[0]+210, coord[1]+18, duration=0.2)
    time.sleep(0.33)
    pyautogui.click()
    time.sleep(0.33)

    # click handover
    pyautogui.moveTo(656, 674, duration=0.33)
    time.sleep(0.33)
    pyautogui.click()
    time.sleep(0.33)


def find_cordura_craft_in_lavatory():
    region = [845, 453, 50, 300]
    check_quit_key_press()
    current_image = screenshot(region)
    reference_folder = "find_cordura_craft_in_lavatory"
    references = ["1.png", "2.png", "3.png", "4.png", "5.png", "6.png"]
    locations = find_references(screenshot=current_image, folder=reference_folder, names=references, tolerance=0.99)

    coord = get_first_location(locations)
    return None if coord is None else [coord[1] + 845, coord[0] + 453]


def find_sling_in_lavatory_craft_menu():
    region = [845, 313, 50, 520]
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
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )
    coord = get_first_location(locations)
    return None if coord is None else [coord[1]+845, coord[0]+313]


def set_filters_to_only_ragman():  # sourcery skip: extract-duplicate-method
    # open filter cog button
    click(326, 87)
    time.sleep(1)

    # open+orientate filters window
    coord = find_filters_window_for_sling_purchase()
    pyautogui.moveTo(coord[0], coord[1], duration=0.2)

    # click 'Display offers from' dropdown
    display_offers_from_coord = [coord[0]+120, coord[1]+150]
    click(display_offers_from_coord[0],
          display_offers_from_coord[1], duration=0.2)
    time.sleep(1)

    # click traders
    traders_coord = [coord[0]+120, coord[1]+190]
    click(traders_coord[0], traders_coord[1], duration=0.2)
    time.sleep(1)

    # click OK
    ok_coord = [coord[0]+60, coord[1]+237]
    click(ok_coord[0], ok_coord[1], duration=0.2)
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
    return None if coords is None else [coords[1] + 3, coords[0] + 3]
