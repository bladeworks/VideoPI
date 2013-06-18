#!/usr/bin/python
# -*- coding: utf8 -*-
from bottle import route, run, template, request, static_file, post, get, redirect, error, response
from database import *
from webparser import *
import subprocess
import sys
import os
import time
import urllib
import urllib2
from urlparse import urlparse
from gevent.queue import Queue
from Constants import *
from pyomxplayer import OMXPlayer
from show_image import *
from downloader import *
from config import *
from Helper import *
try:
    from userPrefs import *
except:
    logging.info("No userPrefs.py found so skip user configuration.")
import bottle

from gevent import monkey
monkey.patch_all()
import gevent

bottle.debug = True

current_website = None
currentVideo = None
currentPlayerApp = None

player = None
playThread = None
playQueue = Queue()
imgService = ImgService()
sreenWidth = 0
sreenHeight = 0

import logging
logging.basicConfig(format='%(asctime)s %(threadName)s %(module)s:%(lineno)d %(levelname)s: %(message)s',
                    filename=logStorage, level=logging.DEBUG)


def exceptionLogger(type, value, tb):
    logging.exception("Uncaught exception: %s", value)
    sys.__excepthook__(type, value, tb)


sys.excephook = exceptionLogger


def clearQueue():
    global playQueue
    logging.info("Clear the queue.")
    with playQueue.mutex:
        playQueue.queue.clear()


def parseM3U():
    with open(playlistStorage, 'r') as f:
        return [v.strip() for v in f.readlines() if v.startswith('http')]


def fillQueue(urls=[]):
    global playQueue
    logging.info("fillQueue: %s", urls)
    if urls:
        logging.info("Add item to queue %s", urls)
        for u in urls:
            playQueue.put(u)
    else:
        for v in parseM3U():
            playQueue.put(v)
    # fill other related videos
    if currentVideo and currentVideo.nextVideo:
        logging.debug("Put next: %s", urllib2.unquote(currentVideo.nextVideo))
        playQueue.put("next:%s" % urllib2.unquote(currentVideo.nextVideo))


def startPlayer(url):
    logging.info("Start player for %s", url)
    global player, current_website, currentVideo, screenWidth, screenHeight
    currentVideo.playUrl = url
    player = OMXPlayer(currentVideo, screenWidth, screenHeight)


def play_list():
    global player, playQueue, currentVideo
    while True:
        v = playQueue.get()
        logging.info("Get item from playQueue: %s", v)
        if v.startswith('next:'):
            logging.info("Now play the next: %s", v)
            parse_url(v.replace('next:', ''), redirectToHome=False)
            continue
        else:
            startPlayer(v.strip())
        imgService.begin(LOADING)
        time.sleep(2)
        while True:
            if player and player.isalive():
                time.sleep(1)
                try:
                    if currentVideo:
                        position = int(player.position / 1000000)
                        # logging.debug("Get position = %s", position)
                        if position > 0 and imgService.stop is False:
                            imgService.end()
                        new_progress = int(currentVideo.start_pos) + position
                        if currentVideo.progress != new_progress:
                            currentVideo.progress = new_progress
                            if new_progress % 30 == 0 and new_progress > 0:
                                db_writeHistory(currentVideo)
                except:
                    logging.exception("Got exception")
            else:
                logging.info("Break")
                if currentVideo.downloader:
                    currentVideo.downloader.stop()
                imgService.end()
                if playQueue.empty():
                    imgService.begin(FINISHED)
                break


def terminatePlayer():
    global player
    if player and player.isalive():
        logging.warn("Terminate the previous player")
        player.stop()
        player = None


def new_play_thread():
    global playThread
    if not playThread or (not playThread.isAlive()):
        logging.debug("New a thred to play the list.")
        job = gevent.spawn(play_list)
        job.run()


def getWgetCmd(url, output="-"):
    return wrapRetry('wget -o /tmp/download.log -UMozilla/5.0 -O %s "%s"'
                     % (output, url))


def getAxelCmd(url, output):
    return "rm -f %s && %s " % (output, wrapRetry('axel -n %s -o %s "%s" &>/tmp/download.log'
           % (download_threads, output, url)))


def wrapRetry(cmd, max_retry=20):
    return ("retry=1; while [ $retry -le %s ]; do if %s; then break; fi; sleep 1; "
            "retry=$(( $retry + 1 )); if [ $retry - eq %s ]; then exit 1; fi; done") \
        % (max_retry, cmd, max_retry)


def getFfmpegCmd(ss, inputFile, outputFile):
    if ss > 0:
        return 'nice -n 19 ffmpeg -ss %s -i "%s" -c copy -bsf:v h264_mp4toannexb -y -f mpegts %s 2>%s.log' \
               % (ss, inputFile, outputFile, outputFile)
    else:
        return 'nice -n 19 ffmpeg -i "%s" -c copy -bsf:v h264_mp4toannexb -y -f mpegts %s 2>%s.log' \
               % (inputFile, outputFile, outputFile)


