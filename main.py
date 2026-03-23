from camoufox.sync_api import Camoufox
import json
import time
import random
from settings import *
from curl_cffi import requests as cffi_requests
from new_parser import get_connection, parse_and_store

# Utils

def random_delay():
    random_delay = random.uniform(SLEEP_TIME_MIN, SLEEP_TIME_MAX)
    print(f"Waiting for {random_delay:.2f} seconds")
    time.sleep(random_delay)

# Cookies
    
def get_cookies(url, force=False) -> dict:
    if not force and os.path.exists(COOKIES_PATH):
        saved = json.load(open(COOKIES_PATH))
        if time.time() < saved["expires"]:
            print("Using saved cookies")
            return saved["cookies"]
    print("Generating new cookies")
    return generate_cookies(url, output_file=COOKIES_PATH)

def generate_cookies(url, output_file=COOKIES_PATH):

    """Use Camoufox to navigate to the URL and extract cookies"""

    with Camoufox(humanize=2, headless="virtual", ) as browser:
        page = browser.new_page()
        page.goto("https://www.goldbet.it/scommesse/sport/calcio/italia/serie-a")
        page.wait_for_load_state('networkidle')
        
        cookies_list = page.context.cookies()

        # Use earliest expiring cookie, fall back to manual TTL
        expiring = [c["expires"] for c in cookies_list if c.get("expires", -1) > 0]
        expires = min(expiring) if expiring else time.time() + 6 * 3600

        cookies = {c["name"]: c["value"] for c in cookies_list}

        json.dump({
            "expires": expires,   # unix timestamp from the cookie itself
            "cookies": cookies
        }, open(output_file, "w"))
        
        return cookies


# Fetch data

def fetch_event(tai: int, ti: int, mi: int, ei: int):

    """ Fetch all tabs for a given event.\n
     tai: tournament area id\n
     ti: tournament id\n
     mi: match internal id\n
     ei: event id
    """

    tbI = 0 # Tab principale
    page = 0 # Always 0

    # Fetch first tab to get the list of all tabs for this event

    url = f"{API_URL_DETAILS}/{tai}/{ti}/{mi}/{ei}/{tbI}/{page}"
    tab_ids = fetch_tab(url, ei, tbI, catalog=True)
    random.shuffle(tab_ids)

    # Fetch all tabs for this event

    for tbI in tab_ids[1:4]:
        url = f"{API_URL_DETAILS}/{tai}/{ti}/{mi}/{ei}/{tbI}/{page}"
        fetch_tab(url, ei, tbI)


def fetch_tab(url: str, ei: int, tbI: int, catalog : bool = False):
    
    """ 
    Fetch a single tab for a given event.\n
     url: API URL, format: {API_URL_DETAILS}/{tai}/{ti}/{mi}/{ei}/{tbI}/{page}\n
     ei: event id\n
     tbI: tab id\n
     catalog: whether to return a list of tab ids\n
    """
    random_delay()

    # Check cookies exp date and regenerate if needed
    cookies = get_cookies(url)

    session = cffi_requests.Session(impersonate="firefox", cookies=cookies)  # Firefox since UA is Firefox
    session.headers.update(HEADERS)

    print(f"Fetching {url}")
    resp = session.get(url)
    
    if resp.status_code != 200:
        print(f"Error fetching {url}: {resp.status_code}")
        return None

    # Save to database
    data = resp.json()
    conn = get_connection()
    parse_and_store(data, conn)

    print(f"Saved data for event {ei} tab {tbI}")

    if catalog:
        data = resp.json()["lmtW"]
        tab_ids = [item["tbI"] for item in data if "tbI" in item]
        return tab_ids

def fetch_event_ids(ti: int) -> list[int]:

    """ Fetch the event IDs for a given tournament id.\n
     ti: tournament id\n
    """

    random_delay()

    url = f"{API_URL_OVERVIEW}/0/1/0/{ti}/0/0/0"

    # Check cookies exp date and regenerate if needed
    cookies = get_cookies(url)

    session = cffi_requests.Session(impersonate="firefox", cookies=cookies)  # Firefox since UA is Firefox
    session.headers.update(HEADERS)

    print(f"Fetching {url}")
    resp = session.get(url)
    
    if resp.status_code != 200:
        print(f"Error fetching {url}: {resp.status_code}")
        return None

    data = resp.json()["leo"]
    event_ids = [item["ei"] for item in data if "ei" in item]

    return event_ids

if __name__ == "__main__":
    ti = 93
    event_ids = fetch_event_ids(ti)

    end = len(event_ids) if len(event_ids) < 3 else 3

    for ei in event_ids[:end]:
        fetch_event(tai=0, ti=ti, mi=0, ei=ei)
    