#!/usr/bin/python
# -*- coding: utf8 -*-

import os
from threading import Thread
from Queue import Queue
import logging
import subprocess
import re


screenWidth, screenHeight = 0, 0

def newFifo(filename):
    try:
        os.mkfifo(filename)
    except OSError:
        pass


def newDir(dirname):
    try:
        os.mkdir(dirname)
    except OSError:
        pass


def getScreenSize():
    global screenWidth, screenHeight
    if screenWidth > 0 and screenHeight > 0:
        return (screenWidth, screenHeight)
    try:
        output = subprocess.check_output(['fbset'])
        p = re.compile('mode "(?P<width>\d+)x(?P<height>\d+)"')
        sw, sh = p.search(output).groups()
        screenWidth = float(sw)
        screenHeight = float(sh)
        return (screenWidth, screenHeight)
    except:
        logging.exception("Exception catched")
    return (0, 0)


class Worker(Thread):
    """Thread executing tasks from a given tasks queue"""
    def __init__(self, tasks):
        Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.start()

    def run(self):
        while True:
            func, args, kargs = self.tasks.get()
            try:
                func(*args, **kargs)
            except Exception:
                logging.exception("Got exception")
            self.tasks.task_done()


class ThreadPool:
    """Pool of threads consuming tasks from a queue"""
    def __init__(self, num_threads):
        self.tasks = Queue(num_threads)
        for _ in range(num_threads):
            Worker(self.tasks)

    def add_task(self, func, *args, **kargs):
        """Add a task to the queue"""
        self.tasks.put((func, args, kargs))

    def wait_completion(self):
        """Wait for completion of all the tasks in the queue"""
        self.tasks.join()
