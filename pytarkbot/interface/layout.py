import os
import random

import PySimpleGUI as sg

from .stats import flea_mode_stats, hideout_mode_stats, snipebot_mode_stats


# region CONSTANTS

FLEA_SELL_START_KEY = "flea_sell_start_key"
FLEA_SELL_STOP_KEY = "flea_sell_stop_key"

HIDEOUT_START_KEY = "hideout_start_key"
HIDEOUT_STOP_KEY = "hideout_stop_key"

SNIPEBOT_START_KEY = "snipebot_start_key"
SNIPEBOT_STOP_KEY = "snipebot_stop_key"


# flea sell controls keys
FLEA_SELL_ROWS_INPUT_KEY = "flea_sell_rows_input_key"
FLEA_SELL_REMOVE_OFFERS_TIMER_KEY = "flea_sell_remove_offers_timer_key"


FLEA_SELL_CONTROL_KEYS = [FLEA_SELL_ROWS_INPUT_KEY, FLEA_SELL_REMOVE_OFFERS_TIMER_KEY]


# hideout controls keys
HIDEOUT_SCAV_CASE_TOGGLE_KEY = "hideout_scav_case_toggle_key"
HIDEOUT_MED_STATION_TOGGLE_KEY = "hideout_med_station_toggle_key"
HIDEOUT_LAVATORY_TOGGLE_KEY = "hideout_lavatory_toggle_key"
HIDEOUT_WORKBENCH_TOGGLE_KEY = "hideout_workbench_toggle_key"
HIDEOUT_BITCOIN_TOGGLE_KEY = "hideout_bitcoin_toggle_key"
HIDEOUT_WATER_TOGGLE_KEY = "hideout_water_toggle_key"
SCAV_CASE_TYPE_KEY = "scav_case_type_key"


# snipe controls keys
SNIPEBOT_ITEM_NAME_1_KEY = "item_name_1"
SNIPEBOT_ITEM_PRICE_1_KEY = "item_price_1"
SNIPEBOT_ITEM_NAME_2_KEY = "item_name_2"
SNIPEBOT_ITEM_PRICE_2_KEY = "item_price_2"
SNIPEBOT_ITEM_NAME_3_KEY = "item_name_3"
SNIPEBOT_ITEM_NAME_4_KEY = "item_name_4"
SNIPEBOT_ITEM_PRICE_5_KEY = "item_price_5"
SNIPEBOT_ITEM_PRICE_4_KEY = "item_price_4"
SNIPEBOT_ITEM_NAME_5_KEY = "item_name_5"
SNIPEBOT_ITEM_PRICE_3_KEY = "item_price_3"

# snipebot job toggle keys

RUBLE_FARM_KEY = "ruble_farm_toggle_key"
SPECIFIC_ITEM_KEY = "specific_snipe_farm_toggle_key"

# all the controls keys together for disabling/enabling when the bot is running
CONTROLS_KEYS = [
    FLEA_SELL_ROWS_INPUT_KEY,
    FLEA_SELL_REMOVE_OFFERS_TIMER_KEY,
    HIDEOUT_SCAV_CASE_TOGGLE_KEY,
    HIDEOUT_MED_STATION_TOGGLE_KEY,
    HIDEOUT_LAVATORY_TOGGLE_KEY,
    HIDEOUT_WORKBENCH_TOGGLE_KEY,
    RUBLE_FARM_KEY,
    SPECIFIC_ITEM_KEY,
    HIDEOUT_BITCOIN_TOGGLE_KEY,
    HIDEOUT_WATER_TOGGLE_KEY,
    SNIPEBOT_ITEM_NAME_1_KEY,
    SNIPEBOT_ITEM_PRICE_1_KEY,
    SNIPEBOT_ITEM_NAME_2_KEY,
    SNIPEBOT_ITEM_PRICE_2_KEY,
    SNIPEBOT_ITEM_NAME_3_KEY,
    SNIPEBOT_ITEM_PRICE_5_KEY,
    SNIPEBOT_ITEM_NAME_4_KEY,
    SNIPEBOT_ITEM_PRICE_4_KEY,
    SNIPEBOT_ITEM_NAME_5_KEY,
    SNIPEBOT_ITEM_PRICE_3_KEY,
]

# start keys
START_KEYS = [
    FLEA_SELL_START_KEY,
    HIDEOUT_START_KEY,
    SNIPEBOT_START_KEY,
]

