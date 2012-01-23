from twisted.internet import reactor
from twisted.web.client import getPage, downloadPage
from twisted.internet.defer import DeferredList
import json

class UnknownLinkError(Exception):
    """This error is thrown when the program does not know what to do with a
    link.
    """
    pass


class TooSmallError(Exception):
    pass


def pageCallback(result):
  return len(result)


def processSubmission(child, subreddit):
    """Returns a deferred(?) that will either:
        1. Download an image directly.
        2. Scrape the page of a link (ie a tumblr).
        3. Does nothing because it's not the kind of link we want.
    """
    data = child['data']
    file_name = data['url'].split('/')[-1]
    ext = file_name.split('.')[-1]
    directory = subreddit
    file_path = '%s/%s' % (directory, file_name)


    if ext in ['jpg', 'png', 'gif']:
        d = downloadPage(str(data['url']), file_path)
    else:
        raise UnknownLinkError(data['url'])

    print "trying to download", str(data['url']), file_path

    return d

def changeFileDate(result, subreddit):
    """Changes the file date on a downloaded file."""
    print "changing file date", result, subreddit
    # The date would be in child['data']['created'] but I'm not sure how to acc
    # cess that here?

def checkFileSize(result, subreddit):
    """Fail on files lower than a set size"""
    print "checking file size", result, subreddit

def deleteFile(failure):
    """Delete the resulting file."""
    print "HI GOT TO DELETE YAEH"
    failure.trap(TooSmallError)
    print "deleting file", failure.getErrorMessage()

def writeError(failure):
    print "YO GOT TO WRIE ERR"
    failure.trap(IOError)
    print failure.getErrorMessage()

def subredditCallback(page, subreddit, max_count, count=1):
    """Load x many pages of a subreddit and then do ??"""
    data = json.loads(page)['data']

    previous_after = 'string'  # no idea how to get this either

    dlist = []
    if data['children']:
        for child in data['children']:
            try:
                d = processSubmission(child, subreddit)
                d.addCallback(checkFileSize)
                d.addCallbacks(changeFileDate, deleteFile)
                d.addErrback(writeError)
                dlist.append(d)
            except UnknownLinkError:
                print "Didn't know how to handle link.", child['data']['url']

    # This is the stuff for getting the next page. I guess we do it recursivel
    # y rather than iteratively because async?
    print subreddit, data['after'], previous_after, count, max_count
    if data['after'] != previous_after and count < max_count:
        new_count = count + 1
        print "getting page", str('http://www.reddit.com/r/%s/.json?count=%s&after=%s'
            % (subreddit, new_count, data['after']))

        d = getPage(str('http://www.reddit.com/r/%s/.json?count=%s&after=%s'
            % (subreddit, new_count, data['after'])))
        d.addCallback(subredditCallback, subreddit, max_count, new_count)
        dlist.append(d)
    
    return DeferredList(dlist)

def finish(ign):
    print "Reached the finish!"
    reactor.stop()

def main():
    # only get 5 pages - I need to pass this into the scope of subredditCallbac
    # k somehow, how should I do this?
    max_count = 1
                
    subreddits = [
        'pics'
    ]

    dlist = []
    for subreddit in subreddits:
        d = getPage('http://www.reddit.com/r/%s/.json' % subreddit)
        d.addCallback(subredditCallback, subreddit, max_count)
        dlist.append(d)
    
    d = DeferredList(dlist)
    d.addCallback(finish)

if __name__ == '__main__':
    main()
    reactor.run()
