# py-TarkBot

Automated Flee Market for Escape from Tarkov

Join the [Discord server](https://discord.gg/Cf8fXtayXA)!
## What is Py-TarkBot?
The bot's purpose is to automatically post items on the flea for you. The bot works by selecting items from the top rows of your inventory, looks at the current market price, then posts it just below that (as you would by hand).

I developed this bot because I was bringing out of raid so many barter items that it would take nearly as long to sell all my loot as it would just to get it. Now you can cash in your items for flea-market prices while you AFK!

## Install

[Download and run the latest windows installer](https://github.com/matthewmiglio/py-TarkBot/releases/latest)

## Bug report

Report bugs in the [Github issues tab](https://github.com/matthewmiglio/py-TarkBot/issues). Be descriptive as possible, including screenshots, error messages, and steps to reproduce.

## Contributing and Running from Source

All contributions are welcome, open a pull request to contribute.

For developers, to install the source code with the following:

```bash
git clone https://github.com/matthewmiglio/py-TarkBot.git
cd py-TarkBot
python -m pip install poetry # install poetry for dependency management if you don't have it
poetry install --with dev # --with build # install dependencies
poetry run pre-commit install # optional, but highly recommended for contributing
poetry run python pytarkbot/__main__.py # run the program from source
```
