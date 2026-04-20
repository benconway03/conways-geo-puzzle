# This file is simply to direct users of the old URL, to the new URL.

from flask import Flask

app = Flask(__name__)

@app.route("/", defaults={'path': ''})
@app.route("/<path:path>")
def home(path):
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>GeoPuzzle has moved!</title>
        <meta http-equiv="refresh" content="3;url=https://geo-puzzle.onrender.com" />
    </head>
    <body style="font-family: sans-serif; text-align: center; margin-top: 20%;">
        <h2>🌍 Geo Puzzle has moved!</h2>
        <p>Taking you to the new site...</p>
        <p style="font-size: 0.8em; color: gray;">
            If you are not redirected automatically, 
            <a href="https://geo-puzzle.onrender.com" style="color: blue;">click here</a>.
        </p>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run()