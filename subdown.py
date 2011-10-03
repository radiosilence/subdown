#!/usr/bin/python2.7
# Reddit pics downloader
import threading
from requests import get, TooManyRedirects
from json import loads
from os.path import exists
from os import mkdir, utime
import time
import re
import sys

#global open_files, OPEN_FILE_LIMIT

OPEN_FILE_LIMIT = 512

open_files = 0


class UsageError(Exception):
    pass


class InvalidURLError(BaseException):
    pass


class ExistsError(Exception):
    pass


def find_url(url):
    if re.search(r"(jpg|png|jpeg)$", url):
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
            urls.append({'href': xurl, 'time': stamp})
            print "Added image %s" % xurl
        except InvalidURLError:
            print "No image found at %s" % url
    return urls


def spider(subreddit, pages):
    print "Spidering subreddit %s (%s pages)" % (subreddit, pages)
    after = None
    urls = []
    for i in range(pages):
        print "Loading page", i + 1, 'of /r/%s' % subreddit
        r = get('http://www.reddit.com/r/%s/.json?count=%s&after=%s' %
            (subreddit, 25 * i, after))
        j = loads(r.content)
        after = j['data']['after']
        
        urls.extend(get_urls(j['data']['children']))

    print 'Downloading images for /r/%s' % subreddit
    i = 1
    num_urls = len(urls)
    for url in urls:
        threading.Thread(target=download_file, \
            args=(url, subreddit, num_urls, i)).start()
        i += 1


def download_file(url, subreddit, total, num):
    file_name = url['href'].split('/')[-1]
    global open_files, OPEN_FILE_LIMIT
    tag = '[/r/%s:%d/%d]' % (subreddit, num, total)
    try:
        mkdir(subreddit)
    except OSError:
        pass
    file_name = "%s/%s" % (subreddit, file_name)

    try:
        if exists(file_name):
            raise ExistsError
        while open_files > OPEN_FILE_LIMIT:
            pass
        open_files += 1
        f = open(file_name, 'wb')
        try:
            r = get(url['href'])

            try:
                print '%s Downloading %s, file-size: %2.2fKB' % \
                    (tag, url['href'], float(r.headers['content-length']) \
                        / 1000)
            except TypeError:
                print "%s Downloading %s, file-size: Unknown" % \
                    (tag, url['href'])
            f.write(r.content)
            print "%s %s Finished!" % (tag, url['href'])
        except TooManyRedirects:
            print "Too many redirects for file %s." % url['href']
        except (IndexError, AttributeError):
            print "%s Failed %s" % (tag, url['href'])
        f.close()
        open_files += -1
    except ExistsError:
            print "%s Skipping %s, file exists." % (tag, file_name)
    nows = int(time.time())
    utime(file_name, (nows, url['time']))

def main():
    try:
        subreddits = sys.argv[1].split(',')
        if subreddits[0] == '--help':
            raise UsageError()
    except (IndexError, UsageError):
        print "Usage: subdown.py <subreddit[,subreddit]> [pages]"
        exit()

    try:
        pages = sys.argv[2]
    except IndexError:
        print "Pages not specified, defaulting to one."
        pages = 1

    for subreddit in subreddits:
        threading.Thread(target=spider, args=(subreddit, int(pages))).start()
        
        
if __name__ == '__main__':
    main()
