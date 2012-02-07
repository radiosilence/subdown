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
from twisted.internet.defer import DeferredList
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
            unicode(self.submission)[:15], self.file_name)

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
        # print self.tag, "Updating modified time to", self.timestamp
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

        def retriedSuccess(result, retries):
            print self.tag, 'Succeeded after %s attempts' % \
                (RETRIES - retries + 1)
            return retries

        def processCallback(result):
            print self.tag, 'Processing',
            self.updateModifiedTime()
            try:
                self.checkFileSize()
                print '...saved'
            except TooSmallError:
                self.deleteFile()
                print '...deleted'

        def webErrback(failure):
            failure.trap(twisted.web.error.Error)
            print self.tag, "HTTP Error: %s (%s)" % (
                failure.getErrorMessage(), self.url)

        def partialDownloadErrback(failure, retries):
            print self.tag, "testing partialDownloadErrback"
            failure.trap(twisted.web.client.PartialDownloadError)
            print "...trapped"
            return downloadImage(retries-1)

        def connectionLostErrback(failure, retries):
            print self.tag, "testing ConnectionLostErrBack"
            failure.trap(twisted.internet.error.ConnectionLost)
            print "...trapped"
            return downloadImage(retries-1)

 
        def writeError(failure):
            """If there's a problem writing the file for instance if the 
            directory does not exist.
            """
            failure.trap(IOError)
            print failure.getErrorMessage()

        def finishChild(result):
            print self.tag, "Finished downloading"
            print result
            return result

        def failedChild(failure):
            print self.tag, "Failed to download.", failure.getErrorMessage()
            
        def downloadImage(retries=RETRIES):
            self.deleteFile()
            print self.tag, "Attempt #%s" % (RETRIES-retries+1)
            d = downloadPage(self.url, self.file_path)

            d.addCallbacks(processCallback, writeError)

            if retries < RETRIES:
                d.addCallback(retriedSuccess, retries)

            d.addErrback(partialDownloadErrback, retries)
            d.addErrback(connectionLostErrback, retries)
            d.addErrback(webErrback)
            d.addCallbacks(finishChild, failedChild)
            return d
        
        if os.path.exists(self.file_path):
            raise FileExistsError

        self.checkCreateDir()

        d = downloadImage()
        #print "trying to download", str(self.url), self.file_path
        self.d = d
        return d

class Submission(object):
    """Represents a single submission and provides associated processing
    functions.
    """
    def __init__(self, child, subreddit):
        self.data = child['data']
        self.subreddit = self.data['subreddit']
        self.images = []

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
            unicode(self)[:15])

    @property
    def timestamp(self):
        """Submitted timestamp"""
        return float(self.data['created_utc'])

    def process_images(self, image_urls):
        deferreds = []
        for image in [Image(url, self) for url in image_urls]:
            try:
                deferreds.append(image.retrieve())
            except FileExistsError:
                print image.tag, "File already exists."
                try:
                    image.checkFileSize()
                    image.updateModifiedTime()
                except TooSmallError:
                    image.deleteFile()
        return deferreds

    def retrieve(self):
        deferreds = []
        if re.search(r'imgur\.com', self.url):
            scraper_deferred = ImgurScraper(self.url, self).retrieve()
            scraper_deferred.addCallback(self.process_images)
            deferreds.append(scraper_deferred)
        elif self.ext in ['jpg', 'png', 'gif']:
            raise UnknownLinkError(self.url)
            self.images.append(Image(self.url, self))
        else:
            raise UnknownLinkError(self.url)

        deferreds.extend(self.process_images(self.images))
        return DeferredList(deferreds)

    def __unicode__(self):
        return self.data['title']


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

def finish(ign):
    print "Reached the finish!"
    from time import sleep
    reactor.stop()


def printpage(page):
    print page[:255]
    return page

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
    reactor.run()
