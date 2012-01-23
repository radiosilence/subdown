from twisted.internet import reactor
from twisted.web.client import getPage, downloadPage
from twisted.internet.defer import DeferredList

import json


def pageCallback(result):
  return len(result)

def processSubmission(child):
    """Returns a deferred(?) that will either:
        1. Download an image directly.
        2. Scrape the page of a link (ie a tumblr).
        3. Does nothing because it's not the kind of link we want.
    """
    
    subreddit_name = "BLAH" #  Don't know how to pass this in!!
    file_name = child['data']['url'].split('/')[-1]
    d = downloadPage(child['data']['url'], '%s/%s'
        % (subreddit_name, file_name))

    return the_deferred

def changeFileDate(result):
    """Changes the file date on a downloaded file."""

    # The date would be in child['data']['created'] but I'm not sure how to acc
    # cess that here?
    pass

def checkFileSize(result):
    """Fail on files lower than a set size"""
    pass

def deleteFile(result):
    """Delete the resulting file."""
    pass

def subredditCallback(result):
    """Load x many pages of a subreddit and then do ??"""
    data = json.loads(result)

    count = 2  # no idea how get this from here?? needs to be next page count
    previous_after = 'string'  # no idea how to get this either

    dlist = []
    if data['children']:
        for child in data['children']:
            d = processSubmission(child)
            d.addCallback(checkFileSize)
            d.addBoth(changeFileDate, deleteFile))
            dlist.append(d)

    # This is the stuff for getting the next page. I guess we do it recursivel
    # y rather than iteratively because async?
    if data['after'] != previous_after and count < max_count:
        d = getPage('http://www.reddit.com/r/wallpapers/.json?count=%s&after=%s'
            % (count, data['after']))
        d.addCallback(subredditCallback)
        dlist.append(d)
    
    return deferredList(dlist)

def finish(ign):
  reactor.stop()

def main():
    # only get 5 pages - I need to pass this into the scope of subredditCallbac
    # k somehow, how should I do this?
    max_count = 5
                
    subreddits = [
        'wallpapers',
        'pics'
    ]

    dlist = []
    for subreddit in subreddits:
        d = getPage('http://www.reddit.com/r/%s/.json' % subreddit)
        d.addCallback(subredditCallback)
        dlist.append(d)
    
    d = deferredList(dlist)
    d.addCallback(finish)

if __name__ == '__main__';
    main()
    reactor.run()