def merge_play(sections, where=0, start_idx=0, delta=0):
    global currentVideo
    clearQueue()
    logging.info("Merge and play: where = %s, start_idx = %s, delta = %s", where, start_idx, delta)
    if download_to_local:
        currentVideo.playUrl = download_file
    else:
        currentVideo.playUrl = "/tmp/all.ts"
        newFifo(currentVideo.playUrl)
    download_args = ""
    download_lines = []
    p_list = []
    dp = download_program
    ffmpeg_input = ""
    if len(sections[start_idx:]) == 1 and delta == 0:
        dp = "private"
    if dp == "private":
        if len(sections[start_idx:]) == 1 and delta == 0:
            multiDownloader = MultiDownloader(sections[start_idx:], alternativeUrls=currentVideo.alternativeUrls)
            currentVideo.downloader = multiDownloader
            if multiDownloader.outfile != currentVideo.playUrl:
                download_args += '%s > %s 2>/tmp/cat.log' % (multiDownloader.getCatCmds()[0], currentVideo.playUrl)
        else:
            multiDownloader = MultiDownloader(sections[start_idx:], alternativeUrls=currentVideo.alternativeUrls)
            catCmds = multiDownloader.getCatCmds()
            ffmpeg_part = "/tmp/ffmpeg_part"
            currentVideo.downloader = multiDownloader
            p_list = []
            for idx, catCmd in enumerate(catCmds):
                pname = os.path.join(ffmpeg_part, str(idx))
                newFifo(pname)
                download_lines.append("{\n%s | %s\n}" % (catCmd, getFfmpegCmd(0, "-", pname)))
                p_list.append(pname)
            ffmpeg_input = " ".join(p_list)
            download_args += 'cat %s | ffmpeg -f mpegts -i - -ss %s -c copy -y -f mpegts %s 2> /tmp/merge.log &\n' \
                             % (ffmpeg_input, delta, currentVideo.playUrl)
            download_args += " && ".join(download_lines)
    else:
        if len(sections[start_idx:]) == 1:
            dp = "wget"
        logging.info("dp = %s", dp)
        for idx, v in enumerate(sections[start_idx:]):
            pname = "/tmp/p%s" % idx
            fname = "/tmp/f%s" % dp
            newFifo(pname)
            p_list.append(pname)
            if idx == 0:
                if dp == 'axel':
                    download_lines.append("{\n%s && %s\n}" % (getAxelCmd(v, fname), getFfmpegCmd(delta, fname, pname)))
                    continue
                download_lines.append("{\n%s\n}" % getFfmpegCmd(delta, v, pname))
                continue
            if dp == 'wget':
                download_lines.append("{\n%s | %s\n}" % (getWgetCmd(v), getFfmpegCmd(0, "-", pname)))
            elif dp == 'axel':
                download_lines.append("{\n%s && %s\n}" % (getAxelCmd(v, fname), getFfmpegCmd(0, fname, pname)))
            else:
                download_lines.append("{\n%s\n}" % getFfmpegCmd(0, v, pname))
        ffmpeg_input = " ".join(p_list)
        download_args += 'cat %s | ffmpeg -f mpegts -i - -c copy -y -f mpegts %s 2> /tmp/merge.log &\n' \
                         % (ffmpeg_input, currentVideo.playUrl)
        download_args += " && ".join(download_lines)
    currentVideo.download_args = download_args
    fillQueue(urls=[currentVideo.playUrl])
    new_play_thread()


def getSections():
    if currentVideo.realUrl == playlistStorage:
        return parseM3U()
    else:
        return [currentVideo.realUrl]


def play_url(redirectToHome=True):
    global player, currentVideo, currentPlayerApp, playQueue, progress
    clearQueue()
    terminatePlayer()
    db_writeHistory(currentVideo)
    logging.info("Playing %s", currentVideo.realUrl)
    # logging.debug("currentVideo = %s", currentVideo)
    new_play_thread()
    if currentVideo.realUrl == playlistStorage:
        # Because omxplayer doesn't support list we have to play one by one.
        sections = getSections()
        func = fillQueue
        args = []
        if 'merge' in websites[current_website] and websites[current_website]['merge']:
            func = merge_play
            args = sections
        logging.debug("currentVideo.progress = %s", currentVideo.progress)
        if currentVideo.progress > advanceTime:
            result = goto(currentVideo.progress - advanceTime, 0)
            if result != 'OK':
                func(args)
        else:
            func(args)
    else:
        fillQueue([currentVideo.realUrl])
    if redirectToHome:
        while not (player and player.isalive()):
            time.sleep(1)
        redirect('/')


