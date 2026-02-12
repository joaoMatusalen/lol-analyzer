from flask import Flask, render_template, request, jsonify
from riot_service import get_play_analysis

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json

    player_name = data["playerName"]
    tag = data["playerTag"]
    region = data["region"]

    result = get_play_analysis(player_name, tag, region)

    return jsonify(result)

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

if __name__ == "__main__":
    app.run(debug=True)