import sqlite3, requests, json, googlemaps, numpy as np, sys, urllib.parse
from flask import Flask, render_template, request, session, flash, g, current_app, redirect, url_for
from datetime import datetime

def get_db_connection():
    dbconnect = sqlite3.connect('friendfinder.db')
    dbconnect.row_factory = sqlite3.Row
    return dbconnect

app = Flask(__name__)

@app.route("/")
def index():
    friends = get_friends_list()
    return render_template('index.html', friends = friends, nearby_results = '', api_key = api_key, center = '', locations = '', selectedlocations = '', returnedlocations = '')

@app.route('/placesearch', methods=['POST'])
def placesearch():
    activity = request.form['activity']
    if not activity:
        activity = ''
    locations = []
    locationswithuser = []
    latlnglocations = []
    for i in range(0,100):
        current = 'friendaddress' + str(i)
        if current in request.form:
            temp = request.form['friendaddress' + str(i)]
            temp = temp.split(",")
            temp[0] = float(temp[0])
            temp[1] = float(temp[1])
            locations.append(temp[:2])
            locationswithuser.append(temp)
    #get the center coords of the addresses
    center_coords = get_geocenter(locations)
    for locations in locations:
        latlngtuple = (locations[0],locations[1])
        latlnglocations.append(latlngtuple)
    #return latlnglocations
    distance_results = gmaps.distance_matrix(origins=latlnglocations, destinations=latlngtuple, mode="driving")
    distance_results = distance_results.get('rows')
    maxcounter = 0
    maxdur = 0
    for results in distance_results:
        maxcounter += 1
        tempdur = results.get('elements')
        tempdur = tempdur[0].get('duration')
        tempdur = int(tempdur.get('value'))
        if maxdur < tempdur:
            maxdur = tempdur
            farthestuser = maxcounter
    print(farthestuser)
    #print("Coords: ", center_coords)
    #print("Type: ",type(center_coords))
    #set radius each time it's called
    results_min = 10  #how many results
    min_radius = 500 #meters
    max_radius = 60000 #largest it will search
    search_radius = min_radius
    radius_grow_rate = 1 
    radius_grow_rate_min = 0.1 #for rate scaling
    safety_counter = 1
    
    search_success = False
    while not search_success:
        if search_radius >= max_radius:
            #try an error
            raise Exception("Max search radius exceeded")
            break #out of the
        if safety_counter > 12:
            print("Something's wrong with the loop.")
            break
        nearby_results = gmaps.places_nearby(center_coords, search_radius, keyword = activity, open_now=True)
        #check the status
        query_status = nearby_results['status']   
        if query_status == "ZERO_RESULTS":
            search_radius += search_radius*radius_grow_rate
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
        print(safety_counter)
        safety_counter += 1
    #end of while
    nearby_results_filtered = []
    nearby_results_for_marker = []
    for results in results:
        googlesearch = results.get('name') + ' ' + results.get('vicinity')
        googlesearch = urllib.parse.quote_plus(googlesearch)
        nearby_results_filtered.append([results.get('name'), results.get('vicinity'), results.get('rating'), googlesearch])
        resultsgeo = results.get('geometry')
        resultsgeo = resultsgeo.get('location')
        nearby_results_for_marker.append([resultsgeo.get('lat'), resultsgeo.get('lng'), results.get('name'), results.get('vicinity')])
    friends = get_friends_list()
    return render_template('index.html', friends = friends, nearby_results = nearby_results_filtered, center = center_coords, selectedlocations = locationswithuser, returnedlocations = nearby_results_for_marker)

def get_friends_list():
    if 'user_id' in session:
        dbconnect = get_db_connection()
        friends = dbconnect.execute('SELECT users.username, users.address, latitude, longitude FROM users INNER JOIN friends ON users.id = friends.friend_id WHERE users.username = ? OR friends.user_id = ? ORDER BY users.username ASC', (session['user_id'],session['user_id'])).fetchall()
        dbconnect.close()
    else:
        friends = ''
    return friends

