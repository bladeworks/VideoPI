#!/usr/bin/python
# -*- coding: utf8 -*-

import requests
from downloader import ThreadPool
import time
import logging


class Result:

    def __init__(self, url, resp, duration):
        self.url = url
        self.resp = resp
        self.duration = duration


class BatchRequests:

    def __init__(self, urls, header_only=True, headers={'User-Agent': 'Mozilla/5.0'}):
        self.urls = urls
        self.header_only = header_only
        self.headers = headers
        self.results = []

    def get(self):
        pool = ThreadPool(len(self.urls))
        for url in self.urls:
            pool.add_task(self.getOne, url)
        pool.wait_completion()
        return self.results

    def getOne(self, url):
        logging.info("Get %s", url)
        start_time = time.time()
        resp = None
        try:
            if self.header_only:
                resp = requests.head(url, headers=self.headers, timeout=2)
            else:
                resp = requests.get(url, headers=self.headers, timeout=2)
        except Exception:
            logging.exception("Got exception")
        if resp and resp.history:
            url = resp.history[-1].headers['location']
        duration = time.time() - start_time
        logging.info("It takes %s to get %s.", duration, url)
        self.results.append(Result(url, resp, duration))

    def findFastest(self):
        if not self.results:
            self.get()
        fastest = sorted(self.results, key=lambda result: result.duration)[0].url
        logging.info("The fastest in %s is %s", self.urls, fastest)
        return fastest

    def rank(self):
        if not self.results:
            self.get()
        ranked = [r.url for r in sorted(self.results, key=lambda result: result.duration) if r.duration < 2]
        logging.info("Ranked = %s" % ranked)
        return ranked

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(module)s:%(lineno)d %(levelname)s: %(message)s', level=logging.DEBUG)
    BatchRequests(['http://www.google.com', 'http://www.baidu.com', 'http://192.168.1.100']).rank()
