from flask import Flask, render_template, request
import requests
from dotenv import load_dotenv
import os

load_dotenv()
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
template_path = os.getenv("TEMPLATE_PATH")


app = Flask(__name__, template_folder=template_path)
def authenticate_oauth(client_id, client_secret):
    token_url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    response = requests.post(token_url, data=params)
    if response.status_code == 200:
        data = response.json()
        if 'access_token' in data:
            return data['access_token']
    return None

def get_user_info(access_token, username):
    url = f"https://api.twitch.tv/helix/users?login={username}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-ID": client_id
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data['data'][0] if 'data' in data and len(data['data']) > 0 else None
    return None

def get_stream_info(access_token, username):
    url = f"https://api.twitch.tv/helix/streams?user_login={username}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-ID": client_id
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data['data'][0] if 'data' in data and len(data['data']) > 0 else None
    return None

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/get_info', methods=['POST'])
def get_info():
    access_token = authenticate_oauth(client_id, client_secret)
    if access_token:
        username = request.form.get('username')
        user_info = get_user_info(access_token, username)
        stream_info = get_stream_info(access_token, username)
        return render_template('user_info.html', user_info=user_info, stream_info=stream_info)
    else:
        return "Не удалось получить Bearer токен доступа."

if __name__ == "__main__":
    app.run(debug=True)
