#!/usr/bin/python
# -*- coding: utf8 -*-

# zoom
zoom = 1.0

# 1为普清，2为高清，3为超清, 4为原画
default_format = 4

# 播放历史记录时往前进多少秒以便回忆
advanceTime = 30

# 日志存放位置
logStorage = "/tmp/videopi.log"

# playlist.m3u
playlistStorage = "/tmp/playlist.m3u"

# additonal omxplayer args for omxplayer
additonal_omxplayer_args = "--audio_queue=10 --video_queue=40 --audio_fifo=30 --video_fifo=10"

# database
dbStorage = "media.db"

# if download to local
download_to_local = False

# download file, only used if download_to_local is True
download_file = "/download/all.ts"

# download_cache_size, only used if download_to_local is True
download_cache_size = 5242880
