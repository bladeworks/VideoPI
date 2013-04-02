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
from config import *
try:
    from userPrefs import *
except:
    logging.info("Not userPrefs.py found so skip user configuration.")

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
                 progress=0, sections=[], start_pos=0):
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
        self.sections = sections
        self.start_pos = start_pos
        self.width, self.height = (0, 0)
        if int(self.duration) == 0 and self.realUrl:
            self.duration = self.getDurationWithFfmpeg(self.realUrl)

    def getResolution(self):
        if not(self.width and self.height):
            url = self.realUrl
            if self.realUrl == playlistStorage:
                with open(playlistStorage, 'r') as f:
                    url = [v.strip() for v in f.readlines() if v.startswith('http')][0]
            output = subprocess.check_output(['ffprobe', '-v', 'quiet', '-of', 'json', '-show_streams',
                                              '-select_streams', 'v', url])
            logging.debug('output = %s', output)
            format = json.loads(output)
            self.width = int(format['streams'][0]['width'])
            self.height = int(format['streams'][0]['height'])
        return (self.width, self.height)

    def getDurationWithFfmpeg(self, url):
        if url == playlistStorage:
            duration = 0
            with open(playlistStorage, 'r') as f:
                for u in [v.strip() for v in f.readlines() if v.startswith('http')]:
                    duration += self.getSingleDurationWithFfmpeg(u)
            return duration
        else:
            return self.getSingleDurationWithFfmpeg(url)

    def getSingleDurationWithFfmpeg(self, url):
        logging.info("Get duration with ffmpeg for: %s", url)
        duration = 0
        try:
            output = subprocess.check_output(['ffprobe', '-v', 'quiet', '-of', 'json', '-show_format',
                                              '-select_streams', 'v', url])
            logging.debug('output = %s', output)
            format = json.loads(output)
            duration = int(float(format['format']['duration']))
        except:
            logging.exception("Exception catched")
        logging.info("Get duration with ffmpeg return: %s", duration)
        return duration

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
        if int(self.duration) <= 0:
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
        return "url=%s, realUrl=%s, duration=%s, progress=%s, site=%s, typeid=%s, \
               dbid=%s, availableFormat=%s, currentFormat=%s, sections=%s, allRelatedVideo=%s, \
               previousVideo=%s, nextVideo=%s" % \
               (self.url, self.realUrl, self.duration, self.progress, self.site, self.typeid,
               self.dbid, self.availableFormat, self.currentFormat, self.sections,
               self.allRelatedVideo, self.previousVideo, self.nextVideo)


class WebParser:
    __metaclass__ = abc.ABCMeta
    m3u_pattern = re.compile('<input type="hidden" name="inf" value="(?P<m3u>.*?)"/>', flags=re.DOTALL)
    single_pattern = re.compile('下载地址.*?<a href="(?P<url>.*?)"', flags=re.DOTALL)

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

    def fetchWeb(self, url, via_proxy=False, use_wget=False):
        logging.debug("Fetch %s", url)
        if use_wget:
            return subprocess.check_output("wget -q -O - %s | cat" % url, shell=True)
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
        try:
            req = urllib2.Request(url.encode('utf8'), None, headers)
        except urllib2.HTTPError:
            req = urllib2.Request(url, None, headers)
        return urllib2.urlopen(req).read()

    def getAvailableFormat(self):
        flvcdUrl = "http://www.flvcd.com/parse.php?kw=%s" % self.url
        responseString = self.fetchWeb(flvcdUrl).decode('gb2312', 'ignore').encode('utf8')
        if not "解析失败" in responseString:
            self.availableFormat.append(1)
        if "format=high" in responseString:
            self.availableFormat.append(2)
        if "format=super" in responseString:
            self.availableFormat.append(3)

    def getM3UFromFlvcd(self):
        # 默认清晰度最高的
        self.getAvailableFormat()
        if not self.availableFormat:
            return None
        if not self.format:
            if default_format in self.availableFormat:
                self.format = default_format
            else:
                self.format = self.availableFormat[-1]
        flvcdUrl = "http://www.flvcd.com/parse.php?kw=%s&flag=one&format=%s" % \
            (self.url, format2keyword[self.format])
        responseString = self.fetchWeb(flvcdUrl).decode('gb2312', 'ignore').encode('utf8')
        m3u = self.parseField(self.m3u_pattern, responseString, 'm3u')
        if not m3u:
            m3u = self.parseField(self.single_pattern, responseString, 'url')
        with open(playlistStorage, 'wb') as f:
            f.write('#EXTM3U\n')
            f.write(m3u)
        return playlistStorage

    def replaceResponse(self, responseString, replaces, skips=[]):
        logging.info("Replace response now.")
        skip_pre = "dontreplacexyz"
        ret = responseString
        for skip in skips:
            ret = ret.replace(skip, "%s%s" % (skip_pre, skip))
        for replace in replaces:
            ret = ret.replace(replace[0], replace[1])
        for skip in skips:
            ret = ret.replace("%s%s" % (skip_pre, skip), skip)
        return ret


