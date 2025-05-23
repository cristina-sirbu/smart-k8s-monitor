from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/<TO-CHANGE>"

OLLAMA_API = "http://localhost:11434/api/generate"

@app.route("/alert", methods=["POST"])
def alert():
    data = request.json
    for alert in data.get("alerts", []):
        description = alert['annotations'].get('description', 'No description.')
        prompt = f"You are a DevOps assistant. What should I do if this alert fires: {description}"
        llm_response = get_llm_response(prompt)

        message = f"🚨 *{alert['labels']['alertname']}*\n\n> {description}\n\n🤖 {llm_response}"
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
    return jsonify({"status": "ok"}), 200

def get_llm_response(prompt: str) -> str:
    try:
        response = requests.post(OLLAMA_API, json={
            "model": "mistral",
            "prompt": prompt,
            "stream": False,
            "temperature": 0.7
        }, timeout=60)
        return response.json().get("response", "").strip()
    except Exception as e:
        return f"[LLM error] {str(e)}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)