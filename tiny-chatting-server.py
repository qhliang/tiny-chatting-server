#! /usr/bin/python
# coding: utf-8

import os
import sys
import time
import select
import socket
import signal
import argparse

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
      
class User:
  '''A user who are online'''
  def __init__(self, addr, port, nick=''):
    self.addr = addr
    self.port = port
    self.nick = nick
    
  
# server class
class Chatting_server:
  '''A server for chat online service'''
  def __init__(self):
    self.user_list = {}
    self.loger = Loger('Server is starting...')
    signal.signal(signal.SIGINT, self.signal_handle)
    
    # 处理附加参数
    description = '''A demon server for chatting online. Enjoying'''
    parser = argparse.ArgumentParser(description = description)
    parser.add_argument('--name', nargs='?', type=str, help = description, default = 'Default')
    parser.add_argument('--port', nargs='?', type=int, help = description, default = 8080)
    parser.add_argument('--max', nargs='?', type=int, help = description, default = 5)
    args = parser.parse_args()
    self.name = args.name
    self.port = args.port
    self.maxUser = args.max
    del args
    del parser 
    
    host_name = socket.gethostname()
    host_ip = socket.gethostbyname(host_name)
    # 绑定套接字建立服务器
    try:
      self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      self.server.bind((host_ip, self.port))
      self.server.listen(3)
    except socket.error, e:
      self.loger.log(e)
    self.loger.log('Server is running at %s:%d' % (host_ip, self.port))
    self.loop()
    
  def loop(self):
    inputs = [self.server]
    self.outputs = []
    running = True
    while running:
      self.loger.log('log before select')
      try:
        readable, writeable, exceptional = select.select(inputs, [], [])
      except select.error, e:
        self.loger.log('error while selectting : %s' % e)
      self.loger.log('log after select')
      
      self.loger.log( 'rs = %d; ws = %d; es = %d' % (len(readable), len(writeable), len(exceptional)))
      # 有事件发生, 可读/可写/异常
      for sock in readable:
        # 有新的连接请求
        if sock == self.server:
          state, client_no = self.insert_user()
          if not state:
            running = False
            break
          inputs.append(client_no)
          self.outputs.append(client_no)
          
        # 从键盘收到数据
        elif sock == sys.stdin:
          key_data = sys.stdin.readline()
          if 'stop' == key_data.lower():
            self.loger.log('stop command from keyboard.')
            running = False
            
        # 有新数据到达
        else:
          recv_data = sock.recv(1024)
          if len(recv_data)!=0:
            nick = self.user_list[sock].nick
            self.loger.log('recv msg from %d[%s]: %s' % (sock.fileno(), nick, recv_data))
            if recv_data.startswith('$$'):
              running = self.command_handle(sock, recv_data[2:], inputs, self.outputs)
            else :
              self.send(nick, self.user_list.keys(), recv_data)
          else:
            inputs.remove(sock)
            self.outputs.remove(sock)
            self.loger.log('removed %d from inputs and outputs and closed it ' % sock.fileno())
            try:
              sock.close()
            except socket.error, e:
              pass
            
    self.loger.log('the server will be cleaned.')
    clean_server()
    
  # 键盘中断处理函数
  def signal_handle(self, signum, frame):
    self.loger.log('recv exit signal from keyboard')
    self.loger.log('server will be cleaned')
    self.clean_server()
    
              
  # 内部函数，发送数据到指定文件号(用户)
  def _send(self, dest_no, msg):
    try:
      dest_no.sendall(msg)
    except socket.error, e:
      self.loger.log('error with sending msg: %s' % e)
      
  # 发送数据到指定文件号(用户)
  def send(self, from_user_nick, dest_no_list, msg):
    if not len(from_user_nick):
      from_user_nick = '-Anonymous-'
    msg = '[%s\t]' % from_user_nick + msg
    for dest_no in dest_no_list:
      self._send(dest_no, msg)
  
  # 从指定文件号(用户)接收数据
  def receive(self, user_no):
    state = False
    recv_data = ''
    try:
      while True:
        str = user_no.recv(1024)
        if not len(str):
          break
        recv_data += str
      state = True
    except socket.error, e:
      self.loger.log('error while receiving data from %d' % user_no.fileno())
    return state, recv_data
  
  # 处理用户消息中的命令
  def command_handle(self, user_no, command_str, inputs, outputs):
    state = True
    command_list = command_str.split()
    if len(command_list) == 1:
      if 'EXIT' == command_list[0]:
        inputs.remove(user_no)
        outputs.remove(user_no)
        self.remove_user(user_no)
      else:
        self.send('-Server-', [user_no], 'Unknown command')
    elif len(command_list) == 2:
      if 'SERV' == command_list[0]:
        if 'EXIT' == command_list[1]:
          state = False
        else:
          self.send('-Server-', [user_no], 'Unknown command')
      else:
        self.send('-Server-', [user_no], 'Unknown command')
    return state
  
  # 添加用户到用户列表
  def insert_user(self):
    result = True
    try:
      client_no, client_info = self.server.accept()
      self.user_list[client_no] = User(client_info[0], client_info[1])
      self.loger.log('new connection from %d %s' % (client_no.fileno(), str(client_info)))
    except socket.error, e:
      self.loger.log('error while accepting: %s' % e)
      result = False
    return result, client_no
    
  # 从用户列表删除用户
  def remove_user(self, user_no):
    self.loger.log('user exited %d %s' % (user_no.fileno(), self.user_list[user_no].nick))
    del self.user_list[user_no]
    user_no.close()
    
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