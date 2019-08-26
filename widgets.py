#!/usr/bin/python3

import sys, os, re
import weakref

import urwid
from urwid import WidgetWrap, Pile, Columns, Text, Padding, AttrWrap, SelectableIcon, Divider, WidgetPlaceholder, WidgetDisable, SolidFill, Filler, BoxAdapter, Frame
from urwid.command_map import ACTIVATE, CURSOR_LEFT, CURSOR_RIGHT
from urwid.util import is_mouse_press

from utils import isInt, LINE_H, datetime, timedelta, datetime_now, datetime_today, to_date, to_datetime

class TextFocusable(Text):
   """
   Just selectable version of `Text` widget, but without cursor like in `SelectableIcon`.
   """
   _selectable=True
   def keypress(self, size, key): return key

   def mouse_event(self, size, event, button, x, y, focus): return True

#! былоб здорово расширить эту обертку, добавив поддержку различных именованных стилей вместо индексных, ну и заодно удобный метод для модификации и получения по имени. но придется переписать существующий код фокусировки
class AttrWrapEx(AttrWrap):
   def __init__(self, w, *attrs):
      assert attrs
      self._original_map=list(attrs)
      super().__init__(w, attrs[0], focus_attr=(attrs[1] if len(attrs)>1 else None))

class WidgetPlaceholderEx(WidgetPlaceholder):
   def __getattr__(self,name):
      """
      Call getattr on wrapped widget.  This has been the longstanding
      behaviour of AttrWrap, but is discouraged.  New code should be
      using AttrMap and .base_widget or .original_widget instead.
      """
      return getattr(self._original_widget, name)

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
         if callable(w.contents):
            try:
               tArr.extend(w.contents())
            except KeyError: pass
         else:
            tArr.extend(w.contents)

class FocusableMultiStyleWidget(FocusableWidget):
   def render(self, size, focus=False):
      inherit_focus(self, focus)
      return super().render(size, focus)

class SelectableMultiStyleWidget(FocusableWidget):
   signals=['select']

   def __init__(self, w, *args, group=None, separate_style=False, on_select=None, **kwargs):
      assert group is None or isinstance(group, dict)
      if separate_style:
         assert isinstance(w, AttrWrapEx) and len(w._original_map)>=3
      self.__separate_style=separate_style
      self._selected=False
      self._group={} if group is None else group
      self._group[hash(self)]=weakref.ref(self)
      super().__init__(w, *args, **kwargs)
      if on_select:
         urwid.connect_signal(self, 'select', on_select)
      self.__just_restyled=False

   def unselect(self):
      if not self._selected: return
      self._selected=False
      self.__just_restyled=True
      self._invalidate()

   def group(self):
      return self._group

   def group_memebers(self):
      return (o() for o in self._group.values())

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
      self._emit('select')

   def selected(self):
      for o in self._group.values():
         if isinstance(o, SelectableMultiStyleWidget) and o._selected: yield o

   def is_selected(self):
      return self._selected

   def keypress(self, size, key):
      if self._command_map[key]!=ACTIVATE:
         return super().keypress(size, key)
      self.select()

   def mouse_event(self, size, event, button, x, y, focus):
      if is_mouse_press(event):
         if button==4 or button==5:
            self.keypress(size, 'up' if button==4 else 'down')
            return True
         if button==1:
            self.select()
            return True
      return super().mouse_event(size, event, button, x, y, focus)

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
      return super().render(size, focus)

class FiltersList(WidgetPlaceholder):
   def __init__(self, data):
      self.data=data
      self._items=[]
      self._itemsMap={}
      self.refresh()
      self._w=urwid.ListBox(urwid.SimpleFocusListWalker(self._items))
      self._w=AttrWrapEx(self._w, 'style1', 'style1')
      super().__init__(self._w)

   def refresh(self):
      res1=[]
      res2=[]
      for k, v in self.data.items():
         assert v.get('type')
         assert v.get('name')
         # assert v.get('query')
         if v['type']=='main': to=res1
         elif v['type']=='more': to=res2
         else: continue
         if k not in self._itemsMap:
            self._itemsMap[k]=FilterItem(k, v, showDescr=v.get('descr'))
         else:
            self._itemsMap[k].set_counter(v.get('count', ''))
         to.append(self._itemsMap[k])
      self._items*=0
      self._items+=res1+[Text('More:', align='center', wrap='space')]+res2

   def set_counter(self, key, value):
      self._itemsMap[key].set_counter(value)

