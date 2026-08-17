import os
import sys
import locale


if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


##
BLACKLIST_TEMP = {}

## ROUTES
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SRC_DIR)
USERDATA_DIR = os.path.join(ROOT_DIR, "assets", "userdata")


## FILES
GLOBAL_USERDATA_FILES = ["proxies.txt", "useragents.txt"]
USERDATA_WEBSITES_FILES = ["authorizations.txt", "cookies.txt", "refreshtokens.txt", "fingerprints.txt", "users_id.txt", "last_rewards.txt"]
USERDATA_FILES = GLOBAL_USERDATA_FILES + USERDATA_WEBSITES_FILES
USERDATA = {f: {} for f in USERDATA_FILES}


## UI
ASCII_TITLE = r"""
   _______                   ___ ___                
  |   _   |.--.--.-----.    |   |   |               
  |       ||  |  |  -__|    |-     -|               
  |___|___| \___/|_____|    |___|___|               
                                                  
   _____                           __               
  |     |_.---.-.--.--.-----.----.|  |--.-----.----.
  |       |  _  |  |  |     |  __||     |  -__|   _|
  |_______|___._|_____|__|__|____||__|__|_____|__|""" + "\n\n"
PRIMARY_COLOR = "#ffe37d"
ERROR_COLOR = "#FF5E5E"
SUCCESS_COLOR = "#6EFF69"
DIV_TEXT = f"{'─' * 40}"


## WEBSITES CONFIGS
WEBSITE_CONFIG = {
    "MM2WILD": {
        "URL": "https://mm2wild.com",
        "SITEKEY": "0x4AAAAAACO5aJWBw_BqLmoe"
    },
    "HarvesterGG": {
        "URL": "https://harvester.gg",
        "SITEKEY": "0x4AAAAAABmYnXTFqSjG46kr"
    }
}
