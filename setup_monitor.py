# Парсинг страниц
from bs4 import BeautifulSoup
# Библиотека обработчика телеграмм
from telegram_handler import telegram_handler
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
import datetime
import random
from glob import glob
import locale
import copy
locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')


logging.basicConfig(filename="./logs/avito_monitor_log.log", level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


class avito_monitor:
	"""Класс монитора авито. Использует очередь, которую пытается загрузить из файла, также поступает и со всеми
	ссылками на предметы, которые мониторит по тегам из очереди. !!!НУЖНО ПЕРЕДАТЬ ЭКЗЕМПЛЯР КЛАССА telegram_handler."""
	def __init__(self, queue_path=None, prev_scan_path=None):
		"""Читает query и множества url из файлов. Если не удалось - оставляет их пустыми."""
		def read_text_file(file_path):
			file = list()
			with open(file_path, "r") as f:
				for line in f:
					file.append(line)
				f.close()
			return file

		if queue_path != None:
			try:
				self.queue = read_text_file(queue_path)
			except FileNotFoundError:
				logging.warning("Файл с очередью на мониторинг не найден. Очередь будет пустой.")
				self.empty_queue_flag = True
				self.queue = dict()
		else:
			logging.warning("Файл с очередью на мониторинг не указан. Очередь будет пустой.")
			self.queue = dict()

		self.telegram_handler = telegram_handler()
		self.telegram_handler.get_chat_id()

		self.sess = requests.Session()

		self.lock = Lock()


	def save_state(self):
		filename = str(datetime.datetime.now()).replace(" ", "_")
		current_queue = copy.deepcopy(self.queue)
		for tag in current_queue.keys():
			current_queue[tag]["monitor_start_time"] = str(current_queue[tag]["monitor_start_time"])

		if not os.path.exists("./saved_states"):
			os.mkdir("./saved_states")

		with open("./saved_states/" + filename + "_state.json", "w") as json_save:
			json.dump(current_queue, json_save)
		self.telegram_handler.send_message("Очередь была сохранена под названием %s" % (filename))


	def load_state_list(self):
		all_saves = glob("./saved_states/*")
		if all_saves:
			saves_string = str()
			for num, filename in enumerate(all_saves):
				saves_string += (str(num) + " " + filename + "\n")
			self.telegram_handler.send_message("Список доступных сохранений:\n" + saves_string)
		else:
			self.telegram_handler.send_message("Сохранений нет")


	def load_state(self, filename_num):
		all_saves = glob("./saved_states/*")
		with open(all_saves[filename_num], "r") as json_save:
			loading_queue = json.load(json_save)

		for tag in loading_queue.keys():
			loading_queue[tag]["monitor_start_time"] = datetime.datetime.strptime(loading_queue[tag]["monitor_start_time"], "%Y-%m-%d %H:%M:%S.%f") 

		self.queue = copy.deepcopy(loading_queue)
		self.telegram_handler.send_message("Очередь %s была загружена" % (all_saves[filename_num]))

		self.empty_queue_flag = False


	def write_links_into_file(self, links, filename):
		"""Запись ссылок из списка в фаил"""
		with open(filename, "a") as file:
			for link in links:
				file.write(link + "\n")
			file.close()


	def random_delay(self, upper_limit, lower_limit):
		time.sleep(random.randint(upper_limit, lower_limit))


	def message_handler(self, message):
		"""Обработчик сообщений. Добавляет в очередь тэги или удаляет их."""
		if "add" in message:
			if not re.search("\d+", message):
				price_range = None
				command, value = message.split(" ")
			else:
				command, value, price_range = message.split(" ")

			self.telegram_handler.send_message("Тэг '%s' был добавлен в очередь. \n Очередь: %s" % (value, str(list(self.queue.keys())) + " <-- " + str(value)))
			self.telegram_handler.send_message("Собираю информацию по запросу %s" % (value))

			pages_num, total_num = self.get_query_info(value, price_range)

			self.queue[value] = dict()
			self.queue[value]["pages_num"] = pages_num
			self.queue[value]["ad_num"] = total_num
			self.queue[value]["links"] = list()
			self.queue[value]["monitor_start_time"] = datetime.datetime.now()
			self.queue[value]["price_range"] = price_range

			self.telegram_handler.send_message("По запросу %s - %s объявлений, доступно страниц - %s \nНачинаю мониторить" % (value, total_num, pages_num))

			self.empty_queue_flag = False
			

		elif "delete" in message:
			command, value = message.split(" ")
			self.telegram_handler.send_message("Тэг '%s' был удален из очереди. \n Очередь: %s" % (value, str(list(self.queue.keys())) + " --> " + str(value)))
			del self.queue[value]
		elif str(message) == "clear queue":
			self.telegram_handler.send_message("Очередь очищена.")
			self.queue = dict()
		elif str(message) == "get queue":
			self.telegram_handler.send_message("Очередь: %s" % str(list(self.queue.keys())))
		elif str(message) == "load state list":
			self.load_state_list()
		elif re.search("load state \d+", message):
			self.load_state(int(re.search("\d+", message).group(0)))
		elif str(message) == "save state":
			self.save_state()
		else:
			self.telegram_handler.send_message("Команда не соответствует формату")


	def monitor_queue(self):
		"""Функция мониторинга. Если очередь пустая, то просто ожидает. Как только в query добавляется
		тэг - начинает мониторить."""
		while True:
			try:
				if not self.queue:
					logging.info("Очередь пустая, ожидаю запроса")
					self.telegram_handler.send_message("Очередь пустая, ожидаю запроса")
					self.empty_queue_flag = True
					while True:
						if not self.empty_queue_flag:
							break
						else:
							pass
				else:
					for tag in list(self.queue.keys()):
						for page in range(1, int(self.queue[tag]["pages_num"]) + 1):
							if not self.scrape_all_urls_from_page(tag, page, self.queue[tag]["price_range"]):
								break
							self.random_delay(3,6)
						if len(self.queue[tag]["links"]) >= 2000:
							self.queue[tag]["links"] = list()
							self.queue[tag]["monitor_start_time"] = datetime.datetime.now()
						self.random_delay(10, 15)
			except Exception as e:
				print(e)


	def get_query_info(self, query_word, price_range):
		"""Получение информации о запросе - количество страниц и количество объявлений"""
		if not price_range:
			get = self.sess.get("https://www.avito.ru/moskva?q={query}".format(query=query_word))
		else:
			lower_limit, upper_limit = price_range.split("-")
			get = self.sess.get("https://www.avito.ru/moskva?pmax={upper}&pmin={lower}&q={query}".format(query=query_word, upper=upper_limit, lower=lower_limit))
		
		if re.search("Ничего не найдено", get.text):
			self.telegram_handler.send_message("По данному запросу ничего не найдено. Тэг будет удален из очереди.")
			self.telegram_handler.send_message("Тэг '%s' был удален из очереди. \n Очередь: %s" % (query_word, str(list(self.queue.keys())) + " --> " + str(query_word)))
			del self.queue[query_word]

		try:
			pages_num = re.findall("page\(\d+", get.text)[-1][5:] 
		except:
			pages_num = 1

		total_num = int(re.findall('page-title/count">[0-9a-z& :;]+', get.text)[0].replace(' ', '').split(">")[1])   

		return pages_num, total_num


	def scrape_all_urls_from_page(self, query_word, page_num, price_range):
		if not price_range:
			get = self.sess.get("https://www.avito.ru/moskva?s=104&q={query}&p={page}".format(query=query_word, page=page_num))
		elif price_range:
			lower_limit, upper_limit = price_range.split("-")
			get = self.sess.get("https://www.avito.ru/moskva?pmax={upper}&pmin={lower}&q={query}&p={page}&s=104".format(query=query_word, page=page_num, upper=upper_limit, lower=lower_limit))

		soup = BeautifulSoup(get.text, "lxml")

		for tag in soup.find_all("div", {"class":"description item_table-description"}):
			link = tag.find_all("a", {"class":"snippet-link"})[0]["href"]
			price = tag.find_all("meta", {"itemprop":"price"})[0]["content"]
			date = str(datetime.date.today().year) + ' ' + tag.find_all("div", {"class":"snippet-date-info"})[0]["data-tooltip"]
			date_pythonic = datetime.datetime.strptime(date, "%Y %d %B %H:%M")
			
			if date_pythonic >= (self.queue[query_word]["monitor_start_time"] - datetime.timedelta(minutes=1)):
				if link not in self.queue[query_word]["links"]:
					self.telegram_handler.send_message("https://www.avito.ru" + link)
					self.queue[query_word]["links"].append(link)
			else:
				if page_num != 1:
					return False


	def main(self):
		consumer = Thread(target=self.monitor_queue)
		consumer.start()


def start_monitor():
	monitor = avito_monitor()
	return monitor
