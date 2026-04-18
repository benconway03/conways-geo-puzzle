from flask import Flask, render_template, request, session, jsonify
from geogame import GeoGame  # Imports your exact class from your other file!
import difflib
import time
from tinydb import TinyDB, Query
import datetime

db = TinyDB('leaderboard.json')

app = Flask(__name__)
app.secret_key = "super_secret_key_change_this" # Required for sessions to work

# Initialize the game engine once for the server to use
game_engine = GeoGame()
valid_countries = game_engine.df_countries['COUNTRY'].tolist()

@app.route("/")
def home():
    session['target'] = game_engine.get_daily_country()
    session['start_time'] = None  # <--- Change this line
    session['guess_count'] = 0
    return render_template("index.html")

@app.route("/guess", methods=["POST"])
def process_guess():

    if session.get('start_time') is None:
        session['start_time'] = time.time()

    user_guess = request.form.get("guess").strip().title()
    target = session.get('target')
    
    # 1. Alias check (Add your aliases here just like in the terminal version!)
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
    name = request.form.get("name").strip()[:20] # Limit to 20 chars
    guesses = session.get('guess_count')
    
    # Calculate final time (same logic as before)
    elapsed = time.time() - session.get('start_time')
    
    # Get today's date for the daily leaderboard
    today = str(datetime.datetime.now(datetime.timezone.utc).date())
    
    # Save to database
    db.insert({
        'name': name,
        'guesses': guesses,
        'time': round(elapsed, 2),
        'date': today
    })
    
    return jsonify({"status": "success"})

@app.route("/get_leaderboard")
def get_leaderboard():
    today = str(datetime.datetime.now(datetime.timezone.utc).date())
    Score = Query()
    # Fetch all scores for today, sorted by least guesses, then fastest time
    scores = db.search(Score.date == today)
    sorted_scores = sorted(scores, key=lambda x: (x['guesses'], x['time']))
    
    return jsonify(sorted_scores[:10]) # Return top 10

if __name__ == "__main__":
    app.run(debug=True)