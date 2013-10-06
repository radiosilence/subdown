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
                    log.info(this.name, "Got page", self.currentPage);
                    var data = JSON.parse(str).data,
                        submissions = data.submissions;
                    this.currentAfter = data.after;
                    this.currentPage += 1;
                    this.name = data.subreddit;
                    resolve(submissions);
                });
            })
        });
    }
    processSubmissions(submissions: Submission[]): Promise {
        return Promise.map(submissions, this.processSubmission);
    }
    processSubmission(submission: Submission): Promise  {
        new Promise(function(resolve, reject) {
            var imageSet: ImageSet = new ImageSet(
                new Date(submission.data.created),
                this
            );
            if (submission.data.url.match(/^http:\/\/i\.imgur\.com\/\w+\.(jpg|png|gif)$/)) {
                imageSet.addUrl(submission.data.url);
            } 
            resolve(imageSet);
        });
    }
    downloadImageSets(imageSets: ImageSet[]): Promise {
        for (var i in imageSets) {
            imageSets[i].download()
        }
    }
}

interface Submission {
    data: {
        url: string;
        created: number;
    }
}

class ImageSet {
    created: Date;
    subreddit: Subreddit;
    images: ImageURL[];
    constructor(created: Date, subreddit: Subreddit) {
        this.created = created;
        this.subreddit = subreddit;
    }
    addUrl(url: string) {
        this.images.push(new ImageURL(url, this));
    }
    download(): Promise {
        for (var i in this.images) {
            this.images[i].download();
        }
    }
}

class ImageURL {
    url: string;
    filename: string;
    path: string;
    imageSet: ImageSet;

    constructor(url: string, imageSet: ImageSet) {
        this.url = url;
        this.imageSet = imageSet;
        this.filename = this.url.split("/").slice(-1)[0];
        this.path = [this.imageSet.subreddit.name, this.filename].join('/');
    }
    download() {
        this.testFile(this.url).then(
            this.save
        ).then(
            this.setUpdatedTime
        ).then(function() {
            log.info(this.imageSet.subreddit.name, "Downloaded", this.url); 
        }).catch(ImageAlreadyExistsError, function (){}
        ).catch(function(err) {
            log.error(this.subreddit, this.url, err);
        });
    }
    testFile(image: string): Promise {
        return fs.existsAsync(this.path).catch(function() {
            throw new ImageAlreadyExistsError();
        }).then(function() {
            fs.mkdirAsync(this.imageSet.subreddit.name).catch(function() {});
        });
    }
    save(): Promise {
        var parts: string[] = this.url.split('/'),
            options = {
                'host': parts[2],
                'path': "/" + parts.slice(3).join('/')
            };
        return fs.openAsync(this.path, 'w').then(function (fd) {
            http.request(options, function(res) {
                res.on('error', function(err) {
                    throw new Error(err);
                }); 
                res.on('data', function(chunk) {
                    fs.writeAsync(fd, chunk, 0, chunk.length)
                });
                res.on('end', function() {
                    fs.closeAsync(fd);
                })
            }).end()
        });
    }
    setUpdatedTime(): void {
    }
}

function main(names: string[], maxPages: number) {
    for (var i in names) {
        new Subreddit(names[i], maxPages).get();
    }
}

main(['dogpictures', 'labrador'], 10);
