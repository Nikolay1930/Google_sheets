import psycopg2
import httplib2
import requests
import time
import datetime
import copy

from googleapiclient.discovery import build
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from oauth2client.service_account import ServiceAccountCredentials
from lxml import etree

from settings import *


def get_rate() -> float:
    """ Получение актуального курса USD/RUB"""
    # Получение сегодняшней даты и преобразование к нужному формату
    data = datetime.date.today().strftime("%d/%m/%Y")
    # Получение актуального курса рубля к доллару
    res = requests.get(f'https://www.cbr.ru/scripts/XML_daily.asp?date_req={data}').content
    tree = etree.XML(res)
    rate = tree.xpath(f'/ValCurs/Valute[@ID="R01235"]/Value')[0].text
    return float(rate.replace(',', '.'))


def create_database() -> None:
    """ Создание БД PostgreSQL """
    try:
        # Подключение к БД
        connection = psycopg2.connect(user=sql_connect['user'],
                                      password=sql_connect['password'],
                                      host=sql_connect['host'],
                                      port=sql_connect['port'])
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = connection.cursor()    # Курсор для выполнения операций с базой данных
        cursor.execute('CREATE DATABASE ' + sql_connect['database'])
    except:
        print("Ошибка при создании БД")
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("БД успешно создана. Соединение с PostgreSQL закрыто")


def create_tables() -> None:
    """ Создание таблицы в БД"""
    try:
        # Подключение к БД
        connection = psycopg2.connect(user=sql_connect['user'],
                                      password=sql_connect['password'],
                                      host=sql_connect['host'],
                                      port=sql_connect['port'],
                                      database=sql_connect['database'])
        cursor = connection.cursor()    # Курсор для выполнения операций с базой данных
        # Запрос к БД
        cursor.execute('''CREATE TABLE orders
            (id INT PRIMARY KEY NOT NULL,
            number_order INT,
            price_dollar REAL,
            price_rub REAL,
            date DATE);''')
        connection.commit()
    except:
        print("Ошибка при создании таблицы")
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("Таблица создана. Соединение с PostgreSQL закрыто")


def update_table(values: list) -> None:
    """ Обновление таблицы в БД """
    try:
        # Подключение к БД.
        connection = psycopg2.connect(user=sql_connect['user'],
                                      password=sql_connect['password'],
                                      host=sql_connect['host'],
                                      port=sql_connect['port'],
                                      database=sql_connect['database'])
        cursor = connection.cursor()    # Курсор для выполнения операций с базой данных
        rate: float = get_rate()   # Получение актуального курса доллара
        insert_query = '''INSERT INTO orders (id, number_order, price_dollar, price_rub, date)
                                    VALUES (%s, %s, %s, %s, %s)'''
        update_query = '''UPDATE orders SET date = %s, price_rub = %s, price_dollar = %s, number_order = %s   
                                    WHERE id = %s'''
        # Обновление таблицы
        for row in values:
            row.insert(-1, rate*float(row[2]))
            cursor.execute(f'SELECT id FROM orders WHERE id = {row[0]}')
            res = cursor.fetchall()
            if not res:     # Если такого id нет, то добавление новой записи
                cursor.execute(insert_query, row)
            else:           # Иначе обновление записи
                row = row[-1::-1]
                cursor.execute(update_query, row)
            connection.commit()
    except:
        print("Ошибка при обновлении таблицы")
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("Таблица обновлена. Соединение с PostgreSQL закрыто")


def connect_to_sheets() -> list:
    """ Подключение к серверу, считывание данных из таблицы на сервере """
    # Авторизуемся и получаем экземпляр доступа к API
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        CREDENTIALS_FILE,
        ['https://www.googleapis.com/auth/spreadsheets',
         'https://www.googleapis.com/auth/drive'])
    http_auth = credentials.authorize(httplib2.Http())
    service = build('sheets', 'v4', http=http_auth)

    # Считываем данные
    values = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range='A2:D999',
        majorDimension='ROWS'
    ).execute()
    return values['values']


if __name__ == '__main__':
    # create_database()   # Создание БД
    # create_tables()     # Создание таблицы
    values_primer: list = []     # Переменная для хранения состояния таблицы на сервере
    while True:
        values = connect_to_sheets()    # Подключаемся к серверу и получаем данные
        # Если полученные данные не равны предыдущим полученным данным, то обновляем таблицу.
        # Если данные в таблице на сервере не изменились, действия не выполняются
        if values != values_primer:
            values_primer = copy.deepcopy(values)   # Сохраняем состояние таблицы на сервере
            update_table(values)    # Обноляем таблицу
        time.sleep(10)
