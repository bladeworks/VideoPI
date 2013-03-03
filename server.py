#!/usr/bin/python
# -*- coding: utf8 -*-
from bottle import route, run, template, request, static_file, post, get, redirect
from database import *
from webparser import Video, QQWebParser, QQWebParserMP4, YoukuWebParser
import subprocess
import threading

websites = {
    "qq": {
        "title": "腾讯视频(flv)",
        "url": "http://v.qq.com",
        "parser": QQWebParser
    },
    "qqmp4": {
        "title": "腾讯视频(mp4)",
        "url": "http://v.qq.com",
        "parser": QQWebParserMP4
    },
    "youku": {
        "title": "优酷视频",
        "url": "http://www.youku.com",
        "parser": YoukuWebParser
    },
}

current_website = None
currentVideo = None

player = None
actionToKey = {
    'pause': 'p',
    'volup': '+',
    'voldown': '-',
    'forward': '\x1B[C',
    'backward': '\x1B[D'
}
lock = threading.RLock()


def isProcessAlive(process):
    if process:
        if process.poll() is None:
            print "Process is alive"
            return True
    print "Process is not alive"
    return False


def play_url():
    global player, currentVideo
    if currentVideo.realUrl == 'playlist.m3u':
        print "play playlist.m3u"
        db_writeHistory(currentVideo)
        player = subprocess.Popen(["/Applications/VLC.app/Contents/MacOS/VLC",
                                  currentVideo.realUrl],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        with lock:
            if player and isProcessAlive(player):
                print "teminate the process"
                player.terminate()
                player = None
            # player = subprocess.Popen(["vi", "omxplayer", url], \
            #    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            db_writeHistory(currentVideo)
            print "Finish write history"
            # player = subprocess.Popen(["open", "-a", "/Applications/MPlayerX.app", "--args",
                # "-url", url, "-StartByFullScreen", "YES"], \
            player = subprocess.Popen(["/Applications/MPlayerX.app/Contents/MacOS/MPlayerX", '-url',
                                      currentVideo.realUrl, "-StartByFullScreen", "YES"],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return template("index", title=currentVideo.title, duration=currentVideo.durationToStr(),
                    websites=websites, currentVideo=currentVideo)


@route('/')
def index():
    global title, duration_str
    return template('index', websites=websites)


@route('/play')
def history_play():
    global currentVideo
    currentVideo = db_getById(request.query.id)
    redirect('/forward?site=%s&url=%s&dbid=%s' % (currentVideo.site, currentVideo.url, currentVideo.dbid))


@route('/static/<filename:path>')
def static(filename):
    return static_file(filename, root='static')


@post('/control/<action>')
def control(action):
    global player
    feedback = ""
    if player and isProcessAlive(player):
        if action == 'stop':
            player.stdin.write("q")
            player = None
            feedback = "OK"
        else:
            if action in actionToKey:
                print "Write:", actionToKey[action]
                player.stdin.write(actionToKey[action])
                feedback = "OK"
            else:
                feedback = "Unknow action: " + action
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
                                <p>总共%s</p>
                            </a>
                            <a href="#" onclick="deleteHistory('%s');return false" data-role="button" data-icon="delete"></a>
                        </li>
                        """ % (video.dbid, video.title, video.durationToStr(), video.dbid)
    return responseString


@post('/delete/<id>')
def delete(id):
    db_delete(id)


@post('/clear')
def clear():
    db_delete(-1)


@route('/forward')
def forward():
    global vid, title, duration, duration_str
    format = None
    url = request.query.url
    if 'site' in request.query:
        global current_website
        current_website = request.query.site
        print 'set current_website to ' + current_website
    if 'format' in request.query:
        format = int(request.query.format)
    print "forward to", url
    parser = websites[current_website]['parser'](url, format)
    parseResult = parser.parse()
    if isinstance(parseResult, Video):
        global currentVideo
        currentVideo = parseResult
        if 'dbid' in request.query:
            currentVideo.dbid = request.query.dbid
        return play_url()
    else:
        return parseResult

run(host='0.0.0.0', port=8000, reloader=True)