# stop keys
STOP_KEYS = [
    FLEA_SELL_STOP_KEY,
    HIDEOUT_STOP_KEY,
    SNIPEBOT_STOP_KEY,
]

# donate button stuff


DONATE_BUTTON_KEY = "donate_button_key"


# endregion


# region DONATE BUTTON LAYOUTS


def filter_donate_image_sources(path_list):
    good_paths = []

    for path in path_list:
        if ".png" not in path or "donate" not in path:
            continue
        good_paths.append(path)

    return good_paths


# grab all the donate images
donate_image_sources = os.listdir()

# if 'github exists in the list, then we're in a source code version of the bot, so source the images from the assets folder
if ".github" in donate_image_sources:
    donate_image_sources = []

    files = os.listdir("pytarkbot/interface/assets")
    for file in files:
        path = os.path.join("pytarkbot/interface/assets", file)
        donate_image_sources.append(path)


donate_image_sources = filter_donate_image_sources(donate_image_sources)

print(donate_image_sources)


random_image_index = random.randint(0, len(donate_image_sources) - 1)
random_image_path = donate_image_sources[random_image_index]


DONATE_BUTTON_LAYOUTS = [
    [
        [
            sg.Button(
                image_source=random_image_path,
                size=(55, 7),
                key=DONATE_BUTTON_KEY,
            )
        ]
    ],
]

# endregion


# region FLEA SELL MODE INTERFACE STUFF

flea_sell_info_layout = [
    [
        sg.Text(
            "Flea Sell mode sells items in your stash on the flea market according to current market prices. ",
            size=(35, None),
        )
    ],
    [
        sg.Text(
            "Select the number of rows in your stash (from the top) you want to sell, and how long to wait before removing offers.",
            size=(35, None),
        )
    ],
]


flea_sell_mode_controls_layout = [
    [
        sg.Text("Rows in stash: "),
        sg.Slider(
            range=(0, 11),
            default_value=5,
            orientation="horizontal",
            key=FLEA_SELL_ROWS_INPUT_KEY,
        ),
    ],
    [
        sg.Text("Remove offers timer:"),
        sg.DropDown(
            ["1m", "2m", "3m", "5m"],
            key=FLEA_SELL_REMOVE_OFFERS_TIMER_KEY,
            default_value="2m",
        ),
    ],
]


feal_sell_mode_buttons_layout = [
    [
        sg.Button("Start", key=FLEA_SELL_START_KEY),
        sg.Button("Stop", key=FLEA_SELL_STOP_KEY),
    ],
]

