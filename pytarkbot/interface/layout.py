import PySimpleGUI as sg

from .stats import stat_box, flea_mode_stats, hideout_mode_stats


hideout_mode_instructions_text = """The bot farms crafts for lavatory,
water collector, bitcoin farm, medstation, and workbench.

The bot farms cordura, purified water, bitcoins, pile of meds, and green gunpowder. Favorite these crafts in each station.
"""


flea_mode_instructions_text = """1. Tarkov must be set to windowed mode
2. Program must be run as administrator.

Matthew Miglio, Martin Miglio - Nov 2022"""

# defining various things for tab 1
flea_mode_layout = [
    [
        sg.Frame(
            layout=[[sg.Text(flea_mode_instructions_text, size=(35, None))]],
            title="Info",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
    # stats
    [
        sg.Frame(
            layout=flea_mode_stats,
            title="Flea Mode Stats",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
    # buttons
    [
        sg.Frame(
            layout=[
                [
                    sg.Text("Rows in Stash:"),
                    sg.Slider(
                        range=(1, 11),
                        default_value=11,
                        key="rows_to_target",
                        orientation="horizontal",
                        size=(26, None),
                        relief=sg.RELIEF_FLAT,
                        enable_events=True,
                    ),
                ],
                [
                    sg.Text("Remove Offers Timer:"),
                    sg.Combo(
                        ["1m", "2m", "5m", "10m"],
                        key="remove_offers_timer",
                        default_value="5m",
                        enable_events=True,
                    ),
                ],
                [
                    sg.Column(
                        [
                            [
                                sg.Button("Start", key="flea_mode_start"),
                                sg.Button("Stop", disabled=True),
                            ]
                        ],
                        element_justification="left",
                        expand_x=True,
                    ),
                    sg.Column(
                        [
                            [
                                sg.Button("Help"),
                                sg.Button("Issues?", key="issues-link"),
                                sg.Button("Donate"),
                            ]
                        ],
                        element_justification="right",
                        expand_x=True,
                    ),
                ],
            ],
            title="Controls",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
    [
        stat_box("time_since_start", size=(7, 1)),
        sg.InputText(
            "Idle",
            key="current_status",
            use_readonly_for_disable=True,
            disabled=True,
            text_color="blue",
            expand_x=True,
        ),
    ],
    # https://www.paypal.com/donate/?business=YE72ZEB3KWGVY&no_recurring=0&item_name=Support+my+projects%21&currency_code=USD
]


# defining various things for tab 2


hideout_mode_layout = [
    [
        sg.Frame(
            layout=[[sg.Text(flea_mode_instructions_text, size=(35, None))]],
            title="Info",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
    # directions
    [
        sg.Frame(
            layout=[[sg.Text(hideout_mode_instructions_text, size=(35, None))]],
            title="Directions",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
    [
        sg.Frame(
            layout=[
                [
                    sg.Text("'Bitcoin' Farming"),
                    sg.Checkbox("", key="bitcoin_checkbox", default=True),
                ],
                [
                    sg.Text("Lavatory 'Cordura' Farming"),
                    sg.Checkbox("", key="lavatory_checkbox", default=True),
                ],
                [
                    sg.Text("Medstation 'Pile of Meds' Farming"),
                    sg.Checkbox("", key="medstation_checkbox", default=True),
                ],
                [
                    sg.Text("'Purified Water' Farming"),
                    sg.Checkbox("", key="water_checkbox", default=True),
                ],
                [
                    sg.Text("Workbench 'Green Gunpowder' Farming"),
                    sg.Checkbox("", key="workbench_checkbox", default=True),
                ],
                [
                    sg.Text("Scav Case Farming"),
                    sg.Checkbox("", key="scav_case_checkbox", default=True),
                ],
                [
                    sg.Text("Scav Case Type"),
                    sg.DropDown(
                        ["Moonshine", "Intel", "95000", "15000", "2500"],
                        default_value="2500",
                        key="scav_case_type",
                    ),
                ],
            ],
            title="Job List",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
    # stats
    [
        sg.Frame(
            layout=hideout_mode_stats,
            title="Hideout Mode Stats",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
    # buttons
    [
        sg.Frame(
            layout=[
                [
                    sg.Column(
                        [
                            [
                                sg.Button("Start", key="hideout_mode_start"),
                                sg.Button("Stop", disabled=True),
                            ]
                        ],
                        element_justification="left",
                        expand_x=True,
                    ),
                    sg.Column(
                        [
                            [
                                sg.Button("Help"),
                                sg.Button("Issues?", key="issues-link"),
                                sg.Button("Donate"),
                            ]
                        ],
                        element_justification="right",
                        expand_x=True,
                    ),
                ],
            ],
            title="Controls",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
    [
        stat_box("time_since_start", size=(7, 1)),
        sg.InputText(
            "Idle",
            key="message",
            use_readonly_for_disable=True,
            disabled=True,
            text_color="blue",
            expand_x=True,
        ),
    ],
    # https://www.paypal.com/donate/?business=YE72ZEB3KWGVY&no_recurring=0&item_name=Support+my+projects%21&currency_code=USD
]


# defining various things for tab 2
snipebot_mode_layout = [
    [sg.Text("This is the third tab. Add your text here.")],
]


# a list of all the keys that contain user configuration


hideout_user_config_key = [
    "bitcoin_checkbox",
    "lavatory_checkbox",
    "medstation_checkbox",
    "water_checkbox",
    "workbench_checkbox",
    "scav_case_checkbox",
    "scav_case_type",
]

user_config_keys = [
    "rows_to_target",
    "remove_offers_timer",
    "ruble_sniping_toggle",
    "item_sniping_toggle",
    "item_name_1",
    "item_price_1",
    "item_name_2",
    "item_price_2",
    "item_name_3",
    "item_price_3",
] + hideout_user_config_key

# list of button and checkbox keys to disable when the bot is running
disable_keys = user_config_keys +  ["flea_mode_start"]
hideout_disable_keys =hideout_user_config_key + ["hideout_mode_start"]
