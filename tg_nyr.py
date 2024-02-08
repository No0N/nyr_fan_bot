import telebot
import urllib.request
import xml.etree.ElementTree as ET
import time
import sqlite3
import pytz
from datetime import datetime, timedelta
from cons import xml_url, token_tg, chat_id, chat_id_tmp


bot = telebot.TeleBot(token_tg)

def create_table_if_not_exists(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            pubDate TEXT,
            url TEXT,
            post TEXT
        )
    ''')
    conn.commit()

def insert_data(conn, title, pub_date, video_url, post_content):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO videos (title, pubDate, url, post) VALUES (?, ?, ?, ?)
    ''', (title, pub_date, video_url, post_content))
    conn.commit()

def update_post_status(conn, video_id):
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE videos SET post = 'X' WHERE id = ?
    ''', (video_id,))
    conn.commit()

def check_if_record_exists(conn, title, pub_date, video_url, post_content):
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id FROM videos WHERE url=?
    ''', (video_url,))
    return cursor.fetchone() is not None

def send_message_to_channel(schedule_time):
    try:
        conn = sqlite3.connect(database_file)
        cursor = conn.cursor()

        # Выбираем первую запись с пустым полем post
        cursor.execute('SELECT id, title, url FROM videos WHERE post IS NULL OR post = "" LIMIT 1')
        row = cursor.fetchone()

        print(f"Row from database: {row}")

        # Получаем текущее время в Московском времени
        current_time = datetime.now(pytz.timezone('Europe/Moscow'))
        
        print(f"CT={current_time}, ST={schedule_time}") 
        
        if row is not None:
            video_id, video_title, video_url = row  # Поля с ID, названием и URL видео

            # Планируем отправку сообщения в заданное время
            if current_time >= schedule_time:
                # Убираем дату из названия
                video_title_cleaned = video_title.split(' - ')[0]
                
                jojotime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(jojotime)
                print(f"CT={current_time}, ST={schedule_time}") 

                # Отправляем сообщение с названием и ссылкой в основной чат
                message_text_main_chat = f"{video_title_cleaned}\n\n{video_url}"
                bot.send_message(chat_id=chat_id, text=message_text_main_chat)
                print("Сообщение успешно отправлено в основной чат.")

                # Проставляем в поле post значение 'X' для выбранной строки
                update_post_status(conn, video_id)
            else:
                print("Время для отправки еще не наступило.")

        else:
            print("Нет записей с пустым полем post.")

            # Отправляем сообщение с текущим временем во временный чат
            current_time_tmp_chat = current_time.strftime("%H:%M:%S")
            message_text_tmp_chat = f"Текущее время: {current_time_tmp_chat}"
            bot.send_message(chat_id=chat_id_tmp, text=message_text_tmp_chat)
            print("Сообщение с текущим временем успешно отправлено во временный чат.")

        conn.close()

    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")

# Функция для конвертации scheduled_datetime во время сервера
def convert_to_server_time(scheduled_datetime):
    server_timezone = pytz.timezone('Europe/Moscow')  # Ваш часовой пояс сервера
    server_time = datetime.now(server_timezone)
    return scheduled_datetime.astimezone(server_timezone)

def parse_xml_and_save_to_db(url, db_file):
    conn = sqlite3.connect(db_file)
    create_table_if_not_exists(conn)

    while True:
        try:
            # Получаем данные XML по ссылке
            response = urllib.request.urlopen(url)
            xml_data = response.read()

            # Парсим XML
            root = ET.fromstring(xml_data)

            # Счетчик добавленных записей
            added_rows_count = 0

            # Проходим по элементам и записываем данные в базу данных
            for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
                title = entry.find('{http://www.w3.org/2005/Atom}title').text
                pub_date = entry.find('{http://www.w3.org/2005/Atom}published').text
                video_url = entry.find('{http://www.w3.org/2005/Atom}link').attrib['href']

                # Проверяем наличие элемента <content>
                content_element = entry.find('{http://www.w3.org/2005/Atom}content')
                post_content = content_element.text if content_element is not None else ""

                # Проверяем, существует ли запись с такими же данными в базе данных, и проверяем, содержатся ли ключевые слова в заголовке
                if not check_if_record_exists(conn, title, pub_date, video_url, post_content) and \
                    ("NHL Highlights" in title) and ("Rangers" in title):
                    # Выводим информацию в формате ключ:значение
                    print(f"Title: {title}")
                    print(f"pubDate: {pub_date}")
                    print(f"url: {video_url}")
                    print(f"post: {post_content}")
                    print()

                    # Записываем данные в базу данных
                    insert_data(conn, title, pub_date, video_url, post_content)
                    added_rows_count += 1

            # Конвертируем время сервера
            server_time = convert_to_server_time(scheduled_datetime)

            # Проверяем, больше ли текущее время сервера или равно scheduled_datetime
            if server_time >= scheduled_datetime:
                # Отправляем сообщение
                send_message_to_channel(server_time)

            # Ждем 5 минут перед следующим опросом
            time.sleep(300)  # 300 секунд = 5 минут

        except Exception as e:
            print(f"Ошибка при обработке XML данных: {e}")

    conn.close()

if __name__ == "__main__":
    database_file = "videos_database.db"
    
    # Указываем время в MSK для отправки сообщения (в формате HH:MM)
    scheduled_time_utc = datetime.strptime("01:30", "%H:%M").time()
    
    # Конвертируем в московское время
    scheduled_datetime = datetime.combine(datetime.today(), scheduled_time_utc).astimezone(pytz.timezone('Europe/Moscow'))

    parse_xml_and_save_to_db(xml_url, database_file)
