#!/usr/bin/env python
# coding: utf-8
import datetime
import re
import sys
from collections import namedtuple
import os
import time
import simplejson as json
import requests
import mimetypes

from clint.textui import puts, indent, colored

import gevent
from gevent import monkey; monkey.patch_socket()

subreddits = ['HistoryPorn', 'bondage']
max_count = 20

TEMPLATE = 'http://www.reddit.com/r/{}/.json?count={}&after={}'

Submission = namedtuple('Submission',
    'url filename created subreddit')


def useful_part(url):
    return url.split('/')[-1].split('?')[0].split('#')[0]


def url_filename(url):
    if re.search(r'imgur\.com', url) and not re.search(r'i.imgur\.com', url):
        return '{}.jpg'.format(
            useful_part(url)
        )
    else:
        return useful_part(url)


def fix_url(url):
    if re.search(r'imgur\.com', url) and not re.search(r'i.imgur\.com', url):
        return 'http://i.imgur.com/{}.jpg'.format(
            useful_part(url)
        )
    else:
        return url


def get_page(subreddit, count, after, max_count):
    url = TEMPLATE.format(subreddit, count, after)
    result = requests.get(url, timeout=2)
    puts('{} {} (Page {} of {})'.format(colored.green('==>'), subreddit,
        count + 1, max_count))
    try:
        if result.status_code != 200:
            raise Exception
        data = json.loads(result.content)['data']
    except:
        raise Exception('404 Not Found')
    return data['children'], result.encoding, data['after']


def get_subreddit(subreddit, max_count, count=0, after=None):
    while count < max_count:
        children, encoding, after = get_page(subreddit, count, after,
            max_count)
        download_children(children, encoding)
        count += 1


def download_children(children, encoding):
    def valid(child):
        exts = ('jpg', 'jpeg', 'png', 'gif')
        return url_filename(child['data']['url']).split('.')[-1] in exts
    jobs = []
    quote = '  {} '.format(colored.blue('->'))
    with indent(len(quote), quote=quote):
        for child in filter(valid, children):
            url = child['data']['url']
            filename = url_filename(url)
            submission = Submission(
                fix_url(url),
                filename.encode(encoding),
                datetime.datetime.fromtimestamp(child['data']['created']),
                subreddit
            )
            jobs.append(gevent.spawn(download_submission, submission))

        gevent.joinall(jobs, timeout=10)
        for job in jobs:
            if not job.value:
                puts(colored.red('Timed out {}'.format(
                    job.args[0].filename)))
                job.kill()


def set_utime(path, created):
    timestamp = time.mktime(created.timetuple())
    os.utime(path, (timestamp, timestamp))


def download_submission(s):
    path = '{}/{}'.format(
        s.subreddit,
        s.filename
    )
    if not os.path.exists(s.subreddit):
        os.mkdir(s.subreddit)

    if os.path.exists(path):
        puts('Skipping (exists) {}'.format(path))
        set_utime(path, s.created)
        return True

    puts('Adding {}'.format(path))
    try:
        r = requests.get(s.url, timeout=5)
    except Exception as e:
        puts(colored.red('Error: {} <{}>'.format(
            path,
            str(e)
        )))
        return True

    with open(path, 'w') as f:
        f.write(r.content)
    puts('Downloaded {}'.format(path))
    set_utime(path, s.created)
    return True


def fix_subreddit_name(subreddit):
    url = TEMPLATE.format(subreddit, '', '')
    return json.loads(
        requests.get(url).content)['data']['children'][0]['data']['subreddit']


if __name__ == '__main__':
    for subreddit in subreddits:
        try:
            subreddit = fix_subreddit_name(subreddit)
        except:
            puts(colored.red('Failed to load subreddit {}'.format(subreddit)))
            continue
        try:
            get_subreddit(subreddit, max_count)
        except Exception as e:
            raise
            puts(colored.red(str(e)))

# urls = [url.format(port) for port in [8051, 8052]]
# jobs = [gevent.spawn(requests.get, url) for url in urls]
# gevent.joinall(jobs, timeout=4)
# print [job.value for job in jobs]