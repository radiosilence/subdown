var require = require || function () {};
var Promise = require('bluebird'),
    http = Promise.promisify(require('http')),
    fs = Promise.promisify(require('fs')),
    log = require('npmlog');
log.heading = 'subdown';

class ImageAlreadyExistsError extends Error {};
class MaxPagesReachedError extends Error {};


class Subreddit {
    name: string;
    currentPage: number;
    currentAfter: string;
    maxPages: number;

    constructor(name: string, maxPages: number) {
        this.name = name;
        this.maxPages = maxPages;
        this.currentPage = 1;
        this.currentAfter = '';
    }
    get(): void {
        if (this.currentPage > this.maxPages)
            throw new MaxPagesReachedError();
        this.getPage().then(
            function(submissions: {}[]) {
                this.get();
                this.processSubmissions(submissions).then(
                    this.downloadImageSets
                );
            }
        ).catch(MaxPagesReachedError, function(){});
    }
    getPage(): Promise {
        return new Promise(function(resolve, reject) {
            var options = {
                'host': 'www.reddit.com',
                'path': ['/r/', this.name, '/.json/?page=', this.currentPage, '&after=', this.currentAfter].join('')
            };
            http.getAsync(options).then(function(reponse) {
                var str: string = '';
                response.on('data', function(chunk) {
                    str += chunk;
                });
                response.on('end', function() {
                    log.info(this.name, ["Got page", page].join(' '));
                    var data = JSON.parse(str).data,
                        submissions = data.submissions;
                    this.currentAfter = data.after;
                    this.currentPage += 1;
                    resolve(submissions);
                });
            })
        });
    }
    processSubmissions(submissions: {}[]): Promise {
        return Promise.map(submissions, this.processSubmission);
    }
    processSubmission(submission: {}): Promise  {
        new Promise(function(resolve, reject) {
            var imageSet: ImageSet = new ImageSet(
                Date(submission.data.created),
                this
            );
            if (submission.data.url.match(/^http:\/\/i\.imgur\.com\/\w+\.(jpg|png|gif)$/)) {
                imageSet.addUrl(submission.data.url);
            } 
            resolve(imageSet);
        });
    }
    downloadImageSets(imageSets: ImageSet[]): Promise {
        for (i in imageSets) {
            imageSets[i].download()
        }
    }
}

class ImageSet {
    created: Date;
    subreddit: Subreddit;
    images: Image[];
    constructor(created: Date, subreddit: Subreddit) {
        this.created = created;
        this.subreddit = subreddit;
    }
    addUrl(url: string) {
        this.images.push(Image(url, this));
    }
    download(): Promise {
        for (i in self.images) {
            self.images[i].download();
        }
    }
    
    
}

class Image {
    url: string;
    filename: string;
    path: string;
    imageSet: ImageSet;

    constructor(url: string, imageSet: ImageSet) {
        this.url = url;
        this.imageSet = imageSet;
        this.path = this.url.split("/").slice(-1)[0];
        this.filename = [this.imageSet.subreddit.name, this.filename()].join('/');
    }
    download(): {
        this.testFile(url).then(
            this.save()
        ).then(
            this.setUpdatedTime
        ).catch(ImageAlreadyExistsError, function (){}
        ).catch(function(err) {
            log.error(this.subreddit, url, err);
        });
    }
    testFile(image: string) {
        return fs.existsAsync(this.path).catch(function() {
            throw new ImageAlreadyExistsError();
        }).then(function() {
            fs.mkdirAsync(subreddit).catch(function() {});
        }).then(function() {
            return [url, path];
        });
    }
}
function main(names: string[], maxPages: number) {
    for (i in names) {
        s = Subreddit(names[i], maxPages);
        s.get();
    }
}
main(['dogpictures', 'labrador'], 10);
// { "kind": string; "data": { "modhash": string; "children": {}[]; "after": string; "before": null; }; }
