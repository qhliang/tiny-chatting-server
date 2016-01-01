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

from loger import Loger

  
# server class
class Chatting_server:
  '''A server for chat online service'''
  User_Info_Dict_Template = {'IP':'', 'PORT':0, 'NICK':''}
  
  def __init__(self):
    self.user_list = {}
    self.loger = Loger('Server is starting...')
    self.running = False
    # self.name = ''
    # self.ip 
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
    else:
      self.loger.log('error while initting server')
      clean_server()
    
  def loop(self):
    inputs = [self.server]
    
    # 新建线程接收来自键盘的消息
    thread = threading.Thread(target=self.listen_keyboard)
    thread.setDaemon(True)
    thread.start()
    
    self.running = True
    # 等待接收键盘消息的套接字的连接
    try:
      socket_key, t = self.server.accept()
      inputs.append(socket_key)
    except socket.error, e:
      self.loger.log('error while accept key socket')
      self.running = False
    
    # 循环等待消息
    while self.running:
      #self.loger.log('user_list -->> ')
      #for i in self.user_list.keys():
      #  self.loger.log('%d ' % i.fileno() + str(self.user_list[i]))
      #self.loger.log('log before select')
      t = '[' + str(len(self.user_list)) + '] '
      for i in self.user_list.keys():
        t += str(i.fileno()) + '(' + self.user_list[i]['NICK']+ ') '
      self.loger.log(t)
      
      try:
        rl, wl, el = select.select(inputs, [], [])
      except select.error, e:
        self.loger.log('error while selectting : %s' % e)
      #self.loger.log('log after select')
      
      #self.loger.log( 'rs = %d; ws = %d; es = %d' % (len(rl), len(wl), len(el)))
      
      # 有事件发生, 可读/可写/异常
      for sock in rl:
        
        # 有新的连接请求
        if sock == self.server:
          try:
            client_no, client_info = self.server.accept()
          except socket.error, e:
            self.loger.log('error while acceptting new connection : %s' % e)
            self.running = False
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
          # 来自键盘的消息
          if sock == inputs[1]:
            if 'EXIT' == recv_data:
              self.running = False
              continue
          elif len(recv_data):
            if recv_data.startswith('$$'):
              self.command_handle(sock, recv_data[2:], inputs)
            else:
              self.check_broadcast(sock, recv_data)
          else:
            if self.server == sock:
              self.running = False
            self.loger.log('%d has closed the socket' % sock.fileno())
            inputs.remove(sock)
            self.remove_user(sock)
            
    self.check_broadcast(self.server, 'server will be closed in seconds')
    self.loger.log('the server will exit ')
    self.clean_server()
    return True
    
  # 另外一个线程监听来自键盘的消息并转发到对应的socket中，来唤醒select
  def listen_keyboard(self):
    i = 10
    connect = False
    socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while i:
      try:
        socket_client.connect((self.ip, self.port))
        connect = True
        break
      except socket.error, e:
        self.loger.log('%dst times: error while key socket connectting server socket' % i)
      i -= 1
      time.sleep(1)
    if connect:
      while True:
        try:
          data = raw_input()
          socket_client.sendall(data)
          if 'EXIT' == data:
            break
        except EOFError:
          socket_client.sendall('EXIT')
          break
        except socket.error, e:
          self.loger.log('send keyboard msg failed')
    socket_client.close()
  
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
      self.ip = host_ip
      result = True
    except socket.error, e:
      self.loger.log(e)
      self.clean_server()
    return result
  
  # 初始化接收键盘消息的套接字对
  def init_keyboard(self):
    result = False
    try:
      self.stdin_serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.stdin_serv.bind((self.ip, 6363))
      self.stdin_serv.listen(1)
      self.loger.log('socket for keyboard ready ')
      result = True
    except socket.error, e:
      self.loger.log('error while setting keyboard socket')
    return result
  
  # 键盘中断处理函数
  def signal_handle(self, signum, frame):
    self.loger.log('recv exit signal from keyboard')
    self.loger.log('server will be cleaned')
    self.server.close()
    
              
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
    if not msg.endswith(os.linesep):
      msg += os.linesep
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
            self.check_broadcast(self.server, 'Hi, %s, welcome' % command_list[1])
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
      try:
        user_no.close()
      except socket.error, e:
        pass
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