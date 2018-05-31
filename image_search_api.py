#!/usr/bin/env python3

# see https://github.com/NikolaiT/GoogleScraper for API details

# TODO make cache optional
# TODO get chromedriver from env variables
# FIXME external config file option in config.py
# TODO support search multiple keywords

import argparse
import sys
import os
sys.path.append('GoogleScraper')
from GoogleScraper import scrape_with_config, GoogleSearchError
from GoogleScraper.database import ScraperSearch, SERP, Link
import time

import threading,requests, os, urllib


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', dest='search_engine', default='google',
                        help='so far only confirmed Google is working')
    parser.add_argument('-type', dest='search_type', default='image')
    parser.add_argument('-o', dest='output_dir', default='images/',
                        help='directory to save downloaded images to')
    parser.add_argument('-k', dest='keyword',
                        help='single keyword for search')
    parser.add_argument('-f', dest='keyword_file',
                        help='filename containing list of keywords for search')
    parser.add_argument('-n', dest='num_threads', default=100,
                        help='num of threads to use for downloading images')
    return parser.parse_args()


class FetchResource(threading.Thread):
    """Grabs a web resource and stores it in the target directory"""
    def __init__(self, target, urls):
        super().__init__()
        self.target = target
        self.urls = urls

    def run(self):
        for url in self.urls:
            url = urllib.parse.unquote(url)
            with open(os.path.join(self.target, url.split('/')[-1]), 'wb') as f:
                try:
                    content = requests.get(url).content
                    f.write(content)
                except Exception as e:
                    pass
                print('[+] Fetched {}'.format(url))
                

def image_search(output_dir, config, num_threads):
    try:
        search = scrape_with_config(config)
    except GoogleSearchError as e:
        print(e)

        
    image_urls = []
    for serp in search.serps:
        image_urls.extend(
            [link.link for link in serp.links]
        )

        
    print('[i] Going to scrape {num} images and saving them in "{dir}"'.format(
        num=len(image_urls),
        dir=output_dir
    ))
    

    # make a directory for the results
    try:
        os.mkdir(output_dir)
    except FileExistsError:
        pass

    
    # fire up n threads to get the images
    threads = [FetchResource(output_dir, []) for i in range(num_threads)]
    while image_urls:
        for t in threads:
            try:
                t.urls.append(image_urls.pop())
            except IndexError as e:
                break

    threads = [t for t in threads if t.urls]

    for t in threads:
        t.start()

    for t in threads:
        t.join()



if __name__ == '__main__':
    args = parse_args()
    # either provide keyword or file
    assert (not args.keyword and args.keyword_file) or (args.keyword and not args.keyword_file)


    config = {
        'search_engines': args.search_engine,
        'search_type': args.search_type,
        'scrapemethod': 'selenium',
        'num_pages_for_keyword' : 1,
        'image_type' : 'Photo'
    }
    
    if args.keyword:
        config['keyword'] = args.keyword
    else:
        config['keyword_file'] = args.keyword.file
    
    image_search(args.output_dir,
                 config,
                 args.num_threads)  # TODO allow multiple keywords
