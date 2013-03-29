#!/usr/bin/python
# -*- coding: utf8 -*-

from threading import Thread
import time
import subprocess
import logging

LOADING = "loading"
FINISHED = "finished"


class ImgService:

    def __init__(self):
        self.stop = False
        self.delay = 0
        self.repeat = False
        self.filenames = []
        self.what = None

    def begin(self, what):
        self.what = what
        logging.debug("Begin %s", self.what)
        try:
            self._clear()
            self.stop = False
            if self.what == LOADING:
                self.delay = 2
                self.repeat = True
                self.filenames = ["static/img/loading/frame%s.png" % (i + 1) for i in range(12)]
                self.show_image()
            elif self.what == FINISHED:
                self.delay = 0
                self.repeat = False
                self.filenames = ["static/img/finished.jpg"]
                self.show_image()
        except:
            logging.exception("Exception catched")

    def show_image(self):
        if self.repeat:
            thread = Thread(target=self._show_thread)
            thread.start()
        else:
            self._show_image()

    def _show_thread(self):
        while not self.stop:
            self._show_image()

    def _show_image(self):
        for filename in self.filenames:
            if self.stop:
                break
            cmd = "/usr/bin/fbv -i -s %s %s" % (self.delay, filename)
            subprocess.call(cmd, shell=True)
            time.sleep(0.1)

    def _clear(self):
        subprocess.call(["/usr/bin/dd", "if=/dev/zero", "of=/dev/fb0"])

    def end(self):
        logging.debug("End %s", self.what)
        if self.what and self.stop is False:
            self.stop = True
            time.sleep(0.2)
            self._clear()


if __name__ == '__main__':
    service = ImgService()
    service.begin(LOADING)
    time.sleep(5)
    service.end()
    service.begin(FINISHED)
