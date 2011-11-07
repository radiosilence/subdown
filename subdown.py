#!/usr/bin/python2.7
# Reddit pics downloader
from multiprocessing import Process, Pool, TimeoutError, Value, Array
from requests import get, TooManyRedirects
from json import loads, dumps
from os.path import exists, getsize, abspath
from os import mkdir, utime
from threading import Thread
import os
import time
import re
import sys
import subprocess
import xmlrpclib

class UsageError(Exception):
    pass


class InvalidURLError(BaseException):
    pass


class ExistsError(Exception):
    pass

class State:
    active = False
    def __init__(self, active):
        self.active = active
    def activate(self):
        self.active = True
    def deactivate(self):
        self.active = False
    @property
    def state(self):
        return self.active

def find_url(url):
    if re.search(r"(jpg|png|jpeg|gif)$", url):
        return url
    else:
        mo = re.search(r"http://imgur\.com/([a-zA-Z0-9]+)", url)
        if mo != None:
            return "http://i.imgur.com/%s.jpg" % mo.group(1)
        else:
            raise InvalidURLError


def get_urls(children):
    urls = []
    for sub in children:
        url = sub['data']['url']
        stamp = int(sub['data']['created'])
        try:
            xurl = find_url(url)
            urls.append({
                'href': xurl,
                'time': stamp,
                'subreddit': sub['data']['subreddit']
            })
        except InvalidURLError:
            pass
    return urls


def spider_subreddit(subreddit, pages):
    aria2 = xmlrpclib.ServerProxy('http://localhost:6800/rpc').aria2
    print "Spidering subreddit %s (%s pages)" % (subreddit, pages)
    after = None
    gids = []
    for i in range(pages):
        print "Loading page", i + 1, 'of /r/%s' % subreddit
        r = get('http://www.reddit.com/r/%s/.json?count=%s&after=%s' %
            (subreddit, 25 * i, after))
        j = loads(r.content)
        after = j['data']['after']
        urls = get_urls(j['data']['children'])

        if subreddit != urls[0]['subreddit']:
            print "Correcting case /r/%s ==> /r/%s" % \
                (subreddit, urls[0]['subreddit'])
            subreddit = urls[0]['subreddit']

        for url in urls:
            d = download_file(url, aria2)
            if d:
                gids.append(d)
    return gids

def get_filename(url):
    return "%s/%s" % (url['subreddit'], url['href'].split('/')[-1])

def update_time(url):
    utime(get_filename(url), (nows, url['time']))

def download_file(url, aria2):
    subreddit = url['subreddit']
    try:
        mkdir(subreddit)
    except OSError:
        pass
    file_name = get_filename(url)
    if file_name.split('/')[-1] == 'a.jpg':
        return None
    directory = "/".join(file_name.split("/")[:-1])
    try:
        if exists(file_name):
            if not remove_broken_file(url):
                raise ExistsError
        gid = aria2.addUri([url['href']], {
            'out': file_name
        })
        return gid
    except ExistsError:
        print "Skipping %s, file exists." % file_name
        return None

def remove_broken_file(url):
    file_name = get_filename(url)
    if getsize(file_name) < 50:
        os.remove(file_name)
        return True
    return False

GIDS = []
def main():
    try:
        subreddits = sys.argv[1].split(',')
        if subreddits[0] == '--help':
            raise UsageError()
    except (IndexError, UsageError):
        print "Usage: subdown.py <subreddit[,subreddit]> [pages]"
        exit()

    try:
        pages = int(sys.argv[2])
    except IndexError:
        print "Pages not specified, defaulting to one."
        pages = 1

    null = open(os.devnull, 'w')
    p = subprocess.Popen([
        'aria2c',
        '--enable-rpc',
        '--allow-overwrite',
        '-j', '10',

    ], stdout=null)
    results = []


    spiders = Pool(processes=4)

    for subreddit in subreddits:
        result = spiders.apply_async(
            spider_subreddit,
            (subreddit, pages),
            callback=extend_gids
        )
        results.append(result)
    
    state = State(True)
    display = Thread(target=show_status, args=(GIDS, state))
    display.start()
    for result in results:
        result.wait()
    state.value = False
    display.join()
    p.terminate()
    null.close()

def extend_gids(gids):
    GIDS.extend(gids)


class State:
    def __init__(self, value):
        self.value = value



def show_status(gids, state):
    i = 0
    spinner = ['-', '\\', '|', '/']
    incomplete = 0
    import pprint
    pp = pprint.PrettyPrinter(indent=2)
    while incomplete > 0 or state.value == True or len(gids) == 0:
        time.sleep(0.1)
        statuses = []
        incomplete = 0
        complete = 0
        error = 0
        s = xmlrpclib.ServerProxy('http://localhost:6800/rpc')
        mc = xmlrpclib.MultiCall(s)
        for gid in gids:
            mc.aria2.tellStatus(gid)
        r = mc()

        for s in list(r):
            uri = s['files'][0]['uris'][0]['uri']
            if len(uri) > 28:
                uri = uri[:25] + '...'
            if s['status'] == 'complete':
                complete += 1
                statuses.append('%s: %s' % (uri, s['status']))
            elif s['status'] == 'error':
                error += 1
                statuses.append('%s: %s' % (uri, s['status']))
            else:
                incomplete += 1
                statuses.append('%s: %s [%sKB/%sKB]' % (
                    uri, s['status'],
                    float(s['completedLength']) / 1024.0,
                    float(s['totalLength']) / 1024.0))
            
        os.system(['clear', 'cls'][os.name == 'nt'])
        print "\n".join(statuses)
        print "%s complete, %s incomplete, %s error." % \
            (complete, incomplete, error), spinner[i % 4]
        i += 1
    return True


if __name__ == '__main__':
    main()
