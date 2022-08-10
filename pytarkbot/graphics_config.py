import shutil


def save_default_settings_to_file(logger):
    try:
        #get user_default_settings_file
        default_settings_path=r"C:\Users\Matt\AppData\Roaming\Battlestate Games\Escape from Tarkov\Settings\Graphics.ini"

        #path to store default_settings
        default_settings_storage_path = r"C:\Users\Matt\Desktop\1\my Programs\Flee-Bot\config\user_default_config\Graphics.ini"

        #write user_defualt_settings to 
        src=default_settings_path
        dst=default_settings_storage_path
        shutil.copyfile(src, dst)
    except:
        pass
    
    logger.log("Saved current graphics settings to file.")


def set_tarkov_settings_to_bot_config(logger):
    try:
        #get user_default_settings_file
        default_settings_path=r"C:\Users\Matt\AppData\Roaming\Battlestate Games\Escape from Tarkov\Settings\Graphics.ini"
        default_settings_file = open(default_settings_path, "r")

        #get bot_settings_file
        bot_settings_path=r"C:\Users\Matt\Desktop\1\my Programs\Flee-Bot\config\config_for_bot\Graphics.ini"
        bot_settings_file = open(bot_settings_path, "r")

        #write bot settings to settings_file
        src=bot_settings_path
        dst=default_settings_path
        shutil.copyfile(src, dst)
    except:
        pass
    
    logger.log("Loaded bot config.")
    
    
def set_tarkov_settings_to_default_config(logger):
    try:
        #get user_default_settings_file from storage
        saved_default_settings_path=r"C:\Users\Matt\Desktop\1\my Programs\Flee-Bot\config\user_default_config\Graphics.ini"

        #get settings_file location
        current_settings_path=r"C:\Users\Matt\AppData\Roaming\Battlestate Games\Escape from Tarkov\Settings\Graphics.ini"

        #write bot settings to settings_file
        src=saved_default_settings_path
        dst=current_settings_path
        shutil.copyfile(src, dst)
    except:
        pass
    
    logger.log("Loaded default config.")