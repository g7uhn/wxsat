#!/usr/bin/env python2
#    This software is Copyright (C) 2012 by James C. Ahlstrom, and is
#    free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#  April 2017, Modified by Andy Webster G7UHN for control of rtl_fm recording based on GPredict's AOS and LOS outputs

import os
import sys, time, socket, traceback, string
import subprocess
from datetime import datetime

PORT = 7356        # Default port used by GQRX

timestr = "null"

# This module creates a Hamlib TCP server that implements the rigctl protocol.  To start the server,
# run "./wxsat-receive-XXXXXX.py" from a command line where "XXXXXX" is replaced by the relevant satellite designation.
# To exit the server, type control-C.  Connect a client (e.g. GPredict) to the server using localhost and port 7356.
# The TCP server will imitate a software defined radio, and you can get and set the frequency, etc.
# The commands "AOS" and "LOS" have been added to cater for GPredict control of software to record satellite passes,
# specifically starting and stopping an rtl_fm recording process.

# Only the commands dump_state, freq, mode, ptt, vfo, AOS and LOS are implemented.

class HamlibHandler:
  """This class is created for each connection to the server.  It services requests from each client"""

  SingleLetters = {		               # convert single-letter commands to long commands
    'f':'freq',
    'm':'mode',
    't':'ptt',
    'v':'vfo',
    }

  def __init__(self, app, sock, address):
    self.app = app		               # Reference back to the "hardware"
    self.sock = sock
    sock.settimeout(0.0)
    self.address = address
    self.received = ''
    h = self.Handlers = {}
    h[''] = self.ErrProtocol
    h['dump_state']	= self.DumpState
    h['get_freq']	= self.GetFreq
    h['set_freq']	= self.SetFreq
    h['get_mode']	= self.GetMode
    h['set_mode']	= self.SetMode
    h['get_vfo']	= self.GetVfo
    h['get_ptt']	= self.GetPtt
    h['set_ptt']	= self.SetPtt


  def Send(self, text):
    """Send text back to the client."""
    try:
      self.sock.sendall(text)
    except socket.error:
      self.sock.close()
      self.sock = None

  def Reply(self, *args):	                # args is name, value, name, value, ..., int
    """Create a string reply of name, value pairs, and an ending integer code."""
    if self.extended:			        # Use extended format
      t = "%s:" % self.cmd		        # Extended format echoes the command and parameters
      for param in self.params:
        t = "%s %s" % (t, param)
      t += self.extended
      for i in range(0, len(args) - 1, 2):
        t = "%s%s: %s%c" % (t, args[i], args[i+1], self.extended)
      t += "RPRT %d\n" % args[-1]
    elif len(args) > 1:		                # Use simple format
      t = ''
      for i in range(1, len(args) - 1, 2):
        t = "%s%s\n" % (t, args[i])
    else:		                        # No names; just the required integer code
      t = "RPRT %d\n" % args[0]
    print 'Reply', t
    self.Send(t)

  def ErrParam(self):		                # Invalid parameter
    self.Reply(-1)

  def UnImplemented(self):	                # Command not implemented
    self.Reply(-4)

  def ErrProtocol(self):	                # Protocol error
    self.Reply(-8)

  def Process(self):
    """This is the main processing loop, and is called frequently.  It reads and satisfies requests."""
    if not self.sock:
      return 0
    try:	                                # Read any data from the socket
      text = self.sock.recv(1024)
    except socket.timeout:	                # This does not work
      pass
    except socket.error:	                # Nothing to read
      pass
    else:					# We got some characters
      self.received += text
    if '\n' in self.received:	                # A complete command ending with newline is available
      cmd, self.received = self.received.split('\n', 1)	# Split off the command, save any further characters
    else:
      return 1
    cmd = cmd.strip()		                # Here is our command
