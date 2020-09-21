# Запросы
import requests
# Прочие инструменты
import json
# Логгирование
import logging
import sys


logging.basicConfig(filename="./logs/telegram_handler_log.log", level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


class telegram_handler:
	"""Обработчик событий Telegram"""
	def __init__(self):
		self.bot_url = ""
		self.delete_webhook()
		self.chat_id = self.get_chat_id()


	def set_webhook(self, url):
		"""Функция установки вебхуков на туннель"""
		payload = {"url": url}
		post = requests.post(self.bot_url + "setWebhook", json=payload)

		if json.loads(post.text)["description"] == "Webhook is already set":
			logging.info("Вебхуки уже установлены на адрес %s" % (url))
		elif json.loads(post.text)["description"] == "Webhook was set":
			logging.info("Вебхуки установлены на адрес %s" % (url))
		else:
			logging.error("Не удалось установить вебхук на адрес %s" % (url))


	def delete_webhook(self):
		"""Функция установки вебхука на туннель"""
		payload = {"url": ""}
		post = requests.post(self.bot_url + "setWebhook", json=payload)


	def get_chat_id(self):
		"""Узнаем откуда пришло последнее сообщение."""
		get = requests.get(self.bot_url + "getUpdates")
		self.chat_id = get.json()["result"][-1]["channel_post"]["chat"]["id"]


	def send_message(self, message_text):
		"""Отправка сообщения в чат"""
		answer = {"chat_id": self.chat_id, "text": message_text}
		post = requests.post(self.bot_url + "sendMessage", json=answer)