class FilterItem(SelectableMultiStyleWidget,):
   def __init__(self, val, data, showDescr=True, group={}):
      self.value=val
      self.data=data
      self._w_name=TextFocusable(f'{self.data["name"]}')
      self._w_count=Text('', align='right')
      self.set_counter(self.data.get('count'))
      self._w_descr=None
      if showDescr:
         self._w_descr=Text(f"{self.data['descr']}")
         self._w_descr=AttrWrapEx(self._w_descr, 'style2', 'style2-focus', 'style2-select')
      w1=Columns([self._w_name, self._w_count], 1)
      w=Pile([w1, self._w_descr]) if showDescr else w1
      w=AttrWrapEx(Padding(w, left=1, right=1), 'style1', 'style1-focus', 'style1-select')
      super().__init__(w, group=group, separate_style=True)

   def set_counter(self, val):
      self.__count=val
      s=f'({val})' if isInt(val) else ''
      self._w_count.set_text(s)

   counter=property(lambda self: self.__count, set_counter)

class DialogList(AttrWrap):
   MOUSE_WHEEL_SPEED=3
   signals=['open', 'close']

   def __init__(self, loader, andLoad=True, on_open=None, on_close=None):
      self.loader=loader
      self.walker=DialogWalker(loader, andLoad)
      self._w=urwid.ListBox(self.walker)
      super().__init__(self._w, 'style0', 'style0')
      if on_open:
         urwid.connect_signal(self, 'open', on_open)
      if on_close:
         urwid.connect_signal(self, 'close', on_close)

   focus=property(lambda self: self._w.focus)
   focus_position=property(lambda self: self._w.focus_position)

   def keypress(self, size, key):
      w, pos=self.focus, self.focus_position
      if isinstance(w, WidgetPlaceholder):
         w2=w.original_widget
         if(
            (key=='right' and isinstance(w2, DialogHeader)) or
            (key=='left' and isinstance(w2, DialogStory))
         ):
            isOpen=isinstance(w2, DialogStory)
            w.original_widget=getattr(w.original_widget, 'original' if isOpen else 'collapsed')
            self._emit('close' if isOpen else 'open')
            self._w.body._modified()
            return
      if isinstance(w, Message):
         if self._command_map[key]==ACTIVATE:
            print(self.focus.data['bodyHtml'] or self.focus.data['bodyPlain'])
      return super().keypress(size, key)

   def mouse_event(self, size, event, button, x, y, focus):
      if is_mouse_press(event):
         if button==4 or button==5:
            #! not works correctly
            # self._w.set_focus(
            #    self._w.body.get_shifted(self._w.body.focus, (-1 if button==4 else 1)*self.MOUSE_WHEEL_SPEED)[1],
            #    coming_from='above' if button==4 else 'below',
            # )
            # return True
            pass
            self.keypress(size, 'up' if button==4 else 'down')
            return True
      return super().mouse_event(size, event, button, x, y, focus)

