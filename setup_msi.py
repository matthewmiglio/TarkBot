import sys

from cx_Freeze import Executable, setup

product_name = "py-tarkbot"

try:
    version = sys.argv[sys.argv.index("--target-version") + 1]
except ValueError:
    version = "dev"


bdist_msi_options = {
    "upgrade_code": "{494bebef-6fc5-42e5-98c8-e63457934579}",
    "add_to_path": False,
    "initial_target_dir": f"[ProgramFilesFolder]\\{product_name}",
    "summary_data": {
        "author": "Matthew Miglio, Martin Miglio",
        "comments": "A bot for Escape from Tarkov's Flee Market",
        "keywords": "tarkov bot automation",
    },
}


# GUI applications require a different base on Windows
base = None
# if sys.platform == 'win32':
#    base = 'Win32GUI'

exe = Executable(
    script="pytarkbot\\__main__.py",
    base=base,
    shortcut_name=f"{product_name} {version}",
    shortcut_dir="DesktopFolder",
    target_name=f"{product_name}.exe",
    copyright="2022 Matthew Miglio",
)

setup(
    name=product_name,
    description="Tarkov Automated",
    executables=[exe],
    options={
        "bdist_msi": bdist_msi_options,
        "build_exe": {"excludes": ["test", "setuptools"]},
    },
)
