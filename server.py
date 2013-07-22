#!/usr/bin/python
# -*- coding: utf8 -*-
from bottle import route, run, template, request, static_file, post, get, redirect, error, response
import subprocess
import sys
import time
import urllib
import urllib2
import bottle
from urlparse import urlparse
from Constants import websites, actionDesc
from Helper import newFifo, newDir
from database import db_getHistory, db_delete
from player import Controller
from config import get_cfg
from webparser import Video

bottle.debug = True

import logging
logger = logging.getLogger()
handler = logging.handlers.RotatingFileHandler(get_cfg('logStorage'), maxBytes=1000000, backupCount=2)
formatter = logging.Formatter(fmt='%(asctime)s %(threadName)s %(module)s:%(lineno)d %(levelname)s: %(message)s')
handler.setFormatter(formatter)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)


def exceptionLogger(type, value, tb):
    logging.exception("Uncaught exception: %s", value)
    sys.__excepthook__(type, value, tb)


sys.excephook = exceptionLogger

controller = None
current_website = None


def _render(wait=False, redirect_to=None):
    if (wait):
        while not (controller.currentPlayer and controller.currentPlayer.video and controller.currentPlayer.isAlive()):
            time.sleep(0.1)
    if redirect_to:
        redirect(redirect_to)
    if controller and controller.currentPlayer and controller.currentPlayer.video and controller.currentPlayer.isAlive():
        return template("index", websites=websites, currentVideo=controller.currentPlayer.video, actionDesc=actionDesc,
                        history=db_getHistory())
    else:
        return template("index", websites=websites, currentVideo=None, actionDesc=actionDesc,
                        history=db_getHistory())


@route('/')
def index():
    return _render()


@route('/play')
def history_play():
    global controller
    if controller:
        controller.stopAll()
    controller = Controller(None)
    controller.parseHistory(request.query.id, request.query.start)
    _render(wait=True, redirect_to='/')


@route('/static/<filename:path>')
def static(filename):
    return static_file(filename, root='static')


@post('/control/<action>')
def control(action):
    feedback = ""
    if controller and controller.currentPlayer.isAlive():
        feedback = "OK"
        if action == "stop":
            controller.stopAll()
        elif action == "pause":
            controller.currentPlayer.toggle_pause()
        elif action == "volup":
            controller.currentPlayer.volup()
        elif action == "voldown":
            controller.currentPlayer.voldown()
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
                            <a href="#" onclick="deleteHistory('%s');return false" class="split-button-custom ui-btn ui-btn-up-b ui-shadow ui-btn-corner-all ui-btn-icon-notext" data-role="button" data-icon="delete" data-iconpos="notext" data-corners="true" data-shadow="true" data-iconshadow="true" data-wrapperels="span" data-theme="b" title=""><span class="ui-btn-inner"><span class="ui-btn-text"></span><span class="ui-icon ui-icon-delete ui-icon-shadow">&nbsp;</span></span></a>
                            <a href="/play?id=%s&start=0" class="split-button-custom ui-btn ui-btn-up-b ui-shadow ui-btn-corner-all ui-btn-icon-notext" data-role="button" data-icon="refresh" data-iconpos="notext" data-ajax="false" data-corners="true" data-shadow="true" data-iconshadow="true" data-wrapperels="span" data-theme="b" title=""><span class="ui-btn-inner"><span class="ui-btn-text"></span><span class="ui-icon ui-icon-refresh ui-icon-shadow">&nbsp;</span></span></a>                            <a href="#" style="display: none;">Dummy</a>
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
    if controller and controller.currentPlayer and controller.currentPlayer.isAlive():
        currentVideo = controller.currentPlayer.video
        currentVideo.progress = controller.currentPlayer.video.progress
        return {"title": currentVideo.title, "progress": str(currentVideo.progress), "duration": currentVideo.durationToStr()}
    else:
        return {"title": "N/A", "progress": "0", "duration": "N/A"}


@post('/goto/<where>')
def goto(where):
    controller.goto(where)
    return "OK"


@route('/forward')
def forward():
    global current_website, controller
    format, dbid = None, None
    if 'site' in request.query:
        current_website = request.query.site
    if 'format' in request.query:
        format = int(request.query.format)
    if 'dbid' in request.query:
        dbid = request.query.dbid
    url = request.query.url
    # if it's the same url with the nextPlayer then just stop the current player.
    if controller and controller.nextPlayer and urllib2.unquote(url) == urllib2.unquote(controller.nextPlayer.video.url):
        controller.stopCurrentPlayer()
        _render(wait=True, redirect_to='/')
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
    newController = Controller(current_website)
    if dbid:
        res = newController.parseHistory(dbid, -1, format)
    else:
        res = newController.parse(url, format)
    if res:
        return res 
    else:
        if controller:
            controller.stopAll()
        controller = newController
    _render(wait=True, redirect_to='/')


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
    global current_website
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


newFifo('/tmp/cmd')
newFifo('/tmp/all.ts')
newDir('/tmp/ffmpeg_part')
newDir('/tmp/download_part')
for i in range(1000):
    newFifo('/tmp/download_part/%s' % i)


try:
    if sys.platform == 'darwin':
        run(host='0.0.0.0', port=7777, reloader=True)
    else:
        run(host='0.0.0.0', port=80, quiet=True)
except:
    logging.exception("Exception catched")
