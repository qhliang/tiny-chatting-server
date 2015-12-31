#! /usr/bin/python
# coding: utf-8

import time

# 日志项类
class LogerItem:
  '''item for loger'''
  def __init__(self, msg):
    self.time = time.strftime('%H:%M:%S')
    self.msg = msg
    
  def show(self):
    print "%s\t%s" % (self.time, self.msg)

# 日志类
class Loger:
  '''A log class'''
  def __init__(self, msg=''):
    self.logList = []
    self.log('Loger starting')
    if not len(msg):
      self.log(msg)
  
  def __del__(self):
    del self.logList
    
  def _log(self, msg):
    item = LogerItem(msg)
    self.logList.append(item)
    return item
  
  def log(self, msg):
    item = self._log(msg)
    item.show()
    
  def onlyPrint(self, msg):
    LogerItem(msg).show()
    
  def printAllLogs(self):
    for item in self.logList:
      print "%s\t%s" % (item.time, item.msg)
      