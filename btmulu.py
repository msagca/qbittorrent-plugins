#VERSION: 1.0
#AUTHOR: msagca
# -*- coding: utf-8 -*-

from helpers import retrieve_url
from html.parser import HTMLParser
from novaprinter import prettyPrinter
import queue
import threading

class PrettyWorker(threading.Thread):

	def __init__(self, queue):
		super().__init__()
		self.queue = queue

	def run(self):
		while True:
			try:
				prettyPrinter(self.queue.get(timeout=3))
			except queue.Empty:
				return
			self.queue.task_done()

class btmulu(object):

	name = "BTmulu"
	url = "https://www.btmulu.com"
	supported_categories = {"all": "0"}

	class BTmuluParser(HTMLParser):

		def __init__(self, url):
			super().__init__()
			self.engine_url = url
			self.results_per_page = 20
			self.torrent_info = {
				"link": -1,
				"name": -1,
				"size": -1,
				"seeds": -1,
				"leech": -1,
				"engine_url": self.engine_url,
				"desc_link": -1
			}
			self.total_results = 0
			self.print_result = False
			self.find_results_per_page = False
			self.find_summary = True
			self.find_torrent = False
			self.find_torrent_extension = False
			self.find_torrent_info = False
			self.find_torrent_link = False
			self.find_torrent_name = False
			self.find_torrent_size = False
			self.find_total_results = False
			self.parse_results_per_page = False
			self.parse_torrent_name = False
			self.parse_torrent_size = False
			self.parse_total_results = False
			self.skip_torrent_extension = False

			self.print_queue = queue.Queue()
			self.print_worker = PrettyWorker(self.print_queue)

		def handle_starttag(self, tag, attrs):
			if self.find_summary:
				if tag == "div":
					attributes = dict(attrs)
					if "class" in attributes:
						if attributes["class"] == "summary":
							self.find_summary = False
							self.find_results_per_page = True
			elif self.find_results_per_page:
				if tag == "b":
					self.find_results_per_page = False
					self.parse_results_per_page = True
			elif self.find_total_results:
				if tag == "b":
					self.find_total_results = False
					self.parse_total_results = True
			elif self.find_torrent:
				if tag == "article":
					attributes = dict(attrs)
					if "data-key" in attributes:
						self.find_torrent = False
						self.find_torrent_link = True
			elif self.find_torrent_link:
				if tag == "a":
					attributes = dict(attrs)
					if "href" in attributes:
						if attributes["href"].find("hash") != -1:
							torrent_link = attributes["href"].strip()
							self.torrent_info["desc_link"] = f"{self.engine_url}{torrent_link}"
							magnet_id = torrent_link.split("hash/")[1].split(".html")[0].strip()
							self.torrent_info["link"] = f"magnet:?xt=urn:btih:{magnet_id}"
							self.find_torrent_link = False
							self.find_torrent_info = True
			elif self.find_torrent_info:
				if tag == "h4":
					self.find_torrent_info = False
					self.find_torrent_extension = True
			elif self.find_torrent_extension:
				if tag == "span":
					attributes = dict(attrs)
					if "class" in attributes:
						if attributes["class"].find("label") != -1:
							self.find_torrent_extension = False
							self.skip_torrent_extension = True
			elif self.find_torrent_size:
				if tag == "p":
					self.find_torrent_size = False
					self.parse_torrent_size = True

		def handle_data(self, data):
			if self.parse_results_per_page:
				results_per_page = data.split("-")[1].strip()
				if results_per_page.isnumeric():
					self.results_per_page = int(results_per_page)
				self.parse_results_per_page = False
				self.find_total_results = True
			elif self.parse_total_results:
				total_results = data.replace(",", "").strip()
				if total_results.isnumeric():
					self.total_results = int(total_results)
				self.parse_total_results = False
				self.find_torrent = True
			elif self.parse_torrent_name:
				self.torrent_info["name"] = data.strip()
				self.parse_torrent_name = False
				self.find_torrent_size = True
			elif self.parse_torrent_size:
				if data.find("Size") != -1:
					if data.find("Created") != -1:
						size, unit = data.split("Size：")[1].split("Created")[0].split(" ")
				elif data.find("ファイルサイズ") != -1:
					if data.find("創建時期") != -1:
						size, unit = data.split("ファイルサイズ：")[1].split("創建時期")[0].split(" ")
				elif data.find("文件大小") != -1:
					if data.find("创建时间") != -1:
						size, unit = data.split("文件大小：")[1].split("创建时间")[0].split(" ")
				elif data.find("文件大小") != -1:
					if data.find("創建時間") != -1:
						size, unit = data.split("文件大小：")[1].split("創建時間")[0].split(" ")
				if isinstance(size, str) and isinstance(unit, str):
					size = size.strip()
					unit = unit.strip()
					if unit == "GB":
						size = str(float(size)*1024*1024*1024)
					elif unit == "MB":
						size = str(float(size)*1024*1024)
					elif unit == "KB":
						size = str(float(size)*1024)
					else:
						size = -1
				else:
					size = -1
				self.torrent_info["size"] = size
				self.parse_torrent_size = False
				self.print_result = True

		def handle_endtag(self, tag):
			if self.print_result:
				self.print_queue.put(self.torrent_info)
				self.torrent_info = {
					"link": -1,
					"name": -1,
					"size": -1,
					"seeds": -1,
					"leech": -1,
					"engine_url": self.engine_url,
					"desc_link": -1
				}
				self.print_result = False
				self.find_torrent = True
			elif self.skip_torrent_extension:
				self.skip_torrent_extension = False
				self.parse_torrent_name = True

	def search(self, what="ubuntu", cat="all"):
		parser = self.BTmuluParser(self.url)
		parser.print_worker.start()
		parser.print_queue.join()
		page_number = 1
		torrent_count = 1
		while True:
			search_url = f"{self.url}/search/page-{page_number}.html?name={what}"
			try:
				retrieved_page = retrieve_url(search_url)
				parser.feed(retrieved_page)
			except:
				break
			if torrent_count < parser.total_results:
				#torrent_count += parser.results_per_page
				torrent_count += 20
				page_number += 1
				if page_number > 50:
					break
			else:
				break
		"""
		while not parser.print_queue.empty():
			prettyPrinter(parser.print_queue.get())
		"""
		parser.close()
