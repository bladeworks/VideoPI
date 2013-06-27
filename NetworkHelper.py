#!/usr/bin/python
# -*- coding: utf8 -*-

import requests
from Helper import ThreadPool
import time
import logging


class Result:

    def __init__(self, url, resp, duration, range_support=True):
        self.url = url
        self.resp = resp
        self.duration = duration
        self.range_support = range_support


class BatchRequests:

    def __init__(self, urls, header_only=True, headers={'User-Agent': 'Mozilla/5.0'}, replace_url=True, retry=1):
        self.urls = urls
        self.header_only = header_only
        self.headers = headers
        self.results = []
        self.replace_url = replace_url
        self.retry = retry

    def get(self):
        self.results = [None] * len(self.urls)
        pool = ThreadPool(5)
        for idx, url in enumerate(self.urls):
            pool.add_task(self.getOne, url, idx)
        pool.wait_completion()
        return self.results

    def getOne(self, url, idx):
        logging.info("Get %s", url)
        start_time = time.time()
        resp = None
        if not 'Range' in self.headers:
            self.headers["Range"] = "bytes=0-1000000000000"
        range_support = False
        for r in range(self.retry):
            try:
                if self.header_only:
                    resp = requests.head(url, headers=self.headers, allow_redirects=True, timeout=2)
                else:
                    resp = requests.get(url, headers=self.headers, allow_redirects=True, timeout=2)
                if resp.status_code == 206:
                    range_support = True
                break
            except Exception:
                logging.exception("Got exception")
                logging.debug("Retry %s", r)
        if resp and resp.history and self.replace_url:
            url = resp.history[-1].headers['location']
        duration = time.time() - start_time
        logging.info("It takes %s to get %s.", duration, url)
        self.results[idx] = Result(url, resp, duration, range_support)

    def findFastest(self):
        if not self.results:
            self.get()
        fastest = sorted(self.results, key=lambda result: result.duration)[0].url
        logging.info("The fastest in %s is %s", self.urls, fastest)
        return fastest

    def rank(self):
        if not self.results:
            self.get()
        ranked = [r.url for r in sorted(self.results, key=lambda result: result.duration) if r and r.duration < 2]
        logging.info("Ranked = %s" % ranked)
        return ranked

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(module)s:%(lineno)d %(levelname)s: %(message)s', level=logging.DEBUG)
    BatchRequests(['http://www.google.com', 'http://www.baidu.com', 'http://192.168.1.100']).rank()
