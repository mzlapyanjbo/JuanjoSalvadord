#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos2d "compile" plugin
#
# Copyright 2013 (C) Luis Parravicini
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"compile" plugin for cocos2d command line tool
'''

__docformat__ = 'restructuredtext'

import sys
import os
import json
import inspect

import cocos2d

class CCPluginCompile(cocos2d.CCPlugin):
    """
    compiles a project
    """

    @staticmethod
    def plugin_name():
      return "compile"

    @staticmethod
    def brief_description():
        return "compiles a project in debug mode"

    def build_android(self):
        project_dir = self._platforms.android_path
        if project_dir is None:
            return

        cocos2d.Logging.info("building native")
        self._run_cmd("cd \"%s\" && ./build_native.sh" % project_dir)
        cocos2d.Logging.info("building apk")
        self._run_cmd("cd \"%s\" && ant debug" % project_dir)

    def build_ios(self):
        project_dir = self._platforms.ios_path
        if project_dir is None:
            return
        #TODO do it

    def run(self, argv):
        self.parse_args(argv)
        self.build_android()
        self.build_ios()