FLEA_MODE_LAYOUT = [
    # info frame
    [
        sg.Frame(
            layout=flea_sell_info_layout,
            title="Info",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
    # controls frame
    [
        sg.Frame(
            title="Controls",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
            layout=flea_sell_mode_controls_layout,
        )
    ],
    # stats frame
    [
        sg.Frame(
            layout=flea_mode_stats,
            title="Stats",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
    # buttons frame
    [
        sg.Frame(
            layout=feal_sell_mode_buttons_layout,
            title="",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
    # donate button frame
    [
        sg.Frame(
            layout=random.choice(DONATE_BUTTON_LAYOUTS),
            title="",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
]

# endregion


# region Hideout MODE INTERFACE STUFF


hideout_info_layout = [
    [
        sg.Text(
            "Hideout bot starts and collects the toggled crafts. You must have the required items and fuel in your stash.",
            size=(35, None),
        )
    ],
    [
        sg.Text(
            "Applicable crafts must be favorited in their respective stations: Green Gunpowder, Cordura, Pile of Meds",
            size=(35, None),
        )
    ],
]


hideout_mode_controls_layout = [
    [
        sg.Checkbox(text="Scav case", key=HIDEOUT_SCAV_CASE_TOGGLE_KEY, default=True),
        sg.Checkbox(
            text="Med Station ", key=HIDEOUT_MED_STATION_TOGGLE_KEY, default=True
        ),
        sg.Checkbox(text="Lavatory ", key=HIDEOUT_LAVATORY_TOGGLE_KEY, default=True),
    ],
    [
        sg.Checkbox(text="Workbench ", key=HIDEOUT_WORKBENCH_TOGGLE_KEY, default=True),
        sg.Checkbox(text="Bitcoin ", key=HIDEOUT_BITCOIN_TOGGLE_KEY, default=True),
        sg.Checkbox(text="Water ", key=HIDEOUT_WATER_TOGGLE_KEY, default=True),
    ],
    [
        sg.Text("Scav Case Type: "),
        sg.DropDown(
            default_value="2500",
            values=["2500", "15000", "95000", "Intel", "Moonshine"],
            key=SCAV_CASE_TYPE_KEY,
        ),
    ],
]


HIDEOUT_MODE_LAYOUT = [
    # info frame
    [
        sg.Frame(
            layout=hideout_info_layout,
            title="Info",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
    # station checkboxes
    [
        sg.Frame(
            layout=hideout_mode_controls_layout,
            title="Station Toggles",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
    # stats
    [
        sg.Frame(
            layout=hideout_mode_stats,
            title="Stats",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
    # start/stop buttons
    [
        sg.Frame(
            layout=[
                [
                    sg.Button("Start", key=HIDEOUT_START_KEY),
                    sg.Button("Stop", key=HIDEOUT_STOP_KEY),
                ]
            ],
            title="",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
]

# endregion


# region SNIPE MODE INTERFACE STUFF


snipebot_info_layout = [
    [
        sg.Text(
            "FLEA SNIPE MODE has two options: Specific item sniping, and rouble farm sniping.",
            size=(35, None),
        )
    ],
    [
        sg.Text(
            "SPECIFIC ITEM SNIPING uses the item inputs to target items your want to buy at or below a given price.",
            size=(35, None),
        )
    ],
    [
        sg.Text(
            "ROUBLE FARM SNIPING automatically snipes preset items below vendor price, so you can resell them to Therapist for a profit.",
            size=(35, None),
        )
    ],
    [
        sg.Text(
            "Selecting both modes will rotate between either mode.",
            size=(35, None),
        )
    ],
]

snipe_mode_controls_layout = [
    [
        sg.Text(
            "                             Item names                                    "
        ),
        sg.Text("Maximum price"),
    ],
    [
        sg.Input(key=SNIPEBOT_ITEM_NAME_1_KEY),
        sg.Input(key=SNIPEBOT_ITEM_PRICE_1_KEY),
    ],
    [
        sg.Input(key=SNIPEBOT_ITEM_NAME_2_KEY),
        sg.Input(key=SNIPEBOT_ITEM_PRICE_2_KEY),
    ],
    [
        sg.Input(key=SNIPEBOT_ITEM_NAME_3_KEY),
        sg.Input(key=SNIPEBOT_ITEM_PRICE_3_KEY),
    ],
    [
        sg.Input(key=SNIPEBOT_ITEM_NAME_4_KEY),
        sg.Input(key=SNIPEBOT_ITEM_PRICE_4_KEY),
    ],
    [
        sg.Input(key=SNIPEBOT_ITEM_NAME_5_KEY),
        sg.Input(key=SNIPEBOT_ITEM_PRICE_5_KEY),
    ],
]


job_select_layout = [
    [
        sg.Checkbox("Specific Item Snipe", key=SPECIFIC_ITEM_KEY, default=True),
        sg.Checkbox("Rouble Farm", key=RUBLE_FARM_KEY),
    ]
]


SNIPEBOT_MODE_LAYOUT = [
    # info
    [
        sg.Frame(
            layout=snipebot_info_layout,
            title="Info",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
    # job select
    [
        sg.Frame(
            layout=job_select_layout,
            title="Job Select",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
    # item inpouts
    [
        sg.Frame(
            layout=snipe_mode_controls_layout,
            title="Item input",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
    # stats
    [
        sg.Frame(
            layout=snipebot_mode_stats,
            title="Stats",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
    # start/stop buttons
    [
        sg.Frame(
            layout=[
                [
                    sg.Button("Start", key=SNIPEBOT_START_KEY),
                    sg.Button("Stop", key=SNIPEBOT_STOP_KEY),
                ]
            ],
            title="",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
]
# endregion


# region MAIN LAYOUT


def make_tarkbot_window():
    # tabs
    flea_sell_tab = sg.Tab(
        "Flea Sell",
        FLEA_MODE_LAYOUT,
    )
    flea_snipe_tab = sg.Tab(
        "Flea Snipe",
        SNIPEBOT_MODE_LAYOUT,
    )
    hideout_tab = sg.Tab(
        "Hideout",
        HIDEOUT_MODE_LAYOUT,
    )

    # tab group
    tab_group = sg.TabGroup(
        [
            [
                flea_sell_tab,
                flea_snipe_tab,
                hideout_tab,
            ]
        ]
    )

    # main layout
    layout = [
        [tab_group],
    ]

    # return window
    return sg.Window("Py-TarkBot v1.0.0", layout, finalize=True, size=(500, 590))


# endregion
