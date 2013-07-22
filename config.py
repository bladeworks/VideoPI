#!/usr/bin/python
# -*- coding: utf8 -*-

import os
from configobj import ConfigObj

DEFAULT_CFG = os.path.join(os.path.dirname(__file__), "default.cfg")
USER_CFG = os.path.join(os.path.dirname(__file__), "user.cfg")

defaultCfg = ConfigObj(DEFAULT_CFG)
userCfg = None
if os.path.isfile(USER_CFG):
	userCfg = ConfigObj(USER_CFG)

def get_cfg(name):
	if userCfg and userCfg[name]:
		return userCfg[name]
	else:
		return defaultCfg[name]
