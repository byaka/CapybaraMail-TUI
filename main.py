#!/usr/bin/python3
import sys, os, datetime

import urwid
import urwid.raw_display
from urwid import Columns, Pile, AttrWrap, ListBox, Text, Divider, Padding
from widgets import DialogHeader, FilterItem, DialogList

urwid.set_encoding("UTF-8")

from utils import NULL, LINE_H, datetime, timedelta, datetime_now, datetime_today, to_date, to_datetime, Print2FIle

from dialogLoader import DialogLoader

class FiltersList(urwid.SimpleFocusListWalker):
   def __init__(self):
      data=[
         FilterItem('#inbox', {'name':'Inbox', 'descr':'Untagged dialogs'}),
         FilterItem('#backlog', {'name':'Backlog', 'descr':'Todo tasks'}),
         FilterItem('#notes', {'name':'Notes', 'descr':'Useful info'}),
         FilterItem('#custom1', {'name':'Custom 1', 'descr':'Created by user'}),
         Text('Filters:', align='center', wrap='space'),
         FilterItem('#done', {'name':'Done', 'descr':'Completed  tasks'}, showCounter=False),
         FilterItem('#spam', {'name':'Spam', 'descr':'Marked as spam'}),
         FilterItem('#all', {'name':'All', 'descr':''}, showCounter=False, showDescr=False),
         FilterItem('#my1', {'name':'My 1', 'descr':''}, showCounter=False, showDescr=False),
         FilterItem('#my2', {'name':'My 2', 'descr':''}, showCounter=False, showDescr=False),
         Divider(LINE_H),
      ]
      super().__init__(data)

class DialogWalkerDummy(urwid.SimpleFocusListWalker):
   def __init__(self):
      data=[
         DialogHeader('d1', [
            {'id':'m1', 'isIncoming':True, 'from':'user1@mail.ru', 'to':['byaka.life@gmail.com', 'user2@mail.ru'], 'cc':None, 'bcc':None, 'subject':'Some message 1', 'timestamp':datetime_now()-timedelta(days=1), 'bodyPlain':'Some text 1', 'bodyHtml':'', 'attachments':[], 'labels':('#favorite',)},
            {'id':'m1', 'isIncoming':False, 'from':'user1@mail.ru', 'to':['byaka.life@gmail.com', 'user2@mail.ru'], 'cc':None, 'bcc':None, 'subject':'Some message 1', 'timestamp':datetime_now()-timedelta(days=1), 'bodyPlain':'Some text 1', 'bodyHtml':'', 'attachments':[], 'labels':('#favorite',)},
            {'id':'m1', 'isIncoming':True, 'from':'user1@mail.ru', 'to':['byaka.life@gmail.com', 'user2@mail.ru'], 'cc':None, 'bcc':None, 'subject':'Some message 1', 'timestamp':datetime_now()-timedelta(days=1), 'bodyPlain':'Some text 1', 'bodyHtml':'', 'attachments':[], 'labels':('#favorite',)},
         ]),
         DialogHeader('d2', [
            {'id':'m2', 'isIncoming':False, 'from':'user1@mail.ru', 'to':['byaka.life@gmail.com', 'user2@mail.ru'], 'cc':None, 'bcc':None, 'subject':'Some message 2', 'timestamp':datetime_now()-timedelta(days=1), 'bodyPlain':'Some text 2', 'bodyHtml':'', 'attachments':[], 'labels':('#unread',)},
         ]),

      ]
      super().__init__(data)

class ScreenMain(object):
   palette = [
      ('body', '', '', '', 'g3', '#eef'),
      ('style1', '', '', '', 'g85', '#866'),
      ('style1-focus', '', '', '', 'g85', '#888'),
      ('style1-select', '', '', '', 'g85,bold', '#68d'),
      ('style2', '', '', '', 'g70', '#866'),
      ('style2-focus', '', '', '', 'g70', '#888'),
      ('style2-select', '', '', '', 'g70,bold', '#68d'),
      ('style3', '', '', '', 'g3', '#ddf'),
      ('style3-focus', '', '', '', 'g85', '#68d'),
      ('style3bold', '', '', '', 'bold,g3', '#ddf'),
      ('style3bold-focus', '', '', '', 'bold,g85', '#68d'),
      ('style4', '', '', '', 'g40', '#ddf'),
      ('style4-focus', '', '', '', 'g40', '#68d'),
      ('style4bold', '', '', '', 'bold,g40', '#ddf'),
      ('style4bold-focus', '', '', '', 'bold,g40', '#68d'),
      ('style5', '', '', '', '#880', '#ddf'),
      ('style5-focus', '', '', '', '#da6', '#68d'),
      ('style5bold', '', '', '', 'bold,#880', '#ddf'),
      ('style5bold-focus', '', '', '', 'bold,#da6', '#68d'),
      ('incoming', '', '', '', 'bold,g100', '#86d'),
      ('outgoing', '', '', '', 'bold,g100', '#6a6'),
      ('unread', '', '', '', '#880', '#a06'),
   ]

   def __init__(self, apiExecutor):
      self.apiExecutor=apiExecutor

      self.screen=urwid.raw_display.Screen()
      self.screen.set_terminal_properties(colors=256)
      self.screen.reset_default_terminal_palette()
      self.screen.register_palette(self.palette)

      self._dialogList=DialogList(DialogLoader(
         self.apiExecutor,
         'John Smith', None,
         dateStart='today', dateEnd=True, direction=-1,
         limitDates=5, limitResults=5,
      ))
      # self._dialogList=ListBox(DialogWalkerDummy())

      self.layout=AttrWrap(Columns([
         ('weight', 2, AttrWrap(ListBox(FiltersList()), 'style1', 'style1')),  # sidebar
         ('weight', 8, self._dialogList),  # wrapper
      ], 0), 'body')

      self.layout.set_focus_column(0)
      self.layout=urwid.Frame(self.layout)

   def run(self):
      self.loop=urwid.MainLoop(self.layout, screen=self.screen, unhandled_input=self.input)
      self.loop.run()

   def input(self, input, raw_input=None):
      if 'q' in input or 'Q' in input: raise urwid.ExitMainLoop()
      return []


if __name__ == '__main__':
   import builtins
   p2f=Print2FIle()
   builtins.print=p2f.print

   from jsonrpc_requests import Server
   apiExecutor=Server('http://localhost:7001/api')
   ScreenMain(apiExecutor).run()
