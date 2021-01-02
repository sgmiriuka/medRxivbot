#!/usr/bin/env python

import time
import logging
import os
from datetime import date, timedelta
from utils import read_from_database, papers_to_db, tweet_login


def search_and_tweet():
     '''
     Search papers, filter them, and tweet. 
     '''
     papers_to_db()
     k_now = read_from_database()
     if not k_now:
          logging.info('No papers published yesterday')
     else:          
          api = tweet_login()
          dois = []
          for n_tweets, line in enumerate(k_now):
               matched_kw = line[0]
               tu = list(line[1])
               doi = tu[0]
               title = tu[1]
               if doi in dois:
                     continue
               else:
                     dois.append(doi)
               link = tu[3]
               n_char = len(title)
               if n_char > 110:
                     title_length = 110 - len(title)
                     _title_to_post = title[:title_length]
                     final_title = _title_to_post + '...'
               else:
                     final_title = title
               cwd = os.getcwd()
               with open(cwd + '/medRxivbot/scripts/temp.txt', 'w') as f:
                    f.write(final_title + '\n' + link)
               with open(cwd + '/medRxivbot/scripts/temp.txt', 'r') as f:
                    api.update_status(f.read())
               f.close()
               time.sleep(5)
          logging.info('Number of tweets today: %s', n_tweets + 1)


if __name__ == '__main__':
     search_and_tweet()
     logging.info('End')