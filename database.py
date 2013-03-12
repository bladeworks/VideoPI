#!/usr/bin/python
# -*- coding: utf8 -*-
from webparser import Video
import sqlite3
import time
import logging
#CREATE TABLE media(id INTEGER PRIMARY KEY, title TEXT NOT NULL, url TEXT NOT NULL, last_play_date INTEGER, last_play_pos INTEGER, duration INTEGER, site TEXT)


def db_getHistory():
    con = sqlite3.connect('media.db')
    con.row_factory = sqlite3.Row
    with con:
        c = con.cursor()
        c.execute("SELECT * \
            FROM media order by last_play_date desc LIMIT 5")
        data = c.fetchall()
        videos = []
        for d in data:
            videos.append(Video(str(d['title']), str(d['url']), '', d['duration'], d['site'], dbid=d['id']))
        return videos


def db_writeHistory(video):
    con = sqlite3.connect('media.db')
    logging.debug("Write: %s", video)
    with con:
        if video.dbid:
            if video.progress > 0:
                logging.debug("set last_play_pos = %s for %s", video.progress, video.dbid)
                con.execute("""
                    UPDATE media SET last_play_pos = ?, last_play_date = ? WHERE id = ?
                    """, (video.progress, int(time.time()), video.dbid,))
            else:
                con.execute("""
                    UPDATE media SET last_play_date = ? WHERE id = ?
                    """, (int(time.time()), video.dbid,))
        else:
            con.execute("""
                INSERT INTO media (title, url, last_play_date, last_play_pos, duration, site)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (buffer(video.title), buffer(video.url), int(time.time()), 0, video.duration, video.site))
        con.commit()


def db_getById(id):
    con = sqlite3.connect('media.db')
    con.row_factory = sqlite3.Row
    with con:
        cur = con.cursor()
        cur.execute("SELECT * FROM media WHERE id = ?", [id])
        data = cur.fetchone()
        return Video(str(data['title']), str(data['url']), '', data['duration'], data['site'],
                     dbid=data['id'], progress=int(data['last_play_pos']))


def db_delete(id):
    logging.debug("Delete %s", id)
    con = sqlite3.connect('media.db')
    with con:
        if id == -1:
            # Delete all
            con.execute("DELETE FROM media")
        else:
            con.execute("DELETE FROM media WHERE id = ?", [id])
        con.commit()
