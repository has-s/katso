from flask import Flask, render_template, request, redirect, url_for
import requests
from dotenv import load_dotenv
import os

load_dotenv()
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
template_path = os.getenv("TEMPLATE_PATH")
redirect_uri = os.getenv("REDIRECT_URI")

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
def get_past_streams(access_token, user_id, limit=10):
    url = f"https://api.twitch.tv/helix/videos?user_id={user_id}&type=archive&first={limit}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-ID": client_id
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data['data'] if 'data' in data else None
    return None

def get_access_token(code):
    token_url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }
    response = requests.post(token_url, data=params)
    if response.status_code == 200:
        data = response.json()
        if 'access_token' in data:
            return data['access_token']
    return None

# Эндпоинт для авторизации
@app.route('/authorize')
def authorize():
    authorize_url = f"https://id.twitch.tv/oauth2/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=chat:read"
    return redirect(authorize_url)

# Эндпоинт для обработки редиректа после авторизации
@app.route('/callback')
def callback():
    code = request.args.get('code')
    if code:
        access_token = get_access_token(code)
        if access_token:
            return redirect(url_for('chat_messages', access_token=access_token))
    return "Ошибка при получении токена доступа."

# Функция для получения токена доступа по коду авторизации
def get_access_token(code):
    token_url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }
    response = requests.post(token_url, data=params)
    if response.status_code == 200:
        data = response.json()
        if 'access_token' in data:
            return data['access_token']
    return None

# Эндпоинт для получения сообщений чата
@app.route('/chat/messages')
def chat_messages():
    access_token = request.args.get('access_token')
    if access_token:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Client-ID": client_id
        }
        response = requests.get("https://api.twitch.tv/helix/chat/recent", headers=headers)
        if response.status_code == 200:
            messages = response.json()['data']
            return render_template('chat_messages.html', messages=messages)
    return "Ошибка при получении сообщений чата."


@app.route('/')
def index():
    return render_template("index.html")

@app.route('/get_info', methods=['POST'])
def get_info():
    access_token = authenticate_oauth(client_id, client_secret)
    if access_token:
        username = request.form.get('username')
        user_info = get_user_info(access_token, username)
        stream_info = get_stream_info(access_token, user_info['id'])
        past_streams = get_past_streams(access_token, user_info['id'])
        return render_template('user_info.html', user_info=user_info, stream_info=stream_info, past_streams=past_streams)
    else:
        return "Не удалось получить Bearer токен доступа."

if __name__ == "__main__":
    app.run()
