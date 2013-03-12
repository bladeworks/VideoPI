#!/usr/bin/python
# -*- coding: utf8 -*-
import abc
import re
import urllib2
import json
import logging
import subprocess
import time
from urlparse import urlparse
from struct import unpack

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
                 dbid=None, availableFormat=[], currentFormat=None,
                 previousVideo=None, nextVideo=None, allRelatedVideo=[],
                 progress=0, paused=False, sections=[]):
        self.title = str(title)
        self.url = url
        self.realUrl = realUrl
        self.duration = str(int(float(duration)))
        self.site = site
        self.typeid = typeid
        self.dbid = dbid
        self.availableFormat = availableFormat
        self.currentFormat = currentFormat
        self.previousVideo = previousVideo
        self.nextVideo = nextVideo
        self.allRelatedVideo = allRelatedVideo
        self.progress = progress
        self.paused = paused
        self.sections = sections
        self.previousSection = None
        self.nextSection = None
        self.currentSection = None

    @staticmethod
    def formatDuration(duration):
        duration_str = ""
        if duration:
            minutes = int(duration) / 60
            seconds = int(duration) % 60
            if minutes:
                duration_str += str(minutes) + "分钟"
            if seconds:
                duration_str += str(seconds) + "秒"
        return duration_str

    def durationToStr(self):
        if self.duration <= 0:
            return "N/A"
        return self.formatDuration(self.duration)

    def getCurrentIdx(self):
        return self.getSectionsFrom(self.progress)[1]

    def getSectionsFrom(self, where):
        t = 0
        c_idx = None
        new_progress = 0
        for idx, val in enumerate(self.sections):
            new_progress = t
            t += int(float(val['seconds']))
            if t >= where:
                c_idx = idx
                break
        if c_idx is not None:
            return (new_progress, c_idx)
        return (None, None)

    def __str__(self):
        return "url=%s, realurl=%s, duration=%s, site=%s, typeid=%s, \
               dbid=%s, availableFormat=%s, currentFormat=%s, sections=%s" % \
               (self.url, self.realUrl, self.duration, self.site, self.typeid,
               self.dbid, self.availableFormat, self.currentFormat, self.sections)


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
            logging.debug("%s = %s", fieldName, field)
        return field

    def calc_sogou_hash(self, t, host):
        s = (t + host + 'SogouExplorerProxy').encode('ascii')
        code = len(s)
        dwords = int(len(s)/4)
        rest = len(s) % 4
        v = unpack(str(dwords) + 'i'+str(rest)+'s', s)
        for vv in v:
            if (isinstance(vv, str)):
                break
            a = (vv & 0xFFFF)
            b = (vv >> 16)
            code += a
            code = code ^ (((code << 5) ^ b) << 0xb)
            # To avoid overflows
            code &= 0xffffffff
            code += code >> 0xb
        if rest == 3:
            code += ord(s[len(s)-2]) * 256 + ord(s[len(s)-3])
            code = code ^ ((code ^ (ord(s[len(s)-1])*4)) << 0x10)
            code &= 0xffffffff
            code += code >> 0xb
        elif rest == 2:
            code += ord(s[len(s)-1]) * 256 + ord(s[len(s)-2])
            code ^= code << 0xb
            code &= 0xffffffff
            code += code >> 0x11
        elif rest == 1:
            code += ord(s[len(s)-1])
            code ^= code << 0xa
            code &= 0xffffffff
            code += code >> 0x1
        code ^= code * 8
        code &= 0xffffffff
        code += code >> 5
        code ^= code << 4
        code = code & 0xffffffff
        code += code >> 0x11
        code ^= code << 0x19
        code = code & 0xffffffff
        code += code >> 6
        code = code & 0xffffffff
        return hex(code)[2:].rstrip('L').zfill(8)

    def getTZ(self):
        return time.timezone / (-60*60)

    def fetchWeb(self, url, via_proxy=False):
        logging.debug("Fetch %s", url)
        host = urlparse(url).hostname
        headers = {}
        if self.getTZ != 8:
            headers = {'User-Agent': 'Mozilla/5.0',
                       'X-Forwarded-For': '220.181.111.158'}
            proxy = urllib2.ProxyHandler({})
            if via_proxy:
                proxy = urllib2.ProxyHandler({'http': 'h0.edu.bj.ie.sogou.com'})
                t = hex(int(time.time()))[2:].rstrip('L').zfill(8)
                headers = {'User-Agent': 'Mozilla/5.0',
                           'Host': host,
                           'X-Forwarded-For': '220.181.111.158',
                           'Proxy-Connection': 'keep-alive',
                           'X-Sogou-Auth': '81795E50665FE4212A3B4D3391950B74/30/853edc6d49ba4e27',
                           'X-Sogou-Tag': self.calc_sogou_hash(t, host),
                           'X-Sogou-Timestamp': t}
            urllib2.install_opener(urllib2.build_opener(proxy))
        req = urllib2.Request(url.encode('utf8'), None, headers)
        return urllib2.urlopen(req).read()

    def getAvailableFormat(self):
        flvcdUrl = "http://www.flvcd.com/parse.php?kw=%s" % self.url
        responseString = self.fetchWeb(flvcdUrl).decode('gb2312', 'ignore').encode('utf8')
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
        responseString = self.fetchWeb(flvcdUrl).decode('gb2312', 'ignore').encode('utf8')
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
    qq_tv_pattern = re.compile('\<a _hot="detail.story" title="(?P<title>.*?)" href="(?P<url>.*?)"\>')

    def __init__(self, url, format):
        WebParser.__init__(self, "qqmp4", url, format)

    def parse(self):
        if self.url.startswith('http://v.qq.com/cover') or self.url.startswith('http://v.qq.com/prev'):
            video = self.parseVideo()
            if video.typeid == 2:
                #电视剧
                if self.url.count('/') <= 5 and not self.url.startswith('http://v.qq.com/prev'):
                    self.url = self.url.replace('cover', 'detail')
                    logging.debug("The url is for TV, forward to the detail page")
                    return self.parseWeb()
            return video
        else:
            return self.parseWeb()

    def getRelatedVideoes(self):
        detailUrl = (self.url.rpartition('/')[0] + '.html').replace('cover', 'detail')
        responseString = self.fetchWeb(detailUrl)
        nextVideo = None
        previousVideo = None
        allRelatedVideo = []
        current = False
        for (title, url) in self.qq_tv_pattern.findall(responseString):
            fullUrl = 'http://v.qq.com%s' % url
            if current and (not nextVideo):
                nextVideo = fullUrl
                logging.info("Next is %s" % nextVideo)
            relatedVideo = {'title': title, 'url': fullUrl, 'current': False}
            if url in self.url:
                current = True
                relatedVideo['current'] = True
            if not current:
                previousVideo = fullUrl
            allRelatedVideo.append(relatedVideo)
        logging.info("Previous is %s" % previousVideo)
        return (previousVideo, nextVideo, allRelatedVideo)

    def getSections(self, vid):
        url = "http://vv.video.qq.com/getinfo?platform=11&otype=json&vids=%s&defaultfmt=shd" % vid
        responseString = self.fetchWeb(url, via_proxy=True)
        d = json.loads(responseString.partition('=')[2][:-1])['vl']['vi'][0]['cl']['ci']
        return [{"no": str(v["idx"]), "seconds": str(int(float(v['cd'])))} for v in d]

    def parseVideo(self):
        logging.info("parseVideo %s", self.url)
        responseString = self.fetchWeb(self.url)
        if '<title></title>' in responseString:
            self.url = self.url.replace('cover', 'prev')
            responseString = self.fetchWeb(self.url)
        vid = self.parseField(self.qq_vid_pattern, responseString, "vid")
        title = self.parseField(self.qq_title_pattern, responseString, "title")
        duration = self.parseField(self.qq_duration_pattern, responseString, "duration")
        if not duration:
            duration = "0"
        typeid = None
        typeidStr = self.parseField(self.qq_typeid_pattern, responseString, "typeid")
        if typeidStr:
            typeid = int(typeidStr)
        nextVideo = None
        previousVideo, nextVideo, allRelatedVideo = None, None, None
        if typeid == 2:
            previousVideo, nextVideo, allRelatedVideo = self.getRelatedVideoes()
        sections = self.getSections(vid)
        realUrl = self.getVideoUrl(vid=vid)
        return Video(title, self.url, realUrl, duration, self.site, typeid,
                     availableFormat=self.availableFormat, currentFormat=self.format,
                     previousVideo=previousVideo, nextVideo=nextVideo,
                     allRelatedVideo=allRelatedVideo, sections=sections)

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

    def getSections(self, vid):
        return []

    def getVideoUrl(self, **args):
        return "http://vsrc.store.qq.com/%s.flv" % args['vid']


