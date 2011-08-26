#!/usr/bin/python
# Reddit pics downloader
from requests import get
from json import loads
from os.path import exists
from os import mkdir
import urllib2
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
        u = urllib2.urlopen(url)
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        f = open(file_name, 'wb')
        print "Downloading: %s Bytes: %s" % (file_name, file_size)

        file_size_dl = 0
        block_sz = 8192
        while True:
            buffer = u.read(block_sz)
            if not buffer:
                break

            file_size_dl += len(buffer)
            f.write(buffer)
            status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100.
            / file_size)
            status = status + chr(8) * (len(status) + 1)
            print status,

        f.close()
    except IndexError:
        print "Failed %s" % url
    except urllib2.URLError:
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
        PAGES = sys.argv[2]
    except IndexError:
        print "Pages not specified, defaulting to one."
        PAGES = 1

    urls = []
    after = None
    for subreddit in subreddits:
        for i in range(int(PAGES)):
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
            except urllib2.HTTPError:
                print "HTTP Error while downloading %s" % url
            except ExistsError:
                print "Skipping %s, file exists." % url
