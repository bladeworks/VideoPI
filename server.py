#!/usr/bin/python
# -*- coding: utf8 -*-
from bottle import route, run, template, request, static_file, post, get, redirect, error, response
from database import *
from webparser import *
from string import Template
import subprocess
import platform
import sys
import os
import time
import urllib
from urlparse import urlparse
from threading import Thread
from Queue import Queue

websites = {
    "qq": {
        "title": "腾讯视频(flv)",
        "url": "http://v.qq.com",
        "parser": QQWebParser,
        "icon": "http://v.qq.com/favicon.ico",
        "info": "flv格式，不分段，但不能选择清晰度。"
    },
    "qqmp4": {
        "title": "腾讯视频(mp4)",
        "url": "http://v.qq.com",
        "parser": QQWebParserMP4,
        "icon": "http://v.qq.com/favicon.ico",
        "info": "mp4格式，分段，可选择清晰度。"
    },
    "youku": {
        "title": "优酷视频",
        "url": "http://www.youku.com",
        "parser": YoukuWebParser,
        "icon": "http://www.youku.com/favicon.ico",
        "info": "mp4格式，分段，可选择清晰度。"
    },
    "wangyi": {
        "title": "网易公开课",
        "url": "http://open.163.com",
        "parser": WangyiWebParser,
        "icon": "http://open.163.com/favicon.ico",
        "info": "Nothing"
    },
    "yinyuetai": {
        "title": "音悦台",
        "url": "http://www.yinyuetai.com",
        "parser": YinyuetaiWebParser,
        "icon": "http://s.yytcdn.com/favicon.ico",
        "info": "Nothing"
    },
    "kankan": {
        "title": "迅雷看看",
        "url": "http://www.kankan.com",
        "parser": KankanWebParser,
        "icon": "http://www.kankan.com/favicon.ico",
        "info": "Nothing",
        "externaldownload": True
    },
    "youtube": {
        "title": "Youtube",
        "url": "http://www.youtube.com",
        "parser": YoutubeWebParser,
        "icon": "http://www.youtube.com/favicon.ico",
        "info": "Nothing"
    },
}

current_website = None
currentVideo = None
currentPlatform = platform.system()
currentPlayerApp = None

player = None
downloader = None
playThread = None
playQueue = Queue()

experiment = True

actionToKey = {
    'pause': 'p',
    'stop': 'q',
    'volup': '+',
    'voldown': '-',
    'f30': '\x1B[D',
    'b30': '\x1B[C',
    'f600': '\x1B[A',
    'b600': '\x1B[B',
    'showinfo': 'z',
    'speedup': '1',
    'speeddown': '2',
    'togglesub': 's',
}

actionDesc = [
    [
        ('pause', 'Pause'),
        ('stop', 'Stop'),
        ('volup', 'Increase Volume'),
        ('voldown', 'Decrease Volume')
    ],
    # [
    #     ('f30', 'Seek +30'),
    #     ('b30', 'Seek -30'),
    #     ('f600', 'Seek +600'),
    #     ('b600', 'Seek -600')
    # ],
    # [
    #     ('showinfo', 'z'),
    #     ('speedup', '1'),
    #     ('speeddown', '2'),
    #     ('togglesub', 's'),
    # ]
]

actionToKeyMac = {
    'MPlayerX':
    {
        'pause': '49',
        'stop': '12 using command down',
        'volup': '24',
        'voldown': '27',
        'fullscreen': '3',
    },
    'VLC':
    {
        'pause': '49',
        'stop': '12 using command down',
        'volup': '126 using command down',
        'voldown': '125 using command down',
        'fullscreen': '3 using command down',
    }
}

import logging
logging.basicConfig(format='%(asctime)s %(module)s %(levelname)s: %(message)s',
                    filename='app.log', level=logging.DEBUG)


def exceptionLogger(type, value, tb):
    logging.exception("Uncaught exception: %s", value)
    sys.__excepthook__(type, value, tb)


sys.excephook = exceptionLogger


def isProcessAlive(process):
    if process:
        if process.poll() is None:
            return True
    return False


def clearQueue():
    global playQueue
    with playQueue.mutex:
        playQueue.queue.clear()


def parseM3U():
    with open('playlist.m3u', 'r') as f:
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
        logging.debug("Put next: %s", currentVideo.nextVideo)
        playQueue.put("next:%s" % currentVideo.nextVideo)


