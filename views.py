#!/usr/bin/python3
import sys, os, datetime, time

import urwid
from urwid import Columns, Pile, AttrWrap, ListBox, Text, Divider, Padding
from widgets import FiltersList, DialogList, AttrWrapEx

from utils import urwidEventBubbling, NULL, LINE_H, datetime, timedelta, datetime_now, datetime_today, to_date, to_datetime, Print2FIle
from dialogLoader import DialogLoader
from collections import defaultdict

urwidEventBubbling.monkey_patch()

class ViewBase(urwid.Frame):
   def __init__(self, apiExecutor, events=None):
      self.apiExecutor=apiExecutor
      self.childs=[]
      self._w_init()
      self._bind_events(events)
      self._bind_later_queue=defaultdict(list)
      super().__init__(self._w)

   def _w_init(self):
      self._w=None

   def reload(self):
      for o in self.childs:
         if hasattr(o, 'reload'): o.reload()

   def _bind_events(self, events):
      for k, f in events.items():
         w, ev=k.split('.', 1)
         assert hasattr(self, w)
         w=getattr(self, w)
         assert isinstance(w, urwid.Widget)
         urwidEventBubbling.connect_signal(w, ev, f)

   def _bind_events_later(self, ev):
      if ev not in self._bind_later_queue: return
      tArr=self._bind_later_queue.pop(ev)


class ViewMain(ViewBase):
   def _w_init(self):
      self.dialogLoader=DialogLoader(
         self.apiExecutor,
         'John Smith', None,
         dateStart='today', dateEnd=True, direction=-1,
         limitDates=5, limitResults=5,
      )

      self.dialogList=DialogList(self.dialogLoader)

      tArr={
         '#inbox': {'type':'main', 'name':'Inbox', 'descr':'Untagged dialogs'},
         '#backlog': {'type':'main', 'name':'Backlog', 'descr':'Todo tasks', 'count':10},
         '#notes': {'type':'main', 'name':'Notes', 'descr':'Useful info', 'count':2},
         '#custom1': {'type':'main', 'name':'Custom 1', 'descr':'Created by user', 'count':5},
         '#done': {'type':'more', 'name':'Done', 'descr':'Completed  tasks'},
         '#spam': {'type':'more', 'name':'Spam', 'descr':'Marked as spam'},
         '#all': {'type':'more', 'name':'All', 'descr':''},
         '#my1': {'type':'more', 'name':'My 1', 'descr':''},
         '#my2': {'type':'more', 'name':'My 2', 'descr':''},
      }

      self.filtersList=FiltersList(tArr)

      self._w=AttrWrap(Columns([
         ('weight', 2, self.filtersList),  # sidebar
         ('weight', 8, self.dialogList),  # wrapper
      ], 0), 'style0')
      self.childs+=[self.dialogList, self.filtersList]
