import PySimpleGUI as sg

from .theme import THEME

sg.theme(THEME)


def stat_box(stat_name: str, size=(5, 1)):
    return sg.Text(
        "0",
        key=stat_name,
        relief=sg.RELIEF_SUNKEN,
        text_color="blue",
        size=size,
    )

#flea mode stuff
flea_sell_mode_stats_titles = [
    [
        [
            sg.Text("Starting Money: "),
        ],
        [
            sg.Text("Current Money: "),
        ],
        [
            sg.Text("Fee Total: "),
        ],
        [
            sg.Text("Items Sold: "),
        ],
        [
            sg.Text("Roubles Made: "),
        ],
    ],
    [
        [
            sg.Text("Sale Attempts: "),
        ],
        [
            sg.Text("Offers Removed: "),
        ],
        [
            sg.Text("Success Rate: "),
        ],
        [
            sg.Text("Restarts: "),
        ],
    ],
]


flea_sell_mode_stats_values = [
    [
        [
            stat_box("starting_money"),
        ],
        [
            stat_box("current_money"),
        ],
        [
            stat_box("fee_total"),
        ],
        [
            stat_box("item_sold"),
        ],
        [
            stat_box("roubles_made"),
        ],
    ],
    [
        [
            stat_box("sale_attempts"),
        ],
        [
            stat_box("offers_removed"),
        ],
        [
            stat_box("success_rate"),
        ],
        [
            stat_box("restarts"),
        ],
    ],
]

flea_mode_stats = [
    [
        sg.Column(flea_sell_mode_stats_titles[0], element_justification="right"),
        sg.Column(flea_sell_mode_stats_values[0], element_justification="left"),
        sg.Column(flea_sell_mode_stats_titles[1], element_justification="right"),
        sg.Column(flea_sell_mode_stats_values[1], element_justification="left"),
    ]
]


#hideout mode stuff
hideout_mode_stats_title = [
    [
        [
            sg.Text("Workbench Starts: "),
        ],
        [
            sg.Text("Workbench Collects"),
        ],
        [
            sg.Text("Bitcoin Collects"),
        ],
        [
            sg.Text("Lavatory Starts"),
        ],
        [
            sg.Text("Lavatory Collects"),
        ],
        [
            sg.Text("Scav Case Starts"),
        ],
        [
            sg.Text("Scav Case Collects"),
        ],
        [
            sg.Text("Est Profit"),
        ],
    ],
    [
        [
            sg.Text("Medstation Starts"),
        ],
        [
            sg.Text("Medstation Collects"),
        ],
        [
            sg.Text("Water Filters"),
        ],
        [
            sg.Text("Water Collects"),
        ],
        [
            sg.Text("Restarts"),
        ],
        [
            sg.Text("Est Time Per Station"),
        ],
        [
            sg.Text("Autorestarts"),
        ],
    ],
]


hideout_mode_stats_values = [
    [
        [
            stat_box("workbench_starts"),
        ],
        [
            stat_box("workbench_collects"),
        ],
        [
            stat_box("bitcoin_collects"),
        ],
        [
            stat_box("lavatory_starts"),
        ],
        [
            stat_box("lavatory_collects"),
        ],
        [
            stat_box("scav_case_starts"),
        ],
        [
            stat_box("scav_case_collects"),
        ],
        [
            stat_box("profit", size=(10, 1)),
        ],
    ],
    [
        [
            stat_box("medstation_starts"),
        ],
        [
            stat_box("medstation_collects"),
        ],
        [
            stat_box("water_filters"),
        ],
        [
            stat_box("water_collects"),
        ],
        [
            stat_box("restarts"),
        ],
        [
            stat_box("station_time"),
        ],
        [
            stat_box("autorestarts"),
        ],
    ],
]

hideout_mode_stats = [
    [
        sg.Column(hideout_mode_stats_title[0], element_justification="right"),
        sg.Column(hideout_mode_stats_values[0], element_justification="left"),
        sg.Column(hideout_mode_stats_title[1], element_justification="right"),
        sg.Column(hideout_mode_stats_values[1], element_justification="left"),
    ]
]
