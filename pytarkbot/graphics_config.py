import shutil


def save_default_settings_to_file(logger,src,dst):
    src=r"C:\Users\Matt\AppData\Roaming\Battlestate Games\Escape from Tarkov\Settings\Graphics.ini"
    dst=r"C:\Users\Matt\Desktop\1\my Programs\py-tark\py-tark\pytarkbot\config\user_default_config\Graphics.ini"
    
    try:
        shutil.copyfile(src=src, dst=dst)
    except:
        logger.log("!!!!!Error saving default settings to file!!!!!")
        pass
    logger.log(f"\n\nSaved current graphics settings to {dst}.\n\n")


def set_tarkov_settings_to_bot_config(logger,src,dst):
    src=r"C:\Users\Matt\Desktop\1\my Programs\py-tark\py-tark\pytarkbot\config\config_for_bot\Graphics.ini"
    dst=r"C:\Users\Matt\AppData\Roaming\Battlestate Games\Escape from Tarkov\Settings\Graphics.ini"
    
    try:
        shutil.copyfile(src=src, dst=dst)
    except:
        logger.log("!!!!!Error setting the graphics settings to bot default!!!!!")
        pass
    logger.log(f"\n\nLoaded bot config from {src}.\n\n")
    
    
def set_tarkov_settings_to_default_config(logger,src,dst):
    src=r"C:\Users\Matt\Desktop\1\my Programs\py-tark\py-tark\pytarkbot\config\user_default_config\Graphics.ini"
    dst=r"C:\Users\Matt\AppData\Roaming\Battlestate Games\Escape from Tarkov\Settings\Graphics.ini"
    
    try:
        shutil.copyfile(src=src, dst=dst)
    except:
        logger.log("!!!!!Error setting tarkov settings back to user default!!!!!")
        pass
    
    
    logger.log(f"\n\nLoaded default config from {src}\n\n")
    