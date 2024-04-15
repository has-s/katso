from flask import Flask, redirect, request
import requests

app = Flask(__name__)

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

@app.route('/')
def index():
    return "Katso."

@app.route('/get_token')
def get_token():
    client_id = "5gu01uujpold2a2nf3bdjpf0erifzn"
    client_secret = "beaty65di005fmryt8fhhygmdizhtq"
    access_token = authenticate_oauth(client_id, client_secret)
    if access_token:
        return redirect(f"/token?access_token={access_token}")
    else:
        return "Не удалось получить Bearer токен доступа."

@app.route('/token')
def token():
    access_token = request.args.get('access_token')
    return f"Bearer токен доступа: {access_token}"

if __name__ == "__main__":
    app.run(debug=True)
