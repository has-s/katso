const axios = require('axios');

class ChatFormat {
    constructor(value) {
        this.value = value;
    }
}

ChatFormat.JSON = "json";

class DownloadType {
    constructor(value) {
        this.value = value;
    }
}

DownloadType.VIDEO = 1;

class DownloadOptions {
    constructor(download_type, video_id, download_format, video_start = null) {
        this.download_type = download_type;
        this.video_id = video_id;
        this.download_format = download_format;
        this.video_start = video_start;
    }
}

class ChatDownloader {
    constructor(download_options) {
        this.download_options = download_options;
    }

    async _fetch_chat_data() {
        const headers = {
            "Client-ID": "kd1unb4b3q4t58fwlpcbzcbnm76a8fp"
        };

        let url;
        let payload;
        if (this.download_options.download_type.value === DownloadType.VIDEO) {
            url = "https://gql.twitch.tv/gql";
            payload = {
                "operationName": "VideoCommentsByOffsetOrCursor",
                "variables": {
                    "videoID": this.download_options.video_id,
                    "contentOffsetSeconds": this.download_options.video_start
                },
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "b70a3591ff0f4e0313d126c6a1502d79a1c02baebb288227c582044aa76adf6a"
                    }
                }
            };
        }

        try {
            const response = await axios.post(url, payload, { headers });
            return response.data;
        } catch (error) {
            console.error("Error fetching chat data:", error);
            return null;
        }
    }

    async _process_chat_data(chat_data) {
        if (!chat_data) {
            console.log("No chat data to process");
            return [];
        }

        const processed_comments = [];
        for (const comment of chat_data[0].data.video.comments.edges) {
            const processed_comment = {
                '_id': comment.node.id,
                'created_at': comment.node.createdAt,
                'content_offset_seconds': comment.node.contentOffsetSeconds,
                'commenter': {
                    'display_name': comment.node.commenter.displayName.trim(),
                    '_id': comment.node.commenter.id,
                    'name': comment.node.commenter.login
                },
                'message': {
                    'body': comment.node.message.fragments.map(fragment => fragment.text).join(""),
                    'user_color': comment.node.message.userColor
                }
            };
            processed_comments.push(processed_comment);
        }

        return processed_comments;
    }
}

async function get_chat_from(chat_downloader, timestamp) {
    try {
        // Устанавливаем временную метку начала загрузки чата
        chat_downloader.download_options.video_start = timestamp;

        // Получаем данные чата
        const chat_data = await chat_downloader._fetch_chat_data();

        return chat_data;

    } catch (error) {
        console.error("Error fetching chat data:", error);
        return null;
    }
}

function get_last_message_timestamp(chat_data) {
    let last_message_timestamp = null;

    // Проверяем наличие данных чата
    if (chat_data && chat_data.data && chat_data.data.video && chat_data.data.video.comments) {
        const comments = chat_data.data.video.comments.edges;

        // Если есть комментарии, получаем временную метку последнего сообщения
        if (comments.length > 0) {
            const last_comment = comments[comments.length - 1].node;
            last_message_timestamp = last_comment.createdAt;

            // Преобразуем формат временной метки
            last_message_timestamp = last_message_timestamp.replace('T', ' ').replace('Z', '');
        }
    }

    return last_message_timestamp;
}

function filter_chat_data(chat_part) {
    // Создаем список для хранения отфильтрованных данных
    const filtered_data = [];

    // Итерируемся по комментариям и извлекаем только нужные данные
    for (const comment of chat_part.data.video.comments.edges) {
        const commenter_id = comment.node.commenter.id;
        const display_name = comment.node.commenter.displayName;
        const timestamp = comment.node.contentOffsetSeconds;
        const message_text = comment.node.message.fragments[0].text;

        // Создаем объект для каждого комментария с нужными данными
        const filtered_comment = {
            "commenter_id": commenter_id,
            "display_name": display_name,
            "timestamp": timestamp,
            "message_text": message_text
        };

        // Добавляем объект комментария в список
        filtered_data.push(filtered_comment);
    }

    return filtered_data;
}

