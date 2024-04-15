from flask import Flask, redirect, request
import requests

app = Flask(__name__)

CLIENT_ID = "5gu01uujpold2a2nf3bdjpf0erifzn"
CLIENT_SECRET = ("beaty65di005fmryt8fhhygmdizhtq")
REDIRECT_URI = "http://katso.vercel.app/callback"

# Маршрут для перенаправления на страницу авторизации Twitch
@app.route("/authorize")
def authorize():
    # Формирование URL для запроса авторизации
    auth_url = f"https://id.twitch.tv/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=viewing_activity_read"

    return redirect(auth_url)

# Маршрут для обработки ответа от Twitch после авторизации
@app.route("/callback")
def callback():
    # Получение кода авторизации из параметра запроса
    code = request.args.get("code")

    # Обмен кода авторизации на токен доступа
    token_url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI
    }
    response = requests.post(token_url, data=params)
    data = response.json()

    # Получение токена доступа из ответа
    access_token = data.get("access_token")

    # Теперь вы можете использовать access_token для вызова методов Twitch API

    return "Authorization successful! You can now use this token to call Twitch API."

if __name__ == "__main__":
    app.run(debug=True)
