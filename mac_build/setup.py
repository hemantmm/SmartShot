from setuptools import setup

APP = ['app_main.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'plist': {
        'CFBundleName': 'SmartShot',
        'CFBundleDisplayName': 'SmartShot',
        'CFBundleGetInfoString': "Automatically organize your screenshots using OCR-powered smart filenames",
        'CFBundleIdentifier': "com.smartshot.app",
        'CFBundleVersion': "1.0.0",
        'CFBundleShortVersionString': "1.0.0",
        'LSUIElement': True, # Runs as a menu bar app (no dock icon)
        'NSDesktopFolderUsageDescription': 'SmartShot needs access to your Desktop folder to detect and rename new screenshots automatically.',
        'NSDocumentsFolderUsageDescription': 'SmartShot needs access to your Documents folder in case you choose to save your screenshots there.',
    },
    'packages': ['rumps', 'smartshot', 'watchdog'],
    'includes': ['tkinter'],
}

setup(
    app=APP,
    name='SmartShot',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
)
