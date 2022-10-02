import psycopg2
import datetime
import time
from telethon import TelegramClient
from settings import *


client = TelegramClient('send_message', api_id, api_hash)


async def main(lst_send: list) -> None:
    """ Отправляет сообщения в телеграмм """
    try:
        for row in lst_send:
            await client.send_message(name_user, f'Заказ № {row[0]} просрочил срок доставки на {row[1]} days!')
            time.sleep(1)
    except ValueError:
        pass


if __name__ == '__main__':
    try:
        # Подключение к БД.
        connection = psycopg2.connect(user=sql_connect['user'],
                                      password=sql_connect['password'],
                                      host=sql_connect['host'],
                                      port=sql_connect['port'],
                                      database=sql_connect['database'])
        cursor = connection.cursor()  # Курсор для выполнения операций с базой данных
        data_now = datetime.date.today()    # Получение сегодняшней даты
        cursor.execute('SELECT * FROM orders')
        res = cursor.fetchall()
        lst_send: list = []
        for row in res:
            delta_day = (row[-1] - data_now).days   # Разница между датой поставки и сегодняшним днем
            if delta_day < 0:                       # Сохраняем просроченные заказы в список
                lst_send.append([row[1], delta_day])
    except:
        print("Ошибка при обращение к БД")
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("Соединение с PostgreSQL закрыто")
    if lst_send:  # Вызываем функцию для отправки сообщений
        with client:
            client.loop.run_until_complete(main(lst_send))