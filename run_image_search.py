#!/usr/bin/env python3
# see https://github.com/NikolaiT/GoogleScraper for API details

# TODO make cache optional
# FIXME external config file option in config.py
# TODO support search multiple keywords
import argparse
import os, sys, re

sys.path.append('GoogleScraper')
from GoogleScraper import scrape_with_config, GoogleSearchError
from GoogleScraper.database import ScraperSearch, SERP, Link
import time

import threading,requests, os, urllib
from GoogleScraper.core import get_command_line

KEYWORD_NUM = None

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', dest='search_engine', default='google',
                        help='so far only confirmed Google is working')
    parser.add_argument('-type', dest='search_type', default='image')
    parser.add_argument('-o', dest='output_dir', default='images/',
                        help='directory to save downloaded images to')
    parser.add_argument('-of', dest='output_dir_file',
                        help='list of keyword-directory pairs to save downloaded images to')
    parser.add_argument('-k', dest='keyword', default=None,
                        help='single keyword for search')
    parser.add_argument('-kf', dest='keyword_file',
                        help='filename containing list of keywords for search')
    parser.add_argument('-n', dest='num_threads', default=100, type=int,
                        help='num of threads to use for downloading images')
    parser.add_argument('-m', dest='max_num_results_per_keyword', type=int,
                        help='useful if you want to cap the number of results')
    parser.add_argument('-p', dest='port', type=int, default=2000,
                        help='define port for chromedriver')
    parser.add_argument('-u', dest='url_directory', type=str, required=True,
                        help='define path of parent directory for keyword/{list-urls}')
    return parser.parse_args()

class FetchResource(threading.Thread):
    """Grabs a web resource and stores it in the target directory"""
    def __init__(self, target, urls, keyword):
        super().__init__()
        self.target = target
        self.urls = urls
        self.keyword = keyword

    def run(self):
        for i, url in enumerate(self.urls):
            url = urllib.parse.unquote(url)
            if url == '':
                continue
            
            with open(os.path.join(self.target, url.strip('/').split('/')[-1]), 'wb') as f:
                try:
                    content = requests.get(url).content
                    f.write(content)
                except Exception as e:
                    pass

                #print('[+] Fetched {}'.format(url))

def get_urls(serps):
    image_urls = []
    for serp in serps:
        image_urls.extend([link.link for link in serp.links])

    if MAX_NUM_URLS == None or len(image_urls) <= MAX_NUM_URLS:
        return image_urls
    else:
        return image_urls[0:MAX_NUM_URLS]
    return image_urls

def check_output_dir(output_dir, keyword):
    try:
        os.mkdir(output_dir)
    except FileExistsError:
        pass


def run_threads(keyword, image_urls, output_dir, num_threads):
    # fire up n threads to get the images
    if len(image_urls) == 0: return
    
    threads = [FetchResource(output_dir, [], keyword) for i in range(num_threads)]
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
    
def store_by_keyword(search, keyword_outdir_pairs, num_threads, url_directory):
    # make sure every keyword has a corresponding output directory
    keywords = list(set([s.query for s in search.serps]))
    assert len(list(filter(lambda k: k not in keyword_outdir_pairs.keys(), keywords))) == 0
    
    all_urls = {kw : get_urls(filter(lambda s: s.query == kw, search.serps)) for kw in keywords}
    with open('{}/{}'.format(url_directory, KEYWORD_NUM), 'w') as f:
        for kw in sorted(keywords):
            image_urls = all_urls.get(kw)
        
            if len(image_urls) == 0:
                continue

            output_dir = keyword_outdir_pairs[kw]
            check_output_dir(output_dir, kw)

        
            print('[i] Going to scrape {num} images for {keyword} and saving them in "{dir}"'.format(
                num=len(image_urls),
                keyword=kw,
                dir=output_dir
            ))


            for url in image_urls:
                f.write('{} {}\n'.format(url, output_dir))
            #map(lambda url: f.write('{} {}\n'.format(url, output_dir)), image_urls)
            
            
            #run_threads(kw, image_urls, output_dir, num_threads)
            print('Finished for {}'.format(kw))
        
