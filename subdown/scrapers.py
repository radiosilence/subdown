"""These scrapers basically take a URL to an HTML page (or whatever) and turn
it into a list of image URLs, through a series of confusing and weird
callbacks.
"""

import re

from twisted.web.client import getPage
from lxml.html import fromstring
from lxml.cssselect import CSSSelector


class Scraper(object):
    urls = []
    submission = None

    def __init__(self, url, submission=None):
        self._url = str(url)
        self.submission = submission


class ImgurScraper(Scraper):
    """A scraper to get large images from Imgur"""
    @property
    def deferred(self):
        """Returns the deferred for grabbing the HTML page"""
        url = re.sub(
            r'http://i\.imgur\.com/([a-zA-Z0-9]+)\.(jpg|jpeg|png|gif)',
            r'http://imgur.com/\1',
            self._url)
        self._url = url
        d = getPage(url)
        d.addCallback(self.scrape)
        return d

    def scrape(self, page):
        """Takes the HTML and returns a list of urls"""
        urls = []
        h = fromstring(page)
        s = CSSSelector('div.image img')
        urls = [el.attrib['src'] for el in s(h)]
        print "searched %s found " % self._url, urls
        return urls

class TumblrScraper(Scraper):

    @property
    def deferred(self):
        return []