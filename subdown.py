#!/usr/bin/env python
# coding: utf-8

from collections import namedtuple

import simplejson as json
import requests

from clint.textui import puts, indent, colored

import gevent
from gevent import socket
from gevent import monkey; monkey.patch_socket()

subreddits = ['HistoryPorn',]
max_count = 2

TEMPLATE = 'http://reddit.com/r/{}/.json?count={}&after={}'

#url = 'http://localhost:{}'


def get_page(subreddit, page, after):
    url = TEMPLATE.format(subreddit, page, after)
    result = requests.get(url, timeout=2)
    puts('Getting page')
    try:
        if result.status_code != 200:
            raise Exception
        data = json.loads(result.content)['data']
    except:
        raise Exception('404 Not Found')
    return data['children'], data['after']

def get_subreddit(subreddit, max_count, count=0, after=None):
    while count < max_count:
        quote = colored.yellow('[{}/{}] '.format(count + 1, max_count))
        with indent(len(quote), quote=quote):
            children, after = get_page(subreddit, count, after)
            download_children(children)
        count += 1

def download_children(children):
    def valid(child):
        return True

    puts("Downloading children")
    for child in filter(valid, children):
        url = child['data']['url']
        quote = u'{} '.format(unicode(url)).encode('utf-8')
        if len(quote) > 30:
            quote = u'{}... '.format(quote[:19])
        with indent(len(quote), quote=quote):
            puts("Downloading")
if __name__ == '__main__':
    for subreddit in subreddits:
        quote = colored.magenta(' -> {}'.format(subreddit))
        with indent(len(quote), quote=quote):
            try:
                get_subreddit(subreddit, max_count)
            except Exception as e:
                puts(colored.red(str(e)))

# urls = [url.format(port) for port in [8051, 8052]]
# jobs = [gevent.spawn(requests.get, url) for url in urls]
# gevent.joinall(jobs, timeout=4)
# print [job.value for job in jobs]