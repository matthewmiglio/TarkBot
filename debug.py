
from pytarkbot.client import orientate_tarkov_client, resize_window, screenshot
from pytarkbot.flee import get_current_price
from pytarkbot.hideout import buy_slings_for_cordura_craft, check_if_at_booze_generator, check_if_at_intelligence_center, check_if_at_lavatory, check_if_at_medstation, check_if_at_nutrition_unit, check_if_at_scav_case, check_if_at_water_collector, check_if_at_workbench, check_for_lavatory_get_items, check_lavatory, check_this_station_name, get_items_from_lavatory, get_to_cordura_craft_in_lavatory, get_to_hideout, start_cordura_craft_in_hideout
from pytarkbot.launcher import check_if_on_tark_main
from pytarkbot.logger import Logger
import numpy
from matplotlib import pyplot as plt
from pytarkbot.tesseract_install import setup_tesseract

logger = Logger()
setup_tesseract()


# orientate_tarkov_client("EscapeFromTarkov", logger)

# state_flee_mode()

# while True:
#     print(get_current_price())


# plt.imshow(numpy.asarray(screenshot()))
# plt.show()




# get_to_cordura_craft_in_lavatory()
# buy_slings_for_cordura_craft(logger)
# start_cordura_craft_in_hideout()




check_lavatory()