def play_list():
    global player, playQueue, currentVideo, downloader
    while True:
        v = playQueue.get()
        logging.info("Play %s", v)
        if v.startswith('next:'):
            _play_url(v.replace('next:', ''))
        else:
            if current_website and 'externaldownload' in websites[current_website] and websites[current_website]['externaldownload']:
                logging.info("Use external download tool")
                downloader = subprocess.Popen(["wget", v.strip(), "-O", "omxpipe", "-o", "download.log"])
                player = subprocess.Popen(["omxplayer", "-p", "-o", "hdmi", "omxpipe", '--vol', '-1000'],
                                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            else:
                player = subprocess.Popen(["omxplayer", "-p", "-o", "hdmi", v.strip(), '--vol', '-1000'],
                                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while isProcessAlive(player):
            time.sleep(1)
            if currentVideo and (not currentVideo.paused):
                currentVideo.progress += 1


def terminatePlayer():
    global player, downloader
    if player and isProcessAlive(player):
        logging.warn("Terminate the previous player")
        player.terminate()
        player = None
    if downloader and isProcessAlive(downloader):
        logging.warn("Terminate the previous downloader")
        downloader.terminate()
        downloader = None
        subprocess.call(["killall", "-9", "ffmpeg"])


def play_url(where=0):
    global player, currentVideo, currentPlayerApp, playQueue, paused, progress
    clearQueue()
    db_writeHistory(currentVideo)
    terminatePlayer()
    logging.info("Playing %s", currentVideo.realUrl)
    logging.debug("currentVideo = %s", currentVideo)
    if currentPlatform != 'Darwin':
        global playThread
        if not playThread or (not playThread.isAlive()):
            logging.debug("New a thred to play the list.")
            playThread = Thread(target=play_list)
            playThread.start()
    if currentVideo.realUrl == 'playlist.m3u':
        if currentPlatform == 'Darwin':
            currentPlayerApp = 'VLC'
            player = subprocess.Popen(["/Applications/VLC.app/Contents/MacOS/VLC",
                                      #currentVideo.realUrl, '--fullscreen'],
                                      currentVideo.realUrl],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            # Because omxplayer doesn't support list we have to play one by one.
            sections = parseM3U()
            if experiment and len(sections) > 1:
                outputFileName = 'all.ts'
                exec_filename = "merge.sh"
                try:
                    os.remove(exec_filename)
                    os.remove(outputFileName)
                except OSError:
                    pass
                lines = []
                p_list = []
                for idx, v in enumerate(sections):
                    pname = "p%s" % idx
                    newFifo(pname)
                    lines.append("wget %s | ffmpeg -i pipe:0 -c copy -bsf:v h264_mp4toannexb -flags -global_header -y -f mpegts %s 2> %s.log &\n" % (v, pname, pname))
                    p_list.append(pname)
                lines.append('ffmpeg -f mpegts -i "concat:%s" -c copy -y -f mpegts all.ts 2> merge.log\n' % "|".join(p_list))
                with open(exec_filename, 'wb') as f:
                    f.writelines(lines)
                global downloader
                downloader = subprocess.Popen(["sh", "merge.sh"])
                timeout = 30
                while True:
                    if os.path.exists(outputFileName):
                        fillQueue(urls=[outputFileName])
                        break
                    else:
                        time.sleep(1)
                        timeout -= 1
                        if timeout == 0:
                            return "Timeout after 30 seconds."
            else:
                if currentVideo.progress > 0:
                    result = goto(currentVideo.progress, 0)
                    if result != 'OK':
                        fillQueue()
                else:
                    fillQueue()
    else:
        if currentPlatform == 'Darwin':
            currentPlayerApp = 'MPlayerX'
            player = subprocess.Popen(["/Applications/MPlayerX.app/Contents/MacOS/MPlayerX", '-url',
                                      currentVideo.realUrl, "-StartByFullScreen", "YES"],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            fillQueue([currentVideo.realUrl])
    if currentPlatform == 'Darwin':
        # Try to send it to the second screen
        templateStr = """osascript\
 -e "delay 3"\
 -e "tell application \\"$currentPlayerApp\\""\
 -e "set position of window 1 to {1900, 30}"\
 -e "end tell" """
        executeCmdForMac(templateStr)
    return template("index", websites=websites, currentVideo=currentVideo, actionDesc=actionDesc,
                    history=db_getHistory())


def sendKeyForMac(keyString):
    templateStr = """osascript\
 -e "tell application \\"$currentPlayerApp\\""\
 -e "activate"\
 -e "tell application \\"System Events\\" to tell process \\"$currentPlayerApp\\" to key code $keycode"\
 -e "end tell" """
    executeCmdForMac(templateStr, params={"keycode": keyString})


def executeCmdForMac(templateStr, params={}):
    s = Template(templateStr)
    p = {"currentPlayerApp": currentPlayerApp}
    if params:
        for k, v in params.iteritems():
            p[k] = v
    cmd = s.substitute(p)
    logging.info("Execuing command: %s", cmd)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = p.communicate()
    logging.debug("out = %s\nerr = %s\nreturnCode = %s", out, err, p.returncode)


def _play_url(url, format=None, dbid=None):
    logging.debug("_play_url %s", url)
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
            return play_url()
    parser = websites[current_website]['parser'](url, format)
    parseResult = parser.parse()
    if isinstance(parseResult, Video):
        currentVideo = parseResult
        logging.info('currentVideo = %s', str(currentVideo))
        if dbid:
            currentVideo.dbid = dbid
            currentVideo.progress = db_getById(int(dbid)).progress
        return play_url(where=currentVideo.progress)
    else:
        logging.info('No video found, return the web page.')
        return parseResult


@route('/')
def index():
    if not isProcessAlive(player):
        global currentVideo
        currentVideo = None
    return template("index", websites=websites, currentVideo=currentVideo, actionDesc=actionDesc,
                    history=db_getHistory())


@route('/play')
def history_play():
    global currentVideo
    currentVideo = db_getById(request.query.id)
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
    if player and isProcessAlive(player):
        if (currentPlatform != 'Darwin' and action in actionToKey) or\
                (currentPlatform == 'Darwin' and action in actionToKeyMac[currentPlayerApp]):
            if currentPlatform == 'Darwin':
                logging.info("Send key code: %s", actionToKeyMac[currentPlayerApp][action])
                sendKeyForMac(actionToKeyMac[currentPlayerApp][action])
            else:
                logging.info("Send key code: %s", actionToKey[action])
                player.stdin.write(actionToKey[action])
            if action == "stop":
                if currentVideo.progress > 0:
                    logging.debug("Write last_play_pos to %s", currentVideo.progress)
                    db_writeHistory(currentVideo)
                player = None
                currentVideo = None
            if action == "pause":
                currentVideo.paused = (not currentVideo.paused)
            feedback = "OK"
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
                                <h3>%s</h3>
                                <p>总共%s(%s)</p>
                            </a>
                            <a href="#" onclick="deleteHistory('%s');return false"></a>
                        </li>
                        """ % (video.dbid, video.title, video.durationToStr(),
                               websites[video.site]['title'], video.dbid)
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
    if currentVideo:
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
    if new_progress is not None and c_idx is not None:
        if c_idx != currentIdx:
            currentVideo.progress = new_progress
            clearQueue()
            fillQueue(parseM3U()[c_idx:])
            terminatePlayer()
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
        url = "http://so.open.163.com/movie/search/searchprogram/ot0/%s/1.html?vs=%s&pltype=2" % (request.query.vs, request.query.vs)
        logging.debug("The url for wangyi search is: %s", url)
    return _play_url(url, format, dbid)


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
    p_results = urlparse(request.url)
    to_replace = p_results.scheme + "://" + p_results.netloc
    print to_replace
    redirectTo = "%s?site=%s&url=%s" % ('/forward', current_website,
                                        request.url.replace(to_replace,
                                        websites[current_website]['url']))
    if current_website == 'youku' and request.url.startswith("/search_video"):
        redirectTo = "%s?site=%s&url=%s" % ('/forward', current_website,
                                            request.url.replace(to_replace,
                                            "http://www.soku.com"))
    logging.debug("Redirect to %s", redirectTo)
    response.set_header('location', redirectTo)
    response.status = 303


@error(500)
def error500(error):
    return ("Exception: %s\nDetails: %s" % (error.exception, error.traceback)).replace('\n', '<br>')

import bottle
bottle.debug = True


def newFifo(filename):
    try:
        os.mkfifo(filename)
    except OSError:
        pass


if currentPlatform == 'Darwin':
    run(host='0.0.0.0', port=8000, reloader=True)
else:
    newFifo('omxpipe')
    run(host='0.0.0.0', port=80, reloader=True)