class DialogWalker(urwid.ListWalker):
   def __init__(self, loader, andLoad=True):
      self._loader=loader
      if andLoad:
         self._loader.load()
      self._data={}
      self.focus=(None, None, 0, None)  # (list-index, date, dialog, msg)

   def isOpened(self, date, dialog):
      if date not in self._data or dialog<0 or dialog>=len(self._data[date]):
         return False
      return isinstance(self._data[date][dialog].original_widget, DialogStory)

   def _get_nearest_date(self, direction, date):
      dateStep=direction*self._loader.direction if direction else self._loader.direction
      if date is not None and direction:
         date=(to_date(date)+timedelta(days=dateStep)).strftime('%Y-%m-%d')
         if date in self._data:
            dialog=0 if dateStep<0 else len(self._data[date])-1
            msg=None if direction>0 or not self.isOpened(date, dialog) else self._data[date][dialog].messageCount-1
            return date, dialog, msg
      date, data=self._loader.get(date, dateStep)
      if data is False:
         return None, 0, None
      elif date not in self._data:
         print(f'DIALOG_CACHE_UPDATE {date}')
         self._data[date]=tuple(WidgetPlaceholderEx(DialogHeader(None, o)) for o in data)
      dialog=0 if dateStep<0 else len(self._data[date])-1
      msg=None if direction>0 or not self.isOpened(date, dialog) else self._data[date][dialog].messageCount-1
      return date, dialog, msg

   def _get_nearest_dialog(self, direction, date, dialog):
      if date not in self._data:
         return self._get_nearest_date((-1 if direction<0 else +1), date)
      dialog+=direction
      if dialog>=0 and dialog<len(self._data[date]):
         msg=None if direction>0 or not self.isOpened(date, dialog) else self._data[date][dialog].messageCount-1
         return date, dialog, msg
      return self._get_nearest_date((-1 if direction<0 else +1), date)

   def _get_nearest_msg(self, direction, date, dialog, msg):
      if date not in self._data:
         return self._get_nearest_date((-1 if direction<0 else +1), date)
      if dialog<0 or dialog>=len(self._data[date]):
         return self._get_nearest_dialog(direction, date, dialog)
      if self.isOpened(date, dialog):
         if msg is None:
            if direction<=0:
               return self._get_nearest_dialog(direction or -1, date, dialog)
            msg=0
         else:
            msg+=direction
         if msg==-1:
            return date, dialog, None
         elif msg>=0 and msg<self._data[date][dialog].messageCount:
            return date, dialog, msg
      return self._get_nearest_dialog(direction, date, dialog)

   def _get(self, direction, list_index, date, dialog, msg):
      if(
         not direction and
         date in self._data and
         dialog>=0 and
         dialog<len(self._data[date]) and
         (msg is None or (msg>=0 and msg<self._data[date][dialog].messageCount))
      ):
         w=self._data[date][dialog]
         if msg is not None:
            w=w.messageList[msg]
         else:
            w.makeStriped(list_index%2)
         return w, (list_index, date, dialog, msg)
      #
      date, dialog, msg=self._get_nearest_msg(direction, date, dialog, msg)
      if date is None:
         return None, (list_index, date, dialog, msg)
      w=self._data[date][dialog]
      if msg is not None:
         w=w.messageList[msg]
      else:
         list_index=(list_index+direction) if list_index is not None else 0
         w.makeStriped(list_index%2)
      return w, (list_index, date, dialog, msg)

   def get_next(self, pos):
      w, i=self._get(+1, *pos)
      print(f'GET_NEXT {pos} --> {i}')
      return w, i

   def get_prev(self, pos):
      w, i=self._get(-1, *pos)
      print(f'GET_PREV {pos} --> {i}')
      return w, i

   def get_shifted(self, pos, step):
      w, i=self._get(step, *pos)
      print(f'GET_SHIFTED ({step}) {pos} --> {i}')
      return w, i

   def get_focus(self):
      w, i=self._get(0, *self.focus)
      print(f'GET_FOCUS {i}')
      return w, i

   def set_focus(self, pos):
      old=self.focus
      self.focus=pos
      print(f'SET_FOCUS {old} --> {pos}')
      self._modified()

class DialogStory(FocusableMultiStyleWidget,):
   def __init__(self, original):
      self.original=original
      self._w=AttrWrapEx(TextFocusable('collapsed dialog dummy', align='center', wrap='any'), 'style3', 'style3-focus')
      self._w_child=()
      super().__init__(self._w)

   @property
   def messageList(self):
      return self.original.messageList

   @property
   def messageCount(self):
      return self.original.messageCount

   def makeStriped(self, striped):
      self.original.makeStriped(striped)

