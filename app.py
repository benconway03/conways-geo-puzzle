from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from geogame import GeoGame 
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
    game_settings = db['settings']
else:
    print("WARNING: MONGO_URI not found. Leaderboard won't save permanently.")
    leaderboard = None 
    game_settings = None

app = Flask(__name__)
app.secret_key = "bjlasd87923jkf9832!*^&dskkasd" 
app.permanent_session_lifetime = timedelta(days=30)

game_engine = GeoGame()
valid_countries = game_engine.df_countries['COUNTRY'].tolist()

@app.route("/")
def home():
    session.permanent = True 
    today = str(datetime.datetime.now(datetime.timezone.utc).date())

    global_target = None
    if game_settings is not None:
        override = game_settings.find_one({'setting': 'global_target', 'date': today})
        if override:
            global_target = override['country']

    if not global_target:
        global_target = game_engine.get_daily_country()

    if session.get('date') != today or session.get('target') != global_target:
        session['date'] = today
        session['target'] = global_target
        session['start_time'] = None
        session['guess_count'] = 0
        session['has_won'] = False
        session['submitted_score'] = False
        session['grid'] = []
        session['time_str'] = ""

    return render_template("index.html", 
                           has_won=session.get('has_won', False), 
                           submitted=session.get('submitted_score', False),
                           guesses=session.get('guess_count', 0),
                           share_grid="".join(session.get('grid', [])), 
                           time_str=session.get('time_str', ""),
                           countries=valid_countries)