# This function will be called when a 500 error occurs
@app.errorhandler(500)
def internal_server_error(error):
    return render_template('error.html', error=error), 500

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
api_key = "AIzaSyCQHMg2sZwnUTRQavAXTYhqv7BGzl7j2EQ"
gmaps = googlemaps.Client(key=api_key)

app.secret_key = 'secretwords'

# dbconnectect to database
def get_db_dbconnectection():
    dbconnect = sqlite3.connect('friendfinder.db')
    dbconnect.row_factory = sqlite3.Row
    return dbconnect

# Registration form route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        address = request.form['address']
        password = request.form['password']
        
        googlelatlng = gmaps.geocode(address=address)
        googlelatlng = googlelatlng[0].get('geometry')
        googlelatlng = googlelatlng.get('location')
        googlelatlng = [googlelatlng['lat'],googlelatlng['lng']]

        #Here I figure we convert address to coords and save in users, for long,lat
        #didn't wannna make the requests during testing here

        # Check if username already exists
        dbconnect = get_db_dbconnectection()
        user = dbconnect.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user is not None:
            return 'Username already exists!'

        # Insert new user into database
        dbconnect.execute('INSERT INTO users (username, address, password, latitude, longitude) VALUES (?, ?, ?, ?, ?)', (username, address, password, googlelatlng[0], googlelatlng[1]))
        dbconnect.commit()
        dbconnect.close()
        
        return redirect(url_for('login'))

    return render_template('register.html')

# Login form route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if email and password are correct
        dbconnect = get_db_dbconnectection()
        user = dbconnect.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        dbconnect.close()
        if user is None:
           return redirect(url_for('register'))

        # Save user id to session
        session['user_id'] = user['id']
        return redirect(url_for('dashboard'))

    return render_template('login.html')

# Dashboard route
@app.route('/dashboard')
def dashboard():
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Get user info from database
    dbconnect = get_db_dbconnectection()
    user = dbconnect.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    friends = get_friends_list()
    
    return render_template('dashboard.html', user=user, friends=friends)

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/add_friend', methods=['POST'])
def add_friend():
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Get form data
    friend_username = request.form.get('friend_username')

    # Find friend user by username
    dbconnect = get_db_dbconnectection()
    friend_user = dbconnect.execute('SELECT * FROM users WHERE username = ?', (friend_username,)).fetchone()

    # If friend user not found, display error message
    if friend_user is None:
        flash('User not found')
        return redirect(url_for('dashboard'))

    # Insert friendship into database
    dbconnect.execute('INSERT INTO friends (user_id, friend_id) VALUES (?, ?)', (session['user_id'], friend_user['id']))
    dbconnect.commit()
    dbconnect.close()

    # Display success message
    flash('Friend added')
    return redirect(url_for('dashboard'))

@app.route('/change_address', methods=['POST'])
def change_address():
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Get form data
    address = request.form.get('change_address')
    
    #Get Geocode
    googlelatlng = gmaps.geocode(address=address)
    googlelatlng = googlelatlng[0].get('geometry')
    googlelatlng = googlelatlng.get('location')
    googlelatlng = [googlelatlng['lat'],googlelatlng['lng']]


    # Find friend user by username
    dbconnect = get_db_dbconnectection()
    print("UPDATE users SET address='%s', latitude='%s', longitude='%s'WHERE id='%s'" % (address, googlelatlng[0], googlelatlng[1], session['user_id']))
    dbconnect.execute("UPDATE users SET address='%s', latitude='%s', longitude='%s'WHERE id='%s'" % (address, googlelatlng[0], googlelatlng[1], session['user_id']))
    dbconnect.commit()
    dbconnect.close()

    # Display success message
    flash('Address Changed')
    return redirect(url_for('dashboard'))