class DialogHeader(FocusableMultiStyleWidget,):
   STRIPED_STYLE_SUFFIX='-striped'

   def __init__(self, val, data, striped=False):
      self.value=val
      self.data=data
      self._w_init()
      self.collapsed=DialogStory(self)
      self.__msgs=None
      self._w=AttrWrapEx(self._w, 'style3', 'style3-focus')
      self.makeStriped(striped)
      super().__init__(self._w)

   def makeStriped(self, striped):
      for o in (
         self._w, *self._w_child,
         self.collapsed._w, *self.collapsed._w_child,
      ):
         if not isinstance(o, AttrWrapEx): continue
         old_attr=o._original_map[0]
         s=old_attr.endswith(self.STRIPED_STYLE_SUFFIX)
         if s==striped: continue
         new_attr=(old_attr+self.STRIPED_STYLE_SUFFIX) if striped else old_attr[:-len(self.STRIPED_STYLE_SUFFIX)]
         o._original_map[0]=new_attr
         if o.attr!=new_attr:
            o.attr=new_attr
            o._invalidate()

   def _w_prep(self):
      self._w_indicator=AttrWrapEx(TextFocusable('', align='left', wrap='any'), 'style4', 'style4-focus')
      self._w_timestamp=AttrWrapEx(Text('', align='center', wrap='clip'), 'style4', 'style4-focus')
      self._w_statusbar=AttrWrapEx(Text('', align='center', wrap='clip'), 'style5', 'style5-focus')
      self._w_members=AttrWrapEx(Text('', align='left', wrap='space'), 'style3', 'style3-focus')
      self._w_subject=AttrWrapEx(Text('', align='left', wrap='clip'), 'style3', 'style3-focus')
      self._w_lastmsg=AttrWrapEx(Text('', align='left', wrap='clip'), 'style4', 'style4-focus')
      self._w_child=(
         self._w_indicator,
         self._w_timestamp,
         self._w_statusbar,
         self._w_members,
         self._w_subject,
         self._w_lastmsg,
      )

   def _w_init(self):
      self._w_prep()
      self.refresh()
      self._w=Columns([
         (1, self._w_indicator),
         Padding(Columns([
            (11, Padding(Pile([self._w_timestamp, self._w_statusbar]), right=1)),
            (20, Padding(self._w_members, right=2)),
            Pile([self._w_subject, self._w_lastmsg]),
         ], 0), left=1),
      ], 0)

   @property
   def messageList(self):
      if self.__msgs is None:
         self.__msgs=tuple(Message(i, o) for i, o in enumerate(self.data))
      return self.__msgs

   @property
   def messageCount(self):
      return len(self.data)

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
      val=[('unread', '  ')] if unread else '  '
      self._w_indicator.set_text(val)
      # timestamp
      val=to_date(self.data[-1]['timestamp'])
      if val==datetime_today().date():
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
      val=val.replace('\r', '').replace('\n', ' ')[:80]
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
      return super().keypress(size, key)

