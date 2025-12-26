from setuptools import setup
import os

APP = ['../TkStaticVideoGenerator.py']
APP_NAME = "StaticVideoGenerator"

OPTIONS = {
    'argv_emulation': False, # Set to False to prevent terminal-like behavior
    'packages': ['PIL', 'tkinterdnd2'],
    'plist': {
        'CFBundleName': APP_NAME,
        'CFBundleDisplayName': APP_NAME,
        'CFBundleIdentifier': "com.yourname.staticvideogenerator",
        'CFBundleVersion': "1.0.0",
        'CFBundleShortVersionString': "1.0.0",
        'LSMinimumSystemVersion': '10.10',
        'NSHighResolutionCapable': True,
    },
}

setup(
    app=APP,
    name=APP_NAME,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
