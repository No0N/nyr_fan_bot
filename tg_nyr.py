import telebot
import urllib.request
import xml.etree.ElementTree as ET
import time
import sqlite3
from datetime import datetime
import pytz
from cons import xml_url, token_tg, chat_id

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

def send_message_to_channel():
    try:
        moscow_timezone = pytz.timezone('Europe/Moscow')
        current_time = datetime.now(moscow_timezone)
        current_hour = current_time.hour
        current_minute = current_time.minute

        if 9 <= current_hour < 10 and current_minute <= 10:
            conn = sqlite3.connect(database_file)
            cursor = conn.cursor()

            cursor.execute('SELECT id, title, url FROM videos WHERE post IS NULL OR post = "" LIMIT 1')
            row = cursor.fetchone()

            print(f"Row from database: {row}")

            if row is not None:
                video_id, video_title, video_url = row

                video_title_cleaned = video_title.split(' - ')[0]

                message_text_main_chat = f"{video_title_cleaned}\n\n{video_url}"
                bot.send_message(chat_id=chat_id, text=message_text_main_chat)
                print("Сообщение успешно отправлено в основной чат.")

                update_post_status(conn, video_id)
            else:
                print("Нет записей с пустым полем post. ")

            conn.close()
        else:
            print(f"Время не в заданном диапазоне для отправки сообщения.")

    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")

def parse_xml_and_save_to_db(url, db_file):
    conn = sqlite3.connect(db_file)
    create_table_if_not_exists(conn)

    while True:
        try:
            response = urllib.request.urlopen(url)
            xml_data = response.read()

            root = ET.fromstring(xml_data)

            added_rows_count = 0

            for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
                title = entry.find('{http://www.w3.org/2005/Atom}title').text
                pub_date = entry.find('{http://www.w3.org/2005/Atom}published').text
                video_url = entry.find('{http://www.w3.org/2005/Atom}link').attrib['href']

                content_element = entry.find('{http://www.w3.org/2005/Atom}content')
                post_content = content_element.text if content_element is not None else ""

                if not check_if_record_exists(conn, title, pub_date, video_url, post_content) and \
                    ("NHL Highlights" in title) and ("Rangers" in title):

                    print(f"Title: {title}")
                    print(f"pubDate: {pub_date}")
                    print(f"url: {video_url}")
                    print(f"post: {post_content}")
                    print()

                    insert_data(conn, title, pub_date, video_url, post_content)
                    added_rows_count += 1

            send_message_to_channel()

            time.sleep(300)

        except Exception as e:
            print(f"Ошибка при обработке XML данных: {e}")

    conn.close()

if __name__ == "__main__":
    database_file = "videos_database.db"
    parse_xml_and_save_to_db(xml_url, database_file)
