# py-TarkBot

Automated Flee Market for Escape from Tarkov

Join the [Discord server](https://discord.gg/Cf8fXtayXA)!

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
