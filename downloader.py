#!/usr/bin/python
# -*- coding: utf8 -*-

import requests
import logging
import time
import os
import subprocess
import sys
from threading import Thread
from Queue import Queue
from NetworkHelper import BatchRequests
from config import get_cfg

chunk_size = int(get_cfg('chunk_size'))
download_threads = int(get_cfg('download_threads'))

if sys.platform == 'darwin':
    AXEL_PATH = os.path.join(os.path.dirname(__file__),"darwin", "axel")
else:
    AXEL_PATH = os.path.join(os.path.dirname(__file__), "axel")


class Downloader:

    def __init__(self, url, download_threads, chunk_size, start_percent=0,
                 outfile=None, file_seq=0, alternativeUrls=[], total_length=None):
        self.url = url
        self.total_length = total_length
        logging.info("Construct downloader for url %s", self.url)
        self.download_threads = download_threads
        self.chunk_size = chunk_size
        self.outfile = outfile
        self.alternativeUrls = alternativeUrls
        self.write_done = False
        self.file_seq = file_seq
        self.start_percent = start_percent
        self.start_byte = 0
        self.getSizeInfo()
        self.download_thread = Thread(target=self.download)
        self.start_time = 0
        self.write_queue = Queue(1)
        self.write_thread = Thread(target=self.writeFile)
        self.download_process = None
        self.stopped = False
        self.file_queue = Queue()
        self.file_queue.put('/tmp/faxel0')
        self.file_queue.put('/tmp/faxel1')

    def writeFile(self):
        while True:
            result = self.write_queue.get()
            logging.info("Get %s", result)
            if result != 'stopped':
                if self.outfile:
                    filename = self.outfile
                else:
                    filename = "/tmp/download_part/%s" % self.file_seq
                logging.debug("Begin write file %s", filename)
                subprocess.call("cat %s > %s" % (result, filename), shell=True)
                logging.debug("End write file %s" % filename)
                self.file_queue.put(result)
                self.file_seq += 1
            else:
                break
            if self.stopped and self.write_queue.empty():
                break
        logging.info("Write stopped")
        self.write_done = True

    def getSizeInfo(self):
        if not self.total_length:
            headers = {'User-Agent': 'Mozilla/5.0'}
            for i in range(10):
                if self.stopped:
                    return
                resp = requests.head(self.url, headers=headers, allow_redirects=True, timeout=2)
                if 200 <= resp.status_code < 300:
                    info = resp.headers
                    break
                else:
                    logging.info("The status_code is %s, retry %s", resp.status_code, (i + 1))
            logging.debug('info = %s', info)
            self.total_length = int(int[info["content-length"]])
        new_length = self.total_length * (1 - self.start_percent)
        self.start_byte = self.total_length - new_length
        self.total_length = new_length
        self.file_num = int(self.total_length / self.chunk_size)
        if self.total_length % self.chunk_size > 0:
            self.file_num += 1
        logging.info("total_length = %s, chunk_size = %s", self.total_length, self.chunk_size)

    def start(self):
        self.download_thread.start()
        self.write_thread.start()

    def download(self):
        start_byte = 1
        urls = [self.url]
        #if self.alternativeUrls:
        #    urls = self.alternativeUrls
        while True:
            if self.stopped:
                break
            filename = self.file_queue.get()
            if filename == 'stopped':
                break
            end_byte = start_byte + self.chunk_size - 1
            if end_byte > self.total_length:
                end_byte = self.total_length
            logging.info("Downloading %s-%s", start_byte, end_byte)
            download_cmd = [AXEL_PATH, '-n', str(self.download_threads), '-o', filename, '-f', str(start_byte), '-t', str(end_byte)]
            download_cmd.extend(urls)
            # logging.info("Download_cmd: %s", download_cmd)
            # logging.info("Download_cmd: %s", " ".join(download_cmd))
            for i in range(5):
                # Run the axel to download the file
                if self.stopped:
                    break
                if i > 0:
                    logging.warn("Retry %s", i)
                subprocess.call(["rm", "-f", filename])
                subprocess.call(["rm", "-f", "/tmp/%s.st" % filename])
                with open('/tmp/download.log', 'w') as f:
                    self.download_process = subprocess.Popen(download_cmd, stdout=f)
                expected_file_size = end_byte - start_byte + 1
                self.download_process.communicate()
                try:
                    file_size = os.path.getsize(filename)
                    if file_size == expected_file_size:
                        break
                    else:
                        logging.warn("Filesize mismatch, expect %s but got %s", expected_file_size, file_size)
                except:
                    logging.exception("Got exception")
            else:
                raise Exception("Failed after retry 5 times")
            logging.info("Done: Downloading %s-%s", start_byte, end_byte)
            self.write_queue.put(filename)
            if end_byte < self.total_length:
                start_byte = end_byte + 1
            else:
                break
        self.write_queue.put("stopped")
        while not self.write_done:
            time.sleep(0.1)
        self.stopped = True
        logging.info("Finished download")

    def stop(self):
        self.stopped = True
        try:
            if self.download_process:
                self.download_process.terminate()
        except:
            logging.exception("Got exception")
        logging.info("Clear file_queue")
        try:
            self.file_queue.get(False)
            self.file_queue.get(False)
        except:
            logging.exception("Got exception")
        try:
            self.file_queue.put('stopped', False)
        except:
            logging.exception("Got exception")
        logging.info("Clear write_queue")
        try:
            self.write_queue.get(False)
            self.write_queue.get(False)
        except:
            logging.exception("Got exception")
        try:
            self.write_queue.put('stopped', False)
        except:
            logging.exception("Got exception")

    def getCatCmd(self):
        logging.info("Total file_num = %s", self.file_num)
        return "cat %s" % " ".join(['/tmp/download_part/%s' % i for i in range(self.file_seq, self.file_seq + self.file_num)])


