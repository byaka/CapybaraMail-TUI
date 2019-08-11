#!/usr/bin/python3
import sys, os, datetime, time

import urwid

from utils import urwidEventBubbling, ScreenFixed, MagicDict, NULL, datetime, timedelta, datetime_now, datetime_today, to_date, to_datetime, Print2FIle

import jsonrpc_requests

from views import ViewMain

THEME = [
   ('style0', '', '', '', 'g3', '#eef'),
   ('style1', '', '', '', 'g85', '#866'),
   ('style1-reverse', '', '', '', 'g85,bold', '#a88'),
   ('style1bold', '', '', '', 'g85,bold', '#866'),
   ('style1-focus', '', '', '', 'g85', '#888'),
   ('style1-select', '', '', '', 'g85,bold', '#68d'),
   ('style2', '', '', '', 'g70', '#866'),
   ('style2-focus', '', '', '', 'g70', '#888'),
   ('style2-select', '', '', '', 'g70,bold', '#68d'),
   ('style3', '', '', '', 'g3', 'g85'),
   ('style3-striped', '', '', '', 'g3', 'g93'),
   ('style3-focus', '', '', '', 'g85', '#68d'),
   ('style3bold', '', '', '', 'bold,g3', 'g85'),
   ('style3bold-focus', '', '', '', 'bold,g85', '#68d'),
   ('style4', '', '', '', 'g40', 'g85'),
   ('style4-striped', '', '', '', 'g40', 'g93'),
   ('style4-focus', '', '', '', 'g40', '#68d'),
   ('style4bold', '', '', '', 'bold,g40', 'g85'),
   ('style4bold-striped', '', '', '', 'bold,g40', 'g93'),
   ('style4bold-focus', '', '', '', 'bold,g40', '#68d'),
   ('style5', '', '', '', '#880', 'g85'),
   ('style5-striped', '', '', '', '#880', 'g93'),
   ('style5-focus', '', '', '', '#da6', '#68d'),
   ('style5bold', '', '', '', 'bold,#880', 'g85'),
   ('style5bold-striped', '', '', '', 'bold,#880', 'g93'),
   ('style5bold-focus', '', '', '', 'bold,#da6', '#68d'),
   ('incoming', '', '', '', 'bold,g100', '#86d'),
   ('outgoing', '', '', '', 'bold,g100', '#6a6'),
   ('unread', '', '', '', '#880', '#a06'),
]

class ControllerBase(object):
   def __init__(self, config, theme):
      self.config=config
      urwid.set_encoding("UTF-8")
      self.apiExecutor=jsonrpc_requests.Server(self.config.api)
      self.views=MagicDict()
      self.views.empty=urwid.Frame(urwid.SolidFill())
      self.screenObj=ScreenFixed()
      self.screenObj.set_terminal_properties(colors=256)
      self.screenObj.reset_default_terminal_palette()
      self.screenObj.register_palette(theme)
      self._init()

   def setView(self, view=None):
      view=view or 'empty'
      assert view in self.views
      self.loopUrwid.widget=self.views[view]

   def run(self):
      self.loop=urwid.AsyncioEventLoop()
      self.loopUrwid=urwid.MainLoop(
         self.views.empty,
         screen=self.screenObj,
         unhandled_input=self.cb_keyboardUnhandled,
         handle_mouse=True,
         pop_ups=True,
         event_loop=self.loop
      )
      self.setView(self.config.defaultView)
      self.loopUrwid.run()

   def cb_keyboardUnhandled(self, data, raw=None):
      if 'q' in data or 'Q' in data: raise urwid.ExitMainLoop()
      return []

class ControllerMain(ControllerBase):
   def _init(self):
      self.views.main=ViewMain(self.apiExecutor, self.config, events={
         'sidebar_filters.select': self.cb_filtersList_select,
         'dialogs.open': self.cb_dialogList_open,
         'dialogs.close': self.cb_dialogList_close,
      })

   def cb_dialogList_open(self, w, *args):
      pass

   def cb_dialogList_close(self, w, *args):
      pass

   def cb_filtersList_select(self, w, *args):
      print('SELECT', w)


if __name__ == '__main__':
   import builtins
   p2f=Print2FIle()
   builtins.print=p2f.print

   CONFIG=MagicDict({
      'user':'John Smith',
      'api':'http://localhost:7001/api',
      'defaultView':'main',
      'filters':{
         '#inbox': {'type':'sidebar.main', 'name':'Inbox', 'descr':'Untagged dialogs'},
         '#backlog': {'type':'sidebar.main', 'name':'Backlog', 'descr':'Todo tasks'},
         '#notes': {'type':'sidebar.main', 'name':'Notes', 'descr':'Useful info'},
         '#custom1': {'type':'sidebar.main', 'name':'Custom 1', 'descr':'Created by user'},
         '#done': {'type':'sidebar.more', 'name':'Done', 'descr':'Completed  tasks'},
         '#spam': {'type':'sidebar.more', 'name':'Spam', 'descr':'Marked as spam'},
         '#all': {'type':'sidebar.more', 'name':'All', 'descr':''},
         '#my1': {'type':'sidebar.more', 'name':'My 1', 'descr':''},
         '#my2': {'type':'sidebar.more', 'name':'My 2', 'descr':''},
      }

   })

   ControllerMain(CONFIG, THEME).run()
