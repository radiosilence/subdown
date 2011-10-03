#!/usr/bin/python2.7
# Reddit pics downloader
from multiprocessing import Process, Pool, TimeoutError
from requests import get, TooManyRedirects
from json import loads
from os.path import exists
from os import mkdir, utime
import time
import re
import sys

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
            urls.append({'href': xurl, 'time': stamp, 'subreddit': sub['data']['subreddit']})
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

    if subreddit != urls[0]['subreddit']:
        print "Correcting case /r/%s ==> /r/%s" % (subreddit, urls[0]['subreddit'])
        subreddit = urls[0]['subreddit']
    print 'Downloading images for /r/%s' % subreddit
    p = Pool(processes=20)
    result = p.map_async(download_file, [(url, subreddit) for url in urls])
    try:
        result.get()
    except TimeoutError:
        print "Unfortunately, /r/%s took took long." % subreddit
    sys.exit()


def download_file(args):
    url = args[0]
    subreddit = args[1]
    file_name = url['href'].split('/')[-1]
    try:
        mkdir(subreddit)
    except OSError:
        pass
    file_name = "%s/%s" % (subreddit, file_name)

    try:
        if exists(file_name):
            raise ExistsError

        opened = False
        while not opened:
            try:
                f = open(file_name, 'wb')
                opened = True
            except IOError:
                pass

        try:
            r = get(url['href'], timeout=10)

            try:
                print 'Downloading %s, file-size: %2.2fKB' % \
                    (url['href'], float(r.headers['content-length']) \
                        / 1000)
            except TypeError:
                print "%s Downloading %s, file-size: Unknown" % \
                    (tag, url['href'])
            f.write(r.content)
            message =  "%s Finished!" % url['href']
        except TooManyRedirects:
            message = "Too many redirects for file %s." % url['href']
        except (IndexError, AttributeError):
            message = "Failed %s" % url['href']
        f.close()
    except ExistsError:
            message = "Skipping %s, file exists." % file_name
    nows = int(time.time())
    utime(file_name, (nows, url['time']))
    print message
    return message

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
        Process(target=spider, args=(subreddit, int(pages))).start()
        
        
if __name__ == '__main__':
    main()