class MultiDownloader:

    def __init__(self, urls, downloadLock=None, start_percent=0, outfile=None, alternativeUrls=[]):
        self.urls = urls
        self.chunk_size = chunk_size
        self.start_percent = start_percent
        self.file_seq = 0
        self.download_threads = download_threads
        self.catCmds = []
        self.downloaders = []
        self.currentDownloader = None
        self.stopped = False
        self.download_thread = Thread(target=self.download)
        self.outfile = outfile
        self.downloadLock = downloadLock
        self.alternativeUrls = alternativeUrls
        logging.info("chunk_size = %s, download_threads = %s", self.chunk_size, download_threads)

    def setLock(self, lock):
        self.downloadLock = lock

    def getSizeInfo(self):
        ress = BatchRequests(self.urls, replace_url=False, retry=10).get()
        for idx, res in enumerate(ress):
            url = res.url
            total_length = int(res.resp.headers["content-length"])
            logging.info(res.resp.headers)
            current_chunk_size = self.chunk_size
            if not res.range_support:
                logging.warn("Range request not supported so set process_num to 1.")
                current_chunk_size = total_length
            if idx == 0:
                downloader = Downloader(url, self.download_threads, current_chunk_size, self.start_percent,
                                        outfile=self.outfile, file_seq=self.file_seq,
                                        alternativeUrls=self.alternativeUrls, total_length=total_length)
            else:
                downloader = Downloader(url, self.download_threads, current_chunk_size,
                                        outfile=self.outfile, file_seq=self.file_seq,
                                        alternativeUrls=self.alternativeUrls, total_length=total_length)
            self.file_seq += downloader.file_num
            self.downloaders.append(downloader)
            self.catCmds.append(downloader.getCatCmd())

    def start(self):
        self.download_thread.start()

    def download(self):
        with self.downloadLock:
            for idx, downloader in enumerate(self.downloaders):
                if self.stopped:
                    break
                logging.info("Start downloading %s - %s" % (idx + 1, downloader.url))
                self.currentDownloader = downloader
                self.currentDownloader.start()
                while not self.currentDownloader.write_done:
                    time.sleep(0.1)

    def stop(self):
        self.stopped = True
        if self.currentDownloader:
            logging.info("Stopping currentDownloader")
            self.currentDownloader.stop()
            while not self.currentDownloader.write_done:
                if self.outfile:
                    self.releaseFiles([self.outfile])
                else:
                    self.releaseFiles(['/tmp/download_part/%s' % self.currentDownloader.file_seq])
                time.sleep(0.1)

    def releaseFiles(self, files):
        for f in files:
            try:
                DEVNULL = open(os.devnull, 'wb')
                p = subprocess.Popen(['cat', f], stdout=DEVNULL, stderr=DEVNULL)
                time.sleep(0.1)
                p.terminate()
            except:
                logging.exception("Got exception")
            finally:
                DEVNULL.close()
                logging.info("File %s released" % f)

    def getCatCmds(self):
        logging.info("catCmds: %s" % self.catCmds)
        return self.catCmds

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(module)s:%(lineno)d %(levelname)s: %(message)s', level=logging.DEBUG)
    downloader = MultiDownloader(['http://newflv.sohu.ccgslb.net/17/198/DUZhTZJjqW9YNoZXGgksU4.mp4?key=qIchGoS9DHw46ZS0A53Gt3192YHEbcpA'])
    downloader.start()
    time.sleep(5)
    downloader.stop()
    downloader.getCatCmds()