@app.route("/guess", methods=["POST"])
def process_guess():
    if session.get('has_won'):
        return jsonify({"status": "error", "message": "You already won today! Come back tomorrow."})

    if session.get('start_time') is None:
        session['start_time'] = time.time()

    user_guess = request.form.get("guess").strip().title()
    target = session.get('target')
    
    aliases = {"Usa": "United States", "Uk": "United Kingdom"}
    if user_guess in aliases:
        user_guess = aliases[user_guess]

    if user_guess in valid_countries:
        final_guess = user_guess
    else:
        matches = difflib.get_close_matches(user_guess, valid_countries, n=1, cutoff=0.7)
        if matches:
            final_guess = matches[0]
        else:
            return jsonify({"status": "error", "message": f"❌ '{user_guess}' not found. Check spelling!"})

    session['guess_count'] += 1
    
    if 'grid' not in session:
        session['grid'] = []

    if final_guess == target:
        session['grid'].append("🟩")

        raw_time = time.time() - session['start_time']
        
        penalty_seconds = (session['guess_count']-1) * 3
        
        total_time = raw_time + penalty_seconds
        
        session['final_time'] = total_time 
        session['has_won'] = True 
        
        mins, secs = int(total_time // 60), total_time % 60
        time_str = f"{mins}m {secs:.1f}s" if mins > 0 else f"{secs:.1f}s"
        
        session['time_str'] = time_str

        return jsonify({
            "status": "win", 
            "message": f"🎉 You Won! {final_guess} is correct! Took {session['guess_count']} guesses in {time_str} (includes +{penalty_seconds}s penalty).",
            "grid": "".join(session['grid']),
            "time_str": time_str
        })
    else:
        session['grid'].append("🟥")
        dist, bearing = game_engine.country_dist(target, final_guess)
        return jsonify({
            "status": "continue", 
            "message": f"❌ {final_guess} is {dist} away. Head {bearing}"
        })


@app.route("/save_score", methods=["POST"])
def save_score():

    if session.get('submitted_score'):
        return jsonify({"status": "error", "message": "Score already submitted today!"})

    try:
        name = request.form.get("name").strip()[:20]
        guesses = session.get('guess_count')
        

        elapsed = session.get('final_time', time.time() - session.get('start_time'))
        today = str(datetime.datetime.now(datetime.timezone.utc).date())
        
        if leaderboard is not None:

            leaderboard.insert_one({
                'name': name,
                'guesses': guesses,
                'time': round(elapsed, 2),
                'date': today
            })
   
            session['submitted_score'] = True 
            
        return jsonify({"status": "success"})
    
    except Exception as e:
        print(f"Database Error: {e}")
        return jsonify({"status": "error"}), 500
    
@app.route("/get_leaderboard")
def get_leaderboard():
    today = str(datetime.datetime.now(datetime.timezone.utc).date())
    
    if leaderboard is not None:

        scores_cursor = leaderboard.find({'date': today}).sort([('time', 1), ('guesses', 1)]).limit(10)
        
        scores = list(scores_cursor)
        
        for s in scores:
            s['_id'] = str(s['_id'])
    else:
        scores = []
        
    return jsonify(scores)

# --- PRACTICE MODE ROUTES ---

@app.route("/practice")
def practice():
    # If they don't have a practice game going, start one!
    if not session.get('p_target'):
        session['p_target'] = random.choice(valid_countries)
        session['p_start_time'] = None
        session['p_guess_count'] = 0
        session['p_has_won'] = False
        session['p_grid'] = []
        session['p_time_str'] = ""

    # FIX: We changed submitted=True to submitted=False here!
    return render_template("index.html", 
                           is_practice=True, 
                           has_won=session.get('p_has_won', False), 
                           submitted=False, 
                           guesses=session.get('p_guess_count', 0),
                           share_grid="".join(session.get('p_grid', [])), 
                           time_str=session.get('p_time_str', ""),
                           countries=valid_countries)

@app.route("/reset_practice")
def reset_practice():
    # Wipes the practice variables and picks a new random country
    session['p_target'] = random.choice(valid_countries)
    session['p_start_time'] = None
    session['p_guess_count'] = 0
    session['p_has_won'] = False
    session['p_grid'] = []
    session['p_time_str'] = ""
    return redirect(url_for('practice'))

@app.route("/guess_practice", methods=["POST"])
def process_practice_guess():
    if session.get('p_has_won'):
        return jsonify({"status": "error", "message": "You already won! Click 'Skip / New Country' to play again."})

    if session.get('p_start_time') is None:
        session['p_start_time'] = time.time()

    user_guess = request.form.get("guess").strip().title()
    target = session.get('p_target')
    
    aliases = {"Russia": "Russian Federation", "Usa": "United States", "Uk": "United Kingdom"}
    if user_guess in aliases:
        user_guess = aliases[user_guess]

    if user_guess in valid_countries:
        final_guess = user_guess
    else:
        matches = difflib.get_close_matches(user_guess, valid_countries, n=1, cutoff=0.7)
        if matches:
            final_guess = matches[0]
        else:
            return jsonify({"status": "error", "message": f"❌ '{user_guess}' not found. Check spelling!"})

    session['p_guess_count'] += 1
    
    if 'p_grid' not in session:
        session['p_grid'] = []
    
    if final_guess == target:
        session['p_grid'].append("🟩") 
        session.modified = True 
        
        raw_time = time.time() - session['p_start_time']
        penalty_seconds = (session['p_guess_count']-1) * 3
        total_time = raw_time + penalty_seconds
        
        session['p_final_time'] = total_time 
        session['p_has_won'] = True 
        
        mins, secs = int(total_time // 60), total_time % 60
        time_str = f"{mins}m {secs:.1f}s" if mins > 0 else f"{secs:.1f}s"
        session['p_time_str'] = time_str 

        return jsonify({
            "status": "win", 
            # FIX: We added the time_str and penalty_seconds to this message!
            "message": f"🎉 You Won! {final_guess} is correct! Took {session['p_guess_count']} guesses in {time_str} (includes +{penalty_seconds}s penalty).",
            "grid": "".join(session['p_grid']), 
            "time_str": time_str              
        })
    else:
        session['p_grid'].append("🟥") 
        session.modified = True  
        
        dist, bearing = game_engine.country_dist(target, final_guess)
        return jsonify({
            "status": "continue", 
            "message": f"❌ {final_guess} is {dist} away. Head {bearing}"
        })

@app.route("/dev-reset")
def dev_reset():

    session.clear()
    return redirect(url_for('home'))

@app.route("/admin-clear-board")
def admin_clear_board():

    secret_key = request.args.get("key")
    if secret_key != "leaderboardreset1!":
        return "Unauthorized", 401

    today = str(datetime.datetime.now(datetime.timezone.utc).date())
    
    if leaderboard is not None:
        result = leaderboard.delete_many({'date': today})
        
        return f"""
        <h3>Success!</h3> 
        <p>Deleted {result.deleted_count} scores for {today}.</p>
        <a href='/'>Click here to go back to the game</a>
        """
    else:
        return "Error: Database not connected."
    
@app.route("/admin-random-target")
def admin_random_target():

    secret_key = request.args.get("key")
    if secret_key != "resetcountry1!": 
        return "Unauthorized", 401

    random_country = random.choice(valid_countries)
    today = str(datetime.datetime.now(datetime.timezone.utc).date())

    if game_settings is not None:

        game_settings.update_one(
            {'setting': 'global_target'},
            {'$set': {'country': random_country, 'date': today}},
            upsert=True
        )

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