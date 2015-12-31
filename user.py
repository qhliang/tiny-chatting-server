#! /usr/bin/python
# coding: utf-8

# 用户类
class User:
  '''A user  who are online'''
  def __init__(self, addr, port, nick=''):
    self.addr = addr
    self.port = port
    self.nick = nick
    