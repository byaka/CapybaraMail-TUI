#!/usr/bin/python3

import sys, os, re
import weakref

import urwid
from urwid import WidgetWrap, Pile, Columns, Text, Padding, AttrWrap, SelectableIcon, Divider, WidgetPlaceholder, WidgetDisable, SolidFill, Filler, BoxAdapter, Frame
from urwid.command_map import ACTIVATE
from urwid.util import is_mouse_press

from utils import LINE_H, datetime, timedelta, datetime_now, datetime_today

class TextFocusable(Text):
   """
   Just selectable version of `Text` widget, but without cursor like in `SelectableIcon`.
   """
   _selectable=True
   def keypress(self, size, key): return key

   def mouse_event(self, size, event, button, x, y, focus): return True

class AttrWrapEx(AttrWrap):
   def __init__(self, w, *attrs):
      assert attrs
      self._original_map=list(attrs)
      self.__super.__init__(w, attrs[0], focus_attr=(attrs[1] if len(attrs)>1 else None))

_FILTERS_GROUP={}

class FocusableWidget(WidgetWrap):
   def selectable(self):
      return True

def inherit_focus(children, focus):
   tArr=list(children) if isinstance(children, list) else [children]
   while tArr:
      w=tArr.pop()
      if isinstance(w, tuple): w=w[0]
      if isinstance(w, AttrWrapEx) and focus<len(w._original_map):
         new_attr=w._original_map[focus]
         if w.attr!=new_attr:
            w.attr=new_attr
            w._invalidate()
      if hasattr(w, '_original_widget'):  # for AttrWrap, AttrMap etc
         tArr.append(w._original_widget)
      if hasattr(w, '_w'):  # WidgetWrap
         tArr.append(w._w)
      if hasattr(w, 'contents'):  # for Pile, Columns etc
         tArr.extend(w.contents)

class MultiStyleWidget(FocusableWidget):
   def render(self, size, focus=False):
      inherit_focus(self, focus)
      return self.__super.render(size, focus)

class SelectableMultiStyleWidget(FocusableWidget):
   def __init__(self, w, *args, group=None, separate_style=False, **kwargs):
      assert group is None or isinstance(group, dict)
      if separate_style:
         assert isinstance(w, AttrWrapEx) and len(w._original_map)>=3
      self.__separate_style=separate_style
      self._selected=False
      self._group={} if group is None else group
      self._group[hash(self)]=weakref.ref(self)
      self.__super.__init__(w, *args, **kwargs)

      self.__just_restyled=False

   def unselect(self):
      if not self._selected: return
      self._selected=False
      self.__just_restyled=True
      self._invalidate()

   def unselect_others(self):
      for o in self._group.values():
         o=o()
         if o is not self and isinstance(o, SelectableMultiStyleWidget) and o._selected: o.unselect()

   def select(self, unselect_others=True):
      if unselect_others:
         self.unselect_others()
      if self._selected: return
      self._selected=True
      self.__just_restyled=True
      self._invalidate()

   def selected(self):
      for o in self._group.values():
         if isinstance(o, SelectableMultiStyleWidget) and o._selected: yield o

   def is_selected(self):
      return self._selected

   def keypress(self, size, key):
      if self._command_map[key] != ACTIVATE:
         return self.__super.keypress(size, key)
      self.select()

   def mouse_event(self, size, event, button, x, y, focus):
      if button!=1 or not is_mouse_press(event):
         return self.__super.mouse_event(size, event, button, x, y, focus)
      self.select()
      return True

   def render(self, size, focus=False):
      if self.__separate_style:
         focus=2 if self._selected else focus
         if self.__just_restyled and focus:
            self.__just_restyled=False
            o=self._w._original_map
            self._w=AttrWrapEx(self._w._original_widget, o[0], o[2], o[1])
      else:
         focus=self._selected or focus
      inherit_focus(self, focus)
      return self.__super.render(size, focus)

class FilterItem(SelectableMultiStyleWidget,):
   def __init__(self, val, data, showCounter=True, showDescr=True):
      self.value=val
      self.data=data
      self._w_name=TextFocusable(f'{self.data["name"]}')
      self._w_count=None
      if showCounter:
         self._w_count=Text('', align='right')
         self.set_counter(0)
      self._w_descr=None
      if showDescr:
         self._w_descr=Text(f'{self.data["descr"]}')
         self._w_descr=AttrWrapEx(self._w_descr, 'style2', 'style2-focus', 'style2-select')
      w1=Columns([self._w_name, self._w_count], 1) if showCounter else self._w_name
      w=Pile([w1, self._w_descr]) if showDescr else w1
      w=AttrWrapEx(Padding(w, left=1, right=1), 'style1', 'style1-focus', 'style1-select')
      self.__super.__init__(w, group=_FILTERS_GROUP, separate_style=True)

   def set_counter(self, val):
      self.__count=val
      self._w_count.set_text(f'({self.__count})')

   counter=property(lambda self: self.__count, set_counter)

