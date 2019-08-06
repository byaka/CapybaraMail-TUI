#!/usr/bin/python3
import sys, os, re, code, platform
import datetime
from datetime import timedelta
import urwid

NULL=object()

datetime_now=datetime.datetime.now
datetime_today=datetime.datetime.today

import gc, urwid

class UrwidEventBubbling:
   def __init__(self, original):
      self.original_supported=original._signals._supported
      self.original_connect=original._signals.connect
      self.original_emit=original._signals.emit

   def connect(self, obj, name, *args, **kwargs):
      sig_cls = obj.__class__
      old=self.original_supported.get(sig_cls, [])
      if name not in old:
         self.original_supported[sig_cls]=old+[name]
      result=self.original_connect(obj, name, *args, **kwargs)
      self.original_supported[sig_cls]=old
      return result

   def emit(self, obj, name, *args):
      result=self.original_emit(obj, name, *args)
      #find parents
      good1=(urwid.ListWalker, urwid.Widget, urwid.WidgetWrap)
      good2=(urwid.MonitoredList,)
      tQueue=[gc.get_referrers(obj)]
      while tQueue:
         for o in tQueue.pop():
            # if isinstance(o, good1+good2+(dict,)):
            #    print('~', type(o), o)
            if isinstance(o, good1):
               self.emit(o, name, *args)
            elif isinstance(o, good2) or (isinstance(o, dict) and ('_body' in o or '_original_widget' in o)):
               tQueue.append(gc.get_referrers(o))
      return result

   connect_signal=connect
   emit_signal=emit

class UrwidEventWrapper:
   def __init__(self):
      self._obj=None

   def connect(self, *args, **kwargs):
      if self._obj is None:
         raise RuntimeError('Not inited yet')
      return self._obj.connect(*args, **kwargs)

   def emit(self, *args, **kwargs):
      if self._obj is None:
         raise RuntimeError('Not inited yet')
      return self._obj.emit(*args, **kwargs)

   @staticmethod
   def monkey_patch():
      from urwid import signals as urwid_signals
      o=UrwidEventBubbling(urwid_signals)
      globals()['urwidEventBubbling']._obj=o
      urwid_signals.connect_signal=o.connect_signal
      urwid_signals.emit_signal=o.emit_signal

   connect_signal=connect
   emit_signal=emit

urwidEventBubbling=UrwidEventWrapper()

class ScreenFixed(urwid.raw_display.Screen):
   def write(self, data):
      if "Microsoft" in platform.platform():
         # replace urwid's SI/SO, which produce artifacts under WSL.
         # https://github.com/urwid/urwid/issues/264#issuecomment-358633735
         # Above link describes the change.
         data = re.sub("[\x0e\x0f]", "", data)
      super().write(data)

class MagicDict(dict):
   """
   Get and set values like in Javascript (dict.<key>).
   """
   def __getattr__(self, k):
      if k[:2]=='__': raise AttributeError(k)
      return self.__getitem__(k)

   __setattr__=dict.__setitem__
   __delattr__=dict.__delitem__
   __reduce__=dict.__reduce__

class Print2FIle(object):
   def __init__(self, path=None):
      self.path=path or os.path.join(os.path.dirname(sys.argv[0]), 'log.txt')
      self._file=open(self.path, 'wt', 1)

   def print(self, *args):
      msg=' '.join(f'{o}' for o in args)
      try:
         self._file.write(f'[{datetime.datetime.now()}] {msg}\n')
      except Exception as e:
         self._file.write(f'[{datetime.datetime.now()}] ERROR_LOGGING {e}\n')

def console_interact(scope=None, msg=None):
   if not sys.stdout.isatty():
      raise RuntimeError('Must be TTY')
   scope=(scope or {}).copy()
   def tFunc():
      raise SystemExit
   scope['exit']=tFunc
   try:
      code.interact(banner=msg, local=scope)
   except SystemExit: pass

def to_datetime(val):
   if isinstance(val, datetime.datetime):
      return val
   elif isinstance(val, datetime.date):
      return datetime.datetime.combine(val, datetime.datetime.min.time())
   elif isinstance(val, str):
      try:
         return datetime.datetime.strptime(val, '%Y-%m-%dT%H:%M:%S')
      except ValueError:
         try:
            return datetime.datetime.strptime(val, '%Y-%m-%d %H:%M:%S')
         except ValueError:
            return datetime.datetime.strptime(val, '%Y-%m-%d')
   elif isinstance(val, int):
      return datetime.datetime.fromtimestamp(val)
   raise ValueError

def to_date(val):
   return to_datetime(val).date()

LINE_H='―'
LINE_V='|'
