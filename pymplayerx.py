#!/usr/bin/python
# -*- coding: utf8 -*-

import subprocess
import logging


class MPlayerX:
    def __init__(self, currentVideo, screenWidth=0, screenHeight=0):
        self.currentVideo = currentVideo
        self._process = None

    def play(self):
        logging.info("Play %s", self.currentVideo.playUrl)
        self._process = subprocess.Popen(['open', '-a', '/Applications/MPlayerX.app', '--args', '-url', self.currentVideo.playUrl])

    def toggle_pause(self):
        pass

    def volup(self):
        pass

    def voldown(self):
        pass

    def stop(self):
        if self._process and self.isalive():
            self._process.terminate()

    def isalive(self):
        if self._process and self._process.poll() is None:
            return True
        return False