class DialogWalker(urwid.ListWalker):
   def __init__(self, loader):
      self._loader=loader
      self._data={}
      self.focus={'date':None, 'index':0}

   def __getitem__(self, pos):
      pass

   def next_position(self, pos):
      pass

   def prev_position(self, pos):
      pass

   def set_focus(self, pos):
      pass
      self._modified()

class DialogHeader(MultiStyleWidget,):
   def __init__(self, val, data):
      self.value=val
      self.data=data
      self._w_indicator=AttrWrapEx(TextFocusable('', align='left', wrap='any'), 'style4', 'style4-focus')
      self._w_timestamp=AttrWrapEx(Text('', align='center', wrap='clip'), 'style4', 'style4-focus')
      self._w_statusbar=AttrWrapEx(Text('', align='center', wrap='clip'), 'style5', 'style5-focus')
      self._w_members=AttrWrapEx(Text('', align='left', wrap='space'), 'style3', 'style3-focus')
      self._w_subject=AttrWrapEx(Text('', align='left', wrap='clip'), 'style3', 'style3-focus')
      self._w_lastmsg=AttrWrapEx(Text('', align='left', wrap='clip'), 'style4', 'style4-focus')
      self.refresh()
      w=Columns([
         (1, self._w_indicator),
         Padding(Pile([Columns([
            (11, Padding(Pile([self._w_timestamp, self._w_statusbar]), right=1)),
            (20, Padding(self._w_members, right=2)),
            Pile([self._w_subject, self._w_lastmsg]),
         ], 0), Divider(LINE_H)]), left=1),
      ], 0)
      w=AttrWrapEx(w, 'style3', 'style3-focus')

      w=Pile([w]+[Message(i, o) for i, o in enumerate(self.data)])

      self.__super.__init__(w)

   def refresh(self):
      me=frozenset(['byaka.life@gmail.com', 'genryrar@gmail.com', 'byaka@buber.ru', 'byaka@clevit.ru'])
      #
      self.data=self._threads2flat(self.data)
      # unread
      unread=any(True for o in self.data if '#unread' in o['labels'])
      if unread:
         self._w_subject._original_map[0]='style3bold'
         self._w_subject._original_map[1]='style3bold-focus'
         self._w_members._original_map[0]='style3bold'
         self._w_members._original_map[1]='style3bold-focus'
         self._w_timestamp._original_map[0]='style4bold'
         self._w_timestamp._original_map[1]='style4bold-focus'
         self._w_lastmsg._original_map[0]='style4bold'
         self._w_lastmsg._original_map[1]='style4bold-focus'
      else:
         self._w_subject._original_map[0]='style3'
         self._w_subject._original_map[1]='style3-focus'
         self._w_members._original_map[0]='style3'
         self._w_members._original_map[1]='style3-focus'
         self._w_timestamp._original_map[0]='style4'
         self._w_timestamp._original_map[1]='style4-focus'
         self._w_lastmsg._original_map[0]='style4'
         self._w_lastmsg._original_map[1]='style4-focus'
      # indicator
      val=[('unread', '   ')] if unread else '   '
      self._w_indicator.set_text(val)
      # timestamp
      val=self.data[-1]['timestamp']
      if val.date()==datetime_today().date():
         val=val.strftime('%H:%M:%S')
      else:
         val=val.strftime('%d %b, %a')
      self._w_timestamp.set_text(val)
      # statusbar
      l=len(self.data)
      val=(
         '★ ' if any(True for o in self.data if '#favorite' in o['labels']) else '☆ ',
         '»' if any(True for o in self.data if me.intersection(o['to'])) else ' ',
         ' ',
         ' ',
         '99' if l>=99 else (f'{l} ' if l<10 else f'{l}')
      )
      self._w_statusbar.set_text(f'[{"".join(val)}]')
      # members
      val=set()
      for o in self.data:
         all=set([o['from']]+o['to'])
         if o['cc']: all.update(o['cc'])
         if o['bcc']: all.update(o['bcc'])
         if all.intersection(me):
            val.add('Me')
            all-=me
         for s in all:
            val.add(s.split('@', 2)[0] or s)
      val=sorted(val)
      self._w_members.set_text(f'{", ".join(val)}')
      # subject
      re_clearReply=re.compile(r'^((?:(?:re)|(?:Re)|(?:RE)):\s*)+')
      for o in self.data:
         val=re_clearReply.sub('', o['subject'])
         if val: break
      self._w_subject.set_text(val)
      # last message
      val=self.data[-1]['bodyPlain'] or self.data[-1]['bodyHtml']
      self._w_lastmsg.set_text(val)

   def _threads2flat(self, data):
      res=[]
      tArr=[data]
      while tArr:
         o=tArr.pop()
         if isinstance(o, (list, tuple)):
            for oo in o:
               tArr.append(oo)
         elif isinstance(o, dict):
            res.append(o)
         else:
            raise ValueError
      return res

   def keypress(self, size, key):

      return self.__super.keypress(size, key)

