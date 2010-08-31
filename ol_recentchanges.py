#!/usr/bin/python

import irclib
import urllib
import time
from datetime import datetime

import sys
sys.path.append('/petabox/sw/lib/python')
import simplejson as json

def get_recent_changes():
    f = urllib.urlopen("http://openlibrary.org/recentchanges.json?bot=false&limit=100")
    contents = f.read()
    f.close()
    
    obj = json.loads(contents)
    #print obj
    return obj
    
def get_title(key):
    f = urllib.urlopen("http://openlibrary.org" + key + '.json')
    contents = f.read()
    f.close()   
    
    try:
        obj = json.loads(contents)
    except ValueError:
        return '(no title)'
    else:
        #print obj
        if '/type/author' == obj['type']['key']:
            return obj['name']
        elif 'title' in obj:
            return obj['title']
        else:
            return key

#sigh... python 2.5's strptime doesn't support %f
#from http://stackoverflow.com/questions/531157/parsing-datetime-strings-with-microseconds:
def str2datetime(s):
    parts = s.split('.')
    dt = datetime.strptime(parts[0], "%Y-%m-%dT%H:%M:%S")
    return dt.replace(microsecond=int(parts[1]))    

def get_latest_timestamp():
    rc = get_recent_changes()
    timestamp = rc[0]['timestamp']
    return str2datetime(timestamp)

lastdate = get_latest_timestamp()

print "joining irc..."
irc = irclib.IRC()
server = irc.server()
server.connect("irc.freenode.net", 6667, "ol_rc")
server.join("#openlibrary_rc", 'hi')
time.sleep(10)

while True:
    rc = get_recent_changes()
    rc.reverse()
    
    numEdits = len(rc)
    iEdit = 1
    
    for edit in rc:

        timestamp = edit['timestamp']
        dt = str2datetime(timestamp)

        print 'processing edit %d/%d at time %s' % (iEdit, numEdits, timestamp)
        iEdit+=1
        
        if dt <= lastdate:
            print 'already processed this date, skipping....'
            continue
        else:
            lastdate = dt
        
        #print edit
        
        numChanges = len(edit['changes'])

        if 1 == numChanges:            
            c = edit['changes'][0]
            
            title = get_title(c['key'])
            
            b = int(c['revision'])
            if 1 == b:
                a = 1
            else:
                a = b-1
            
            diffUrl = 'http://openlibrary.org%s?b=%d&a=%d&_compare=Compare&m=diff' % (c['key'], b, a)
        else:
            
            title = '(%d changes)' % numChanges
            diffUrl  = '-'

        author = edit['author']
        if author:
            user = author[u'key']
            if 0 == user.find('/people/'):
                user = user[8:]
        else:
            user = edit['ip']        
           
        comment = edit['comment']
        change = '[[%s]] %s * %s (%s) /* %s */' % (title, diffUrl, user, timestamp, comment)

        server.privmsg("#openlibrary_rc", change.encode('ascii', 'ignore'))
        irc.process_once()
        print change
        print
        time.sleep(1)
    
    print 'sleeping 60 seconds'
    time.sleep(60)
