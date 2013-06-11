#!/usr/bin/python
# -*- coding: utf8 -*-

import os


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
