import sqlite3, requests, json, googlemaps, numpy as np, sys, urllib.parse
from flask import Flask, render_template, request
from datetime import datetime

def get_db_connection():
    dbconnect = sqlite3.connect('friendfinder.db')
    dbconnect.row_factory = sqlite3.Row
    return dbconnect

app = Flask(__name__)

@app.route("/")
def index():
    friends = get_friends_list()
    return render_template('index.html', friends = friends, nearby_results = '', api_key = api_key, center = '')

@app.route('/placesearch', methods=['POST'])
def placesearch():
    activity = request.form['activity']
    if not activity:
        activity = ''
    time = request.form['time']
    locations = []
    for i in range(0,1000):
        current = 'friendaddress' + str(i)
        if current in request.form:
            temp = request.form['friendaddress' + str(i)]
            temp = temp.split(",")
            temp[0] = float(temp[0])
            temp[1] = float(temp[1])
            locations.append(temp)
    #get the center coords of the addresses
    center_coords = get_geocenter(locations)
    print("Coords: ", center_coords)
    print("Type: ",type(center_coords))
    #set radius each time it's called
    results_min = 10  #how many results
    min_radius = 300 #meters
    max_radius = 60000 #largest it will search
    search_radius = min_radius
    radius_grow_rate = 1 
    radius_grow_rate_min = 0.1 #for rate scaling
    
    search_success = False
    while not search_success:
        nearby_results = gmaps.places_nearby(center_coords, search_radius, keyword = activity, open_now=True)
        #check the status
        query_status = nearby_results['status']   
        if query_status == "ZERO_RESULTS":
            search_radius += search_radius*radius_grow_rate
        elif search_radius >= max_radius:
            #try an error
            raise Exception("Max search radius exceeded")
            break #out of the
        else:
            results = nearby_results.get('results')
            results_cnt = len(results)
            #check how many results were returned
            if results_cnt < results_min: #not enough results, grow radius
                search_radius += search_radius*radius_grow_rate
            else: #we have have enough
                search_success = True
        #scaling radius rate is working
        if radius_grow_rate > radius_grow_rate_min: 
            radius_grow_rate -= radius_grow_rate/10  #dynamically shrink rate as radius grows larger
            #print("radius grow rate ",radius_grow_rate, "rate min ", radius_grow_rate_min)
    #end of while
    nearby_results_filtered = []
    for results in results:
        nearby_results_filtered.append([results.get('name'), results.get('vicinity'), results.get('rating')])
    friends = get_friends_list()
    return nearby_results

def get_friends_list():
    dbconnect = get_db_connection()
    friends = dbconnect.execute('SELECT * FROM users').fetchall()
    dbconnect.close()
    return friends

# This function will be called when a 500 error occurs
@app.errorhandler(500)
def internal_server_error(error):
    return render_template('error.html', error=error), 500

#get data from homepage and send to result.html
@app.route('/result', methods=['POST'])
def process_input():
    currently_open = True #look for items that are open can be set in webpage later
    keyword = request.form['keyword']
    address1 = request.form['address1']
    address2 = request.form['address2']
    address3 = request.form['address3']
    address4 = request.form['address4']
    address5 = request.form['address5']
    address6 = request.form['address6']
    address7 = request.form['address7']
    address7 = request.form['address8']
    # Initialize an empty list to store the addresses
    #addresses_list = [] #list for address inputs
    addresses_coords = [] #list of coord pairs of the addresses
    # Loop through each address
    for i in range(1, 9):
        address_name = f"address{i}"  # Assumes address names are address1, address2, etc.
        address_value = request.form.get(address_name)  # Assumes you are using Flask or similar framework
        # Check if the address has a value
        if address_value:
            # If the address has a value, add it to the list
            geocoded_address = gmaps.geocode(address_value)
            addresses_coords.append(get_coords(geocoded_address))
            #addresses_list.append(address_value)
    
    #get the center coords of the addresses
    center_coords = get_geocenter(addresses_coords)
    print("Coords: ", center_coords)
    print("Type: ",type(center_coords))
    #set radius each time it's called
    results_min = 10  #how many results
    min_radius = 300 #meters
    max_radius = 60000 #largest it will search
    search_radius = min_radius
    radius_grow_rate = 1 
    radius_grow_rate_min = 0.1 #for rate scaling
    
    search_success = False
    while not search_success:
        nearby_results = gmaps.places_nearby(center_coords, search_radius, keyword = keyword, open_now=currently_open)
        #check the status
        query_status = nearby_results['status']   
        if query_status == "ZERO_RESULTS":
            search_radius += search_radius*radius_grow_rate
        elif search_radius >= max_radius:
            #try an error
            raise Exception("Max search radius exceeded")
            break #out of the
        else:
            results = nearby_results.get('results')
            results_cnt = len(results)
            #check how many results were returned
            if results_cnt < results_min: #not enough results, grow radius
                search_radius += search_radius*radius_grow_rate
            else: #we have have enough
                search_success = True
        #scaling radius rate is working
        if radius_grow_rate > radius_grow_rate_min: 
            radius_grow_rate -= radius_grow_rate/10  #dynamically shrink rate as radius grows larger
            #print("radius grow rate ",radius_grow_rate, "rate min ", radius_grow_rate_min)
    #end of while



    #for weekday index
    weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    #get hours by calling places(), and adding to results[]
    getfields = ['current_opening_hours','opening_hours']
    for x in range(len(results)):
        results_place_id = results[x]['place_id']
        details = gmaps.place(results_place_id, session_token=None, fields=getfields)
        #print currently open yes or no
        currently_open = details['result']['opening_hours']['open_now']
        opening_hours = details['result']['current_opening_hours']
        current_day = datetime.today().weekday()
        #print todays hours - what we want
        todays_hours = opening_hours['weekday_text'][current_day]
        results[x]['hours'] = todays_hours
        # Get the name of the current day
        #current_day_name = weekday_names[current_day]
        # Print the opening hours for today with the day of the week
        #print(current_day_name + "'s hours: ", todays_hours,"\n\n")       
    
    #trying to get map working but its giving a 'staticmaperror' on the webpage
    # Generate the URL for the static map
 #   for coords in center_coords:
#        str_center_coords = ', '.join(str(coords))
    str_center_coords = ', '.join('{:.6f}'.format(coord) for coord in center_coords)
    print(str_center_coords)
    params = {
        'center': str_center_coords,
        'zoom': '14',
        'size': '640x400',
        'maptype': 'roadmap',
        'key': api_key
    }
    print("Params: ",params)
    #works with string
    url = 'https://maps.googleapis.com/maps/api/staticmap?' + urllib.parse.urlencode(params)

    #return render_template('result.html', results=results, details=hours)
    return render_template('result.html', results=results,
                           center_coords=center_coords,
                           keyword=keyword,
                           static_map_url=url)


def get_geocenter(coord_list):
  #Takes a coord pair list
  #Returns avg of coordinate pair
  #NOTE: If the earth were flat, this would be accurate, but good enough
  #A more accurate version here (ver2)
  #https://stackoverflow.com/questions/37885798/how-to-calculate-the-midpoint-of-several-geolocations-in-python
  average = [sum(x)/len(x) for x in zip(*coord_list)]
  return average

#takes output of gmaps.geocode()
def get_coords(geo_address):
  geometry = geo_address[0].get('geometry')
  location = geometry.get('location')
  lat = location['lat']
  lng  = location['lng']
  coords = [lat,lng]
  return coords

#Client API key
api_key = "AIzaSyAjaIAjo2SAuqzSqFSjNDcyM_vUQgagA6c"
gmaps = googlemaps.Client(key=api_key)