#!/usr/bin/python
# -*- coding: utf8 -*-
import abc
import re
import urllib2
import json
import logging

format2keyword = {
    1: "",
    2: "high",
    3: "super"
}


class Video:
    formatDict = {
        1: "普通",
        2: "高清",
        3: "超清"
    }

    def __init__(self, title, url, realUrl, duration, site, typeid=1,
                 dbid=None, availableFormat=[], currentFormat=None):
        self.title = str(title)
        self.url = url
        self.realUrl = realUrl
        self.duration = str(int(float(duration)))
        self.site = site
        self.typeid = typeid
        self.dbid = dbid
        self.availableFormat = availableFormat
        self.currentFormat = currentFormat

    def durationToStr(self):
        duration_str = ""
        if self.duration:
            minutes = int(self.duration) / 60
            seconds = int(self.duration) % 60
            if minutes:
                duration_str += str(minutes) + "分钟"
            if seconds:
                duration_str += str(seconds) + "秒"
        return duration_str

    def __unicode__(self):
        return "url=%s, realurl=%s, duration=%s, site=%s, typeid=%s, \
               dbid=%s, availableFormat=%s, currentFormat=%s" % \
               (self.url, self.realUrl, self.duration, self.site, self.typeid,
               self.dbid, self.availableFormat, self.currentFormat)


class WebParser:
    __metaclass__ = abc.ABCMeta
    m3u_pattern = re.compile('<input type="hidden" name="inf" value="(?P<m3u>.*?)"/>', flags=re.DOTALL)

    def __init__(self, site, url, format):
        self.site = site
        self.url = url
        self.format = format
        self.availableFormat = []

    @abc.abstractmethod
    def parse(self):
        pass

    @abc.abstractmethod
    def parseVideo(self):
        pass

    @abc.abstractmethod
    def parseWeb(self):
        pass

    def getVideoUrl(self, **args):
        return self.getM3UFromFlvcd()

    def parseField(self, pattern, str, fieldName):
        r = pattern.search(str)
        field = None
        if r:
            field = r.group(fieldName)
        return field

    def fetchWeb(self, url):
        f = urllib2.urlopen(url)
        return f.read()

    def getAvailableFormat(self):
        flvcdUrl = "http://www.flvcd.com/parse.php?kw=%s" % self.url
        responseString = self.fetchWeb(flvcdUrl).decode('gb2312').encode('utf8')
        if not "解析失败" in responseString:
            self.availableFormat.append(1)
        if "高清版解析" in responseString:
            self.availableFormat.append(2)
        if "超清版解析" in responseString:
            self.availableFormat.append(3)

    def getM3UFromFlvcd(self):
        # 默认清晰度最高的
        self.getAvailableFormat()
        if not self.format:
            self.format = self.availableFormat[-1]
        flvcdUrl = "http://www.flvcd.com/parse.php?kw=%s&flag=one&format=%s" % \
            (self.url, format2keyword[self.format])
        responseString = self.fetchWeb(flvcdUrl).decode('gb2312').encode('utf8')
        m3u = self.parseField(self.m3u_pattern, responseString, 'm3u')
        with open('playlist.m3u', 'wb') as f:
            f.write('#EXTM3U\n')
            f.write(m3u)
        return "playlist.m3u"


class QQWebParserMP4(WebParser):
    qq_vid_pattern = re.compile('vid:"(?P<vid>\w+)"')
    qq_title_pattern = re.compile('title:"(?P<title>.+)"')
    qq_duration_pattern = re.compile('duration:"(?P<duration>\d+)"')
    qq_typeid_pattern = re.compile('typeid:(?P<typeid>\d)')

    def __init__(self, url, format):
        WebParser.__init__(self, "qqmp4", url, format)

    def parse(self):
        if self.url.startswith('http://v.qq.com/cover'):
            video = self.parseVideo()
            if video.typeid == 2:
                #电视剧
                if self.url.count('/') <= 5:
                    self.url = self.url.replace('cover', 'detail')
                    return self.parseWeb()
            return video
        else:
            return self.parseWeb()

    def parseVideo(self):
        logging.info("parseVideo %s", self.url)
        responseString = self.fetchWeb(self.url)
        vid = self.parseField(self.qq_vid_pattern, responseString, "vid")
        title = self.parseField(self.qq_title_pattern, responseString, "title")
        duration = self.parseField(self.qq_duration_pattern, responseString, "duration")
        typeid = self.parseField(self.qq_typeid_pattern, responseString, "typeid")
        realUrl = self.getVideoUrl(vid=vid)
        return Video(title, self.url, realUrl, duration, self.site, int(typeid),
                     availableFormat=self.availableFormat, currentFormat=self.format)

    def parseWeb(self):
        logging.info("parseWeb %s", self.url)
        responseString = self.fetchWeb(self.url)
        logging.debug("Finish fetch web")
        return self.replaceQQ(responseString)

    def replaceQQ(self, responseString):
        return responseString.replace(' href="/', ' href="/forward?site=%s&url=http://v.qq.com/' % self.site).\
            replace(' href="http://v.qq.com/', ' href="/forward?site=%s&url=http://v.qq.com/' % self.site).\
            replace('form action="', 'form action="/forward?site=%s&url=' % self.site).\
            replace('role="search">',
                    'role="search"><input type="hidden" name="url" value="http://v.qq.com/search.html">')


class QQWebParser(QQWebParserMP4):

    def __init__(self, url, format):
        WebParser.__init__(self, 'qq', url, format)

    def getVideoUrl(self, **args):
        return "http://vsrc.store.qq.com/%s.flv" % args['vid']


class YoukuWebParser(WebParser):

    youku_vid_pattern = re.compile("id_(?P<vid>\w+)\.html")

    def __init__(self, url, format):
        WebParser.__init__(self, 'youku', url, format)

    def parse(self):
        if 'youku.com/v_show/id_' in self.url:
            return self.parseVideo()
        else:
            return self.parseWeb()

    def parseVideo(self):
        logging.info("parseVideo %s", self.url)
        vid = self.parseField(self.youku_vid_pattern, self.url, "vid")
        getVideoInfoUrl = "http://v.youku.com/player/getPlayList/VideoIDS/%s" % vid
        responseString = self.fetchWeb(getVideoInfoUrl)
        d = json.loads(responseString)
        realUrl = self.getVideoUrl()
        title = d['data'][0]['title']
        duration = d['data'][0]['seconds']
        return Video(title.encode('utf8'), self.url, realUrl, duration, self.site,
                     availableFormat=self.availableFormat, currentFormat=self.format)

    def parseWeb(self):
        logging.info("parseWeb %s", self.url)
        responseString = self.fetchWeb(self.url)
        logging.debug("Finish fetch web")
        return self.replaceYouku(responseString)

    def replaceYouku(self, responseString):
        return responseString.replace(' href="http://static', ' nohref="http://static').\
            replace(' href="http://', ' href="/forward?site=%s&url=http://' % self.site).\
            replace(' nohref="http://static', ' href="http://static')