class QQWebParserMP4(WebParser):
    qq_vid_pattern = re.compile('vid:"(?P<vid>\w+)"')
    qq_title_pattern = re.compile('title:"(?P<title>.+)"')
    qq_duration_pattern = re.compile('duration:"(?P<duration>\d+)"')
    qq_typeid_pattern = re.compile('typeid:(?P<typeid>\d)')
    qq_tv_pattern = re.compile('\<a _hot="detail.story" title="(?P<title>.*?)" href="(?P<url>.*?)"\>')
    qq_url_pattern = re.compile('url=(?P<url>.*?)"')

    def __init__(self, url, format):
        WebParser.__init__(self, "qqmp4", url, format)

    def parse(self):
        if (self.url.startswith('http://v.qq.com/page')):
            responseString = self.parseWeb()
            self.url = self.parseField(self.qq_url_pattern, responseString, 'url').\
                replace('.html?vid=', '/') + '.html'
            logging.debug("Go to url %s", self.url)
            return self.parse()
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
        replaces = [(' href="/', ' href="/forward?site=%s&url=http://v.qq.com/' % self.site),
                    (' href="http://v.qq.com/', ' href="/forward?site=%s&url=http://v.qq.com/' % self.site),
                    ('form action="/', 'form action="/forward'),
                    ('form action="http://v.qq.com/', 'form action="/forward?url="http://v.qq.com/'),
                    (' name="sform" id="sform"', ''),
                    (' name="sformMid" id="sformMid"', '')]
        return self.replaceResponse(responseString, replaces)


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
        previousVideo, nextVideo, allRelatedVideo = None, None, []
        try:
            previousVideo, nextVideo, allRelatedVideo = self.getRelatedVideoes(d['data'][0]['list'])
        except KeyError:
            pass
        return Video(title.encode('utf8'), self.url, realUrl, duration, self.site,
                     availableFormat=self.availableFormat, currentFormat=self.format,
                     previousVideo=previousVideo, nextVideo=nextVideo,
                     allRelatedVideo=allRelatedVideo, sections=sections)

    def parseWeb(self):
        logging.info("parseWeb %s", self.url)
        responseString = self.fetchWeb(self.url, use_wget=True)
        logging.debug("Finish fetch web")
        replaces = [(' href="http://', ' href="/forward?site=%s&url=http://' % self.site),
                    (" href='http://", " href='/forward?site=%s&url=http://" % self.site),
                    ('action="http://www.soku.com/search_video"', 'action="/forward"'),
                    ('onsubmit="return MiniHeader.dosearch(this);" ', ''),
                    ('type="button" onclick="return MiniHeader.dosearch(document.getElementById(\'headSearchForm\'));"', 'type="submit"'),
                    (' id="headq"', ''),
                    ('http:\/\/v.youku.com\/v_show\/id_', '\/forward?site=%s&url=http:\/\/v.youku.com\/v_show\/id_' % self.site)]
        skips = ['href="http://static']
        return self.replaceResponse(responseString, replaces, skips)


