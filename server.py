from flask import Flask, render_template, redirect, url_for, session, request, jsonify
from supabase import create_client
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv, find_dotenv
from urllib.parse import quote_plus, urlencode
import os
import json
import openai
import requests
import google.generativeai as genai

# ----------------- Load .env -----------------
ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)


# ----------------- Flask Setup -----------------
app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
#----------------Gemini API --------------------
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-pro")
gemini_model = genai.GenerativeModel("gemini-1.5-flash")
chat_session = gemini_model.start_chat(history=[])

# ----------------- Auth0 Setup -----------------
oauth = OAuth(app)
auth0 = oauth.register(
    "auth0",
    client_id=os.getenv("AUTH0_CLIENT_ID"),
    client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
    client_kwargs={"scope": "openid profile email"},
    server_metadata_url=f'https://{os.getenv("AUTH0_DOMAIN")}/.well-known/openid-configuration'
)

# ----------------- Supabase Setup -----------------
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# ----------------- Routes -----------------
@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(redirect_uri=url_for("callback", _external=True))

@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        f"https://{os.getenv('AUTH0_DOMAIN')}/v2/logout?"
        + urlencode(
            {"returnTo": url_for("home", _external=True),
             "client_id": os.getenv("AUTH0_CLIENT_ID")},
            quote_via=quote_plus
        )
    )

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")
    if not user_input:
        return jsonify({"error": "No message provided"}), 400
    try:
        response = chat_session.send_message(user_input)
        return jsonify({"response": response.candidates[0].content.parts[0].text})
    except Exception as e:
        return jsonify({"error": f"Gemini API Error: {str(e)}"}), 500

@app.route("/")
def home():
    return render_template(
        "Website.html",
        session=session.get('user'),
        pretty=json.dumps(session.get('user'), indent=4)
    )

# ----------------- Run App -----------------
if __name__ == '__main__':
    app.run(debug=True)
