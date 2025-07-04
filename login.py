# Copying heavily from https://github.com/arty-name/livejournal-export/blob/master/export.py

import requests
from sys import exit as sysexit

def get_cookie_value(response, cName):
    try:
        header = response.headers.get('Set-Cookie')

        if header:
            return header.split(f'{cName}=')[1].split(';')[0]
        else:
            raise ValueError(f'Cookie {cName} not found in response.')

    except Exception as e:
        print(f"Error extracting required cookie: {cName}. Error: {e}. Exiting...")
        sysexit(1)

# Generic headers to prevent LiveJournal from throwing out this random solicitation
headers = {
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 OPR/113.0.0.0",
    "sec-ch-ua": '"Chromium";v="127"',
    "sec-ch-ua-platform": '"Windows"',
}


def login(username: str, password: str):
    # Get a "luid" cookie so it'll accept our form login.
    try:
        response = requests.get("https://www.livejournal.com/", headers=headers)
    except Exception as e:
        # If attempt to reach LiveJournal fails, error out.
        print(f"Could not retrieve pre-connection cookie from www.livejournal.com. Error: {e}. Exiting.")
        sysexit(1)

    cookies = {
        'luid': get_cookie_value(response, 'luid')
    }

    # Populate dictionary for request
    credentials = {
        'user': username,
        'password': password
    }

    print("Attempting to log in as", username)
    # Login with user credentials and retrieve the two cookies required for the main script functions
    response = requests.post("https://www.livejournal.com/login.bml", data=credentials, cookies=cookies)

    # If not successful, whine about it.
    if response.status_code != 200:
        print("Error - Return code:", response.status_code)

    # If successful, then get the 'Set-Cookie' key from the headers dict and parse it for the two cookies, placing them in a cookies dict
    cookies = {
        'ljloggedin': get_cookie_value(response, 'ljloggedin'),
        'ljmastersession': get_cookie_value(response, 'ljmastersession')
    }
    print("Successfully logged in")
    
    return cookies

