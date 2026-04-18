from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from geogame import GeoGame  # Imports your exact class from your other file!
import difflib
import time
import datetime
from datetime import timedelta
import os
from pymongo import MongoClient
import certifi
import random

MONGO_URI = os.environ.get("MONGO_URI")

if MONGO_URI:
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where()) 
    db = client['geogame_db']       
    leaderboard = db['leaderboard'] 
    game_settings = db['settings'] # <-- New line here
else:
    print("WARNING: MONGO_URI not found. Leaderboard won't save permanently.")
    leaderboard = None 
    game_settings = None # <-- New line here

app = Flask(__name__)
app.secret_key = "super_secret_key_change_this" # Required for sessions to work
app.permanent_session_lifetime = timedelta(days=30)

# Initialize the game engine once for the server to use
game_engine = GeoGame()
valid_countries = game_engine.df_countries['COUNTRY'].tolist()

@app.route("/")
def home():
    session.permanent = True 
    today = str(datetime.datetime.now(datetime.timezone.utc).date())

    # 1. Ask MongoDB if an admin set a global target for today
    global_target = None
    if game_settings is not None:
        override = game_settings.find_one({'setting': 'global_target', 'date': today})
        if override:
            global_target = override['country']

    # 2. If no admin override exists, use the standard daily math
    if not global_target:
        global_target = game_engine.get_daily_country()

    # 3. If it's a new day OR the admin changed the target mid-day, reset the player!
    if session.get('date') != today or session.get('target') != global_target:
        session['date'] = today
        session['target'] = global_target
        session['start_time'] = None
        session['guess_count'] = 0
        session['has_won'] = False
        session['submitted_score'] = False

    return render_template("index.html", 
                           has_won=session.get('has_won', False), 
                           submitted=session.get('submitted_score', False),
                           guesses=session.get('guess_count', 0))

@app.route("/guess", methods=["POST"])
def process_guess():
    # --- ANTI-CHEAT: Stop them from guessing if they already won ---
    if session.get('has_won'):
        return jsonify({"status": "error", "message": "You already won today! Come back tomorrow."})

    if session.get('start_time') is None:
        session['start_time'] = time.time()

    user_guess = request.form.get("guess").strip().title()
    target = session.get('target')
    
    # 1. Alias check
    aliases = {"Russia": "Russian Federation", "Usa": "United States", "Uk": "United Kingdom"}
    if user_guess in aliases:
        user_guess = aliases[user_guess]

    # 2. Fuzzy Matching
    if user_guess in valid_countries:
        final_guess = user_guess
    else:
        matches = difflib.get_close_matches(user_guess, valid_countries, n=1, cutoff=0.7)
        if matches:
            final_guess = matches[0]
        else:
            return jsonify({"status": "error", "message": f"❌ '{user_guess}' not found. Check spelling!"})

    # 3. Process the Game Logic
    session['guess_count'] += 1
    
    if final_guess == target:
        elapsed = time.time() - session['start_time']
        
        # --- TIMER FIX: Freeze the time and save it to the session! ---
        session['final_time'] = elapsed 
        
        # --- ANTI-CHEAT: Mark them as a winner so they can't play again ---
        session['has_won'] = True 
        
        mins, secs = int(elapsed // 60), elapsed % 60
        time_str = f"{mins}m {secs:.1f}s" if mins > 0 else f"{secs:.1f}s"
        
        return jsonify({
            "status": "win", 
            "message": f"🎉 You Won! {final_guess} is correct! Took {session['guess_count']} guesses in {time_str}."
        })
    else:
        # Ask our game engine to do the math using the target stored in the session
        dist, bearing = game_engine.country_dist(target, final_guess)
        return jsonify({
            "status": "continue", 
            "message": f"❌ {final_guess} is {dist} away. Head {bearing}"
        })


@app.route("/save_score", methods=["POST"])
def save_score():
    # --- ANTI-CHEAT: Stop them from submitting multiple names ---
    if session.get('submitted_score'):
        return jsonify({"status": "error", "message": "Score already submitted today!"})

    try:
        name = request.form.get("name").strip()[:20]
        guesses = session.get('guess_count')
        
        # --- Use the frozen time from when they won ---
        elapsed = session.get('final_time', time.time() - session.get('start_time'))
        today = str(datetime.datetime.now(datetime.timezone.utc).date())
        
        if leaderboard is not None:
            # PyMongo uses 'insert_one' to save a dictionary
            leaderboard.insert_one({
                'name': name,
                'guesses': guesses,
                'time': round(elapsed, 2),
                'date': today
            })
            # --- ANTI-CHEAT: Lock the submission form ---
            session['submitted_score'] = True 
            
        return jsonify({"status": "success"})
    
    except Exception as e:
        print(f"Database Error: {e}")
        return jsonify({"status": "error"}), 500
    
@app.route("/get_leaderboard")
def get_leaderboard():
    today = str(datetime.datetime.now(datetime.timezone.utc).date())
    
    if leaderboard is not None:
        # Ask MongoDB to find today's scores, sort them by least guesses (1) 
        # then by fastest time (1), and only give us the top 10
        scores_cursor = leaderboard.find({'date': today}).sort([('guesses', 1), ('time', 1)]).limit(10)
        
        # Convert the cursor to a standard Python list
        scores = list(scores_cursor)
        
        # PyMongo adds a special '_id' to everything, which breaks JSON, so we convert it to a string
        for s in scores:
            s['_id'] = str(s['_id'])
    else:
        scores = []
        
    return jsonify(scores)

@app.route("/dev-reset")
def dev_reset():
    # This wipes your session cookies and redirects you back to the home page!
    session.clear()
    return redirect(url_for('home'))

@app.route("/admin-clear-board")
def admin_clear_board():
    # 1. A basic security check! 
    # The URL must end with ?key=your_secret_password
    secret_key = request.args.get("key")
    if secret_key != "leaderboardreset1!": # Change this to whatever password you want!
        return "Unauthorized", 401

    # 2. Get today's date
    today = str(datetime.datetime.now(datetime.timezone.utc).date())
    
    if leaderboard is not None:
        # 3. Ask PyMongo to delete all entries matching today's date
        result = leaderboard.delete_many({'date': today})
        
        # 4. Print a success message showing how many scores were wiped
        return f"""
        <h3>Success!</h3> 
        <p>Deleted {result.deleted_count} scores for {today}.</p>
        <a href='/'>Click here to go back to the game</a>
        """
    else:
        return "Error: Database not connected."
    
@app.route("/admin-random-target")
def admin_random_target():
    # 1. Security Check
    secret_key = request.args.get("key")
    if secret_key != "resetcountry1!": 
        return "Unauthorized", 401

    random_country = random.choice(valid_countries)
    today = str(datetime.datetime.now(datetime.timezone.utc).date())

    if game_settings is not None:
        # 2. Save this new target to MongoDB so ALL players see it
        # (upsert=True means "update it if it exists, create it if it doesn't")
        game_settings.update_one(
            {'setting': 'global_target'},
            {'$set': {'country': random_country, 'date': today}},
            upsert=True
        )
        
        # 3. Wipe today's leaderboard so scores don't mix!
        if leaderboard is not None:
            leaderboard.delete_many({'date': today})

    return f"""
    <h3>Success! Global Random Target Set.</h3> 
    <p>The target for EVERYONE has been changed to: <strong>{random_country}</strong></p>
    <p>Today's leaderboard has been wiped clean to keep things fair.</p>
    <a href='/dev-reset'>Click here to reset your own browser and play it!</a>
    """

if __name__ == "__main__":
    app.run(debug=True)