#    print 'Get', cmd

    timestr = datetime.now().strftime('%Y%m%d-%H%M%S')

    if not cmd:			                # ??? Indicates a closed connection?
      print 'empty command'
      self.sock.close()
      self.sock = None
      return 0
    # Parse the command and call the appropriate handler
    if cmd[0] == '+':			        # rigctld Extended Response Protocol
      self.extended = '\n'
      cmd = cmd[1:].strip()
    elif cmd[0] in ';|,':		        # rigctld Extended Response Protocol
      self.extended = cmd[0]
      cmd = cmd[1:].strip()
    else:
      self.extended = None
    if cmd[0:1] == '\\':		        # long form command starting with backslash
      args = cmd[1:].split()
      self.cmd = args[0]
      self.params = args[1:]
      self.Handlers.get(self.cmd, self.UnImplemented)()


    elif 'AOS' in cmd:                  # AOS/LOS mods start here!
        timestr = datetime.now().strftime('%Y%m%d-%H%M%S')
        print ('AOS received at ' + timestr)
        self.startRecording()

    elif 'LOS' in cmd:
        timestr = datetime.now().strftime('%Y%m%d-%H%M%S')
        print ('LOS received at ' + timestr)
        self.stopRecording()


    else:				        # deal with single-letter commands
      self.params = cmd[1:].strip()
      cmd = cmd[0:1]
      try:
        t = self.SingleLetters[cmd.lower()]
      except KeyError:
        self.UnImplemented()
      else:
        if cmd in string.uppercase:
          self.cmd = 'set_' + t
        else:
          self.cmd = 'get_' + t
        self.Handlers.get(self.cmd, self.UnImplemented)()

    return 1

  # These are the handlers for each request
  
  def startRecording(self):
    timestr = datetime.now().strftime('%Y-%m-%d-%H%MZ')
    command = ("rtl_fm -d 0 -f 137912500 -M fm -s 40000 -g 34 -F 0 -A fast -E DC /home/pi/wxsat/recorded/%s-NOAA-18.raw &" % timestr)
    subprocess.Popen(command, shell=True)
    self.Reply(0)

  def stopRecording(self):
    subprocess.Popen(["pkill", "rtl_fm"])
    self.Reply(0)

  def DumpState(self):
    self.Send(dump2)

  def GetFreq(self):
    self.Reply('Frequency', self.app.freq, 0)

  def SetFreq(self):
    try:
      x = float(self.params)
      self.Reply(0)
    except:
      self.ErrParam()
    else:
      x = int(x + 0.5)
      self.app.freq = x

  def GetMode(self):
    self.Reply('Mode', self.app.mode, 'Passband', self.app.bandwidth, 0)

  def SetMode(self):
    try:
      mode, bw = self.params.split()
      bw = int(float(bw) + 0.5)
      self.Reply(0)
    except:
      self.ErrParam()
    else:
      self.app.mode = mode
      self.app.bandwidth = bw

  def GetVfo(self):
    self.Reply('VFO', self.app.vfo, 0)

  def GetPtt(self):
    self.Reply('PTT', self.app.ptt, 0)

  def SetPtt(self):
    try:
      x = int(self.params)
      self.Reply(0)
    except:
      self.ErrParam()
    else:
      if x:
        self.app.ptt = 1
      else:
        self.app.ptt = 0

class App:
  """This is the main application class.  It listens for connectons from clients and creates a server for each one."""
  def __init__(self):
    self.hamlib_clients = []
    self.hamlib_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.hamlib_socket.bind(('localhost', PORT))
    self.hamlib_socket.settimeout(0.0)
    self.hamlib_socket.listen(0)
    # This is the state of the "hardware"
    self.freq = 21200500
    self.mode = 'CW'
    self.bandwidth = 2400
    self.vfo = "VFO"
    self.ptt = 0

  def Run(self):
    while 1:
      time.sleep(0.5)
      try:
        conn, address = self.hamlib_socket.accept()
      except socket.error:
        pass
      else:
        print 'Connection from', address
        self.hamlib_clients.append(HamlibHandler(self, conn, address))
      for client in self.hamlib_clients:
        ret = client.Process()
        if not ret:		                        # False return indicates a closed connection; remove the server
          self.hamlib_clients.remove(client)
          print 'Remove', client.address
          break
      

if __name__ == "__main__":
  try:
    App().Run()
  except KeyboardInterrupt:
    sys.exit(0)
