#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys, os

from asciimatics.screen import Screen
from asciimatics.scene import Scene
from asciimatics.widgets import Frame, Layout, ListBox, Widget, Label, PopUpDialog, Text, Divider
from asciimatics.exceptions import ResizeScreenError, StopApplication
from asciimatics.event import KeyboardEvent

from widgets import VirtualLayout, MyListBox

class SidebarMain(object):
   def __init__(self, layout):
      self.layout=layout
      self.folders=[
         ('Inbox', '#inbox'),
         ('Backlog', '#backlog'),
         ('Notes', '#notes'),
         ('Custom 1', '#custom1'),
         ('Custom 2', '#custom2'),
         ('Custom 3', '#custom3'),
      ]
      self.filters=[
         ('Done', '#backlog'),
         ('Spam', '#done'),
         ('Sended', '#sended'),
      ]
      self.layout.add_widget(MyListBox(
         4, self.folders,
         centre=False,
         label=None, name=None,
         add_scroll_bar=False,
         on_change=None, on_select=None
      ))
      self.layout.add_widget(Divider())
      self.layout.add_widget(MyListBox(
         7, self.filters,
         centre=False,
         label=None, name=None,
         add_scroll_bar=False,
         on_change=None, on_select=None
      ))

   def __call__(self):
      return self.layout

class MainScreen(Frame):
   def __init__(self, window):
      super(MainScreen, self).__init__(window, window.height, window.width, has_border=False, has_shadow=True, name="My Form", can_scroll=False)

      self.set_theme('default')

      self._layout=Layout([30, 70], fill_frame=True)
      self.add_layout(self._layout)

      self.layout=[
         VirtualLayout('sidebar', 0, self._layout, SidebarMain),
         VirtualLayout('dialogs', 1, self._layout, None),
      ]

      for l in self.layout:
         l.paint()

      self.redraw()

   def redraw(self):
      self.fix()

   def process_event(self, event):
      if isinstance(event, KeyboardEvent):
         if event.key_code in [ord('q'), ord('Q'), Screen.ctrl("c")]:
            raise StopApplication("User quit")
         elif event.key_code in [ord('1'), ord('2'), ord('3'), ord('4')]:
            # self.layout[0].widgets[0].setHeight(int(chr(event.key_code)))
            # self.redraw()
            self.layout[0].widgets[0].setValue(index=int(chr(event.key_code))-1)
      return super(MainScreen, self).process_event(event)

def main(screen, old_scene):
   screen.play([
      Scene([MainScreen(screen)], -1, name='Main'),
   ], stop_on_resize=True, start_scene=old_scene)

if __name__ == '__main__':
   last_scene = None
   while True:
      try:
         Screen.wrapper(main, catch_interrupt=False, arguments=[last_scene])
         sys.exit(0)
      except ResizeScreenError as e:
         last_scene = e.scene