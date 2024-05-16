from flask import Flask, render_template, request
from dotenv import load_dotenv
from enum import Enum
import requests
import logging
import datetime
import os
import re

import concurrent.futures

load_dotenv()
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
template_path = os.getenv("TEMPLATE_PATH")
redirect_uri = os.getenv("REDIRECT_URI")

app = Flask(__name__, template_folder=template_path)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


# Аунтефикация приложения
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

access_token = authenticate_oauth(client_id, client_secret)


# Определяем классы для формата чата и типа загрузки
class ChatFormat(Enum):
    JSON = "json"
class DownloadType(Enum):
    VIDEO = 1
class DownloadOptions:
    def __init__(self, download_type, video_id, download_format, video_start=None):
        self.download_type = download_type
        self.video_id = video_id
        self.download_format = download_format
        self.video_start = video_start
class ChatDownloader:
    def __init__(self, download_options):
        self.download_options = download_options

    def _fetch_chat_data(self):
        headers = {
            "Client-ID": "kd1unb4b3q4t58fwlpcbzcbnm76a8fp"
        }

        # Формируем запрос в зависимости от типа загрузки
        if self.download_options.download_type == DownloadType.VIDEO:
            url = "https://gql.twitch.tv/gql"
            payload = {
                "operationName": "VideoCommentsByOffsetOrCursor",
                "variables": {
                    "videoID": self.download_options.video_id,
                    "contentOffsetSeconds": self.download_options.video_start
                },
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "b70a3591ff0f4e0313d126c6a1502d79a1c02baebb288227c582044aa76adf6a"
                    }
                }
            }

            try:
                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                print(f"Error fetching chat data: {e}")
                return None

    def _process_chat_data(self, chat_data):
        if not chat_data:
            print("No chat data to process")
            return []

        processed_comments = []
        for comment in chat_data[0]['data']['video']['comments']['edges']:
            processed_comment = {
                '_id': comment['node']['id'],
                'created_at': comment['node']['createdAt'],
                'content_offset_seconds': comment['node']['contentOffsetSeconds'],
                'commenter': {
                    'display_name': comment['node']['commenter']['displayName'].strip(),
                    '_id': comment['node']['commenter']['id'],
                    'name': comment['node']['commenter']['login']
                },
                'message': {
                    'body': "".join(
                        [fragment['text'] for fragment in comment['node']['message']['fragments'] if fragment['text']]),
                    'user_color': comment['node']['message']['userColor']
                }
            }
            processed_comments.append(processed_comment)

        return processed_comments

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

def get_stream_info(access_token, vod_id):
    url = f"https://api.twitch.tv/helix/videos?id={vod_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-ID": client_id
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if 'data' in data and len(data['data']) > 0:
            return data['data'][0]['created_at'], data['data'][0]['duration']
    return None, None

def get_stream_full_info(access_token, vod_id):
    url = f"https://api.twitch.tv/helix/videos?id={vod_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-ID": client_id
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if 'data' in data and len(data['data']) > 0:
            return data['data'][0]
    return None
def get_channel_info(access_token, broadcaster_id):
    url = "https://api.twitch.tv/helix/channels"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-ID": client_id
    }
    params = {
        "broadcaster_id": broadcaster_id
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        return data.get('data', None)
    else:
        print(f"Failed to retrieve channel info. Status code: {response.status_code}")
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


def get_chat_from(chat_downloader, timestamp):
    try:
        # Устанавливаем временную метку начала загрузки чата
        chat_downloader.download_options.video_start = timestamp

        # Получаем данные чата
        chat_data = chat_downloader._fetch_chat_data()

        return chat_data

    except Exception as e:
        print(f"Error fetching chat data: {e}")
        return None


def get_last_message_timestamp(chat_data):
    last_message_timestamp = None

    # Проверяем наличие данных чата
    if chat_data and 'data' in chat_data and 'video' in chat_data['data'] and 'comments' in chat_data['data']['video']:
        comments = chat_data['data']['video']['comments']['edges']

        # Если есть комментарии, получаем временную метку последнего сообщения
        if comments:
            last_comment = comments[-1]['node']
            last_message_timestamp = last_comment['createdAt']

            # Преобразуем формат временной метки
            last_message_timestamp = last_message_timestamp.replace('T', ' ').replace('Z', '')

    return last_message_timestamp

def filter_chat_data(chat_part):
    # Создаем список для хранения отфильтрованных данных
    filtered_data = []

    # Итерируемся по комментариям и извлекаем только нужные данные
    for comment in chat_part["data"]["video"]["comments"]["edges"]:
        commenter_id = comment["node"]["commenter"]["id"]
        display_name = comment["node"]["commenter"]["displayName"]
        timestamp = comment["node"]["contentOffsetSeconds"]
        message_text = comment["node"]["message"]["fragments"][0]["text"]

        # Создаем словарь для каждого комментария с нужными данными
        filtered_comment = {
            "commenter_id": commenter_id,
            "display_name": display_name,
            "timestamp": timestamp,
            "message_text": message_text
        }

        # Добавляем словарь комментария в список
        filtered_data.append(filtered_comment)

    return filtered_data


def flatten_chat(chat_filt):
    flattened_chat = []
    for segment in chat_filt:
        flattened_chat.extend(segment)
    return flattened_chat


import concurrent.futures
import logging

def get_full_chat(vod_id):
    try:
        access_token = authenticate_oauth(client_id, client_secret)
        created_at, duration = get_stream_info(access_token, vod_id)
        logging.info(f"Received request to download chat for VOD ID: {vod_id}")

        download_options = DownloadOptions(
            download_type=DownloadType.VIDEO,
            video_id=vod_id,
            download_format=ChatFormat.JSON,
        )

        chat_downloader = ChatDownloader(download_options)

        # Получаем время начала стрима
        stream_start_time = convert_time_format(created_at)
        stream_duration = duration_to_seconds(duration)

        chat_parts = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=128) as executor:
            futures = []
            for i in range(16):
                start_percent = i * 6.25
                end_percent = (i + 1) * 6.25 if i < 15 else 100
                start_time = (start_percent / 100) * stream_duration
                end_time = (end_percent / 100) * stream_duration
                delta_start = int(start_time)
                delta_end = int(end_time)
                futures.append(
                    executor.submit(
                        get_chat_segment,
                        chat_downloader,
                        delta_start,
                        delta_end,
                        vod_id
                    )
                )
            for future in concurrent.futures.as_completed(futures):
                chat_parts.append(future.result())

        # Слияние всех частей чата в один массив
        full_chat = []
        for part in chat_parts:
            full_chat.extend(part)

        logging.info("Chat downloaded successfully")
        return flatten_chat(full_chat)

    except Exception as e:
        logging.error(f"Error processing download_chat request: {e}")
        return None

