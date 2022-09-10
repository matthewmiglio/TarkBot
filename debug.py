
from pytarkbot.client import orientate_tarkov_client, resize_window, screenshot
from pytarkbot.flee import check_add_offer_window_orientation, get_current_price, orientate_add_offer_window
from pytarkbot.hideout import buy_slings_for_cordura_craft, check_for_get_items_in_workbench, check_if_at_booze_generator, check_if_at_intelligence_center, check_if_at_lavatory, check_if_at_medstation, check_if_at_nutrition_unit, check_if_at_scav_case, check_if_at_water_collector, check_if_at_workbench, check_for_lavatory_get_items, check_lavatory, check_this_station_name, check_workbench, get_items_from_lavatory, get_to_cordura_craft_in_lavatory, get_to_hideout, look_for_producing_in_lavatory, start_cordura_craft_in_hideout
from pytarkbot.launcher import check_if_on_tark_main
from pytarkbot.logger import Logger
import numpy
from matplotlib import pyplot as plt
from pytarkbot.tesseract_install import setup_tesseract

logger = Logger()
setup_tesseract()


# orientate_tarkov_client("EscapeFromTarkov", logger)

# plt.imshow(numpy.asarray(screenshot()))
# plt.show()

# print(check_for_get_items_in_workbench())


orientate_add_offer_window(logger)

# print(check_add_offer_window_orientation())