class YoukuWebParser(WebParser):

    youku_vid_pattern = re.compile("id_(?P<vid>\w+)\.html")
    format2key = {
        1: "flv",
        2: "mp4",
        3: "hd2"
    }

    def __init__(self, url, format):
        WebParser.__init__(self, 'youku', url, format)

    def parse(self):
        if 'youku.com/v_show/id_' in self.url:
            return self.parseVideo()
        else:
            return self.parseWeb()

    def getRelatedVideoes(self, data):
        nextVideo = None
        previousVideo = None
        allRelatedVideo = []
        current = False
        for d in data:
            vid = d['vidEncoded']
            title = d['title']
            url = "http://v.youku.com/v_show/id_%s.html" % vid
            if current and (not nextVideo):
                nextVideo = url
                logging.info("Next is %s" % nextVideo)
            relatedVideo = {'title': title, 'url': url, 'current': False}
            if url in self.url:
                current = True
                relatedVideo['current'] = True
            if not current:
                previousVideo = url
            allRelatedVideo.append(relatedVideo)
        logging.info("Previous is %s" % previousVideo)
        return (previousVideo, nextVideo, allRelatedVideo)

    def parseVideo(self):
        logging.info("parseVideo %s", self.url)
        vid = self.parseField(self.youku_vid_pattern, self.url, "vid")
        getVideoInfoUrl = "http://v.youku.com/player/getPlayList/VideoIDS/%s" % vid
        responseString = self.fetchWeb(getVideoInfoUrl)
        d = json.loads(responseString)
        realUrl = self.getVideoUrl()
        title = d['data'][0]['title']
        duration = d['data'][0]['seconds']
        # {
        #     "no": "3",
        #     "size": "26818399",
        #     "seconds": "186",
        #     "k": "2dcf9f6fbc647634241154a3",
        #     "k2": "17a225161b46a9bc0"
        # },
        sections = d['data'][0]['segs'][self.format2key[self.format]]
        previousVideo, nextVideo, allRelatedVideo = self.getRelatedVideoes(d['data'][0]['list'])
        return Video(title.encode('utf8'), self.url, realUrl, duration, self.site,
                     availableFormat=self.availableFormat, currentFormat=self.format,
                     previousVideo=previousVideo, nextVideo=nextVideo,
                     allRelatedVideo=allRelatedVideo, sections=sections)

    def parseWeb(self):
        logging.info("parseWeb %s", self.url)
        responseString = self.fetchWeb(self.url)
        logging.debug("Finish fetch web")
        return self.replaceYouku(responseString)

    def replaceYouku(self, responseString):
        return responseString.replace(' href="http://static', ' nohref="http://static').\
            replace(' href="http://', ' href="/forward?site=%s&url=http://' % self.site).\
            replace(' nohref="http://static', ' href="http://static')


