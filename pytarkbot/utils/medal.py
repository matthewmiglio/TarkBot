import psutil

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


close_all_medal()
