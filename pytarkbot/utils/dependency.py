import re
import subprocess
import tempfile
import tkinter.messagebox
from os import close, environ
from os.path import abspath, join, pardir
from pathlib import Path
from winreg import HKEY_LOCAL_MACHINE, ConnectRegistry, OpenKey, QueryValueEx

import requests
from bs4 import BeautifulSoup


def install_tesseract() -> None:
    tess_url = "https://digi.bib.uni-mannheim.de/tesseract/"

    # parse the table of files on the tesseract download page
    text = requests.get(tess_url, timeout=10).text
    soup = BeautifulSoup(text, "html.parser")
    table = soup.find("table")
    if table is None:
        raise RuntimeError("Could not find tesseract download table")
    rows = table.find_all("tr")  # type: ignore
    headers = [col.text for col in rows[0].find_all("th")]
    files = []
    for row in rows[1:]:
        values = [col.text for col in row.find_all("td")]
        file_info = dict(zip(headers, values))
        # filter out files that either dont have a name or dont match r'tesseract-ocr-w64-setup.*\.exe'
        if "Name" in file_info and re.match(
            r"tesseract-ocr-w64-setup.*\.exe", file_info["Name"]
        ):
            del file_info[""]  # remove empty column
            files.append(file_info)

    # get the latest file
    latest = sorted(files, key=lambda f: f["Last modified"], reverse=True)[0]

    # download the file to a temp directory
    url = tess_url + latest["Name"]
    print(f"Downloading {url}")
    r = requests.get(url, allow_redirects=True, timeout=10)

    # create the temp file
    fd, temp_path = tempfile.mkstemp()
    close(fd)  # close the file descriptor
    with open(temp_path, "wb") as temp:
        # save the file to a temp directory
        temp.write(r.content)
    # run the installer with subprocess
    print(f"Running {temp_path}")
    subprocess.run([temp_path], check=True)
    print("Tesseract installed")
    environ["TESSERACT_PATH"] = get_tesseract_path()


def get_tesseract_path() -> str:
    try:
        akey = r"SOFTWARE\Tesseract-OCR"
        areg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
        akey = OpenKey(areg, akey)
    except FileNotFoundError:
        akey = r"SOFTWARE\WOW6432Node\Tesseract-OCR"
        areg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
        akey = OpenKey(areg, akey)
    tess_path = str(join(abspath(QueryValueEx(akey, "path")[0]), "tesseract.exe"))
    # check if the path exists
    if not Path(tess_path).exists():
        raise FileNotFoundError(
            f"Tesseract path {tess_path} does not exist. Please install Tesseract."
        )
    return tess_path


def get_bsg_launcher_path() -> str:
    """get the path to the bsg launcher"""
    try:
        akey = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{B0FDA062-7581-4D67-B085-C4E7C358037F}_is1"
        areg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
        akey = OpenKey(areg, akey)
    except FileNotFoundError:
        akey = r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{B0FDA062-7581-4D67-B085-C4E7C358037F}_is1"
        areg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
        akey = OpenKey(areg, akey)
    launcher_file = abspath(
        join(QueryValueEx(akey, "InstallLocation")[0], "BsgLauncher.exe")
    )
    if not Path(launcher_file).exists():
        try:
            akey = (
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\EscapeFromTarkov"
            )
            areg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
            akey = OpenKey(areg, akey)
        except FileNotFoundError:
            akey = r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\EscapeFromTarkov"
            areg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
            akey = OpenKey(areg, akey)
        launcher_file = abspath(
            join(
                QueryValueEx(akey, "InstallLocation")[0],
                pardir,
                "BsgLauncher",
                "BsgLauncher.exe",
            )
        )
    return launcher_file


# on import, check if tesseract is installed, if not, install it
try:
    get_tesseract_path()
except FileNotFoundError as exc:
    if tkinter.messagebox.askyesno(
        "Tesseract OCR not found",
        "py-TarkBot requires Tesseract to run but it was not found.\n\n"
        + "Download and Install Tesseract OCR now?",
        icon="warning",
    ):
        install_tesseract()
    else:
        raise RuntimeError("Tesseract OCR not found") from exc
