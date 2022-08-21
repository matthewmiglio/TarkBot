
from pytarkbot.__main__ import state_flee_mode
from pytarkbot.client import orientate_tarkov_client, resize_window, screenshot
from pytarkbot.flee import get_current_price
from pytarkbot.hideout import get_to_hideout
from pytarkbot.launcher import check_if_on_tark_main
from pytarkbot.logger import Logger
import numpy
from matplotlib import pyplot as plt


logger=Logger()


# orientate_tarkov_client("EscapeFromTarkov", logger)

# state_flee_mode()

while True:
    print(get_current_price())


# plt.imshow(numpy.asarray(screenshot()))
# plt.show()