class YoutubeWebParser(WebParser):

    youtube_title_pattern = re.compile('\<title\>(?P<title>.*?)\</title\>')
    youtube_duration_pattern = re.compile('"length_seconds": (?P<duration>\d+)')

    def __init__(self, url, format):
        WebParser.__init__(self, 'youtube', url, format)

    def getVideoUrl(self, **args):
        realUrl = subprocess.check_output(['youtube-dl', '-g', self.url])
        return realUrl

    def parse(self):
        if 'watch?v=' in self.url:
            return self.parseVideo()
        else:
            return self.parseWeb()

    def parseVideo(self):
        logging.info("parseVideo %s", self.url)
        responseString = self.fetchWeb(self.url)
        title = self.parseField(self.youtube_title_pattern, responseString, 'title')
        duration = self.parseField(self.youtube_duration_pattern, responseString, 'duration')
        realUrl = self.getVideoUrl()
        return Video(title, self.url, realUrl, duration, self.site,
                     availableFormat=self.availableFormat, currentFormat=self.format)

    def parseWeb(self):
        logging.info("parseWeb %s", self.url)
        responseString = self.fetchWeb(self.url)
        logging.debug("Finish fetch web")
        return self.replaceYoutube(responseString)

    def replaceYoutube(self, responseString):
        return responseString.replace(' href="http://s.ytimg.com/', ' nohref="http://s.ytimg.com/').\
            replace(' href="http://', ' href="/forward?site=%s&url=http://' % self.site).\
            replace('action="/results"', 'action="/forward?site=%s&url=http://www.youtube.com/results' % self.site).\
            replace(' href="/', ' href="/forward?site=%s&url=http://www.youtube.com/' % self.site).\
            replace(' nohref="http://s.ytimg.com/', ' href="http://s.ytimg.com/')