class Message(FocusableMultiStyleWidget,):
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
               ('weight', 7, Columns([(2, self._w_indicator_faw), self._w_subject], 0)),
               ('weight', 3, self._w_timestamp),
            ], 2),
            Columns([
               ('weight', 1, Columns([(6, self._w_label_membersMain), self._w_membersMain], 0)),
               ('weight', 1, Columns([(8, self._w_label_membersMore), self._w_membersMore], 0)),
            ], 3),
            Pile([Divider(), self._w_msg]),
            AttrWrapEx(Divider(LINE_H), 'style3', 'style3-focus'),
         ]), left=1), 'style3', 'style3-focus'),
      ], 0)
      s='incoming' if self.data['isIncoming'] else 'outgoing'
      w=AttrWrapEx(w, s)
      super().__init__(w)

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
      val=to_datetime(self.data['timestamp'])
      val=val.strftime(f'%A, %d %B {"%Y " if val.year!=datetime_today().year else ""}%H:%M:%S')
      self._w_timestamp.set_text(val)
      # members
      if incoming:
         self._w_label_membersMain.set_text('From: ')
         val=self.data['from']
         self._w_membersMain.set_text(val)
         val=set()
         for k in ['to', 'cc', 'bcc']:
            if self.data[k]: val.update(self.data[k])
         self._w_membersMore.set_text(', '.join(val))
         self._w_label_membersMore.set_text('And To: ' if val else '')
      else:
         self._w_label_membersMain.set_text('To: ')
         val=self.data['to']
         self._w_membersMain.set_text(', '.join(sorted(val)))
         val=set()
         for k in ['cc', 'bcc']:
            if self.data[k]: val.update(self.data[k])
         self._w_membersMore.set_text(', '.join(sorted(val)))
         self._w_label_membersMore.set_text('And To: ' if val else '')
      # subject
      re_clearReply=re.compile(r'^((?:(?:re)|(?:Re)|(?:RE)):\s*)+')
      val=re_clearReply.sub('', self.data['subject'])
      self._w_subject.set_text(val)
      # last message
      val=self.data['bodyPlain'] or self.data['bodyHtml']
      val='\n'.join(s for s in val.split('\n') if not s.startswith('>'))
      val=val.replace('\r', '').replace('\t', '   ')
      self._w_msg.set_text(val)


class HotkeyItem(Columns,):
   _RE_f=re.compile(r'(\W*)f(\d{1,2})')
   def __init__(self, key, name, on_mouseLeft):
      self.key=key
      self.on_mouseLeft=on_mouseLeft
      super().__init__([
         AttrWrap(Text(self._key2human(key)+' '), 'style1-reverse'),
         (len(name), Text(name)),
      ], 0)

   def _key2human(self, key):
      key=key.replace(' ', '+')
      key=key.replace('shift', '⇧')
      key=key.replace('enter', '↵')
      key=key.replace('delete', '⌦')
      key=key.replace('backspace', '⌫')
      key=key.replace('space', '␣')
      key=key.replace('ctrl', '✲ ')
      key=key.replace('meta', '⌘ ')
      key=key.replace('esc', 'Esc')
      key=self._RE_f.sub('\\1F\\2', key)
      return key

   def pack(self, size, focus=False):
      sw, sh=0, 0
      for w, _ in self.contents:
         sw2, sh2=w.pack(size, focus)
         sw+=sw2
         sh=max(sh, sh2)
      return sw, sh

   def mouse_event(self, size, event, button, x, y, focus):
      if event=='mouse press' and button==1:
         self.on_mouseLeft(self.key)
      return False

class HotkeyBar(AttrWrap,):
   def __init__(self, keyMap=None, bindArgs=None, bindKwargs=None):
      self._keyMap=keyMap or {}
      self._bindArgs=bindArgs or ()
      self._bindKwargs=bindKwargs or {}
      self._state=None
      self._w=Columns([], 1)
      self.refresh()
      super().__init__(self._w, 'style1')

   def refresh(self):
      tMap=self._keyMap
      res=[]
      if self._state is not None:
         n, tMap=self._state
         w=AttrWrap(Text(f'{n}:'), 'style1bold')
         res.append((w, self._w.options('pack')))
         res.append((HotkeyItem('esc', '', on_mouseLeft=self._fire), self._w.options('pack')))
      for key, o in tMap.items():
         res.append((HotkeyItem(key, o[0], on_mouseLeft=self._fire), self._w.options('pack')))
      self._w.contents=res

   def _fire(self, key=None):
      if not key: return
      tMap=self._keyMap if self._state is None else self._state[1]
      if key=='esc' and self._state is not None:
         self._state=None
         self.refresh()
      elif key in tMap:
         n, v=tMap[key]
         print('HOTKEY', key, n, v)
         if callable(v):
            _args=(n,)+self._bindArgs
            _kwargs=self._bindKwargs
            v(*_args, **_kwargs)
            self._state=None
         else:
            self._state=(n, v)
         self.refresh()
      else:
         return False
      return True

   def keypress(self, size, key):
      if not self._fire(key): return key