def get_chat_segment(chat_downloader, start_delta, end_delta, vod_id):
    chat_data = get_chat_from(chat_downloader, start_delta)
    chat_filt = filter_chat_data(chat_data)
    last_stamp = start_delta
    while last_stamp < end_delta:
        chat_part = get_chat_from(chat_downloader, last_stamp)
        glmt = get_last_message_timestamp(chat_part)
        start, duration = get_stream_info(access_token, vod_id)
        strsttime = convert_time_format(start)
        last_stamp = int(calculate_delta(strsttime, glmt))
        chat_filt.extend(filter_chat_data(chat_data))
        logging.info(f"Timestamp {last_stamp}")
    return chat_filt



def convert_time_format(time_str, from_format="%Y-%m-%dT%H:%M:%SZ", to_format="%Y-%m-%d %H:%M:%S.%f"):
    try:
        # Преобразуем строку времени из исходного формата в объект datetime
        time_obj = datetime.datetime.strptime(time_str, from_format)

        # Преобразуем объект datetime обратно в строку в нужном формате
        new_time_str = time_obj.strftime(to_format)

        return new_time_str
    except ValueError as e:
        print("Error:", e)
        return None
def format_duration(duration):
    hours = duration // 3600
    minutes = (duration % 3600) // 60
    seconds = duration % 60
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def duration_to_seconds(duration_str):
    # Регулярное выражение для извлечения часов, минут и секунд из строки
    pattern = r'(\d+)h(\d+)m(\d+)s'

    # Поиск соответствия шаблону в строке
    match = re.match(pattern, duration_str)

    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = int(match.group(3))

        total_seconds = hours * 3600 + minutes * 60 + seconds
        return total_seconds
    else:
        return None


def calculate_delta(time_str1, time_str2):
    try:
        # Преобразуем строки в объекты datetime
        time1 = datetime.datetime.strptime(time_str1, "%Y-%m-%d %H:%M:%S.%f")
        time2 = datetime.datetime.strptime(time_str2, "%Y-%m-%d %H:%M:%S.%f")

        # Вычисляем разницу между временными отметками в секундах
        time_delta = (time2 - time1).total_seconds()

        return time_delta
    except ValueError as e:
        print("Error:", e)
        return None


'''    
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
    return "Ошибка при получении токена доступа"
'''  # Эндпоинт пользовательской авторизации


@app.route('/test')
def test():
    return render_template("test.html")
@app.route('/download_chat', methods=['POST'])
def download_chat():
    try:
        vod_id = request.form['vod_id']
        logging.info(f"Received request to download chat for VOD ID: {vod_id}")
        logging.info("Chat downloaded successfully")

        return render_template('chat.html')

    except Exception as e:
        logging.error(f"Error processing download_chat request: {e}")
        # Возвращаем ошибку в виде HTTP 500 Internal Server Error
        return "Internal Server Error", 500
'''
@app.route('/download_chat', methods=['POST'])
def download_chat():
    try:
        vod_id = request.form['vod_id']
        logging.info(f"Received request to download chat for VOD ID: {vod_id}")

        #chat_data = get_full_chat(vod_id)

        #if chat_data is None:
            #return "Unable to download chat data", 500

        #logging.info("Chat downloaded successfully")

        return render_template('chat.html')#, chat_data=chat_data)

    except Exception as e:
        logging.error(f"Error processing download_chat request: {e}")
        # Возвращаем ошибку в виде HTTP 500 Internal Server Error
        return "Internal Server Error", 500'''


@app.route('/get_info', methods=['POST'])
def get_info():
    if access_token:
        username = request.form.get('username')
        if not username:
            return "Пустой запрос"
        user_info = get_user_info(access_token, username)
        if user_info:
            stream_info = get_stream_info(access_token, username)
            past_streams = get_past_streams(access_token, user_info['id'])
            return render_template('main_info.html', user_info=user_info, stream_info=stream_info,
                                   past_streams=past_streams)
        else:
            return "Пользователь не найден"
    else:
        return "Не удалось получить Bearer токен доступа."
@app.route('/')
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