function flatten_chat(chat_filt) {
    const flattened_chat = [];
    for (const segment of chat_filt) {
        flattened_chat.push(...segment);
    }
    return flattened_chat;
}

async function get_full_chat(vod_id) {
    try {
        const created_at = ''; // Получить данные времени начала стрима
        const duration = ''; // Получить данные продолжительности стрима

        const download_options = new DownloadOptions(
            DownloadType.VIDEO,
            vod_id,
            ChatFormat.JSON
        );

        const chat_downloader = new ChatDownloader(download_options);

        // Получаем данные чата
        let chat_filt = [];
        let last_stamp = 0;
        let chat_data = await get_chat_from(chat_downloader, last_stamp);

        // Получаем время начала стрима
        const stream_start_time = convert_time_format(created_at);
        const stream_duration = duration_to_seconds(duration);

        const delta = parseInt(calculate_delta(stream_start_time, get_last_message_timestamp(chat_data)));

        chat_filt = filter_chat_data(chat_data);
        // Загружаем часть чата, начиная с текущей временной дельты
        chat_data = await get_chat_from(chat_downloader, delta);
        last_stamp = +delta;
        // Загружаем чат по частям, начиная с начала стрима
        chat_filt.push(filter_chat_data(chat_data));
        while (last_stamp <= stream_duration) {
            const chat_part = await get_chat_from(chat_downloader, last_stamp);
            const glmt = get_last_message_timestamp(chat_part);
            const strsttime = stream_start_time;
            last_stamp = parseInt(calculate_delta(strsttime, glmt));
            chat_filt.push(filter_chat_data(chat_data));
        }
        console.log("Chat downloaded successfully");
        return flatten_chat(chat_filt);

    } catch (error) {
        console.error("Error processing download_chat request:", error);
        return null;
    }
}

function convert_time_format(time_str, from_format = "%Y-%m-%dT%H:%M:%SZ", to_format = "%Y-%m-%d %H:%M:%S.%f") {
    try {
        // Преобразуем строку времени из исходного формата в объект Date
        const time_obj = new Date(time_str);

        // Преобразуем объект Date обратно в строку в нужном формате
        const new_time_str = time_obj.toISOString().replace('T', ' ').replace('Z', '');

        return new_time_str;
    } catch (error) {
        console.error("Error:", error);
        return null;
    }
}

function duration_to_seconds(duration_str) {
    // Регулярное выражение для извлечения часов, минут и секунд из строки
    const pattern = /(\d+)h(\d+)m(\d+)s/;

    // Поиск соответствия шаблону в строке
    const match = duration_str.match(pattern);

    if (match) {
        const hours = parseInt(match[1]);
        const minutes = parseInt(match[2]);
        const seconds = parseInt(match[3]);

        const total_seconds = hours * 3600 + minutes * 60 + seconds;
        return total_seconds;
    } else {
        return null;
    }
}

function calculate_delta(time_str1, time_str2) {
    try {
        // Преобразуем строки в объекты Date
        const time1 = new Date(time_str1);
        const time2 = new Date(time_str2);

        // Вычисляем разницу между временными отметками в секундах
        const time_delta = (time2 - time1) / 1000;

        return time_delta;
    } catch (error) {
        console.error("Error:", error);
        return null;
    }
}

// Пример использования:
app.post('/download_chat', async (req, res) => {
    try {
        const vod_id = req.body.vod_id;
        console.log("Received request to download chat for VOD ID:", vod_id);

        const chat_data = await get_full_chat(vod_id);

        if (chat_data === null) {
            res.status(500).send("Unable to download chat data");
            return;
        }

        console.log("Chat downloaded successfully");
        res.render('chat.html', { chat_data });

    } catch (error) {
        console.error("Error processing download_chat request:", error);
        res.status(500).send("Internal Server Error");
    }
});
