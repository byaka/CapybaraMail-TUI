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
   def __init__(self, apiExecutor, config, events=None):
      self.inited=False
      self.apiExecutor=apiExecutor
      self.config=config
      self.childs=[]
      self._w_init()
      self.inited=True
      self._bind_events(events)
      self._bind_later_queue=defaultdict(list)
      super().__init__(self._w)

   def _w_init(self):
      self._w=getattr(self, '_w', None)

   def refresh(self):
      for o in self.childs:
         if hasattr(o, 'refresh'): o.refresh()

   def _bind_events(self, events):
      for k, f in events.items():
         w, ev=k.split('.', 1)
         assert hasattr(self, w)
         w=getattr(self, w)
         assert isinstance(w, urwid.Widget)
         urwidEventBubbling.connect_signal(w, ev, f)

   def _bind_events_later(self, ev):
      #? был нужен когда небыло всплытия событий, нужен ли сейчас?
      # if ev not in self._bind_later_queue: return
      # tArr=self._bind_later_queue.pop(ev)
      pass

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
   def loadData(self):
      pass

   def _w_init(self):
      self.dialogLoader=DialogLoader(
         self.apiExecutor,
         self.config.user, query=None,
         dateStart='today', dateEnd=True, direction=-1,
         limitDates=5, limitResults=5,
      )
      self.dialogs=DialogList(self.dialogLoader)

      self.sidebar_filters=FiltersList({
         k:dict(v, type=v['type'].split('.', 1)[1]) for k,v in self.config.filters.items()
         if v['type'].startswith('sidebar.')
      })

      self._w=AttrWrap(Columns([
         ('weight', 2, self.sidebar_filters),  # sidebar
         ('weight', 8, self.dialogs),  # wrapper
      ], 0), 'style0')
      self.childs+=[self.dialogs, self.sidebar_filters]
      #! в будущем эта карта будет модифицироваться при смене фокуса, таким образом горячие клавиши будут контекстными
      self.hotkeys({
         'f2':('One', self.hk_test_f1),
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

   def setFilters(self, data):
      self.sidebar_filters.data=data
      self.sidebarFilters.refresh()

   def hk_test_f1(self, name):
      print('$', name, self.dialogs.focus.data[0]['dialogId'])
