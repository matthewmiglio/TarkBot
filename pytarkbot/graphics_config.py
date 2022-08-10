import shutil


def save_default_settings_to_file(logger,src,dst):
    try:
        shutil.copyfile(src, dst)
    except:
        pass
    logger.log("Saved current graphics settings to file.")


def set_tarkov_settings_to_bot_config(logger,src,dst):
    try:
        shutil.copyfile(src, dst)
    except:
        pass
    
    logger.log("Loaded bot config.")
    
    
def set_tarkov_settings_to_default_config(logger,src,dst):
    try:
        shutil.copyfile(src, dst)
    except:
        pass
    
    logger.log("Loaded default config.")