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

from docopt import docopt
from clint.textui import puts, indent, colored

import gevent
from gevent import monkey; monkey.patch_socket()

NAME = 'subdown'
VERSION = '0.2.2'
AUTHOR = 'James Cleveland'
SHORT_DESC = 'subreddit image scraper'

__doc__ = """{2}

Usage:
    {0} [options] <subreddit> [<subreddit>...]
    {0} -h | --help
    {0} --version

Options:
    -h --help                   Show this screen.
    --version                   Show version.
    -p --pages=COUNT            Number of pages to grab [default: 1].
    -t --timeout=SECONDS        Timeout for individual images [default: 5].
    -T --page-timeout=SECONDS   Timeout for subreddit pages [default: 20].
""".format(
    NAME,
    VERSION,
    SHORT_DESC
)

TEMPLATE = 'http://www.reddit.com/r/{}/.json?count={}&after={}'

Submission = namedtuple('Submission',
    'url filename created subreddit')


def useful_part(url):
    return url.split('/')[-1].split('?')[0].split('#')[0]


def fix_url(url):
    is_imgur = re.search(r'imgur\.com', url)
    is_file = re.search(r'\.(jpg|png|gif|jpeg)', url)
    if is_imgur and not is_file :
        return 'http://i.imgur.com/{}.jpg'.format(
            useful_part(url)
        )
    else:
        return url


def get_subreddit(subreddit, max_count, timeout, page_timeout):
    count = 0
    after = None
    prev_after = None
    while count < max_count:
        children, encoding, after = get_page(subreddit, count, after,
            max_count, page_timeout)
        download_submissions(subreddit, children, encoding, timeout, page_timeout)
        if prev_after == after:
            puts('Subreddit exhausted')
            break
        prev_after = after
        count += 1


def get_page(subreddit, count, after, max_count, page_timeout):
    url = TEMPLATE.format(subreddit, count, after)
    result = requests.get(url, timeout=page_timeout)
    puts('{} {} (Page {} of {})'.format(colored.green('==>'), subreddit,
        count + 1, max_count))
    try:
        if result.status_code != 200:
            raise Exception
        data = json.loads(result.content)['data']
    except:
        raise Exception('404 Not Found')
    return data['children'], result.encoding, data['after']


def download_submissions(subreddit, children, encoding, timeout, page_timeout):
    def valid(child):
        exts = ('jpg', 'jpeg', 'png', 'gif')
        ext = useful_part(fix_url(child['data']['url'])).split('.')[-1]
        return ext in exts
    jobs = []
    quote = '  {} '.format(colored.blue('->'))

    with indent(len(quote), quote=quote):
        for child in filter(valid, children):
            url = fix_url(child['data']['url'])
            filename = useful_part(url)
            submission = Submission(
                fix_url(url),
                filename.encode(encoding),
                datetime.datetime.fromtimestamp(child['data']['created']),
                subreddit
            )
            jobs.append(gevent.spawn(
                download_submission,
                submission,
                timeout
            ))

        gevent.joinall(jobs, timeout=page_timeout)
        for job in jobs:
            if not job.value:
                puts(colored.red('Timed out {}'.format(
                    job.args[0].filename)))
                job.kill()


def download_submission(s, timeout):
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

    puts('Added {}'.format(path))
    try:
        r = requests.get(s.url, timeout=timeout)
        if r.status_code != 200:
            raise Exception('Non-200 status code (image may not exist)')
        if int(r.headers['content-length']) < (1024 * 5):
            raise Exception('Image size less than 5KB, skipping')
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


def set_utime(path, created):
    timestamp = time.mktime(created.timetuple())
    os.utime(path, (timestamp, timestamp))


def fix_subreddit_name(subreddit):
    url = TEMPLATE.format(subreddit, '', '')
    return json.loads(
        requests.get(url).content)['data']['children'][0]['data']['subreddit']


def subdown(args):
    def coerce_or_die(args, arg, f=int):
        try:
            try:
                val = f(args[arg])
                if val < 0:
                    raise Exception('{} must be positive.'.format(arg))
                return val
            except ValueError:
                raise Exception('{} must be coercable to {}.'.format(arg, f))
        except Exception as e:
            puts(colored.red(str(e)))
            sys.exit(1)
    
    timeout = coerce_or_die(args, '--timeout', f=float)
    page_timeout = coerce_or_die(args, '--page-timeout', f=float)
    max_count = coerce_or_die(args, '--pages')
    subreddits = args['<subreddit>']
    for subreddit in subreddits:
        try:
            subreddit = fix_subreddit_name(subreddit)
        except:
            puts(colored.red('Failed to load subreddit {}'.format(subreddit)))
            continue
        try:
            get_subreddit(subreddit, max_count, timeout, page_timeout)
        except Exception as e:
            raise
            puts(colored.red(str(e)))

def main():
    args = docopt(__doc__, version='{} {}'.format(
        NAME,
        VERSION))
    subdown(args)

if __name__ == '__main__':
    main()
