# py-Tark-Bot

Automated Hideout and Flea Market related interactions for Escape From Tarkov

TarkBot comes equipped with three distinctive modes, each catering to specific needs within Escape from Tarkov. Whether you're a seasoned player or a newcomer looking for an edge, TarkBot has you covered.

Join the [Discord server](https://discord.gg/Cf8fXtayXA)!

# Modes
## Flea Market Bot
The Flea Market Bot is your reliable companion for trading in the chaotic virtual marketplace. This mode automates the process of posting items for sale, utilizing intelligent undercutting strategies to stay competitive. TarkBot ensures that your items are listed efficiently, just like a seasoned trader would, maximizing your profits in the challenging environment of Escape from Tarkov.

## Hideout Bot
The Hideout Bot takes care of your in-game hideout, providing automation for essential activities. It handles the initiation of crafts and the collection of crafted items, allowing you to focus on the action-packed gameplay while your hideout operations run smoothly in the background. Upgrade, craft, sell, and buy items with ease as TarkBot efficiently manages your off-world storage space.

## SnipeBot
The SnipeBot is your vigilant market watcher, constantly scanning for underpriced items on the market. This mode ensures that you don't miss any opportunities to acquire valuable assets at a bargain. TarkBot executes swift buying actions, enabling you to capitalize on market fluctuations and make strategic purchases.

<img src="https://github.com/matthewmiglio/Py-Tark-Hideout-Bot/blob/main/assets/hideout_bot_demo.gif?raw=true" width="70%"/><img src="https://github.com/matthewmiglio/Py-Tark-Hideout-Bot/blob/main/assets/hideout_bot_demo_gui.png?raw=true" width="30%"/>

# Install

Download the latest Windows Installer [here](https://github.com/matthewmiglio/Py-Tark-Hideout-Bot/releases/latest).

# Bug report

Report bugs in the [Github issues tab](https://github.com/matthewmiglio/Py-Tark-Hideout-Bot/issues). Be descriptive as possible, including screenshots, error messages, and steps to reproduce.

# Contributing and Running from Source

All contributions are welcome, open a pull request to contribute.

For developers, to install the source code with the following:

```bash
git clone https://github.com/matthewmiglio/Py-Tark-Hideout-Bot.git
cd Py-Tark-Hideout-Bot
python -m pip install poetry # install poetry for dependency management if you don't have it
poetry install --with dev # --with build # install dependencies
poetry run pre-commit install # optional, but highly recommended for contributing
poetry run python hideoutbot/__main__.py # run the program from source
```
