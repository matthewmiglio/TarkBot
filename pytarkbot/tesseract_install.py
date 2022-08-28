from os import environ, makedirs
from os.path import dirname, exists, expandvars, join, normpath
from socket import gaierror
from subprocess import call
from urllib.request import urlretrieve
from winreg import HKEY_LOCAL_MACHINE, ConnectRegistry, OpenKey, QueryValueEx

from pandas import read_html
from requests.exceptions import ConnectionError
from tqdm import tqdm
from urllib3.exceptions import MaxRetryError, NewConnectionError

top_level = join(expandvars(f'%appdata%'), "py-TarkBot")
install_info_file = join(top_level, 'tesseract_install.json')


class DownloadProgressBar(tqdm):
    """Progress bar for downloasd

    Args:
        tqdm (class): tqdm class
    """

    def update_to(self, b=1, bsize=1, tsize=None) -> None:
        """override update_to of tqdm class

        Args:
            b (int, optional): Defaults to 1.
            bsize (int, optional): Defaults to 1.
            tsize (_type_, optional): Defaults to None.
        """
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


def download_from_url(url: str, output_dir: str, file_name: str) -> str | None:
    """Downloads a file from a url to a directory with a specified file name

    Args:
        url (str): url of item to download
        output_dir (str): directory to save file
        file_name (str): name of file to save

    Raises:
        ValueError: thrown when url does not specify an http or https endpoint

    Returns:
        str | None: returns the path to the file or None if not downloaded
    """
    if not url.lower().startswith('http'):
        raise ValueError from None
    if not exists(join(output_dir, file_name)):
        # remove_previous_downloads(cache_dir)
        try:
            with DownloadProgressBar(
                    unit='B',
                    unit_scale=True,
                    miniters=1,
                    desc=url.split('/')[-1]) as t:
                urlretrieve(
                    url,
                    filename=join(output_dir, file_name),
                    reporthook=t.update_to
                )  # nosec
            return join(output_dir, file_name)
        except (ConnectionError, MaxRetryError, NewConnectionError, gaierror):
            print(
                f'Connection error while trying to download {url} to {join(output_dir, file_name)}')
            return None
    print(f'File already downloaded from {url}.')
    return join(output_dir, file_name)


def make_cache() -> str:
    """creates a cache directory for downloaded installer

    Returns:
        str: the path to the cache directory
    """
    cache_dir = join(dirname(__file__), 'cache')
    if not exists(cache_dir):
        makedirs(cache_dir)
    return cache_dir


def get_tsrct_link() -> list[str] | None:
    """retrieves the link to the latest tesseract download

    Returns:
        list[str] | None: returns a a list of strings as [url, name of file] or None if not found
    """
    url = r"http://digi.bib.uni-mannheim.de/tesseract/"
    ver_df = read_html(url)[0]
    latest_ver = ver_df[
        ver_df['Description'].str.contains("latest", na=False)
    ]['Name'].values[0]
    print(f'Latest version of tesseract is {latest_ver}.')
    return [url + latest_ver, latest_ver] if latest_ver is not None else None


def run_installer(path: str) -> bool:
    """runs a specified installer executable

    Args:
        path (str): path to installer executable

    Returns:
        bool: if install was successful
    """
    return 0 == call(path, shell=False)


def install_dependencies(dependencies: dict[str, list[str] | None]) -> None:
    """installs a list of dependencies from a supplied dictionary

    Args:
        dependencies (dict[str, list[str]  |  None]): a dictioinary of dependencies names and their url
    """
    cache_dir = make_cache()
    for name, download_info in dependencies.items():
        if download_info is not None:
            file_url = download_info[0]
            file_name = download_info[1]
            print(f'Downloading {name} from {file_url} to {cache_dir}.')
            installer_path = download_from_url(file_url, cache_dir, file_name)
            if installer_path is not None:
                print(f'Executing {installer_path}')
                run_installer(installer_path)
        else:
            print(f'Download for {name} is not found.')


def get_tsrct_path() -> str:
    """locate the path of the tesseract directory

    Returns:
        str: the path of the tesseract directory
    """
    try:
        akey = r"SOFTWARE\Tesseract-OCR"
        areg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
        akey = OpenKey(areg, akey)
    except FileNotFoundError:
        akey = r"SOFTWARE\WOW6432Node\Tesseract-OCR"
        areg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
        akey = OpenKey(areg, akey)
    return str(normpath(QueryValueEx(akey, "path")[0]))


def install_tesseract() -> None:
    """install the latest version of tesseract
    """
    dependency_dict = {
        "tesseract": get_tsrct_link()
    }
    install_dependencies(dependency_dict)


def setup_tesseract() -> None:
    """define the environmental variables related to tesseract, install tesseract if neccessary
    """
    try:
        tesseract_path = get_tsrct_path()
    except FileNotFoundError:
        install_tesseract()
        tesseract_path = get_tsrct_path()
    environ["TESSDATA_PREFIX"] = str(join(tesseract_path, 'tessdata'))
    environ["TESSERACT_PATH"] = str(join(tesseract_path, "tesseract.exe"))
