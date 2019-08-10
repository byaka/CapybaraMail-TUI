#!/usr/bin/python3
import sys, os, datetime, time

import urwid
from urwid import Columns, Pile, AttrWrap, ListBox, Text, Divider, Padding
from widgets import FiltersList, DialogList, AttrWrapEx, HotkeyBar

from utils import urwidEventBubbling, NULL, LINE_H, datetime, timedelta, datetime_now, datetime_today, to_date, to_datetime, Print2FIle
from dialogLoader import DialogLoader
from collections import defaultdict

urwidEventBubbling.monkey_patch()

class ViewBase(urwid.Frame):
   def __init__(self, apiExecutor, events=None):
      self.inited=False
      self.apiExecutor=apiExecutor
      self.childs=[]
      self._w_init()
      self.inited=True
      self._bind_events(events)
      self._bind_later_queue=defaultdict(list)
      super().__init__(self._w)

   def _w_init(self):
      self._w=getattr(self, '_w', None)

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
      #? был нужен когда небыло всплытия событий, нужен ли сейчас?
      if ev not in self._bind_later_queue: return
      tArr=self._bind_later_queue.pop(ev)

   def keypress(self, size, key):
      return super().keypress(size, key)

class ViewWithHotkeys(ViewBase):
   def _w_init(self):
      self._keyMap=getattr(self, '_keyMap', {})
      self._w_hotkeybar=HotkeyBar(self._keyMap)
      self._w=urwid.Frame(self._w, footer=self._w_hotkeybar)
      super()._w_init()

   def hotkeys(self, keyMap=None):
      self._keyMap=keyMap
      if self.inited:
         self._w_hotkeybar.refresh()

   def keypress(self, size, key):
      if self._w_hotkeybar.keypress(size, key) is None: return
      return super().keypress(size, key)

class ViewMain(ViewWithHotkeys):
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
      #! в будущем эта карта будет модифицироваться при смене фокуса, таким образом горячие клавиши будут контекстными
      self.hotkeys({
         'f2':('One', lambda *_: print('HK-1')),
         'D':('Three', lambda *_: print('HK-SHIFT-D')),
         'ctrl d':('FourFive', lambda *_: print('HK-CTRL-D')),
         'meta d':('FourFive', lambda *_: print('HK-ALT-D')),
         'enter':('FourFive', lambda *_: print('HK-ENTER')),
         'm':('Move to', {
            '1':('One', lambda *_: print('HK-M,1')),
            '2':('Two', lambda *_: print('HK-M,2')),
            '3':('Three', lambda *_: print('HK-M,3')),
         }),
      })
      super()._w_init()
