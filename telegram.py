#!/usr/bin/env python

import os
import sys
import time
import random
import datetime
import telepot
from elasticsearch import Elasticsearch
from dateutil import tz

class elasticSearch():
  """
  Elsticsearch connector
  """
  def __init__(self, server):
    self.es = Elasticsearch([server])

  def query(self, qry_str, index, size = 1000):
    print "Query: " + str(qry_str) + " on index " + str(index)
    res = self.es.search(index=index, body={"size":size,
      "query": {"filtered": {
          "query":  { "match": qry_str},
          "filter": { "range": {"Date": { "gt": "now-7d"}
            }}}}})
    return res

class telebot():

  def __init__(self, token, elastic, index, groupid, admin):
    self.chat_id  = None
    self.command  = None
    self.username = None

    self.groupid  = groupid
    self.admin    = admin

    self.index    = index
    self.es       = elasticSearch(elastic)
    self.bot      = telepot.Bot(token)

  def run(self):
    self.bot.notifyOnMessage(self.handle)
    print "Bot listening ..."
    while 1:
      time.sleep(10)

  def extractDate(self, date_str):
    date_object = datetime.datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
    utc         = date_object.replace(tzinfo=tz.tzutc())
    localtime   = utc.astimezone(tz.tzlocal())
    return localtime

  def createReturnString(self, data, op = ""):
    finalList = []
    for entry in data["hits"]["hits"]:
      if op == "":
        finalList.append( str(self.extractDate(entry["_source"]["Date"])) + "\r\n"
                             +             str(entry["_source"]["Enemy"])
                             + " vs. " +   str(entry["_source"]["Agent"])
                             + "(L" +      str(entry["_source"]["ALevel"]) + ")\r\n"
                             + "@ " + u''.join((entry["_source"]["Portal"])).encode('utf-8').strip()
                             + "(L" +      str(entry["_source"]["PLevel"]) + ")\r\n"
                             + "https://www.ingress.com/intel?ll=" + str(entry["_source"]["Location"])
                             + "&z=17&pll="                        + str(entry["_source"]["Location"]))

      elif op == "farm":
        finalList.append( str(self.extractDate(entry["_source"]["Date"])) + "\r\n"
                             +       u''.join((entry["_source"]["Portal"])).encode('utf-8').strip() + "\r\n")
  
      elif op == "topList":
        finalList.append( str(self.extractDate(entry["_source"]["Date"])) + "\r\n"
                             +       u''.join((entry["_source"]["Enemy"])).encode('utf-8').strip()
                             + "@" + u''.join((entry["_source"]["Portal"])).encode('utf-8').strip()
                             + "(L"      + str(entry["_source"]["PLevel"]) + ")\r\n-----\r\n")
      else:
        print "Error on return string ..." 

    print str(finalList)[:50]
    return finalList
  
  def getTopAnwers(self, data, count):
    i = -1
    result = ""
    while (count*-1-1) != i:
      result += sorted(data)[i]
      i -= 1
    return result

  def sendMessage(self, data, top = 1):
    try: 
      print str(sorted(data))[:50]
      if top > 1:
        head   = "Top " + str(top) + " :\r\n"
        answer = head + self.getTopAnwers(data, top)
      else:
        answer = sorted(data)[-1]
    except: 
      answer = "Nothing not found"
    finally:
      print "Result: " + str(answer)
      self.bot.sendMessage(self.chat_id, answer, disable_web_page_preview=True)
  
  def handle(self, msg):
    self.chat_id  = msg['chat']['id']
    self.command  = msg['text']
    self.username = msg['from']['username']

    print 'Got command: %s from %s' % (self.command, self.username)
    print str(msg)
  
    if msg["chat"]["type"] == "group"      or self.username == self.admin:
      if msg["chat"]["id"] == int(self.groupid) or self.username == self.admin:
  
        if self.command == '/help':
          helptext  = "I'll give u the last info from elastic i've got:\r\n"
          helptext += "/agent <player>\r\n/address <region>\r\n"
          helptext += "/portal <name>\r\n/enemy <player>\r\n"
          helptext += "/farm\r\n"
          helptext += "Filter just for 7 days."
          self.bot.sendMessage(self.chat_id, helptext.strip())
  
        elif self.command.startswith('/agent'):
          self.sendMessage(self.createReturnString(self.es.query({"Agent":self.command.split(" ")[1]}, self.index)))
  
        elif self.command.startswith('/address'):
          self.sendMessage(self.createReturnString(self.es.query({"Address":self.command.split(" ")[1]}, self.index)))
      
        elif self.command.startswith('/portal'):
          self.sendMessage(self.createReturnString(self.es.query({"Portal":self.command.split(" ")[1]}, self.index)))
      
        elif self.command.startswith('/enemy'):
          self.sendMessage(self.createReturnString(self.es.query({"Enemy":self.command.split(" ")[1]}, self.index)))
  
        elif self.command.startswith('/farm'):
          self.sendMessage(self.createReturnString(self.es.query({"PLevel":"8"}, self.index), op = "farm"),top = 5)
  
        elif self.command.startswith('/e10'):
          self.sendMessage(self.createReturnString(
                             self.es.query({"Enemy":self.command.split(" ")[1]}, self.index), op = "topList"),top = 10)
        elif self.command.startswith('/p10'):
          self.sendMessage(self.createReturnString(
                             self.es.query({"Portal":self.command.split(" ")[1]}, self.index), op = "topList"),top = 10)
        elif self.command.startswith('/a10'):
          self.sendMessage(self.createReturnString(
                             self.es.query({"Agent":self.command.split(" ")[1]}, self.index), op = "topList"),top = 10)
        elif self.command.startswith('/pic'):
          self.bot.sendMessage(self.chat_id, "https://source.unsplash.com/random")
  
      else:
        print "Wrong groupid: " + str(msg["chat"]["id"])
    else:
      print "Not a group"

if __name__ == '__main__':

  helptext  = "Usage: %s" % sys.argv[0]
  helptext += """Needed ENV variables:
                 TOKEN -> telegram bot token
                 ELASTIC -> elasticsearch server ip
                 ES_INDEX -> elasticsearch index
                 GROUPID -> telegram group to bind
                 ADMIN -> addtionial telegram admin user 
              """

  try:    token   = os.environ['TOKEN']
  except: sys.exit(helptext)

  try:    elastic = os.environ['ELASTIC']
  except: sys.exit(helptext) 
  
  try:    index   = os.environ['ES_INDEX']
  except: sys.exit(helptext) 
 
  try:    groupid = os.environ['GROUPID']
  except: sys.exit(helptext) 

  try:    admin   = os.environ['ADMIN']
  except: sys.exit(helptext) 

  if token and elastic and index and groupid and admin:
    telebot(token, elastic, index, groupid, admin).run()
  else:
    sys.exit(helptext)

