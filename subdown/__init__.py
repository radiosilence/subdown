"""
subdown.py
==========

This is a script that is made to quickly access the reddit API and download
images from specified subreddits.

Future goals include the ability to visit linked pages and scrape for large
images.

It is also to aid me in learning best practices with the Twisted framework.
"""

import os, sys
import json
import re

from twisted.internet import reactor
from twisted.web.client import getPage, downloadPage
from twisted.internet.defer import DeferredList, Deferred
from twisted.python import log
import twisted

from scrapers import *

RETRIES = 5

class Image(object):
    """This is an image. Most submissions will only have one image, but some
    may have many (due to scraping).
    """
    def __init__(self, url, submission, timestamp=None):
        self.submission = submission
        self.url = str(url)
        self.deferred = Deferred()
        if not timestamp:
            self.timestamp = self.submission.timestamp
        else:
            self.timestamp = timestamp

    @property
    def directory(self):
        """Returns the directory without the filename"""
        return self.submission.subreddit

    @property
    def file_name(self):
        """Returns file name without path"""
        return self.url.split('/')[-1]

    @property
    def ext(self):
        """Returns file extension"""
        return self.file_name.split('.')[-1]
    
    @property
    def tag(self):
        """Tag for prefixing log entries"""
        return '[%s:%s:%s]' % (self.submission.subreddit,
            unicode(self.submission).replace(' ', '')[:10], self.file_name)

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
        print self.tag, "Updating modified time to", self.timestamp
        os.utime(self.file_path, (self.timestamp, self.timestamp))

    def checkFileSize(self):
        """Fail on files lower than a set size"""
        min_size = 20*1024
        # print self.tag, "Checking file size"
        if os.path.getsize(self.file_path) < min_size:
            print self.tag, os.path.getsize(self.file_path), "<", min_size, "failed!"
            raise TooSmallError

    def deleteFile(self):
        """Delete the resulting file."""
        print self.tag, "Deleting file"
        try:
            os.remove(self.file_path)
        except OSError:
            pass

    def retrieve(self):
        """Returns a deferred(?) that will either:
            1. Download an image directly.
            2. Scrape the page of a link (ie a tumblr).
            3. Does nothing because it's not the kind of link we want.
        """

        def processCallback(result):
            self.updateModifiedTime()
            try:
                self.checkFileSize()
            except TooSmallError:
                self.deleteFile()
            return result

        def partialDownloadErrback(failure, retries):
            failure.trap(twisted.web.client.PartialDownloadError)
            if retries > 0:
                return downloadImage(retries-1)
            else:
                raise MaxRetriesExceededError(
                    "Partial download (max retries exceeded)")

        def connectionLostErrback(failure, retries):
            failure.trap(twisted.internet.error.ConnectionLost)
            if retries > 0:
                return downloadImage(retries-1)
            else:
                raise MaxRetriesExceededError(
                    "Connection lost (max retries exceeded)")
 
        def downloaded(result, retries):
            retries = RETRIES - retries
            print self.tag, "Image downloaded", 
            if retries == 1:
                print "after %s retry." % retries
            elif retries > 1:
                print "after %s retries." % retries
            else:
                print "on first try."
            
            self.deferred.callback(True)
        

        def failed(failure):
            print self.tag, "Failed:", failure.getErrorMessage()
            self.deferred.callback(False)
            
        def downloadImage(retries=RETRIES):
            d = downloadPage(self.url, self.file_path)
            d.addCallback(processCallback)
            d.addCallback(downloaded, retries)


            d.addErrback(partialDownloadErrback, retries)
            d.addErrback(connectionLostErrback, retries)
            d.addErrback(failed)

            return d


        if os.path.exists(self.file_path):
            raise FileExistsError

        self.checkCreateDir()
        downloadImage()
        return self.deferred

class Submission(object):
    """Represents a single submission and provides associated processing
    functions.
    """
    def __init__(self, child, subreddit):
        self.data = child['data']
        self.subreddit = self.data['subreddit']
        self.images = []
        self.deferred = Deferred()
        self.image_deferreds = []

    @property
    def url(self):
        """Returns the URL"""
        return self.data['url']

    @property
    def ext(self):
        """Returns file extension"""
        return self.url.split('.')[-1]

    
    @property
    def tag(self):
        """Tag for prefixing log entries"""
        return '[%s:%s]' % (self.subreddit,
            unicode(self).replace(' ', '')[:10])

    @property
    def timestamp(self):
        """Submitted timestamp"""
        return float(self.data['created_utc'])


    def addImages(self, urls):
        for url in urls:
            self.images.append(Image(url, self))

    def processImages(self):
        for image in self.images:
            try:
                d = image.retrieve()
                self.image_deferreds.append(d)
            except FileExistsError:
                print image.tag, "File already exists."
                try:
                    image.checkFileSize()
                    image.updateModifiedTime()
                except TooSmallError:
                    image.deleteFile()

    def retrieve(self):
        def done(result):
            self.deferred.callback(0)

        def imagesCollected(result):
            self.processImages()
            dl = DeferredList(self.image_deferreds)
            dl.addCallback(done)

        deferreds = []
        if re.search(r'imgur\.com', self.url):
            scraper_deferred = ImgurScraper(self.url, self).retrieve()
            scraper_deferred.addCallback(self.addImages)
            scraper_deferred.addCallback(imagesCollected)

            deferreds.append(scraper_deferred)
        elif self.ext in ['jpg', 'png', 'gif']:
            raise UnknownLinkError(self.url)
            self.images.append(self.url)
            imagesCollecteds()
        else:
            raise UnknownLinkError(self.url)

        return self.deferred

    def __unicode__(self):
        return self.data['title']


class MaxRetriesExceededError(Exception):
    """This is thrown when something tries to download but reaches the set
    allowed amount of retries.
    """
    pass

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


class SubredditPage(object):
    def __init__(self, subreddit, max_count, count=1, after=None):
        self.subreddit = subreddit
        self.max_count = max_count
        self.after = after
        self.count = count
    
    def retrieve(self):
        d = getPage(str('http://www.reddit.com/r/%s/.json?count=%s&after=%s'
            % (self.subreddit, self.count+1, self.after)))

        d.addCallback(self.subredditCallback)
        return d
    

    def subredditCallback(self, page):
        """Load a page of a subreddit, download links, and recursively call self
        on next page for as many pages as required."""
        data = json.loads(page)['data']

        previous_after = None  # no idea how to get this either

        dlist = []
        if data['children']:
            for child in data['children']:
                try:
                    submission = Submission(child, self.subreddit)
                    dlist.append(submission.retrieve())
                    print submission.tag, "Added"
                except UnknownLinkError:
                    print submission.tag, "Unknown Link", submission.url

        if data['after'] != previous_after and self.count < self.max_count:
            sub = SubredditPage(self.subreddit, self.max_count, self.count + 1,
            data['after'])
            dlist.append(sub.retrieve())

        return DeferredList(dlist)

def finish(result):
    print """Finished!"""
    #from time import sleep
    reactor.stop()

def failed(failure):
    print "======================================+++++++"
    print failure.getErrorMessage()
    print "======================================+++++++"


def main():
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

    dlist = []
    for subreddit in subreddits:
        sub = SubredditPage(subreddit, max_count)
        dlist.append(sub.retrieve())
    d = DeferredList(dlist)

    d.addCallback(finish)
    d.addErrback(failed)
    reactor.run()
