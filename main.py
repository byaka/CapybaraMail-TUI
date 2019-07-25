#!/usr/bin/python3
import sys, os, datetime

import urwid
import urwid.raw_display
from urwid import Columns, Pile, AttrWrap, ListBox, Text, RadioButton, Divider, Padding, Button
from widgets import DialogHeader, FilterItem, DialogList

urwid.set_encoding("UTF-8")

from utils import LINE_H, datetime, timedelta, datetime_now, datetime_today, to_date, to_datetime, Print2FIle

class DialogLoader(object):
   def __init__(self, apiExecutor, login, query, dateStart='today', dateEnd=True, direction=-1, limitDates=5, limitResults=5):
      assert direction==1 or direction==-1
      self._dateStart=dateStart
      self._dateEnd=dateEnd
      self._dateStep=direction
      self.__params={
         'login':login,
         'query':query,
         'limitDates':limitDates,
         'limitResults':limitResults,
      }
      self._loaded=False
      self.__cache={}
      self._firstDate=None
      self._lastDate=None
      self._apiExecutor=apiExecutor
      self._ended=False

   direction=property(lambda self: self._dateStep)

   def _load(self):
      p=dict(
         self.__params,
         dates=(self._dateStart,self._dateStep, self._dateEnd),
         asDialogs=True,
         returnFull=True,
         onlyCount=False,
         returnNextDates=True,
      )
      r=self._apiExecutor.filterMessages(**p)
      assert r.get('code', False) is True
      assert r.get('data', None)
      return r['data']

   def isLoaded(self):
      return self._loaded

   def isEnded(self):
      return self._ended

   def dateWasLoaded(self, date):
      if not self._loaded:
         raise RuntimeError('Data not loaded yet')
      if date is None:
         return True
      date=to_date(date)
      if self._dateStep>0:
         if date>=self._firstDate and date<=self._lastDate: return True
      else:
         if date<=self._firstDate and date>=self._lastDate: return True
      return False

   def load(self):
      if self._ended:
         return False, False
      data, targets, nextDates=self._load()
      if not targets:
         self._ended=True
         return False, False
      self.__cache.update(data)
      if self._firstDate is None:
         self._firstDate=to_date(data[0][0])
      self._lastDate=to_date(data[-1][0])
      self._loaded=True
      if not nextDates:
         self._ended=True
      else:
         self._dateStart=nextDates[0]
      return data, targets

   def __iter__(self):
      while True:
         data, targets=self.load()
         if data is False:
            raise StopIteration
         yield data, targets

   def _get_nearest(self, dateStr, dateObj, direction):
      # you must call this method only if you sure that requested date pass `self.dateWasLoaded`
      if not self._loaded:
         raise RuntimeError('Data not loaded yet')
      if dateStr in self.__cache:
         return dateStr, self.__cache[dateStr]
      # this date have no data, so we swith it to next\prev with results
      d=timedelta(days=direction)
      while True:
         dateObj+=d
         dateStr=dateObj.strftime('%Y-%m-%d')
         if dateStr in self.__cache:
            return dateStr, self.__cache[dateStr]

   def get(self, date, direction):
      assert direction==1 or direction==-1
      if not self._loaded:
         raise RuntimeError('Data not loaded yet')
      if date is None:
         # requested first availible date
         date=self._firstDate.strftime('%Y-%m-%d')
         return date, self.__cache[date]
      elif date in self.__cache:
         return date, self.__cache[date]
      dateObj=to_date(date)
      if self.dateWasLoaded(dateObj):
         # requested date in loaded range
         return self._get_nearest(date, dateObj, direction)
      elif direction!=self._dateStep:
         # requested opposite direction so no point to load next data
         return False, False
      else:
         # data for this date not loaded yet
         while True:
            data, targets=self.load()
            if targets is False:
               # search ended
               return False, False
            elif date in self.__cache:
               return date, self.__cache[date]
            elif self.dateWasLoaded(dateObj):
               # requested date in loaded range
               return self._get_nearest(date, dateObj, direction)

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

# class DialogList(urwid.SimpleFocusListWalker):
#    def __init__(self):
#       data=[
#          DialogHeader('d1', [
#             {'id':'m1', 'isIncoming':True, 'from':'user1@mail.ru', 'to':['byaka.life@gmail.com', 'user2@mail.ru'], 'cc':None, 'bcc':None, 'subject':'Some message 1', 'timestamp':datetime_now()-timedelta(days=1), 'bodyPlain':'Some text 1', 'bodyHtml':'', 'attachments':[], 'labels':('#favorite',)},
#             {'id':'m1', 'isIncoming':False, 'from':'user1@mail.ru', 'to':['byaka.life@gmail.com', 'user2@mail.ru'], 'cc':None, 'bcc':None, 'subject':'Some message 1', 'timestamp':datetime_now()-timedelta(days=1), 'bodyPlain':'Some text 1', 'bodyHtml':'', 'attachments':[], 'labels':('#favorite',)},
#             {'id':'m1', 'isIncoming':True, 'from':'user1@mail.ru', 'to':['byaka.life@gmail.com', 'user2@mail.ru'], 'cc':None, 'bcc':None, 'subject':'Some message 1', 'timestamp':datetime_now()-timedelta(days=1), 'bodyPlain':'Some text 1', 'bodyHtml':'', 'attachments':[], 'labels':('#favorite',)},
#          ]),
#          DialogHeader('d2', [
#             {'id':'m2', 'isIncoming':False, 'from':'user1@mail.ru', 'to':['byaka.life@gmail.com', 'user2@mail.ru'], 'cc':None, 'bcc':None, 'subject':'Some message 2', 'timestamp':datetime_now()-timedelta(days=1), 'bodyPlain':'Some text 2', 'bodyHtml':'', 'attachments':[], 'labels':('#unread',)},
#          ]),

#       ]
#       super().__init__(data)

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
         'John Smith', {'or':[
            {'key':'from', 'value':'mail@ajon.ru', 'match':'=='},
            # {'key':'label', 'value':u'черновики', 'match':'=='},
         ]},
         dateStart='today', dateEnd=True, direction=-1,
         limitDates=5, limitResults=5,
      ))

      # self.layout=AttrWrap(Columns([
      #    ('weight', 2, AttrWrap(Pile([
      #       ListBox(FiltersList()),
      #    ]), 'style1', 'style1')),  # sidebar
      #    ('weight', 8, Pile([
      #       ListBox(self._dialogWalker),
      #    ])),  # wrapper
      # ], 0), 'body')

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
