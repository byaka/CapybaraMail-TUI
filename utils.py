#!/usr/bin/python3
import sys, os, re, code, platform
import datetime
from datetime import timedelta
import urwid

NULL=object()

datetime_now=datetime.datetime.now
datetime_today=datetime.datetime.today

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
