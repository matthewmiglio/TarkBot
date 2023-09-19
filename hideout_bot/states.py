import time
from typing import List

from hideout_bot.stations.bitcoin_miner import handle_bitcoin_miner
from hideout_bot.stations.lavatory import handle_lavatory
from hideout_bot.stations.medstation import handle_medstation
from hideout_bot.stations.scav_case import handle_scav_case
from hideout_bot.stations.water_collector import handle_water_collector
from hideout_bot.stations.workbench import handle_workbench
from tarkov.launcher import restart_tarkov


def hideout_mode_state_tree(state: str, logger: object, jobs: List[str]) -> str:
    """
    Runs the hideout bot in a loop, executing the appropriate
    station functions based on the current state.

    Args:
        state (str): The current state of the bot.
        logger (object): The logger object used to log messages.
        jobs (List[str]): A list of jobs that the bot should perform.

    Returns:
        str: The new state of the bot.
    """
    print("-------------------------------------\n")

    if state == "start":
        restart_tarkov(logger)
        state = "check_fuel"

    elif state == "restart":
        logger.add_restart()
        restart_tarkov(logger)
        state = "check_fuel"

    elif state == "check_fuel":
        return "bitcoin"

    elif state == "no_fuel":
        for _ in range(3):
            logger.change_status("Generator has no fuel!!")
        while True:
            pass

    elif state == "autorestart":
        logger.change_status("Entered autorestart state")
        logger.add_autorestart()
        restart_tarkov(logger)
        state = "check_fuel"

    elif state == "bitcoin":
        # if autorestart time, next state is autorestart
        if check_if_should_autorestart(logger):
            state = "autorestart"

        # if not autorestart time, check if bitcoin job is good, or skip to next job
        else:
            # if bitcoin job is selected, next state is bitcoin's outcome
            if "Bitcoin" in jobs:
                state = handle_bitcoin_miner(logger)

            # if bitcoin job isnt selected, the next state is the next job
            else:
                state = "workbench"

        logger.change_status(f"State after bitcoin is {state}")

    elif state == "workbench":
        logger.change_status("Entered workbench state")

        if "Workbench" in jobs:
            state = handle_workbench(logger)
        else:
            state = "water"

        logger.change_status(f"State after workbench is {state}")

    elif state == "water":
        logger.change_status("Entered water state")

        if "water" in jobs:
            state = handle_water_collector(logger)
        else:
            state = "scav_case"

        logger.change_status(f"State after water is {state}")

    elif state == "scav_case":
        logger.change_status("Entered scav_case state")

        if "scav_case" in jobs:
            logger.change_status('Scav case is in jobs')
            if "15000" in jobs:
                craft_type = "15000"
            elif "95000" in jobs:
                craft_type = "95000"
            elif "Moonshine" in jobs:
                craft_type = "moonshine"
            elif "Intel" in jobs:
                craft_type = "intel"
            else:
                craft_type = "2500"

            state = handle_scav_case(logger, craft_type)
        else:
            state = "medstation"

        logger.change_status(f"State after scav_case is {state}")

    elif state == "medstation":
        logger.change_status("Entered medstation state")

        if "medstation" in jobs:
            state = handle_medstation(logger)
        else:
            state = "lavatory"

        logger.change_status(f"State after medstation is {state}")

    elif state == "lavatory":
        logger.change_status("Entered lavatory state")

        if "Lavatory" in jobs:
            state = handle_lavatory(logger)
        else:
            state = "bitcoin"

        logger.change_status(f"State after lavatory is {state}")

    return state


def check_if_should_autorestart(logger):
    hours_running = (time.time() - logger.start_time) / 60 / 60

    autorestarts = logger.autorestarts

    logger.change_status(
        f"Been running {hours_running} hours with {autorestarts} autorestarts"
    )

    # if been running less than an hour
    if hours_running < 1:
        return False

    # if autorestart count is less than hours running - 1, then we should autorestart
    if autorestarts < hours_running - 1:
        return True

    # false otherwise
    return False
