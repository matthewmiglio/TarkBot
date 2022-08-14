import os
from glob import glob

from setuptools import setup

with open("README.md", "r", encoding="utf-8") as f:
    LONG_DESCRIPTION = f.read()

# get github workflow env vars
try:
    version = (os.environ['GIT_TAG_NAME']).replace('v', '')
except KeyError:
    print('Defaulting to 0.0.0')
    version = '0.0.0'

# get files to include in dist
dist_files = [file.replace('pytarkbot/', '')
              for file in glob("pytarkbot/reference_images/*/*.png")]

setup(
    name='py-tarkbot',
    version=version,
    description='Tarkov Flea Automated',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    license='',
    keywords='',
    author='Matthew Miglio',
    url='https://github.com/matthewmiglio/py-TarkBot',
    download_url='https://github.com/matthewmiglio/py-TarkBot/releases',
    install_requires=[
        "pyautogui",
        "numpy",
        "pygetwindow",
        "Pillow",
        "opencv-python",
        "joblib",
        "pytesseract",
        "keyboard",
        "matplotlib",
        "PySimpleGUI",
        
    ],
    packages=['pytarkbot'],
    include_package_data=True,
    package_data={'pytarkbot': dist_files},
    python_requires='>=3.10',
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'pytarkbot = pytarkbot.__main__:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3.10',
    ],
)
