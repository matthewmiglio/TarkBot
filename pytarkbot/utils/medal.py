import os
import psutil
import atexit


# method to get a list of program names, and their PIDs
def get_programs():
    for proc in psutil.process_iter():
        try:
            # print name
            name = proc.name()
            pid = proc.pid

            print(pid, name)

        except:
            pass


def get_medal_pids():
    pids = []

    try:
        for process in psutil.process_iter():
            try:
                name = process.name()
                pid = process.pid

                if "Medal" in name or "medal" in name:
                    pids.append(pid)
            except:
                pass
    except:
        pass

    return pids


# method to close a process given a PID
def close_program(pid):
    try:
        process = psutil.Process(pid)
        process.terminate()
        return True
    except:
        pass

    return False


def close_all_medal():
    pids = get_medal_pids()
    print(f"Closing {len(pids)} medal instances...")

    for pid in pids:
        close_program(pid)
    print(f"Closed {len(pids)} medal instances!")


def get_medal_base_path():
    # using registrey to get the path:
    # ntuser > root > software > microsoft > windows > currentversion > uninstall > medal

    # get the path from the registry:
    import winreg

    # open the registry key
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Medal",
    )

    # get the value of the key
    path = winreg.QueryValueEx(key, "InstallLocation")[0]

    return path


@atexit.register
def restore_medal():
    # get the base path
    try:
        base_path = get_medal_base_path()

        # get the exe path
        exe_path = os.path.join(base_path, "Medal.exe")

        # run the exe
        os.system(f"start {exe_path}")
    except:
        pass


close_all_medal()