def image_search(config, keywords, num_threads, output_dir, keyword_outdir_pairs, url_directory):
    try:
        search = scrape_with_config(config)
    except GoogleSearchError as e:
        print(e)

    if keyword_outdir_pairs:
        ''' each keyword specifies its own output directory'''
        store_by_keyword(search, keyword_outdir_pairs, num_threads, url_directory)

    else:
        ''' everything will be saved in single directory '''
        image_urls = clip_urls(getUrls(search.serps))

        print('[i] Going to scrape {num} images and saving them in "{dir}"'.format(
            num=len(image_urls),
            dir=output_dir
        ))

        check_output_dir(output_dir)

def format_output_dir(kw, output_dir):
    if re.match('.*/.*', kw):
        formatted_kw = re.sub('/', 'forwardslash', kw)
        formatted_output_dir = re.sub(kw, formatted_kw, output_dir)
        print(formatted_output_dir, '\n', output_dir)
        return formatted_output_dir
    return output_dir


def get_keywords(keyword, keyword_file):
    formatted_keywords = []
    if keyword_file:
        keyword_file = os.path.abspath(keyword_file)
        if not os.path.exists(keyword_file):
            raise WrongConfigurationError('The keyword file {} does not exist.'.format(keyword_file))
        else:
            # FIXME need to load keywords
            if keyword_file.endswith('.py'):
                # we need to import the variable "scrape_jobs" from the module.
                sys.path.append(os.path.dirname(keyword_file))
                try:
                    modname = os.path.split(keyword_file)[-1].rstrip('.py')
                    scrape_jobs = getattr(__import__(modname, fromlist=['scrape_jobs']), 'scrape_jobs')
                except ImportError as e:
                    logger.warning(e)
            else:
                with open(keyword_file, 'r') as f:
                    formatted_keywords = sorted(list(set([l.strip('\n').strip() for l in f.readlines()])))
    elif keyword:
        formatted_keywords = [keyword, ]
    elif not keyword and not keyword_file:
        get_command_line(True)
        print('No keywords to scrape for. '\
              'Please provide either an keyword file (Option: --keyword-file) or specify and '
              'keyword with --keyword.')
        return None

    return formatted_keywords

if __name__ == '__main__':
    args = parse_args()

    # either provide keyword or file
    assert (not args.keyword and args.keyword_file) or (args.keyword and not args.keyword_file)

    if args.max_num_results_per_keyword:
        MAX_NUM_URLS = args.max_num_results_per_keyword
    

    # TODO make list of options for google image
    config = {
        'search_engines': args.search_engine,
        'search_type': args.search_type,
        'scrapemethod': 'selenium',
        'num_pages_for_keyword' : 1,
        'image_type' : 'photo', # case sensitive: clipart, photo
        'image_size' : 'Large',
        'image_color' : 'color',
        'port' : args.port
    }

    keywords = get_keywords(args.keyword, args.keyword_file)
    
    if args.keyword_file:
        KEYWORD_NUM = os.path.basename(args.keyword_file)

    # see if output_dir is path to file
    # we'll use this to take care of paths that have special chars
    keyword_outdir_pairs = None
    if args.output_dir_file:
        with open(args.output_dir_file, 'r') as f:
            keyword_outdir_pairs = \
                        {l[0]:format_output_dir(l[0], l[1]) for l in map(lambda d: d.strip('\n').split(' '),
                                                                   f.readlines())}

    # for right now, we need to get words that haven't been covered yet
    # TODO remove
    flags = []
    for kw in keywords:
        directory = keyword_outdir_pairs[kw]

        if os.path.exists(directory) and len(os.listdir(directory)) > 0:
            flags.append(kw)

    keywords = list(filter(lambda k: k not in flags, keywords))

    config['keywords'] = keywords
    config['keyword_file'] = args.keyword_file
    
    image_search(config,
                 keywords,
                 args.num_threads,
                 args.output_dir,
                 keyword_outdir_pairs,
                 args.url_directory)
