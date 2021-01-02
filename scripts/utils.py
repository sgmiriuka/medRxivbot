import requests
from datetime import date, timedelta
import sqlite3
import tweepy
import logging
import os
import bs4 as bs

def get_med_papers():
    '''
    Gets papers from RSS medRxiv 
    '''
    cwd = os.getcwd()
    logging.basicConfig(filename=cwd + '/medRxivbot/scripts/activity.log', format='%(asctime)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',
                          filemode='w', level=logging.DEBUG)
    logging.info('Start with get_papers')
    subjects = ['addiction_medicine','allergy_and_immunology','anesthesia','cardiovascular_medicine',
            'dentistry_and_oral_medicine','dermatology','emergency_medicine','endocrinology',
            'diabetes_mellitus_and_metabolic_disease','epidemiology',
            'forensic_medicine','gastroenterology','genetic_and_genomic_medicine','geriatric_medicine',
            'health_economics','health_informatics','health_policy',
            'health_systems_and_quality_improvement','hematology','HIV/AIDS',
            'infectious_diseases','intensive_care_and_critical_care_medicine','medical_education','medical_ethics',
            'nephrology','neurology','nursing','nutrition','obstetrics_and_gynecology',
            'occupational_and_environmental_health','oncology',
            'ophthalmology','orthopedics','otolaryngology','pain_medicine',
            'palliative_medicine','pathology','pediatrics','pharmacology_and_therapeutics','primary_care_research',
            'psychiatry_and_clinical_psychology','public_and_global_health','radiology_and_imaging',
            'rehabilitation_medicine_and_physical_therapy','respiratory_medicine','rheumatology',
            'sexual_and_reproductive_health','sports_medicine','surgery',
            'toxicology','transplantation','urology']
    today = date.today()
    yesterday = today - timedelta(days = 1)
    all_pubs = []
    n_items = 0
    try:
        for sub in subjects:
            doc = 'http://connect.medrxiv.org/medrxiv_xml.php?subject=' + sub
            soup = bs.BeautifulSoup(requests.get(doc).content, features="xml")
            logging.info('Request: %s', 'http://connect.medrxiv.org/medrxiv_xml.php?subject=' + sub)
            items = soup.find_all('item')
            for item in items:
                this_day = item.find('dc:date').text.replace('\n', '')
                if this_day == str(yesterday):
                    pubs = {}
                    pubs['doi'] = item.find('dc:identifier').text.replace('\n', '')
                    pubs['title'] = item.title.text.replace('\n', '')
                    pubs['publicationdate'] = item.find('dc:date').text.replace('\n', '')
                    pubs['description'] = item.description.text.replace('\n', '')
                    pubs['link'] = item.link
                    all_pubs.append(pubs)
                    n_items += 1
        logging.info('Got papers OK. Number of papers yesterday: {}'.format(n_items))
        return all_pubs
    except:
        logging.info('Connection problems')

def papers_to_db():
    '''Get papers from medRxiv and creates a sqlite3 database'''
    new_publications = get_med_papers()
    cwd = os.getcwd()
    connection = None
    connection = sqlite3.connect(cwd + '/medRxivbot/scripts/medbot.db')
    cursor = connection.cursor()
    cursor.execute('''DROP TABLE if exists yesterday_pubs''')
    cursor.execute('''CREATE TABLE 'yesterday_pubs'
                         ('doi','title','date','abstract','link')''')
    for pub in new_publications:
        doi = pub.get('doi')
        title = pub.get('title')
        pubdate = pub.get('publicationdate')
        abstract = pub.get('description')
        link = pub.get('link')
        link =str(link).replace('<link>', '').replace('</link>', '').replace('\n', '')
        cursor.execute('INSERT INTO yesterday_pubs VALUES(?,?,?,?,?)', 
                            (doi,title, pubdate, abstract, str(link)))
        connection.commit()
    connection.close()


def load_keywords():
     '''
     Read keywords from serach.txt file and converts them into a LIKE sqlite3 search. 
     '''
     cwd = os.getcwd()
     with open(cwd + '/medRxivbot/scripts/search.txt') as f:
          lines = [i.strip() for i in f.readlines()]
          lowline = []
          for line in lines:
               if ') AND (' in line:
                    prelowline = line.replace(') AND (', ' XXXX ')
                    prelowline = prelowline.replace('(', '(abstract LIKE \'%').replace(')', '%\')').replace(' OR ', '%\' OR abstract LIKE \'%').replace(' AND ', '%\' AND abstract LIKE \'%').replace(' NOT ', '%\' abstract NOT LIKE \'%')
                    prelowline = prelowline.replace(' XXXX ', '%\') AND (abstract LIKE \'%')
                    lowline.append([line, prelowline])
               elif ') OR (' in line:
                    prelowline = line.replace(') OR (', ' XXXX ')
                    prelowline = prelowline.replace('(', '(abstract LIKE \'%').replace(')', '%\')').replace(' OR ', '%\' OR abstract LIKE \'%').replace(' AND ', '%\' AND abstract LIKE \'%').replace(' NOT ', '%\' abstract NOT  LIKE \'%')
                    prelowline = prelowline.replace(' XXXX ', '%\') OR (abstract LIKE \'%')
                    lowline.append([line, prelowline])
               elif ') OR (' in line:
                    prelowline = line.replace(') NOT (', ' XXXX ')
                    prelowline = prelowline.replace('(', '(abstract LIKE \'%').replace(')', '%\')').replace(' OR ', '%\' OR abstract LIKE \'%').replace(' AND ', '%\' AND abstract LIKE \'%').replace(' NOT ', '%\' abstract NOT LIKE \'%')
                    prelowline = prelowline.replace(' XXXX ', '%\') AND (abstract NOT LIKE \'%')
                    lowline.append([line, prelowline])
               else:
                    prelowline = line.replace(' OR ', '%\' OR abstract LIKE \'%').replace(' AND ', '%\' AND abstract LIKE \'%').replace(' NOT ', '%\' abstract NOT LIKE \'%')
                    prelowline = 'abstract LIKE \'%' + prelowline + '%\''
                    lowline.append([line, prelowline])
          logging.info('Keywords OK')
          return lowline


def read_from_database():
    '''
    Read keywords in abstract and retrived matched papers.
    '''
    cwd = os.getcwd()
    connection = sqlite3.connect(cwd + '/medRxivbot/scripts/medbot.db')
    cursor = connection.cursor()
    keywords = load_keywords()
    key_retrived = []
    for k in keywords:
        sql = "SELECT doi,title,abstract,link FROM yesterday_pubs WHERE " + k[1] + "COLLATE NOCASE"
        cursor.execute(sql)
        retrived = cursor.fetchall()
        for i in retrived:
            key_re = [k[0], i]
            key_retrived.append(key_re)
            logging.info('Yes, got a paper.')
        if not key_retrived:
            logging.info('No papers matching keywords were found today.')
    return key_retrived

def tweet_login():
     '''
     Log in to twitter account; access granted by codes provded in credential.txt file.
     '''
     creds = []
     cwd = os.getcwd()
     with open(cwd + '/medRxivbot/scriptss/credentials.txt') as f:
          creds = [i.strip() for i in f.readlines()]
          auth = tweepy.OAuthHandler(creds[0], creds[1])
          auth.set_access_token(creds[2], creds[3])
          api = tweepy.API(auth, wait_on_rate_limit=True,
                              wait_on_rate_limit_notify=True)
          try:
               api.verify_credentials()
               logging.info("Authentication OK")
          except:
               logging.critical("Error during authentication")
          return api

