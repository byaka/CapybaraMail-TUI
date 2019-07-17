#!/usr/bin/python3
import sys, os, datetime

import urwid
import urwid.raw_display
from urwid import Columns, Pile, AttrWrap, ListBox, Text, RadioButton, Divider, Padding, Button
from widgets import DialogHeader, FilterItem

urwid.set_encoding("UTF-8")

from utils import LINE_H, datetime, timedelta, datetime_now, datetime_today

class DialogLoader(object):
   def __init__(self, apiCaller, login, query, dateStart='today', dateEnd=True, direction=1, limitDates=5, limitResults=5):
      assert dateStep
      assert direction==1 or direction==-1
      self.__params=locals()
      self.__params.pop('self')
      self.__params.pop('apiCaller')
      self.__params.pop('direction')
      self._dateStep=self.__params['dateStep']=direction
      self._loaded=False
      self.__cache={}
      self._firstDate=None
      self._lastDate=None
      self._apiCaller=apiCaller
      self._canAutoStop=self._check_canAutoStop(self.__params['dateEnd'])
      self._ended=False

   @staticmethod
   def _check_canAutoStop(dateEnd):
      s=dateEnd
      if s is True or s is False or s is None: return False
      return True

   @staticmethod
   def _conv_date(date):
      if isinstance(date, (datetime.datetime, datetime.date)):
         return date
      elif isinstance(date, str):
         return datetime.strptime(date, '%Y%m%d')
      elif isinstance(date, int):
         return datetime.date.fromtimestamp(date)
      raise ValueError

   def _load(self):
      p=dict(self.__params, asDialogs=True, returnFull=True, onlyCount=False)
      return self._apiCaller.filterMessages(**p)

   def isLoaded(self):
      return self._loaded

   def isEnded(self):
      return self._ended

   def dateWasLoaded(self, date):
      if not self._loaded:
         raise RuntimeError('Data not loaded yet')
      date=self._conv_date(date)
      if self._dateStep>0:
         if date>=self._firstDate and date<=self._lastDate: return True
      else:
         if date<=self._firstDate and date>=self._lastDate: return True
      return False

   def load(self):
      if self._ended:
         return False, False
      data, targets=self._load()
      if not targets:
         self._ended=True
         return False, False
      self.__cache.update(data)
      dateLast=self._lastDate=self._conv_date(data[-1][0])
      if self._firstDate is None:
         self._firstDate=self._conv_date(data[0][0])
      self._loaded=True
      if self._canAutoStop:
         dateEnd=self._conv_date(self.__params['dateEnd'])
         dateStep=timedelta(days=self._dateStep)
         dateStart=dateLast+dateStep
         if self._dateStep>0 and dateStart>dateEnd:
            self._ended=True
         elif self._dateStep<0 and dateStart<dateEnd:
            self._ended=True
         else:
            self.__params['dateStart']=dateStart.strftime('%Y%m%d')
      return data, targets

   def __iter__(self):
      while True:
         data, targets=self.load()
         if data is False:
            raise StopIteration
         yield data, targets

   def get(self, date, direction):
      assert direction==1 or direction==-1
      if date in self.__cache:
         return date, self.__cache[date]
      date=self._conv_date(date)
      if self.dateWasLoaded(date):
         d=timedelta(days=direction)
         while True:
            date+=d
            dateS=date.strftime('%Y%m%d')
            if dateS in self.__cache:
               return dateS, self.__cache[dateS]
      else:
         if direction==self._dateStep:
            data, targets=self.load()
            return (False, False) if targets is False else data[0]
         else:
            #~ если дата крайняя и направление не совпадает с исходным
            pass


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

class DialogList(urwid.SimpleFocusListWalker):
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

   def __init__(self):
      self.screen=urwid.raw_display.Screen()
      self.screen.set_terminal_properties(colors=256)
      self.screen.reset_default_terminal_palette()
      self.screen.register_palette(self.palette)

      self.layout=AttrWrap(Columns([
         ('weight', 2, AttrWrap(Pile([
            ListBox(FiltersList()),
         ]), 'style1', 'style1')),  # sidebar
         ('weight', 8, Pile([
            ListBox(DialogList()),
         ])),  # wrapper
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
   ScreenMain().run()
