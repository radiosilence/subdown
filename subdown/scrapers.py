"""These scrapers basically take a URL to an HTML page (or whatever) and turn
it into a list of image URLs, through a series of confusing and weird
callbacks.
"""

import json
import re

from twisted.web.client import getPage
from lxml.html import fromstring
from lxml.cssselect import CSSSelector

from utils import decode


class Scraper(object):
    urls = []

    def __init__(self, url):
        self._url = str(url)

class ImgurScraper(Scraper):
    """A scraper to get large images from Imgur"""

    def retrieve(self):
        """Returns the deferred for grabbing the HTML page"""
        url = re.sub(
            r'http://i?\.?imgur\.com/([a-zA-Z0-9]+)\.(jpg|jpeg|png|gif)',
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
        for el in s(h):
            try:
                urls.append(el.attrib['src'])
            except KeyError:
                try:
                    urls.append(el.attrib['data-src'])
                except KeyError:
                    pass
        
        s = CSSSelector('a.zoom')
        for el in s(h):
            try:
                url = el.attrib['href']
                if url not in urls:
                    urls.append(url)
            except KeyError:
                pass
        """jsons = re.search(r'images: (.*),', page).group(1)
        data = json.loads(jsons)
        for image in data['items']:
            urls.append('http://i.imgur.com/%s%s' % (image['hash'], image['ext']))
        """
        #print "searched %s found " % self._url, urls
        return urls

class TumblrScraper(Scraper):

    def retrieve(self):
        d = getPage(self._url)
        d.addCallback(self.scrape)
        return d
    
    def scrape(self, page):
        """Takes the HTML and returns a list of urls"""
        urls = []
        h = fromstring(page)
        s = CSSSelector('div#content img')
        for el in s(h):
            try:
                print el.attrib
                url = el.attrib['src']
                if url not in urls:
                    urls.append(url)
            except KeyError:
                try:
                    urls.append(el.attrib['data-src'])
                except KeyError:
                    pass
        return urls
