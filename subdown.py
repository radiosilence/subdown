#!/usr/bin/env python
# coding: utf-8
import datetime
from collections import namedtuple

import simplejson as json
import requests

from clint.textui import puts, indent, colored

import gevent
from gevent import socket
from gevent import monkey; monkey.patch_socket()

subreddits = ['HistoryPorn',]
max_count = 2

TEMPLATE = 'http://www.reddit.com/r/{}/.json?count={}&after={}'

Submission = namedtuple('Submission', 'url filename created')

#url = 'http://localhost:{}'


def get_page(subreddit, page, after):
    url = TEMPLATE.format(subreddit, page, after)
    result = requests.get(url, timeout=2)
    puts('Getting page')
    puts(url)
    try:
        if result.status_code != 200:
            raise Exception
        data = json.loads(result.content)['data']
    except:
        raise Exception('404 Not Found')
    return data['children'], result.encoding, data['after']

def get_subreddit(subreddit, max_count, count=0, after=None):
    while count < max_count:
        quote = colored.yellow('[{}/{}] '.format(count + 1, max_count))
        with indent(len(quote), quote=quote):
            children, encoding, after = get_page(subreddit, count, after)
            download_children(children, encoding)
        count += 1

def download_children(children, encoding):
    def valid(child):
        return True

    puts("Downloading children")
    jobs = []
    for child in filter(valid, children):
        url = child['data']['url']
        filename = url.split('/')[-1].split('?')[0]
        submission = Submission(
            url,
            filename,
            datetime.datetime.fromtimestamp(child['data']['created'])
        )
        puts(u'Added {}'.format(filename).encode(encoding))
        jobs.append(gevent.spawn(download_submission, submission))

    gevent.joinall(jobs, timeout=10)
    for job in jobs:
        puts(job.value)

def download_submission(submission):
    return "DOWNLOADED ;) %s" % submission.created

if __name__ == '__main__':
    for subreddit in subreddits:
        quote = ' -> {} '.format(subreddit)
        with indent(len(quote), quote=quote):
            try:
                get_subreddit(subreddit, max_count)
            except Exception as e:
                raise
                puts(colored.red(str(e)))

# urls = [url.format(port) for port in [8051, 8052]]
# jobs = [gevent.spawn(requests.get, url) for url in urls]
# gevent.joinall(jobs, timeout=4)
# print [job.value for job in jobs]