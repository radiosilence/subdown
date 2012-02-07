class Scraper(object):
    pass

class ImgurScraper(Scraper):
    def __init__(self, url):
        self._url = url

    @property
    def urls(self):
        return []

class TumblrScraper(Scraper):
    def __init__(self, url):
        self._url = url

    @property
    def urls(self):
        return []
    