#!/usr/bin/python3
import sys, os, datetime
import traceback

from utils import NULL, datetime, timedelta, datetime_now, datetime_today, to_date, to_datetime

class ApiExecutorError(Exception):
   def __init__(self, code, msg=None):
      super().__init__(code)
      self.code=code
      self.msg=msg

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

   @classmethod
   def parseResponse(cls, resp):
      try:
         code=resp.get('code', NULL)
         data=resp.get('data', NULL)
         assert code is not NULL
         if code is not True and data is not NULL:
            raise ApiExecutorError(code, data)
         assert code is True
      except ApiExecutorError as e:
         print(f'Error on apiExecutor with code `{e.code}`:\n{e.msg}')
         raise
      except Exception:
         print(f'Error while processing response:\n{resp}\n{"-"*30}\n{traceback.format_exc()}')
         raise
      return data

   def _load(self):
      p=dict(
         self.__params,
         dates=(self._dateStart,self._dateStep, self._dateEnd),
         asDialogs=True,
         returnFull=True,
         onlyCount=False,
         returnNextDates=True,
      )
      return self.parseResponse(self._apiExecutor.filterMessages(**p))

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
