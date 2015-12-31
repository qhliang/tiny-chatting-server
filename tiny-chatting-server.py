#! /usr/bin/python
# coding: utf-8

import os
import sys
import copy
import time
import select
import socket
import signal
import argparse
import threading

from user import User
from loger import Loger

  
# server class
class Chatting_server:
  '''A server for chat online service'''
  User_Info_Dict_Template = {'IP':'', 'PORT':0, 'NICK':''}
  
  def __init__(self):
    self.user_list = {}
    self.loger = Loger('Server is starting...')
    # self.name = ''
    # self.port = 0
    # self.max_users = 0
    # self.server 
    signal.signal(signal.SIGINT, self.signal_handle)
    
    # 处理参数
    self.parse_argvs()
    
    # 绑定IP和端口，并开启监听
    # 进入循环处理消息状态
    if self.bing_listen() and self.loop():
      pass
    
  def loop(self):
    inputs = [self.server]
    running = True
    while running:
      print 'user_list = ' ,
      for i in self.user_list.keys():
        print '%d ' % i.fileno() ,
        print self.user_list[i]
      print
      self.loger.log('log before select')
      try:
        rl, wl, el = select.select(inputs, [], [])
      except select.error, e:
        self.loger.log('error while selectting : %s' % e)
      self.loger.log('log after select')
      
      self.loger.log( 'rs = %d; ws = %d; es = %d' % (len(rl), len(wl), len(el)))
      
      # 有事件发生, 可读/可写/异常
      for sock in rl:
        
        # 有新的连接请求
        if sock == self.server:
          try:
            client_no, client_info = self.server.accept()
          except socket.error, e:
            self.loger.log('error while acceptting new connection : %s' % e)
            running = False
            continue
          client_info_dict = {'IP':client_info[0], 'PORT':client_info[1]}
          if self.insert_user(client_no, client_info_dict):
            self.loger.log('add new connection %d OK' % client_no.fileno())
          else:
            self.loger.log('add new connection %d failed' % client_no.fileno())
            continue
          inputs.append(client_no)
          
        # 有新数据到达
        else:
          try:
            recv_data = sock.recv(2048)
            self.loger.log('recveive data from %d [%s]' % (sock.fileno(), recv_data.rstrip()))
          except socket.error, e:
            self.loger.log('error while receiving data from %d' % sock.fileno())
            self.loger.log('%d will be closed' % sock.fileno())
            inputs.remove(sock)
            self.remove_user(sock)
          if len(recv_data):
            if recv_data.startswith('$$'):
              self.command_handle(sock, recv_data[2:], inputs)
            else:
              self.check_broadcast(sock, recv_data)
          else:
            self.loger.log('%d has closed the socket' % sock.fileno())
            inputs.remove(sock)
            self.remove_user(sock)
            
    self.loger.log('the server will exit ')
    clean_server()
    return True
    
  # 解析解收到的参数
  def parse_argvs(self):
    description = '''A demon server for chatting online. Enjoying'''
    parser = argparse.ArgumentParser(description = description)
    parser.add_argument('--name', nargs='?', type=str, help = description, default = 'Default')
    parser.add_argument('--port', nargs='?', type=int, help = description, default = 8080)
    parser.add_argument('--max', nargs='?', type=int, help = description, default = 5)
    args = parser.parse_args()
    self.name = args.name
    self.port = args.port
    self.max_users = args.max
  
  # 绑定IP和端口并监听
  def bing_listen(self):
    result = False
    # 绑定套接字建立服务器
    try:
      host_name = socket.gethostname()
      host_ip = socket.gethostbyname(host_name)
      self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      self.server.bind((host_ip, self.port))
      self.server.listen(3)
      self.loger.log('Server is running at %s:%d' % (host_ip, self.port))
      self.user_list[self.server] = {'IP':host_ip, 'PORT':self.port, 'NICK':'SERVER'}
      result = True
    except socket.error, e:
      self.loger.log(e)
      self.clean_server()
    return result
    
  # 键盘中断处理函数
  def signal_handle(self, signum, frame):
    self.loger.log('recv exit signal from keyboard')
    self.loger.log('server will be cleaned')
    self.clean_server()
    
              
  # 内部函数，发送数据到指定文件号(用户)
  def _send(self, dest_no, msg):
    result = False
    try:
      dest_no.sendall(msg)
      result = True
    except socket.error, e:
      self.loger.log('error with sending msg: %s' % e)
    return result
      
  # 发送数据到指定文件号(用户)
  def send(self, user_no, dest_no_list, msg):
    result = False
    failed_list = []
    try:
      dest_no_list.remove(self.server)
    except:
      pass
    if self.check_user(user_no):
      nick = self.user_list[user_no]['NICK']
      msg = '[%s\t]\t' % nick + msg
      for dest_no in dest_no_list:
        result = self._send(dest_no, msg)
        if not result:
          failed_list.append(dest_no)
      if len(dest_no_list) > 1:
        result = True
    return result, failed_list
  
  # 检查消息的发送者是否有权限发送广播消息并发送消息(如果有权限)
  def check_broadcast(self, user_no, msg):
    result = False
    failed_list = []
    if self.check_user(user_no):
      result, failed_list = self.send(user_no, self.user_list.keys(), msg)
    else:
      self.send(self.server, [user_no], 'You should log in first' + os.linesep)
    return result, failed_list
  
  # 处理用户消息中的命令
  def command_handle(self, user_no, command_str, inputs):
    result = True
    command_list = command_str.split()
    if len(command_list) == 1:
      if 'EXIT' == command_list[0]:
        inputs.remove(user_no)
        self.remove_user(user_no)
      else:
        self.send(self.server, [user_no], 'Unknown command')
    elif len(command_list) == 2:
      if 'SERV' == command_list[0]:
        if 'EXIT' == command_list[1]:
          result = False
        else:
          self.send(self.server, [user_no], 'Unknown command')
      elif 'NAME' == command_list[0]:
        old_info_dict = self.search_user(user_no)
        if isinstance(old_info_dict, dict):
          old_info_dict['NICK'] = command_list[1]
          if self.modify_user(user_no, old_info_dict):
            self.send(self.server, [user_no], 'modified profile OK' + os.linesep)
          else:
            self.send(self.server, [user_no], 'modified profile failed' + os.linesep)
      else:
        self.send(self.server, [user_no], 'Unknown command')
    return result
  
  # 添加用户到用户列表
  def insert_user(self, user_no, user_info_dict):
    result = False
    if user_no not in self.user_list.keys():
      new_info_dict = copy.deepcopy(self.User_Info_Dict_Template)
      for key, value in user_info_dict.items():
        new_info_dict[key] = value
      self.user_list[user_no] = new_info_dict
      result = True
    return result
    
  # 从用户列表删除用户
  def remove_user(self, user_no):
    result = False
    if user_no in self.user_list.keys():
      del self.user_list[user_no]
      user_no.close()
      result = True
    return result
    
  # 修改列表中现有的用户信息
  def modify_user(self, user_no, new_info_dict):
    result = False
    if user_no in self.user_list.keys():
      for key, value in new_info_dict.items():
        self.user_list[user_no][key] = value
      result = True
    return result
  
  # 获取指定用户信息
  def search_user(self, user_no):
    if user_no in self.user_list.keys():
      return self.user_list[user_no]
    else:
      return False
    
  # 查看用户当前状态
  def check_user(self, user_no):
    result = False
    t = self.search_user(user_no)
    self.loger.log(t)
    if t != False:
      if len(t['NICK']):
        result = True
    return result
  
  # 清理服务器资源
  def clean_server(self):
    del self.name
    del self.loger
    for sock in self.user_list:
      sock.close()
    self.server.close()
    sys.exit()
    
if '__main__' == __name__:
  chatting_room = Chatting_server()