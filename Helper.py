#!/usr/bin/python
# -*- coding: utf8 -*-

import os
import subprocess
import re
import logging


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
    try:
        output = subprocess.check_output(['fbset'])
        p = re.compile('mode "(?P<width>\d+)x(?P<height>\d+)"')
        global screenWidth, screenHeight
        sw, sh = p.search(output).groups()
        screenWidth = float(sw)
        screenHeight = float(sh)
    except:
        logging.exception("Exception catched")
