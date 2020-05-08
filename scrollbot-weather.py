#3 hourly forecast URL = http://datapoint.metoffice.gov.uk/public/data/val/wxfcs/all/json/<locationid>?res=3hourly&key=<key>

import time
import datetime
import httplib
import sys
import json
import os.path
import scrollphathd as sphd

SETTINGS_FILE             = ".scrollbot-weather-settings.json"
FORECAST_FILE             = "scrollbot-weather-forecast.json"
FORCAST_POLL_DELAY        = datetime.timedelta(minutes=15)
MESSAGE_UPDATE_POLL_DELAY = datetime.timedelta(minutes=5)
METOFFICE_URL             = "datapoint.metoffice.gov.uk"
REQ_BASE                  = "/public/data/val/wxfcs/all/json/"

WEATHER_TYPE_MAP = {
#   Met Office weather code     Type
    "NA":                       "Unknown",
    "0":                        "Clear",
    "1":                        "Sunny",
    "2":                        "Partly cloudy",
    "3":                        "Partly cloudy",
    "4":                        "Unknown",
    "5":                        "Misty",
    "6":                        "Foggy",
    "7":                        "Cloudy",
    "8":                        "Overcast",
    "9":                        "Light rain showers",
    "10":                       "Light rain showers",
    "11":                       "Drizzle",
    "12":                       "Light rain",
    "13":                       "Heavy rain showers",
    "14":                       "Heavy rain showers",
    "15":                       "Heavy rain",
    "16":                       "Sleet showers",
    "17":                       "Sleet showers",
    "18":                       "Sleet",
    "19":                       "Hail showers",
    "20":                       "Hail showers",
    "21":                       "Hail",
    "22":                       "Light snow showers",
    "23":                       "Light snow showers",
    "24":                       "Light snow",
    "25":                       "Heavy snow showers",
    "26":                       "Heavy snow showers",
    "27":                       "Heavy snow",
    "28":                       "Thunder showers",
    "29":                       "Thunder showers",
    "30":                       "Thunder"
}

DAY_OF_WEEK = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday"
}

def make_metoffice_request(settings):
    REQUEST = REQ_BASE + settings["location_id"] + "?res=3hourly&key=" + settings["api_key"]
    try:
        conn = httplib.HTTPConnection(METOFFICE_URL)
        conn.request("GET", REQUEST)
        resp = conn.getresponse()
        data = resp.read()
    except Exception as err:
        print err
        return None
    else:
        return data

def get_forecast_json(settings):
    json_data = None
    if os.path.exists(FORECAST_FILE):
        last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(FORECAST_FILE))
        if last_modified + FORCAST_POLL_DELAY > datetime.datetime.now():
            f = open(FORECAST_FILE, "r")
            json_data = f.read()
            return json_data

    if json_data == None:
        print "downloading latest forcast at {0}".format(time.strftime('%Y/%m/%d %H:%M:%S'))
        json_data = make_metoffice_request(settings)
        if json_data == None:
            return None
        
        f = open(FORECAST_FILE, "w")
        f.write(json_data)

    return json_data
        
def get_forecast(settings):
    forecast_json = None
    try:
        forecast_json = json.loads(get_forecast_json(settings))
    except Exception as err:
        os.remove(FORECAST_FILE)
        return None
    
    forecast = []
    for day in xrange(2):
        day_forecast = forecast_json["SiteRep"]["DV"]["Location"]["Period"][day]["Rep"]
        date_string = forecast_json["SiteRep"]["DV"]["Location"]["Period"][day]["value"]
        date = datetime.datetime.strptime(date_string, "%Y-%m-%dZ")

        forecasts_in_day = []

        for timeslot in xrange(len(day_forecast)):
            minutes = int(day_forecast[timeslot]["$"])
            date_and_time = date + datetime.timedelta(minutes=minutes)
            time_string = date_and_time.strftime('%H:%M')

            if datetime.datetime.now() > date_and_time:
                continue
            
            weather_type = day_forecast[timeslot]["W"]
            temperature = day_forecast[timeslot]["T"]
            forecasts_in_day.append((time_string, weather_type, temperature))

        day_string = "";
        if day == 0:
            day_string = "Today"
        else:
             day_string = DAY_OF_WEEK[date.weekday()]
        forecast.append((day_string, forecasts_in_day))
        
    return forecast

def get_forecast_string(forecast=None):
    if forecast == None:
        return "Unable to get forecast     "
    
    forecast_string = ""
    for day in forecast:
        day_string, forecasts_in_day = day
        forecast_string += day_string
        forecast_string += ": "
        for forecast_in_day in forecasts_in_day:
            time_string, weather_type, temperature = forecast_in_day
            forecast_string += time_string
            forecast_string += " "
            forecast_string += WEATHER_TYPE_MAP[weather_type]
            forecast_string += " "
            forecast_string += temperature
            forecast_string += "C   "
        forecast_string += "  "

    forecast_string += "   "
    return forecast_string

def read_settings(settings_file=None):
    if settings_file == None:
        return None
    
    if not os.path.exists(settings_file):
        return None
        
    f = open(settings_file, "r")
    settings_json_data = f.read()
    try:
        return json.loads(settings_json_data)
    except Exception as err:
        return None
    

if __name__ == "__main__":
    settings = read_settings(SETTINGS_FILE)
    if settings == None:
        print "Couldn't find settings file "+SETTINGS_FILE
        print "Please create a JSON file with keys location_id and api_key"
        exit(1)

    print '-'*20
    print "Location id: {0}".format(settings["location_id"])
    print '-'*20
    sphd.rotate(180)
    
    last_updated = datetime.datetime.min
    while True:
        if last_updated + MESSAGE_UPDATE_POLL_DELAY < datetime.datetime.now():
            forecast = get_forecast(settings)
            forecast_string = get_forecast_string(forecast)
            print "Updating forecast to: {0}".format(forecast_string)
            sphd.clear()
            sphd.write_string(forecast_string, brightness=0.03)
            last_updated = datetime.datetime.now()
        
        for xPos in xrange(len(forecast_string) * 6):
            sphd.show()
            sphd.scroll(1)
            time.sleep(0.02)
