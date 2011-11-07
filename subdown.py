#!/usr/bin/python2.7
# Reddit pics downloader
from multiprocessing import Process, Pool, Manager
from requests import get, TooManyRedirects
from json import loads, dumps
from os.path import exists, getsize, abspath
from os import mkdir, utime
from threading import Thread
import os
import time
from datetime import datetime
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
    def __init__(self, value):
        self.value = value

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


def spider_subreddit(subreddit, pages, gids, skipped, subreddit_progress, time_register):
    aria2 = xmlrpclib.ServerProxy('http://localhost:6800/rpc').aria2
    after = None
    for i in range(pages):
        r = get('http://www.reddit.com/r/%s/.json?count=%s&after=%s' %
            (subreddit, 25 * i, after))
        j = loads(r.content)
        if after == j['data']['after']:
            break
        after = j['data']['after']
        urls = get_urls(j['data']['children'])

        if subreddit != urls[0]['subreddit']:
            subreddit = urls[0]['subreddit']
        subreddit_progress[subreddit] = i+1

        for url in urls:
            if url['href'].split('/')[-1] == 'a.jpg':
                continue
            time_register[get_filename(url)] = url['time']
            d = download_file(url, aria2, skipped, time_register)
            if d:
                gids.append(d)

    subreddit_progress[subreddit] = '%s (Done)' % \
        subreddit_progress[subreddit]
    
    return gids

def get_filename(url):
    return "%s/%s" % (url['subreddit'], url['href'].split('/')[-1])

def download_file(url, aria2, skipped, time_register):
    subreddit = url['subreddit']
    try:
        mkdir(subreddit)
    except OSError:
        pass
    file_name = get_filename(url)
    
    directory = "/".join(file_name.split("/")[:-1])
    try:
        if exists(file_name) and not exists(file_name + '.aria2'):
            if not remove_broken_file(url):
                raise ExistsError
        gid = aria2.addUri([url['href']], {
            'out': file_name
        })
        return gid
    except ExistsError:
        skipped.value += 1
        return None

def remove_broken_file(url):
    file_name = get_filename(url)
    if getsize(file_name) < 50:
        os.remove(file_name)
        return True
    return False

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
    
    manager = Manager()

    null = open(os.devnull, 'w')
    p = subprocess.Popen([
        'aria2c',
        '--enable-rpc',
        '--allow-overwrite',
        '-j', '20'
    ], stdout=null)
    xrpc = xmlrpclib.ServerProxy('http://localhost:6800/rpc')
    results = []
    spiders = Pool(processes=4)

    gids = manager.list()
    skipped = manager.Value('i', 0)
    subreddit_progress = manager.dict()
    time_register = manager.dict()
    state = manager.Value('i', 1)

    for subreddit in subreddits:
        result = spiders.apply_async(
            spider_subreddit,
            (subreddit, pages, gids, skipped,
                subreddit_progress, time_register)
        )
        results.append(result)
    
    display = Thread(target=show_status, args=(
        gids, state, skipped, subreddit_progress, time_register
    ))
    display.start()
    for result in results:
        result.wait()
    state.value = 0
    display.join()
    xrpc.aria2.forceShutdown()

    now = datetime.now()
    for file_name, when in time_register.items():
        utime(file_name, (time.time(), when))
    time.sleep(1)
    p.terminate()
    null.close()

def show_status(gids, state, skipped, subreddit_progress, time_register):
    i = 0
    spinner = ['-', '\\', '|', '/']
    incomplete = 0
    complete = 0
    while incomplete > 0 or state.value == 1:
        time.sleep(0)
        statuses = []
        incomplete = 0
        error = 0
        xrpc = xmlrpclib.ServerProxy('http://localhost:6800/rpc')
        active = xrpc.aria2.tellActive()
        for s in active:
            uri = s['files'][0]['uris'][0]['uri']
            if len(uri) > 100:
                uri = uri[:97] + '...'
            
            if int(s['totalLength']) == 0:
                prog = 0
            else:
                prog = (int(s['completedLength']) *  20) / int(s['totalLength'])
            
            bar = '[%s%s]' % (
                '#' * prog,
                '-' * (20 - prog)
            )
            statuses.append('%s %s: %s (%sKB/%sKB)' % (
                bar, uri, s['status'],
                float(s['completedLength']) / 1024.0,
                float(s['totalLength']) / 1024.0
            ))
        waiting = xrpc.aria2.tellWaiting(0, 40)
        for s in waiting:
            uri = s['files'][0]['uris'][0]['uri']
            if len(uri) > 58:
                uri = uri[:55] + '...'
            statuses.append('[-------waiting------] %s: waiting' % uri)
            
            
        stat = xrpc.aria2.getGlobalStat()
        incomplete = int(stat['numActive']) + int(stat['numWaiting'])
        os.system(['clear', 'cls'][os.name == 'nt'])
        print "%s downloading, %s waiting, %s complete, %s incomplete, %s error, %s skipped." % \
                (stat['numActive'],
                    stat['numWaiting'],
                    stat['numStopped'], incomplete, error, skipped.value), spinner[i % 4],
        if state.value:
            print "(scanning subreddits)"
        else:
            print ""

        for k, v in subreddit_progress.items():
            print '%s: Page %s' % (k, v)
        print "\n".join(statuses[:40])
        i += 1
    return True


if __name__ == '__main__':
    main()