class WangyiWebParser(WebParser):

    wangyi_pattern = re.compile('<a href="(?P<url>http://v.163.com/movie.*?)".*?>(?P<title>.*?)</a>')
    wangyi_url_replace = re.compile('a .*?href="(?P<url>http://(so.open.163.com|v.163.com|open.163.com).*?)"')
    wangyi_title_pattern = re.compile("<span class='thdTit'>(?P<title>.*?)</span>")

    def __init__(self, url, format):
        WebParser.__init__(self, 'wangyi', url, format)

    def parse(self):
        if 'v.163.com/movie' in self.url:
            return self.parseVideo()
        else:
            return self.parseWeb()

    def parseVideo(self):
        logging.info("parseVideo %s", self.url)
        responseString = self.fetchWeb(self.url)
        title = None
        nextVideo = None
        previousVideo = None
        allRelatedVideo = []
        current = False
        for u, t in self.wangyi_pattern.findall(responseString):
            t = t.decode('gbk').encode('utf8')
            if current and (not nextVideo):
                nextVideo = u
            relatedVideo = {'title': t, 'url': u, 'current': False}
            if u.decode('gbk').encode('utf8') == self.url:
                title = t
                current = True
                relatedVideo['current'] = True
            if not current:
                previousVideo = u
            allRelatedVideo.append(relatedVideo)
        if not title:
            title = self.parseField(self.wangyi_title_pattern, responseString, 'title').decode('gbk').encode('utf8')
        realUrl = self.getVideoUrl()
        duration = 0
        return Video(title, self.url, realUrl, duration, self.site,
                     availableFormat=self.availableFormat, currentFormat=self.format,
                     allRelatedVideo=allRelatedVideo, previousVideo=previousVideo, nextVideo=nextVideo)

    def parseWeb(self):
        logging.info("parseWeb %s", self.url)
        responseString = self.fetchWeb(self.url)
        logging.debug("Finish fetch web")
        s = responseString.replace('<form id="videoSearchForm" target="_blank">', '<form action="/forward" target="_blank">')
        return self.wangyi_url_replace.sub(lambda m: m.group(0).replace(m.group('url'),
                                           '/forward?site=%s&url=%s' % (self.site, urllib2.quote(m.group('url')))), s).decode('gbk')


class YinyuetaiWebParser(WebParser):

    yinyuetai_title_pattern = re.compile('<meta property="og:title" content="(?P<title>.*?)"/>')
    yinyuetai_duration_pattern = re.compile('duration : "(?P<duration>\d+?)"')
    yinyuetai_list_title_pattern = re.compile('<a href="javascript:void\\(0\\)" title="(?P<title>.*?)">')
    yinyuetai_list_url_pattern = re.compile('<span style="display:none" name="videoUrl">(?P<url>.*?)</span>')

    def __init__(self, url, format):
        WebParser.__init__(self, 'yinyuetai', url, format)

    def parse(self):
        if 'www.yinyuetai.com/video' in self.url or \
                'hc.yinyuetai.com/uploads/videos/common' in self.url or \
                'www.yinyuetai.com/playlist' in self.url:
            return self.parseVideo()
        else:
            return self.parseWeb()

    def parseVideo(self):
        logging.info("parseVideo %s", self.url)
        sections = []
        previousVideo, nextVideo, allRelatedVideo = None, None, []
        if 'hc.yinyuetai.com/uploads/videos/common' in self.url:
            realUrl = self.url
            title = 'N/A'
            duration = 0
        elif 'www.yinyuetai.com/playlist' in self.url:
            responseString = self.fetchWeb(self.url)
            titles = self.yinyuetai_list_title_pattern.findall(responseString)
            urls = self.yinyuetai_list_url_pattern.findall(responseString)
            for idx, t in enumerate(titles):
                allRelatedVideo.append({'title': t, 'url': urls[idx], 'current': False})
            nextVideo = allRelatedVideo[1]['url']
            allRelatedVideo[0]['current'] = True
            title = titles[0]
            realUrl = urls[0]
            duration = 0
        else:
            responseString = self.fetchWeb(self.url)
            realUrl = self.getVideoUrl()
            title = self.parseField(self.yinyuetai_title_pattern, responseString, 'title')
            duration = self.parseField(self.yinyuetai_duration_pattern, responseString, 'duration')
        return Video(title, self.url, realUrl, duration, self.site,
                     availableFormat=self.availableFormat, currentFormat=self.format,
                     previousVideo=previousVideo, nextVideo=nextVideo,
                     allRelatedVideo=allRelatedVideo, sections=sections)

    def parseWeb(self):
        logging.info("parseWeb %s", self.url)
        responseString = self.fetchWeb(self.url)
        logging.debug("Finish fetch web")
        replaces = [('a href="/', 'a href="/forward?site=%s&url=/' % self.site),
                    ('a href="http', 'a href="/forward?site=%s&url=http' % self.site)]
        return self.replaceResponse(responseString, replaces)


