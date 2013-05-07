#!/usr/bin/python
# -*- coding: utf8 -*-
from webparser import *

websites = {
    "qq": {
        "title": "腾讯视频(flv)",
        "url": "http://v.qq.com",
        "parser": QQWebParser,
        "icon": "/static/img/favicon/qq.ico",
        "info": "flv格式，不分段，但不能选择清晰度。",
        "merge": True
    },
    "qqmp4": {
        "title": "腾讯视频(分段)",
        "url": "http://v.qq.com",
        "parser": QQWebParserMP4,
        "icon": "/static/img/favicon/qq.ico",
        "info": "分段，可选择清晰度。"
    },
    "youku": {
        "title": "优酷视频(推荐)",
        "url": "http://www.youku.com",
        "parser": YoukuWebParser,
        "icon": "/static/img/favicon/youku.ico",
        "info": "不分段，可选择清晰度。",
        "merge": True
    },
    "wangyi": {
        "title": "网易公开课",
        "url": "http://open.163.com",
        "parser": WangyiWebParser,
        "icon": "/static/img/favicon/wangyi.ico",
        "info": "不分段",
        "merge": True
    },
    "yinyuetai": {
        "title": "音悦台",
        "url": "http://www.yinyuetai.com",
        "parser": YinyuetaiWebParser,
        "icon": "/static/img/favicon/yinyuetai.ico",
        "info": "Nothing"
    },
    "kankan": {
        "title": "迅雷看看",
        "url": "http://www.kankan.com",
        "parser": KankanWebParser,
        "icon": "/static/img/favicon/kankan.ico",
        "info": "Nothing",
        "merge": True
    },
    "youtube": {
        "title": "Youtube",
        "url": "http://www.youtube.com",
        "parser": YoutubeWebParser,
        "icon": "/static/img/favicon/youtube.ico",
        "info": "Nothing"
    },
    "sohu": {
        "title": "搜狐视频",
        "url": "http://tv.sohu.com",
        "parser": SohuWebParser,
        "icon": "/static/img/favicon/sohu.ico",
        "info": "",
        "merge": True,
        "startSupport": True
    }
}

# actionToKey = {
#     'pause': 'p',
#     'stop': 'q',
#     'volup': '+',
#     'voldown': '-',
#     'f30': '\x1B[D',
#     'b30': '\x1B[C',
#     'f600': '\x1B[A',
#     'b600': '\x1B[B',
#     'showinfo': 'z',
#     'speedup': '1',
#     'speeddown': '2',
#     'togglesub': 's',
# }

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

# actionToKeyMac = {
#     'MPlayerX':
#     {
#         'pause': '49',
#         'stop': '12 using command down',
#         'volup': '24',
#         'voldown': '27',
#         'fullscreen': '3',
#     },
#     'VLC':
#     {
#         'pause': '49',
#         'stop': '12 using command down',
#         'volup': '126 using command down',
#         'voldown': '125 using command down',
#         'fullscreen': '3 using command down',
#     }
# }

