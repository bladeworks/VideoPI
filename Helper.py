#!/usr/bin/python
# -*- coding: utf8 -*-

import os
import logging


def newFifo(filename):
    try:
        os.mkfifo(filename)
    except OSError:
        logging.exception("Got exception when newFifo")


def newDir(dirname):
    try:
        os.mkdir(dirname)
    except OSError:
        logging.exception("Got exception when newDir")
