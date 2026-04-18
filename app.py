from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from geogame import GeoGame  # Imports your exact class from your other file!
import difflib
import time
import datetime
from datetime import timedelta
import os
from pymongo import MongoClient

# 1. Grab the secret URL from Render's environment variables
MONGO_URI = os.environ.get("MONGO_URI")

# 2. Connect to MongoDB
# (If we are running locally on your PC and haven't set the variable, we catch the error)
if MONGO_URI:
    client = MongoClient(MONGO_URI)
    db = client['geogame_db']       # Creates a database
    leaderboard = db['leaderboard'] # Creates a collection (table)
else:
    print("WARNING: MONGO_URI not found. Leaderboard won't save permanently.")
    leaderboard = None

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

    if session.get('date') != today:
        session['date'] = today
        session['target'] = game_engine.get_daily_country()
        session['start_time'] = None
        session['guess_count'] = 0
        session['has_won'] = False
        session['submitted_score'] = False

    return render_template("index.html", 
                           has_won=session.get('has_won', False), 
                           submitted=session.get('submitted_score', False),
                           guesses=session.get('guess_count', 0)) # <-- NEW LINE

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

@app.route("/dev-reset")
def dev_reset():
    # This wipes your session cookies and redirects you back to the home page!
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)