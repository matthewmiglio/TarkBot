
from pytarkbot.client import resize_window
from pytarkbot.hideout import get_to_hideout
from pytarkbot.launcher import check_if_on_tark_main
from pytarkbot.logger import Logger

logger=Logger()

title="EscapeFromTarkov"
resize=[1299,999]

# resize_window(window_name=title,resize=resize)

print(check_if_on_tark_main(logger))

get_to_hideout(logger)