def parse_url(url, format=None, dbid=None, redirectToHome=True):
    logging.debug("parse_url %s, format = %s, dbid = %s", url, format, dbid)
    imgService.begin(LOADING)
    global currentVideo
    if currentVideo and currentVideo.allRelatedVideo:
        relatedUrls = [v['url'] for v in currentVideo.allRelatedVideo]
        if (currentVideo.realUrl in relatedUrls) and (url in relatedUrls):
            idx = relatedUrls.index(url)
            # Don't parse the file
            allRelatedVideo = []
            for v in currentVideo.allRelatedVideo:
                v['current'] = False
                if v['url'] == url:
                    v['current'] = True
                allRelatedVideo.append(v)
            previousVideo, nextVideo = None, None
            if idx > 0:
                previousVideo = allRelatedVideo[idx - 1]['url']
            if idx < (len(allRelatedVideo) - 1):
                nextVideo = allRelatedVideo[idx + 1]['url']
            newCurrentVideo = Video(currentVideo.allRelatedVideo[idx]['title'], currentVideo.url, url, 0, current_website,
                                    availableFormat=currentVideo.availableFormat, currentFormat=format,
                                    allRelatedVideo=allRelatedVideo, previousVideo=previousVideo,
                                    nextVideo=nextVideo)
            logging.debug("newCurrentVideo = %s", newCurrentVideo)
            currentVideo = newCurrentVideo
            if dbid:
                currentVideo.dbid = dbid
            logging.debug("currentVideo = %s", currentVideo)
            return play_url(redirectToHome)
    parser = websites[current_website]['parser'](url, format)
    parseResult = parser.parse()
    if isinstance(parseResult, Video):
        terminatePlayer()
        currentVideo = parseResult
        logging.info('currentVideo = %s', str(currentVideo))
        if dbid:
            currentVideo.dbid = dbid
            currentVideo.progress = db_getById(int(dbid)).progress
        return play_url(redirectToHome)
    else:
        logging.info('No video found, return the web page.')
        imgService.end()
        return parseResult


@route('/')
def index():
    if not (player and player.isalive()):
        return template("index", websites=websites, currentVideo=None, actionDesc=actionDesc,
                        history=db_getHistory())
    return template("index", websites=websites, currentVideo=currentVideo, actionDesc=actionDesc,
                    history=db_getHistory())


@route('/play')
def history_play():
    global currentVideo
    currentVideo = db_getById(request.query.id)
    start = int(request.query.start)
    if start >= 0:
        logging.info("Start from %s." % start)
        currentVideo.progress = start
        db_writeHistory(currentVideo)
    redirect('/forward?site=%s&url=%s&dbid=%s' % (currentVideo.site, currentVideo.url,
             currentVideo.dbid))


@route('/static/<filename:path>')
def static(filename):
    return static_file(filename, root='static')


@post('/control/<action>')
def control(action):
    global player, currentVideo
    feedback = ""
    if action == "stop":
        clearQueue()
    if player and player.isalive():
        feedback = "OK"
        if action == "stop":
            if currentVideo.progress > 0:
                logging.debug("Write last_play_pos to %s", currentVideo.progress)
                db_writeHistory(currentVideo)
            terminatePlayer()
            player = None
            currentVideo = None
        elif action == "pause":
            player.toggle_pause()
        elif action == "volup":
            player.volup()
        elif action == "voldown":
            player.voldown()
        else:
            feedback = "Not implemented action: " + action
    else:
        feedback = "Sorry but I can't find any player running."
    return feedback


@get('/history')
def history():
    videos = db_getHistory()
    responseString = ""
    for video in videos:
        responseString += """
                        <li>
                            <a href="/play?id=%s" class="ui-link-inherit" data-ajax="false">
                                <h3>%s(%s)</h3>
                                <p>总共%s(上次播放到%s)</p>
                            </a>
                            <a href="#" onclick="deleteHistory('%s');return false" class="split-button-custom" data-role="button" data-icon="delete" data-iconpos="notext"></a>
                            <a href="/play?id=%s&start=0" class="split-button-custom" data-role="button" data-icon="refresh" data-iconpos="notext" data-ajax="false"></a>
                            <a href="#" style="display: none;">Dummy</a>
                        </li>
                        """ % (video.dbid, video.title, websites[video.site]['title'],
                               video.durationToStr(), Video.formatDuration(video.progress), video.dbid, video.dbid)
    return responseString


@post('/delete/<id>')
def delete(id):
    db_delete(id)


@post('/clear')
def clear():
    db_delete(-1)


@get('/favicon.ico')
def favicon():
    return static_file('favicon.ico', '.')


