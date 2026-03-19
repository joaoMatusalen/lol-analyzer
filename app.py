from flask import Flask, render_template, request, jsonify
from riot_service import get_player_analysis

app = Flask(__name__)

VALID_REGIONS = {"americas", "europe", "asia", "sea"}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}

    player_name = str(data.get("playerName", "")).strip()[:24]
    tag         = str(data.get("playerTag",  "")).strip()[:4]
    region      = str(data.get("region",     "")).strip().lower()

    if not player_name or not tag:
        return jsonify({"error": "Nome e tag são obrigatórios."}), 400

    if region not in VALID_REGIONS:
        return jsonify({"error": "Região inválida."}), 400

    try:
        result = get_player_analysis(player_name, tag, region)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        print(f"Erro interno em /analyze: {e}")
        return jsonify({"error": "Erro interno no servidor. Tente novamente."}), 500

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

if __name__ == "__main__":
    app.run(debug=True)