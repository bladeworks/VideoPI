#!/usr/bin/python
# -*- coding: utf8 -*-

import requests
import logging
import time
import signal
from threading import Thread
from Queue import Queue
from contextlib import contextmanager
from NetworkHelper import BatchRequests
from Helper import ThreadPool
from config import process_num as process_num_config, chunk_size as chunk_size_config, download_timeout
try:
    from userPrefs import process_num as process_num_config, chunk_size as chunk_size_config, download_timeout
except:
    logging.info("No userPrefs.py found so skip user configuration.")


@contextmanager
def runWithTimeout(timeout=1):
    def handler(signum, frame):
        raise IOError("Time out")
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(timeout)
    try:
        yield
    finally:
        signal.alarm(0)


class Downloader:

    def __init__(self, url, process_num=5, chunk_size=1000000, step_size=5, start_percent=0,
                 outfile=None, file_seq=0, alternativeUrls=[], total_length=None):
        self.url = url
        self.total_length = total_length
        logging.info("Construct downloader for url %s", self.url)
        self.process_num = process_num
        self.chunk_size = chunk_size
        self.step_size = step_size
        self.outfile = outfile
        self.alternativeUrls = alternativeUrls
        self.result_queue = Queue()
        self.step_done = False
        self.current_step_size = 0
        self.stopped = False
        self.write_done = False
        self.file_seq = file_seq
        self.start_percent = start_percent
        self.start_byte = 0
        self.getSizeInfo()
        self.result_thread = Thread(target=self.handleResult)
        self.download_thread = Thread(target=self.download)
        self.start_time = 0
        self.write_queue = Queue(1)
        self.write_thread = Thread(target=self.writeFile)

    def download_part(self, part_num, session):
        # Content-Range: bytes 0-499/1234
        # Content-Range: bytes 500-999/1234
        start = self.start_byte + part_num * self.chunk_size
        end = self.start_byte + (part_num + 1) * self.chunk_size - 1
        if end > self.total_length:
            end = self.total_length
        logging.debug("Begin download part %s", part_num)
        headers = {'Range': 'bytes=%s-%s' % (start, end), 'User-Agent': 'Mozilla/5.0'}
        retries = 20
        for i in range(retries):
            if self.stopped:
                self.result_queue.put({part_num: ""})
                return
            try:
                url = self.url
                if self.alternativeUrls:
                    url = self.alternativeUrls[(part_num + retries) % (len(self.alternativeUrls))]
                resp = session.get(url, headers=headers, allow_redirects=True, timeout=2, stream=True)
                if 200 <= resp.status_code < 300:
                    it = resp.iter_content(10000)
                    content = ""
                    chun_start_time = time.time()
                    last_time_get_data = time.time()
                    while True:
                        if (time.time() - chun_start_time) > download_timeout:
                            if len(self.alternativeUrls) > 1:
                                logging.info("Remove %s as it has been timeout" % url)
                                self.alternativeUrls.remove(url)
                            it.close()
                            raise Exception("Timeout while downloading %s" % part_num)
                        if self.stopped:
                            self.result_queue.put({part_num: ""})
                            it.close()
                            return
                        try:
                            next = it.next()
                            if last_time_get_data and (time.time() - last_time_get_data) > 2:
                                it.close()
                                raise Exception("Didn't get data more than 2 seconds")
                            last_time_get_data = time.time()
                        except StopIteration:
                            break
                        if next:
                            content += next
                    self.result_queue.put({part_num: content})
                    break
                else:
                    logging.info("The status_code is %s, retry %s", resp.status_code, (i + 1))
            except Exception:
                # if not isinstance(err.reason, socket.timeout):
                #     raise err
                # else:
                logging.exception("")
                logging.info("Retry %s", i + 1)
        else:
            self.stopped = True
            raise Exception("Failed to download part %s" % part_num)
        logging.debug("Completed download part %s", part_num)

    def handleResult(self):
        result = {}
        while not self.stopped:
            r = self.result_queue.get()
            if self.stopped:
                self.write_queue.put("")
                result = None
                return
            result.update(r)
            if len(result) == self.current_step_size:
                logging.info("Finished step with size %s", self.current_step_size)
                end_time = time.time()
                filesize = 0
                for v in result.itervalues():
                    filesize += len(v)
                assert filesize > (self.current_step_size - 1) * self.chunk_size
                logging.debug("The avg speed is %s", self.computeSpeed(filesize, (end_time - self.start_time)))
                self.write_queue.put(''.join([result[v] for v in sorted(result)]))
                result.clear()
                self.step_done = True

    def writeFile(self):
        while True:
            result = self.write_queue.get()
            logging.info("Get %s", len(result))
            if result:
                if self.outfile:
                    filename = self.outfile
                else:
                    filename = "/tmp/download_part/%s" % self.file_seq
                logging.debug("Begin write file %s", filename)
                try:
                    with open(filename, 'a+b') as f:
                        f.write(result)
                except:
                    logging.exception("Got exception")
                result = None
                logging.debug("End write file %s" % filename)
                self.file_seq += 1
            if self.stopped and self.write_queue.empty():
                logging.info("Write stopped")
                self.write_done = True
                result = None
                break

    def computeSpeed(self, filesize, duration):
        speed = filesize / duration
        if speed > 1024 * 1024:
            return "%s MB/s" % (speed / (1024 * 1024))
        elif speed > 1024:
            return "%s KB/s" % (speed / 1024)
        else:
            return "%s B/s" % speed

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
            # if resp.history:
            #     newUrl = resp.history[-1].headers['location']
            #     self.url = newUrl
            #     logging.warn("Use the new url %s", newUrl)
        new_length = self.total_length * (1 - self.start_percent)
        self.start_byte = self.total_length - new_length
        self.total_length = new_length
        self.total_part = int(self.total_length / self.chunk_size)
        if self.total_length % self.chunk_size > 0:
            self.total_part += 1
        self.file_num = int(self.total_part / self.step_size)
        if self.total_part % self.step_size > 0:
            self.file_num += 1
        logging.info("total_length = %s", self.total_length)

    def start(self):
        self.result_thread.start()
        self.download_thread.start()
        self.write_thread.start()

    def download(self):
        self.pool = ThreadPool(self.process_num)
        try:
            session = requests.Session()
            for start in range(0, self.total_part, self.step_size):
                if self.stopped:
                    break
                self.step_done = False
                self.start_time = time.time()
                end = start + self.step_size
                if end > self.total_part:
                    end = self.total_part
                self.current_step_size = end - start
                for i in range(start, end):
                    self.pool.add_task(self.download_part, i, session)
                while True:
                    if self.step_done or self.stopped:
                        break
                    else:
                        time.sleep(0.1)
            # logging.debug("Finished part %s-%s", p, p + self.step_size)
            # logging.info("The avg speed is %s" self.computeSpeed(self.chunk_size * self.step_size, end_time - start_time))
            self.pool.wait_completion()
            self.stopped = True
            while (not self.write_done):
                time.sleep(0.1)
            logging.info("Finished download")
        finally:
            session.close()

    def stop(self):
        self.stopped = True

    def getCatCmd(self):
        logging.info("Total file_num = %s", self.file_num)
        return "cat %s" % " ".join(['/tmp/download_part/%s' % i for i in range(self.file_seq, self.file_seq + self.file_num)])


