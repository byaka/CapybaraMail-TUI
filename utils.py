#!/usr/bin/python3
import sys, os, re, code
import datetime
from datetime import timedelta

datetime_now=datetime.datetime.now
datetime_today=datetime.datetime.today

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
