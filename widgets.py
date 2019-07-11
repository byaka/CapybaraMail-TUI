#!/usr/bin/python3
# -*- coding: utf-8 -*-

from asciimatics.widgets import Frame, Layout, ListBox, Widget, Label, PopUpDialog, Text, Divider

class VirtualLayout(object):
   def __init__(self, name, column, layout, filler):
      self.name=name
      self.filler=filler
      self.layout=layout
      self.column=column
      self.widgets=[]
      if callable(self.filler):
         self.filler(self)

   def add_widget(self, widget):
      self.widgets.append(widget)

   def paint(self):
      for w in self.widgets:
         self.layout.add_widget(w, self.column)

class MyListBox(ListBox):

   def setHeight(self, height):
      self._required_height=height

   def getHeight(self, height):
      return self._required_height

   def setValue(self, value=None, index=None):
      if value:
         i=self._find_option(value)
      else:
         i=index
      self._line=i
      self.value=self._options[self._line][1]

   def getValue(self):
      return self.value

   def _find_option(self, search_value):
      search_value=search_value.lower()
      #! add fuzzy search
      for text, value in self._options:
         if text.lower().startswith(search_value):
            return value
      return None