class KankanWebParser(WebParser):

    kankan_subid_pattern = re.compile("subid=(?P<subid>\d+)")
    kankan_movietitle_pattern = re.compile("var G_MOVIE_TITLE = '(?P<movietitle>.*?)';")
    kankan_subids_subnames_pattern = re.compile(r"var G_MOVIE_DATA = \{subids:\[(?P<subids>.*?)\],subnames:\[(?P<subnames>.*?)\]")
    kankan_duration_pattern = re.compile(r",length:(?P<duration>\d+),")
    kankan_url_replace = re.compile('a .*?href="(?P<url>.*?)"')

    def __init__(self, url, format):
        WebParser.__init__(self, 'kankan', url, format)

    def parse(self):
        if 'vod.kankan.com' in self.url or 'kankan.xunlei.com/vod' in self.url or\
                'yinyue.kankan.com/vod' in self.url:
            return self.parseVideo()
        else:
            return self.parseWeb()

    def parseVideo(self):
        logging.info("parseVideo %s", self.url)
        realUrl = self.getVideoUrl()
        if not realUrl:
            return "The video not existed. Please try another one."
        subid = self.parseField(self.kankan_subid_pattern, self.url, "subid")
        responseString = self.fetchWeb(self.url).decode('gbk', 'ignore').encode('utf8')
        title = self.parseField(self.kankan_movietitle_pattern, responseString, "movietitle")
        duration = self.parseField(self.kankan_duration_pattern, responseString, "duration")
        previousVideo, nextVideo, allRelatedVideo = None, None, []
        r = self.kankan_subids_subnames_pattern.search(responseString)
        if r:
            subids = r.group('subids')
            subnames = r.group('subnames')
            if subids and subnames:
                subids_list = subids.split(',')
                subnames_list = [v[1:-1] for v in subnames.split(',')]
                current = False
                if len(subids_list) > 1 and subid:
                    for idx, sid in enumerate(subids_list):
                        url = self.url.replace(subid, sid)
                        if current and not nextVideo:
                            nextVideo = url
                        t = subnames_list[idx]
                        if sid == subid:
                            allRelatedVideo.append({'title': t, 'url': url, 'current': True})
                            current = True
                            title += " " + t
                        else:
                            allRelatedVideo.append({'title': t, 'url': url, 'current': False})
                        if not current:
                            previousVideo = url
        sections = []
        return Video(title, self.url, realUrl, duration, self.site,
                     availableFormat=self.availableFormat, currentFormat=self.format,
                     previousVideo=previousVideo, nextVideo=nextVideo,
                     allRelatedVideo=allRelatedVideo, sections=sections)

    def parseWeb(self):
        logging.info("parseWeb %s", self.url)
        responseString = self.fetchWeb(self.url)
        logging.debug("Finish fetch web")
        replaces = [('document.domain="kankan.com";', ''),
                    ("document.domain = 'kankan.com';", ''),
                    ('src="http://misc.web.xunlei.com/data_dot_movie_content_new/js/main_v2.js',
                    'src="/forward?site=%s&url=http://misc.web.xunlei.com/data_dot_movie_content_new/js/main_v2.js' % self.site)]
        s = self.replaceResponse(responseString, replaces)
        return self.kankan_url_replace.sub(lambda m: m.group(0).replace(m.group('url'),
                                           '/forward?site=%s&url=%s' % (self.site, urllib2.quote(m.group('url')))), s)


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
        replaces = [(' href="http://', ' href="/forward?site=%s&url=http://' % self.site),
                    ('action="/results"', 'action="/forward?site=%s&url=http://www.youtube.com/results' % self.site),
                    (' href="/', ' href="/forward?site=%s&url=http://www.youtube.com/' % self.site)]
        skips = ['href="http://s.ytimg.com/']
        return self.replaceResponse(responseString, replaces, skips)
