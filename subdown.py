#!/usr/bin/python
# Reddit pics downloader
from requests import get
from json import loads
from os.path import exists
from os import mkdir
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
        try:
            xurl = find_url(url)
            urls.append(xurl)
            print "Added image %s" % xurl
        except InvalidURLError:
            print "No image found at %s" % url
    return urls


def download_file(url, subreddit=None):
    file_name = url.split('/')[-1]

    if subreddit:
        try:
            mkdir(subreddit)
        except OSError:
            pass
        file_name = "./%s/%s" % (subreddit, file_name)

    if exists(file_name):
        raise ExistsError

    try:
        r = get(url)
        f = open(file_name, 'wb')
        print 'Downloading %s, file-size: %2.2fKB' % \
            (url, float(r.headers['content-length']) / 1000)
        f.write(r.content)
        f.close()
    except IndexError:
        print "Failed %s" % url

if __name__ == '__main__':
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
        after = None
        urls = []
        for i in range(int(pages)):
            print "Loading page", i + 1, 'of /r/%s' % subreddit
            r = get('http://www.reddit.com/r/%s/.json?count=%s&after=%s' %
                (subreddit, 25 * i, after))
            j = loads(r.content)
            after = j['data']['after']
            print after
            urls.extend(get_urls(j['data']['children']))

        for url in urls:
            try:
                download_file(url, subreddit)
            except ExistsError:
                print "Skipping %s, file exists." % url
