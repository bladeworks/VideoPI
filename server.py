#!/usr/bin/python
# -*- coding: utf8 -*-
from bottle import route, run, template, request, static_file, post, get, redirect
from database import *
from webparser import Video, QQWebParser, QQWebParserMP4, YoukuWebParser
from string import Template
import subprocess
import platform

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
currentPlatform = platform.system()
currentPlayerApp = None

player = None
actionToKey = {
    'pause': 'p',
    'stop': 'q',
    'volup': '+',
    'voldown': '-',
}

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


def isProcessAlive(process):
    if process:
        logging.debug("pid = %s", process.pid)
        if process.poll() is None:
            return True
    return False


def play_url():
    global player, currentVideo, currentPlayerApp
    db_writeHistory(currentVideo)
    if player and isProcessAlive(player):
        logging.warn("Terminate the previous player")
        player.terminate()
        player = None
    logging.info("Playing %s", currentVideo.realUrl)
    if currentVideo.realUrl == 'playlist.m3u':
        if currentPlatform == 'Darwin':
            currentPlayerApp = 'VLC'
            player = subprocess.Popen(["/Applications/VLC.app/Contents/MacOS/VLC",
                                      currentVideo.realUrl, '--fullscreen'],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            player = subprocess.Popen(["omxplayer", currentVideo.realUrl],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        if currentPlatform == 'Darwin':
            currentPlayerApp = 'MPlayerX'
            player = subprocess.Popen(["/Applications/MPlayerX.app/Contents/MacOS/MPlayerX", '-url',
                                      currentVideo.realUrl, "-StartByFullScreen", "YES"],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            player = subprocess.Popen(["omxplayer", currentVideo.realUrl],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if currentPlatform == 'Darwin':
        # Try to send it to the second screen
        templateStr = """osascript\
 -e "delay 3"\
 -e "tell application \\"$currentPlayerApp\\""\
 -e "set position of window 1 to {1900, 30}"\
 -e "end tell" """
        executeCmdForMac(templateStr)
    return template("index", title=currentVideo.title, duration=currentVideo.durationToStr(),
                    websites=websites, currentVideo=currentVideo)


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


@route('/')
def index():
    global title, duration_str
    if not isProcessAlive(player):
        global currentVideo
        currentVideo = None
    if currentVideo:
        return template("index", title=currentVideo.title, duration=currentVideo.durationToStr(),
                        websites=websites, currentVideo=currentVideo)
    else:
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
    global player, currentVideo
    feedback = ""
    if player and isProcessAlive(player):
        if action in actionToKey:
            logging.info("Send key code: %s", actionToKeyMac[currentPlayerApp][action])
            if currentPlatform == 'Darwin':
                sendKeyForMac(actionToKeyMac[currentPlayerApp][action])
            else:
                player.stdin.write(actionToKey[action])
            if action == "stop":
                player = None
                currentVideo = None
            feedback = "OK"
        else:
            feedback = "Unknow action: " + action
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
                            <a href="#" onclick="deleteHistory('%s');return false" \
                            data-role="button" data-icon="delete"></a>
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


@route('/forward')
def forward():
    global vid, title, duration, duration_str
    format = None
    url = request.query.url
    if 'site' in request.query:
        global current_website
        current_website = request.query.site
    if 'format' in request.query:
        format = int(request.query.format)
        logging.info("Forwarding to %s", url)
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
