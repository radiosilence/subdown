Promise = require 'bluebird'
http = require 'http'
fs = Promise.promisify(require 'fs')

getSubreddit = (subreddit, pages, page, after) ->
    after = after or undefined
    page = page or 1
    if page > pages
        return null    
    getPage(subreddit, page, after).then(
        ([submissions, next_after]) ->
            getSubreddit subreddit, pages, page + 1, next_after 
            processSubmissions(submissions)
    ).then(
        downloadImageSets
    )

getPage = (subreddit, page, after) ->
    console.log "Getting #{page}:#{after} of #{subreddit}"
    new Promise (resolve, reject) ->
        options = 
            host: 'www.reddit.com'
            path: "/r/#{subreddit}/.json?page=#{page}&after=#{after}"
        
        http.request(options, (response) ->
            str = ''
            response.on 'data', (chunk) ->
                str += chunk

            response.on 'end', ->
                data = (JSON.parse str).data
                after = data.after
                submissions = data.children
                resolve([submissions, after])
        ).end()

processSubmissions = (rawSubmissions) ->
    new Promise (resolve, reject) ->
        imageURLs = []
        Promise.map(rawSubmissions, processSubmission).then((results) ->
            resolve (results)
        )

processSubmission = (submission) ->
    if submission.data.url.match /^http:\/\/i\.imgur\.com\/\w+\.(jpg|png|gif)$/
        return [
            Date(submission.data.created)
            submission.data.subreddit
            [submission.data.url]
        ]
    else
        return null

downloadImageSets = (imageSets) ->
    for imageSet in imageSets
        if not imageSet
            continue
        downloadImageSet imageSet

downloadImageSet = ([created, subreddit, images]) ->
    for url in images
        testFile(created, subreddit, url).then(
            downloadImage
        ).then(
            setUpdatedTime
        ).catch((err) ->
            console.log "Error with image #{url}: #{err}"
        )

testFile = (created, subreddit, url) ->
    console.log "Testing #{subreddit} #{url}"
    new Promise (resolve, reject) ->
        filename = url.split("/")[-1..][0]
        path = [subreddit, filename].join('/')
        fs.exists path, (exists) ->
            if exists
                reject("Already exists")
            else
                quietMakeDir(subreddit).then(->
                    resolve([created, url, path])
                )

quietMakeDir = (dir) ->
    new Promise (resolve, reject) ->
        fs.mkdir(dir, ->
            resolve()
        )

downloadImage = ([created, url, path]) ->
    new Promise (resolve, reject) ->
        getRemoteFile(url).then((response) ->
            writeFile(path, response)
        ).then(->
            resolve([created, path])
        )

getRemoteFile = (url) ->
    new Promise (resolve, reject) ->
        parts = url.split '/'
        options = 
            host: parts[2]
            path: "/" + parts[3..].join('/')
        http.request(options, (response) ->
            resolve response
        ).end()

writeFile = (path, response) ->
    new Promise (resolve, reject) ->
        response.on 'error', (err) ->
            reject err
        fs.open path, 'w', (err, fd) ->
            if err
                reject err
            response.on 'data', (chunk) ->
                fs.write fd, chunk, 0, chunk.length, null, (err, written) ->
                    if err
                        reject err
            response.on 'end', ->
                fs.close fd, ->
                    console.log "Saved #{path}"
                    resolve()

setUpdatedTime = ([created, path]) ->
    # console.log "Set #{created} on #{path}"

main = (subreddits, pages)->
    for subreddit in subreddits
        getSubreddit(subreddit, pages)

main([
    'dogpictures'
    'labrador'
], 10)