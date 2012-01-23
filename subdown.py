"""
subdown.py
==========

This is a script that is made to quickly access the reddit API and download
images from specified subreddits.

Future goals include the ability to visit linked pages and scrape for large
images.
"""

import os, sys

import json

from twisted.internet import reactor
from twisted.web.client import getPage, downloadPage
from twisted.internet.defer import DeferredList

class Submission(object):
    def __init__(self, child, subreddit):
        self.data = child['data']
        self.subreddit = self.data['subreddit']
    
    @property
    def directory(self):
        """Returns the directory without the filename"""
        return self.subreddit

    @property
    def url(self):
        """Returns the URL"""
        return self.data['url']

    @property
    def file_name(self):
        """Returns file name without path"""
        return self.url.split('/')[-1]

    @property
    def ext(self):
        """Returns file extension"""
        return self.file_name.split('.')[-1]
    
    @property
    def file_path(self):
        """Returns the complete path and filename"""
        return '%s/%s' % (self.directory, self.file_name)

    def checkCreateDir(self):
        """Checks if the directory exists, and if not, creates it"""
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)

    def updateModifiedTime(self):
        """Changes the file date on a downloaded file to match that of the
        submission
        """
        os.utime(self.file_path, (0, self.data['created']))

    def process(self):
        """Returns a deferred(?) that will either:
            1. Download an image directly.
            2. Scrape the page of a link (ie a tumblr).
            3. Does nothing because it's not the kind of link we want.
        """

        def fileDateCallback(result):
            """wraps update modified time"""
            self.updateModifiedTime()

        def checkFileSize(result):
            """Fail on files lower than a set size"""
            print "checking file size", self.file_path
            if os.path.getsize(self.file_path) < 20*1024:
                raise TooSmallError

        def deleteFile(failure):
            """Delete the resulting file."""
            failure.trap(TooSmallError)
            print "deleting file", self.file_path
            os.remove(self.file_path)

        def writeError(failure):
            """If there's a problem writing the file for instance if the 
            directory does not exist.
            """

            failure.trap(IOError)
            print failure.getErrorMessage()

        def finishChild(result):
            print "Finished child", self.subreddit, self.file_path, self.url

        
        if os.path.exists(self.file_path):
            raise FileExistsError

        self.checkCreateDir()

        if self.ext in ['jpg', 'png', 'gif']:
            d = downloadPage(str(self.url), self.file_path)
        else:
            raise UnknownLinkError(self.url)
        
        d.addCallback(checkFileSize)
        d.addCallbacks(fileDateCallback, deleteFile)
        d.addErrback(writeError)
        d.addBoth(finishChild)
        print "trying to download", str(self.url), self.file_path
        self.d = d
        return d

class UnknownLinkError(Exception):
    """This error is thrown when the program does not know what to do with a
    link.
    """
    pass

class FileExistsError(Exception):
    """This is an exception raised when the file that would be downloaded from
    a submission is already on the disk.
    """
    pass


class TooSmallError(Exception):
    """Raised if the file is under 20Kb (so probably not a useful image."""
    pass


class UsageError(Exception):
    """Raised if the command line is wrong"""
    pass


def subredditCallback(page, subreddit, max_count, count=1, after=None):
    """Load a page of a subreddit, download links, and recursively call self
    on next page for as many pages as required."""
    data = json.loads(page)['data']

    previous_after = None  # no idea how to get this either

    dlist = []
    if data['children']:
        for child in data['children']:
            try:
                submission = Submission(child, subreddit)
                d = submission.process()
                dlist.append(d)
                print "Added ", submission.url
            except UnknownLinkError:
                print "Didn't know how to handle link.", submission.url
            except FileExistsError:
                submission.updateModifiedTime()
                print "File already exists.", submission.file_path

    if data['after'] != previous_after and count < max_count:
        new_count = count + 1

        d = getPage(str('http://www.reddit.com/r/%s/.json?count=%s&after=%s'
            % (subreddit, new_count, data['after'])))
        d.addCallback(subredditCallback,
            subreddit, max_count, new_count, data['after'])
        dlist.append(d)
    
    return DeferredList(dlist)

def finish(ign):
    print "Reached the finish!"
    reactor.stop()

def main(subreddits, max_count):
    dlist = []
    for subreddit in subreddits:
        d = getPage('http://www.reddit.com/r/%s/.json' % subreddit)
        d.addCallback(subredditCallback, subreddit, max_count)
        dlist.append(d)
    
    d = DeferredList(dlist)
    d.addCallback(finish)

if __name__ == '__main__':
    try:
        subreddits = sys.argv[1].split(',')
        if subreddits[0] == '--help':
            raise UsageError()
    except (IndexError, UsageError):
        print "Usage: subdown.py <subreddit[,subreddit]> [pages]"
        exit()
    try:
        max_count = int(sys.argv[2])
    except IndexError:
        print "Pages not specified, defaulting to one."
        max_count = 1

    main(subreddits, max_count)
    reactor.run()