class MultiDownloader:

    def __init__(self, urls, start_percent=0, outfile=None, alternativeUrls=[]):
        self.urls = urls
        self.process_num = process_num_config
        self.chunk_size = chunk_size_config
        self.step_size = process_num_config
        self.catCmds = []
        self.downloaders = []
        self.currentDownloader = None
        self.stopped = False
        self.download_thread = Thread(target=self.download)
        self.outfile = outfile
        file_seq = 0
        logging.info("process_num = %s, chunk_size = %s, step_size = %s", self.process_num, self.chunk_size, self.step_size)
        ress = BatchRequests(self.urls, replace_url=False, retry=10).get()
        for idx, res in enumerate(ress):
            url = res.url
            total_length = int(res.resp.headers["content-length"])
            logging.info(res.resp.headers)
            process_num = self.process_num
            chunk_size = self.chunk_size
            step_size = self.step_size
            if not res.range_support:
                logging.warn("Range request not supported so set process_num to 1.")
                process_num = 1
                chunk_size = total_length
                step_size = 1
            if idx == 0:
                downloader = Downloader(url, process_num, chunk_size, step_size, start_percent,
                                        outfile=self.outfile, file_seq=file_seq,
                                        alternativeUrls=alternativeUrls, total_length=total_length)
            else:
                downloader = Downloader(url, process_num, chunk_size, step_size,
                                        outfile=self.outfile, file_seq=file_seq,
                                        alternativeUrls=alternativeUrls, total_length=total_length)
            file_seq += downloader.file_num
            self.downloaders.append(downloader)
            self.catCmds.append(downloader.getCatCmd())

    def getSizeInfo(self):
        pass

    def start(self):
        self.download_thread.start()

    def download(self):
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
        def readFile():
            for f in files:
                try:
                    with open(f) as f1:
                        f1.read()
                except:
                    pass
                finally:
                    logging.info("File %s released" % f)
        with runWithTimeout(1):
            readFile()

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
