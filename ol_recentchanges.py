#!/usr/bin/python

import irclib
import urllib
import time
from datetime import datetime

import sys
sys.path.append('/petabox/sw/lib/python')
import simplejson as json

def get_recent_changes():
    try:
        f = urllib.urlopen("http://openlibrary.org/recentchanges.json?bot=false&limit=100")
    except IOError:
        print "get_recent_changes() Connection timed out"
        return None
    
    contents = f.read()
    f.close()
    
    try:
        obj = json.loads(contents)
    except ValueError:
        print 'got ValueError trying to deserialize contents: ' + contents
        return None
    else:
        #print obj
        return obj
    
def get_title(key):
    try:
        f = urllib.urlopen("http://openlibrary.org" + key + '.json')
    except IOError:
        print "get_title() Connection timed out"
        return key
        
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
    if None == rc:
        return datetime.min
    else:
        timestamp = rc[0]['timestamp']
        return str2datetime(timestamp)

lastdate = get_latest_timestamp()

print "joining irc..."
irc = irclib.IRC()
server = irc.server()
server.connect("irc.freenode.net", 6667, "ol_rc")
server.join("#openlibrary_rc", 'hi')

while True:
    irc.process_once()
    print 'sleeping 60 seconds'
    time.sleep(60)
    
    rc = get_recent_changes()
    if None == rc:
        continue
        
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

        lastdate = dt
        
        #print edit
        

        author = edit['author']
        if author:
            user = author[u'key']
            if 0 == user.find('/people/'):
                user = user[8:]
        else:
            user = edit['ip']        
           
        comment = edit['comment']
        
        numChanges = len(edit['changes'])
        print "  got %d changes" % (numChanges)
        
        for c in edit['changes'][0:10]: #limit to 10 to avoid irc flood
            title = get_title(c['key'])
            
            b = int(c['revision'])
            if 1 == b:
                a = 1
            else:
                a = b-1
            
            diffUrl = 'http://openlibrary.org%s?b=%d&a=%d&_compare=Compare&m=diff' % (c['key'], b, a)
        
            change = '[[%s]] %s * %s (%s) /* %s */' % (title, diffUrl, user, timestamp, comment)
    
            server.privmsg("#openlibrary_rc", change.encode('ascii', 'ignore'))
            print change
            print
            time.sleep(1)
    
