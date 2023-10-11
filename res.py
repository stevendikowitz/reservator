import requests
import datetime
import time
from config import DATA
from requests_toolbelt.utils import dump
import pprint

pp = pprint.PrettyPrinter(indent=4)

headers = {
    "authority": "api.resy.com",
    "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="99", "Google Chrome";v="99"',
    "x-origin": "https://resy.com",
    "sec-ch-ua-mobile": "?0",
    "authorization": 'ResyAPI api_key="VbWk7s3L4KiK5fzlO7JD3Q5EYolJI7n5"',
    "accept": "application/json, text/plain, */*",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36",
    "cache-control": "no-cache",
    "sec-ch-ua-platform": '"Windows"',
    "origin": "https://resy.com",
    "sec-fetch-site": "same-site",
    "sec-fetch-mode": "cors",
    "sec-fetch-dest": "empty",
    "referer": "https://resy.com/",
    "accept-language": "en-US,en;q=0.9",
}


def login(username, password):
    data = {"email": username, "password": password}

    response = requests.post(
        "https://api.resy.com/3/auth/password", headers=headers, data=data
    )
    res_data = response.json()
    # pp.pprint(res_data)
    auth_token = res_data["token"]
    payment_method_string = '{"id":' + str(res_data["payment_method_id"]) + "}"
    return auth_token, payment_method_string


def find_table(res_date, party_size, table_time, auth_token, venue_id):
    # convert datetime to string
    day = res_date.strftime("%Y-%m-%d")
    ct = datetime.datetime.now()
    ct = ct.strftime("%H:%M:%S")
    print(f"[{ct}]:  Trying {day} for {str(venue_id)}...\n")
    params = (
        # ("x-resy-auth-token", auth_token),
        ("day", day),
        ("lat", "0"),
        ("long", "0"),
        ("party_size", str(party_size)),
        ("venue_id", str(venue_id)),
    )
    headers["x-resy-auth-token"] = auth_token
    headers[
        "x-resy-universal-auth"
    ] = "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9.eyJleHAiOjE3MDA4NzkyMjEsInVpZCI6OTM4ODA0OCwiZ3QiOiJjb25zdW1lciIsImdzIjpbXSwibGFuZyI6ImVuLXVzIiwiZXh0cmEiOnsiZ3Vlc3RfaWQiOjQzNDcwNTg2fX0.AIaD2v342CzwkNlJnKPdHs_fHWUC-LBc22jd05meHL1BiSmRGVXzBJjA2ye9swpuIYHRGn6fdxs9KxX4KiVkyztAAby4ATRxhftRnMjA5brZ6Gg1BqTHXVFO_wyv9-zIupnw7NaKjUqsc0cf4fJ8aOCGWLCBWFHtysV2t-8-XVnHEDi8"

    response = requests.get(
        "https://api.resy.com/4/find", headers=headers, params=params
    )
    data = response.json()
    results = data["results"]
    if len(results["venues"]) > 0:
        open_slots = results["venues"][0]["slots"]
        if len(open_slots) > 0:
            available_times = [
                (
                    k["date"]["start"],
                    datetime.datetime.strptime(
                        k["date"]["start"], "%Y-%m-%d %H:%M:00"
                    ).hour,
                )
                for k in open_slots
            ]
            closest_time = min(available_times, key=lambda x: abs(x[1] - table_time))[0]

            best_table = [k for k in open_slots if k["date"]["start"] == closest_time][
                0
            ]

            return best_table


def make_reservation(
    auth_token, config_id, res_date, party_size, payment_method_string
):
    # convert datetime to string
    day = res_date.strftime("%Y-%m-%d")
    party_size = str(party_size)
    params = (
        ("x-resy-auth-token", auth_token),
        ("config_id", str(config_id)),
        ("day", day),
        ("party_size", str(party_size)),
    )
    details_request = requests.get(
        "https://api.resy.com/3/details", headers=headers, params=params
    )
    details = details_request.json()
    book_token = details["book_token"]["value"]
    headers["x-resy-auth-token"] = auth_token
    data = {
        "book_token": book_token,
        "struct_payment_method": payment_method_string,
        "source_id": "resy.com-venue-details",
    }

    response = requests.post("https://api.resy.com/3/book", headers=headers, data=data)


def try_table(
    day, party_size, table_time, auth_token, restaurant, payment_method_string
):
    best_table = find_table(day, party_size, table_time, auth_token, restaurant)
    if best_table is not None:
        hour = datetime.datetime.strptime(
            best_table["date"]["start"], "%Y-%m-%d %H:%M:00"
        ).hour
        if (hour > 19) and (hour < 21):
            config_id = best_table["config"]["token"]
            make_reservation(
                auth_token, config_id, day, party_size, payment_method_string
            )
            print("success")
            return 1
    else:
        time.sleep(1)
        return 0


def readconfig():
    return DATA


def main():
    username, password, venue, dates, guests, venues = readconfig()
    auth_token, payment_method_string = login(username, password)
    print(
        "logged in succesfully - disown this task and allow it to run in the background"
    )
    party_size = int(guests)
    table_time = 20
    days = [datetime.datetime.strptime(date, "%m/%d/%Y") for date in dates]
    restaurant = int(venue)

    reserved = 0
    unreserved_restaurants = venues
    while len(unreserved_restaurants) > 0:
        for day in days:
            for restaurant in unreserved_restaurants:
                try:
                    reserved = try_table(
                        day,
                        party_size,
                        table_time,
                        auth_token,
                        int(restaurant),
                        payment_method_string,
                    )
                    if reserved == 1:
                        unreserved_restaurants = [
                            r for r in unreserved_restaurants if r != restaurant
                        ]
                    time.sleep(1)
                except Exception as e:
                    print(e)
                    raise e


main()
