from telegram_handler import telegram_handler
from setup_monitor import start_monitor
# pyngrock для туннелирования
from pyngrok import ngrok
# Flask для обработки запросов, приходящих на сервер
from flask import Flask, request
# Логгирование
import logging
import sys
# Запросы
import requests
# Паралеллизм
from threading import Thread, Lock
# Прочие инструменты
import re
import json
import time

from bs4 import BeautifulSoup


app = Flask(__name__)
@app.route("/", methods=["POST", "GET"])
def index():
	if request.method == "POST":
		post = request.get_json()

		try:
			chat_id = post["channel_post"]["chat"]["id"] # id чата, с которого пришло сообщение
			message = post["channel_post"]["text"] # Сам текст сообщения
			monitor.message_handler(message) # Вызов обработчика монитора
		except:
			pass

	return "<h1>Если эта страница видна, то сервер работает<h1>"


def launch_flask_server():
	"""Запускаем сервер"""
	app.run()


def setup_ngrok(telegram_handler_class):
	"""Создаем туннель на адрес localhost:5000. В функцию нужно передать экземпляр класса telegram_handler"""
	url = re.sub("http", "https", ngrok.connect(5000)) # Внешняя ссылка на туннель
	logging.info("Туннель открыт, ссылка - %s" % (url))
	telegram_handler_class.set_webhook(url)


def setup_server():
	"""Настраиваем сервер - запускаем его и создаем туннель. В функцию нужно передать экземпляр класса telegram_handler"""
	telegram_handler_class = telegram_handler()

	flask_server = Thread(target=launch_flask_server)
	ngrok_setup = Thread(target=setup_ngrok, args=(telegram_handler_class, ))

	flask_server.start()
	ngrok_setup.start()


if __name__ == "__main__":
	setup_server()
	monitor = start_monitor()
	monitor.main()