# class DialogStory(MultiStyleWidget,):
#    def __init__(self, val, data):
#       self.value=val
#       self.data=data
#       self._w_indicator=AttrWrapEx(TextFocusable('', align='left', wrap='any'), 'style4', 'style4-focus')
#       self._w_timestamp=AttrWrapEx(Text('', align='center', wrap='clip'), 'style4', 'style4-focus')
#       self._w_statusbar=AttrWrapEx(Text('', align='center', wrap='clip'), 'style5', 'style5-focus')
#       self._w_members=AttrWrapEx(Text('', align='left', wrap='space'), 'style3', 'style3-focus')
#       self._w_subject=AttrWrapEx(Text('', align='left', wrap='clip'), 'style3', 'style3-focus')
#       self._w_lastmsg=AttrWrapEx(Text('', align='left', wrap='clip'), 'style4', 'style4-focus')
#       self.refresh()
#       w=Columns([
#          (1, self._w_indicator),
#          Pile([Columns([
#             (11, Padding(Pile([self._w_timestamp, self._w_statusbar]), right=1)),
#             (20, Padding(self._w_members, right=2)),
#             Pile([self._w_subject, self._w_lastmsg]),
#          ], 0), Divider(LINE_H)])
#       ], 0)
#       w=AttrWrapEx(w, 'style3', 'style3-focus')
#       self.__super.__init__(w)

class Message(MultiStyleWidget,):
   def __init__(self, val, data):
      self.value=val
      self.data=data
      self._w_indicator_faw=AttrWrapEx(TextFocusable('', align='left', wrap='any'), 'style5', 'style5-focus')
      self._w_indicator_inc=AttrWrapEx(TextFocusable('', align='left', wrap='any'), '')
      self._w_subject=AttrWrapEx(Text('', align='left', wrap='space'), 'style3bold', 'style3bold-focus')
      self._w_timestamp=AttrWrapEx(Text('', align='right', wrap='clip'), 'style4', 'style4-focus')
      self._w_membersMain=AttrWrapEx(Text('', align='left', wrap='space'), 'style3', 'style3-focus')
      self._w_membersMore=AttrWrapEx(Text('', align='left', wrap='space'), 'style3', 'style3-focus')
      self._w_label_membersMain=AttrWrapEx(Text('', align='left', wrap='space'), 'style4', 'style4-focus')
      self._w_label_membersMore=AttrWrapEx(Text('', align='left', wrap='space'), 'style4', 'style4-focus')
      self._w_msg=AttrWrapEx(Text('', align='left', wrap='space'), 'style3', 'style3-focus')
      self.refresh()
      w=Columns([
         (2, self._w_indicator_inc),
         AttrWrapEx(Padding(Pile([
            Columns([
               ('weight', 70, Columns([(2, self._w_indicator_faw), self._w_subject], 0)),
               ('weight', 30, self._w_timestamp),
            ], 2),
            Columns([
               ('weight', 50, Columns([(6, self._w_label_membersMain), self._w_membersMain], 0)),
               ('weight', 50, Columns([(8, self._w_label_membersMore), self._w_membersMore], 0)),
            ], 3),
            Pile([Divider(), self._w_msg]),
            AttrWrapEx(Divider(LINE_H), 'style3', 'style3-focus'),
         ]), left=1), 'style3', 'style3-focus'),
      ], 0)
      s='incoming' if self.data['isIncoming'] else 'outgoing'
      w=AttrWrapEx(w, s)
      self.__super.__init__(w)

   def refresh(self):
      me=frozenset(['byaka.life@gmail.com', 'genryrar@gmail.com', 'byaka@buber.ru', 'byaka@clevit.ru'])
      #
      incoming=self.data['isIncoming']
      # indicator
      self._w_indicator_faw.set_text('★' if '#favorite' in self.data['labels'] else '☆')
      self._w_indicator_inc.set_text('»»»»' if incoming else '««««')
      s='incoming' if self.data['isIncoming'] else 'outgoing'
      self._w_indicator_inc._original_map[0]=s
      # timestamp
      val=self.data['timestamp'].strftime(f'%A, %d %B {"%Y" if self.data["timestamp"].year!=datetime_today().year else ""}%H:%M:%S')
      self._w_timestamp.set_text(val)
      # members
      if incoming:
         self._w_label_membersMain.set_text('From: ')
         self._w_label_membersMore.set_text('And To: ')
         val=self.data['from']
         self._w_membersMain.set_text(val)
         val=set()
         for k in ['to', 'cc', 'bcc']:
            if self.data[k]: val.update(self.data[k])
         self._w_membersMore.set_text(', '.join(val))
      else:
         self._w_label_membersMain.set_text('To: ')
         self._w_label_membersMore.set_text('And To: ')
         val=self.data['to']
         self._w_membersMain.set_text(', '.join(sorted(val)))
         val=set()
         for k in ['cc', 'bcc']:
            if self.data[k]: val.update(self.data[k])
         self._w_membersMore.set_text(', '.join(sorted(val)))
      # subject
      re_clearReply=re.compile(r'^((?:(?:re)|(?:Re)|(?:RE)):\s*)+')
      val=re_clearReply.sub('', self.data['subject'])
      self._w_subject.set_text(val)
      # last message
      val=self.data['bodyPlain'] or self.data['bodyHtml']
      self._w_msg.set_text(val)
