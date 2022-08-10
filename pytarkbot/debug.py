import time


from matplotlib import pyplot as plt
from client import img_to_txt, orientate_client, screenshot
from graphics_config import set_tarkov_settings_to_bot_config, set_tarkov_settings_to_default_config

from image_filtering import  look_for_ruble_symbol
from image_rec import check_for_location, find_references, get_first_location, pixel_is_equal

from logger import Logger




logger=Logger()

# orientate_client("EscapeFromTarkov",[1280,960])
# time.sleep(1)

image_path = r"C:\Users\Matt\Desktop\inc_pics"
index=time.gmtime()
default_settings_path= f"{image_path}"
default_settings_path=f"{default_settings_path}\\{index}.png"


# plt.imshow(numpy.asarray(screenshot()))
# plt.show()



def look_for_shooting_range_symbol():
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
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )

    return get_first_location(locations)



    


# set_tarkov_settings_to_bot_config(logger)

set_tarkov_settings_to_default_config(logger)