@get('/progress')
def get_progress():
    if currentVideo and player and player.isalive():
        return {"title": currentVideo.title, "progress": str(currentVideo.progress), "duration": currentVideo.durationToStr()}
    else:
        return {"title": "N/A", "progress": "0", "duration": "N/A"}


@post('/goto/<where>')
def goto(where, fromPos=-1):
    logging.info("Goto %s", where)
    new_progress, c_idx = currentVideo.getSectionsFrom(int(where))
    logging.debug("new_progress = %s, c_idx = %s", new_progress, c_idx)
    currentIdx = 0
    if fromPos == -1:
        currentIdx = currentVideo.getCurrentIdx()
        logging.debug("currentIdx = %s", currentIdx)
    sections = getSections()
    if new_progress is not None and c_idx is not None:
        if 'merge' in websites[current_website] and websites[current_website]['merge']:
            clearQueue()
            terminatePlayer()
            currentVideo.start_pos = where
            currentVideo.progress = where
            merge_play(sections, where=where, start_idx=c_idx, delta=int(int(where) - int(new_progress)))
            db_writeHistory(currentVideo)
            return 'OK'
        else:
            if c_idx != currentIdx:
                clearQueue()
                terminatePlayer()
                currentVideo.start_pos = new_progress
                currentVideo.progress = new_progress
                fillQueue(sections[c_idx:])
                return "OK"


@route('/forward')
def forward():
    global vid, title, current_website, currentVideo
    format = None
    if 'site' in request.query:
        current_website = request.query.site
    if 'format' in request.query:
        format = int(request.query.format)
    dbid = None
    if 'dbid' in request.query:
        dbid = request.query.dbid
    url = request.query.url
    logging.info("Forwarding to %s", url)
    if current_website and url.startswith('/'):
        url = websites[current_website]['url'] + url
    logging.debug("forward to url: %s", url)
    if current_website == 'youtube' and 'search_query' in request.query:
        url = "%s?%s" % ('http://www.youtube.com/results', request.query_string)
        logging.debug("The url for youtube search is: %s", url)
    if current_website == 'youku' and 'searchdomain' in request.query:
        url = "http://www.soku.com/search_video/q_" + urllib.quote_plus(request.query.q.encode('utf8'))
        logging.debug("The url for youku search is: %s", url)
    if current_website in ('qq', 'qqmp4') and 'ms_key' in request.query:
        url = "http://v.qq.com/search.html"
        logging.debug("The url for youku search is: %s", url)
    if current_website == 'wangyi' and 'vs' in request.query and not url:
        url = "http://so.open.163.com/movie/search/searchprogram/ot0/%s/1.html?vs=%s&pltype=2" \
            % (request.query.vs, request.query.vs)
        logging.debug("The url for wangyi search is: %s", url)
    if current_website == 'sohu' and 'wd' in request.query and not url:
        url = "http://so.tv.sohu.com/mts?box=1&wd=%s" % (request.query.wd)
        logging.debug("The url for sohu search is: %s", url)
    return parse_url(url, format, dbid)


@get('/shutdown')
def shutdown():
    subprocess.call(['sync'])
    subprocess.Popen('sleep 2; poweroff', shell=True)


@get('/restart')
def restart():
    subprocess.call(['sync'])
    subprocess.Popen('sleep 2; reboot', shell=True)


@error(404)
def error404(error):
    logging.debug("404 on url: %s", request.url)
    if request.url == "http://192.168.1.100/jsonrpc":
        return
    p_results = urlparse(request.url)
    to_replace = p_results.scheme + "://" + p_results.netloc
    if request.url.endswith('.css'):
        redirectTo = request.url.replace(to_replace, websites[current_website]['url'])
    else:
        redirectTo = "%s?site=%s&url=%s" % ('/forward', current_website,
                                            urllib2.quote(request.url.replace(to_replace,
                                            websites[current_website]['url'])))
    if current_website == 'youku' and request.url.startswith("/search_video"):
        redirectTo = "%s?site=%s&url=%s" % ('/forward', current_website,
                                            urllib2.quote(request.url.replace(to_replace,
                                            "http://www.soku.com")))
    logging.debug("Redirect to %s", redirectTo)
    response.set_header('location', redirectTo)
    response.status = 303


@error(500)
def error500(error):
    return ("Exception: %s\nDetails: %s" % (error.exception, error.traceback)).replace('\n', '<br>')


newFifo('/tmp/omxpipe')
newFifo('/tmp/cmd')
newDir('/tmp/ffmpeg_part')
newDir('/tmp/download_part')
for i in range(1000):
    newFifo('/tmp/download_part/%s' % i)


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

getScreenSize()
try:
    run(host='0.0.0.0', port=80, quiet=True)
except:
    logging.exception("Exception catched")
