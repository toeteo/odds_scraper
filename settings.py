import os

DB_PATH = "odds.db"

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
RESOURCES_PATH = os.path.join(DIR_PATH, "resources")
RESPONSES_PATH = os.path.join(RESOURCES_PATH, "responses")
PARSED_PATH = os.path.join(RESOURCES_PATH, "parsed")

COOKIES_PATH = os.path.join(DIR_PATH, "cookies.json")

HEADERS = {
        "User-Agent":       "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
        "Accept":           "application/json, text/plain, */*",
        "Accept-Language":  "en-US,en;q=0.9",
        "X-Brand":          "1",
        "X-IdCanale":       "1",
        "X-AcceptConsent":  "false",
        "X-Verticale":      "1",
        "Content-Type":     "application/json",
        "Referer":          "https://www.goldbet.it/scommesse/sport/calcio/italia/serie-a",
        "Sec-Fetch-Dest":   "empty",
        "Sec-Fetch-Mode":   "cors",
        "Sec-Fetch-Site":   "same-origin",
    }

API_URL_DETAILS = "https://www.goldbet.it/api/sport/pregame/getDetailsEventAams"
API_URL_OVERVIEW = "https://www.goldbet.it/api/sport/pregame/getOverviewEventsAams"

SLEEP_TIME_MIN = 1
SLEEP_TIME_MAX = 10