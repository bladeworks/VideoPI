#!/usr/bin/python
# -*- coding: utf8 -*-

from pyomxplayer import OMXPlayer
from pymplayerx import MPlayerX
from Queue import Queue
from threading import Thread, RLock
from Helper import getScreenSize, newFifo
from Constants import websites
from webparser import Video
from database import db_writeHistory, db_getById
from downloader import MultiDownloader
from show_image import ImgService, FINISHED, LOADING
from config import get_cfg
import logging
import sys
import os
import time

downloadLock = RLock()
playLock = RLock()

imgService = ImgService()
playlistStorage = get_cfg('playlistStorage')


class Player:
    def __init__(self, video):
        self.video = video
        screenWidth, screenHeight = getScreenSize()
        if sys.platform == 'darwin':
            self.player = MPlayerX(self.video, screenWidth, screenHeight)
        else:
            self.player = OMXPlayer(self.video, screenWidth, screenHeight)
        self.from_position = video.progress

    def getUrls(self):
        if self.video.realUrl == playlistStorage:
            with open(playlistStorage, 'r') as f:
                urls = [v.strip() for v in f.readlines() if v.startswith('http')]
        else:
            urls = [self.video.realUrl]
        delta = 0
        if int(self.video.progress) > 30:
            if len(self.video.sections) <= 1:
                urls = urls
                delta = int(self.video.progress)
            else:
                new_progress, c_idx = self.video.getSectionsFrom(self.video.progress)
                urls = urls[c_idx:]
                delta = int(self.video.progress - new_progress)
        logging.info("urls = %s, delta = %s", urls, delta)
        return (urls, delta)

    def getFfmpegCmd(self, ss, inputFile, outputFile):
        if ss > 30:
            return 'nice -n 19 ffmpeg -ss %s -i "%s" -ss %s -c copy -bsf:v h264_mp4toannexb -y -f mpegts %s 2>%s.log' \
                   % (ss - 30, inputFile, 30, outputFile, outputFile)
        else:
            return 'nice -n 19 ffmpeg -i "%s" -c copy -bsf:v h264_mp4toannexb -y -f mpegts %s 2>%s.log' \
                   % (inputFile, outputFile, outputFile)

    def init(self):
        # Check the progress and decide the download cmd
        self.video.playUrl = "/tmp/all.ts"
        if len(self.video.sections) <= 1:
            # Unsplitted file
            if self.video.progress <= 30:
                urls, delta = self.getUrls()
                self.video.downloader = MultiDownloader(urls, alternativeUrls=self.video.alternativeUrls)
                self.video.downloader.getSizeInfo()
                self.video.download_args = '%s > %s 2>/tmp/cat.log' % (self.video.downloader.getCatCmds()[0], self.video.playUrl)
            else:
                self.video.downloader = None
                self.video.download_args = self.getFfmpegCmd(self.video.progress, self.getUrls()[0][0], self.video.playUrl)
        else:
            # Splitted file
            urls, delta = self.getUrls()
            self.video.downloader = MultiDownloader(urls, alternativeUrls=self.video.alternativeUrls)
            self.video.downloader.getSizeInfo()
            catCmds = self.video.downloader.getCatCmds()
            ffmpeg_part = "/tmp/ffmpeg_part"
            p_list = []
            download_lines = []
            for idx, catCmd in enumerate(catCmds):
                pname = os.path.join(ffmpeg_part, str(idx))
                newFifo(pname)
                if idx == 0 and delta > 30:
                    download_lines.append("{\n%s | %s\n}" % (catCmd, self.getFfmpegCmd(delta, "-", pname)))
                else:
                    download_lines.append("{\n%s | %s\n}" % (catCmd, self.getFfmpegCmd(0, "-", pname)))
                p_list.append(pname)
            ffmpeg_input = " ".join(p_list)
            download_args = 'cat %s | ffmpeg -f mpegts -i - -c copy -y -f mpegts %s 2> /tmp/merge.log &\n' \
                             % (ffmpeg_input, self.video.playUrl)
            download_args += " && ".join(download_lines)
            self.video.download_args = download_args

    def download(self, lock):
        if self.video.downloader:
            self.video.downloader.setLock(lock)
            self.video.downloader.start()

    def play(self, lock):
        # New a thread to play
        self.playThread = Thread(target=self.play_thread, args=(lock,))
        self.playThread.daemon = True
        self.playThread.start()

    def play_thread(self, lock):
        with lock:
            logging.info("Got lock and play now")
            self.player.play()
            while self.player.isalive():
                time.sleep(1)
                self.video.progress = self.from_position + self.getPosition()
                if not imgService.stop and self.video.progress > 0:
                    imgService.end()
                if self.video.progress % 10 == 0:
                    db_writeHistory(self.video)
            if imgService.stop:
                imgService.begin(FINISHED)

    def stop(self):
        logging.info("Stop downloader")
        if self.video.downloader:
            self.video.downloader.stop()
        logging.info("Stop player")
        self.player.stop()

    def getPosition(self):
        return int(self.player.position / 1000000)

    def isAlive(self):
        return self.player.isalive()

    def toggle_pause(self):
        self.player.toggle_pause()

    def volup(self):
        self.player.volup()

    def voldown(self):
        self.player.voldown()


class Controller:
    def __init__(self, site):
        self.site = site
        self.startPlayThread()
        self.currentPlayer = None
        self.nextPlayer = None
        if self.site:
            self.Parser = websites[self.site]['parser']
        self.stopped = False

    def startPlayThread(self):
        logging.info("Start play thread")
        self.playQueue = Queue()
        self.playThread = Thread(target=self.play)
        self.playThread.daemon = True
        self.playThread.start()

    def parseHistory(self, dbid, start, format=None):
        video = db_getById(dbid)
        self.site = video.site
        self.Parser = websites[self.site]['parser']
        progress = video.progress
        if int(start) >= 0:
            progress = int(start)
        self.parse(video.url, dbid=dbid, progress=progress, format=format)

    def parse(self, url, format=None, dbid=None, progress=0):
        with imgService.show(LOADING):
            parseResult = self.Parser(url, format).parse()
            if isinstance(parseResult, Video):
                if dbid:
                    parseResult.dbid = dbid
                if progress:
                    parseResult.progress = int(progress)
                self.add(parseResult)
            else:
                if parseResult:
                    return parseResult
                else:
                    return "Error happened, please refresh the page."

    def add(self, video):
        self.playQueue.put(Player(video))

    def play(self):
        while True:
            self.nextPlayer = self.playQueue.get()
            # A None object indicate that the thread should be stopped
            if not self.nextPlayer:
                break
            imgService.begin(LOADING)
            self.nextPlayer.init()
            logging.info("### Prepare %s", self.nextPlayer.video.title)
            logging.info("Let's download!")
            with downloadLock:
                if self.stopped:
                    break
                self.nextPlayer.download(downloadLock)
            logging.info("Let's play!")
            with playLock:
                if self.stopped:
                    break
                logging.info("### Play %s", self.nextPlayer.video.title)
                self.currentPlayer = self.nextPlayer
                self.nextPlayer = None
                self.currentPlayer.play(playLock)
                db_writeHistory(self.currentPlayer.video)
            if self.currentPlayer.video.nextVideo:
                logging.info("### Parse nextVideo")
                self.parse(self.currentPlayer.video.nextVideo, self.currentPlayer.video.currentFormat)
            else:
                self.playQueue.put(None)
        logging.info("End the play thread")

    def goto(self, where):
        video = self.currentPlayer.video
        video.progress = int(where)
        self.stopAll()
        while self.playThread.isAlive():
            time.sleep(0.1)
        self.stopped = False
        self.startPlayThread()
        self.add(video)

    def stopCurrentPlayer(self):
        logging.info("Stop current player")
        if self.currentPlayer:
            self.currentPlayer.stop()

    def stopAll(self):
        logging.info("Stop all")
        self.stopped = True
        with self.playQueue.mutex:
            logging.info("Clear")
            self.playQueue.queue.clear()
        logging.info("Put None")
        self.playQueue.put(None)
        if self.nextPlayer:
            logging.info("Stop nextPlayer")
            self.nextPlayer.stop()
        self.stopCurrentPlayer()
