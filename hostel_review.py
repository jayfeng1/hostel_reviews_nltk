# -*- coding: utf-8 -*-
"""
Created on Wed Nov  4 00:28:16 2015

@author: jay

HOSTELWORLD Real reviews

1. Average the numerical ratings where they mentioned the ameneties 
2. Get sentiment analysis for the specific keyword. 
    - Split it into sentences and count negative words and positive ones where
    the keyword is said
3. Make it a twitter bot slash API
4. Let them ask the twitter bot "Hey hostelbot, how is the wifi and shower"
    - parse the question and find wifi and shower
5. Return positive reviews with most common words
"""

import requests
import pandas as pd
from lxml import html
import numpy as np
import re
from textblob import TextBlob
import nltk
from nltk.util import ngrams
from nltk.collocations import *
from collections import Counter

class HostelReview():
    amenities = {
                    'wifi':        ['wifi','internet','wi-fi', 'wi fi', 'wireless'],
                    'breakfast':   ['breakfast', 'breakfest', 'break fast', 'brunch'],
                    'bathroom':    ['bathroom', 'bath room', 'bath', 'restroom', 'toilet', 'urinal', 'lavatory', 'washroom', 'bathrooms'],
                    'shower':      ['shower', 'bathe', 'showers'],
                    'noise':       ['noise', 'noisy', 'quiet', 'loud', 'silent']
                }
    def __init__(self, url):
        """ Initiates the class with a url for the hostel """
        self.url = url

    def request_xml(self, url):
        """ Passes in a url and returns the xml of the page """
        response = requests.get(url)
        xml = html.fromstring(response.text)
        return xml
    
    def find_end(self, xml):
        """ Passes in the xml of a page and returns the number of pages to scrape for reviews """
        end = int(xml.xpath("//div/div[@class='results']/text()")[0].split(' ')[0].split('(')[1])
        if end / 20 > 25: #max out at 25 pages of reviews
            pages = 26
        else:
            pages = end / 20
        return pages
        
    def scrape_to_df(self, base_url, pages):
        """
        Takes in the hostel url and number pages of reviews and returns a dataframe
        with each row representing a review. Columns are: ratings, review, and page number
        """
        df = []
        for i in xrange(1, pages):
            url = base_url + str(i) + "?period=all" #append string to get all reviews
            xml = self.request_xml(url) 
            reviews = xml.xpath('//div[@class="microreviews rounded"]') # list of reviews
            for review in reviews:
                df.append({
                        'rating':(int(review.xpath('.//div/text()')[1].replace('%', ''))), #numerical rating on review
                        'review': ''.join(review.xpath('.//div/p/text()')).strip(), #text of review
                        'page': i #page number
                        })
        return pd.DataFrame(df) 
    
    def count_amenities(self, hostel, key):
        """ If key/amenity found in review, apply phrase in key column """
        hostel[key] = hostel.apply(lambda x: self.get_key_sentence(x['review'], self.amenities[key]), axis=1)
        return hostel
        
    def get_key_sentence(self, x, key_list):
        """Passes in a review and a bag of words associated with the key
           Returns a sentence in the review containing one or more of the bag of words
        """
        delimiters = ',', '.', ';', '!', '?'
        sentences = self.split(delimiters, x, maxsplit=0)
        for sent in sentences: #loop through phrases in paragraph
            for word in sent.split(): #loop through words in phrase
                if word.lower() in key_list: #check for keyword matches
                    return sent.lower().strip()
    
    def split(self, delimiters, string, maxsplit=0):
        """ Takes in comma separated delimiters and splits paragraph string
            into a list of phrases """
        regexPattern = '|'.join(map(re.escape, delimiters))
        return re.split(regexPattern, string, maxsplit)
    
    def count_words(self, word_freq, sent, stopwords, list_key):
        """Takes in a dictionary, sentence or phrase, stopwords, and bag of words
           and appends counts for word frequencies not in stopwords to find
           the most common words in the reviews
        """
        for word in sent.split():
            if word not in stopwords and word not in list_key:
                if word not in word_freq:
                    word_freq[word] = 1
                else:
                    word_freq[word] += 1
        
    def parse_reviews(self, subset, key):
        """ Takes in a dataframe and key
            Returns a dictionary with the highest frequency words and their counts
            where the key was found in the reviews
        """
        word_freq = {}
        stopwords = nltk.corpus.stopwords.words('english')
        for i in xrange(0, len(subset)): #loop through each review
            self.count_words(word_freq, subset[key][i], stopwords, self.amenities[key])    
        return word_freq
        
    def sentiment_analysis(self, key, hostel):
        """ Returns a dictionary of summary sentiment analysis values
        """
        subset = hostel.dropna() #drop reviews not mentioning key
        subset.reset_index(inplace=True) 
        
        subset['sentiment'] = subset[key].apply(lambda x: TextBlob(x).sentiment.polarity)
        
        word_freq = self.parse_reviews(subset, key)
        d = Counter(word_freq)
        phrase_words = [x[0] for x in d.most_common(3)] #find top 3 keywords describing each review
        summary = {
           'phrase_words': d.most_common(3), #dictionary of top 3 common keywords and their counts
           'hotel_avg': np.mean(hostel['rating']), #average rating of the hostel
           'key_avg':   np.mean(subset['rating']), #average rating of reviews specific to key
           'num':       len(hostel), #number of reviews at hostel
           'mean':      np.mean(subset['sentiment']), #average sentiment of review related to key
           'positive':  len(subset[subset['sentiment'] > 0]), #number of positive reviews
           'negative':  len(subset[subset['sentiment'] < 0]), #number of negative reviews
           'zero':      len(subset[subset['sentiment'] == 0]), #number of zero sentiment reviews
           'max_val':   {
               'num': subset.loc[subset['sentiment'].idxmax()]['sentiment'], #sentiment rating for best review
               'phrase': subset.loc[subset['sentiment'].idxmax()][key] #text for best review
            },
           'min_val':   {
               'num': subset.loc[subset['sentiment'].idxmin()]['sentiment'], #sentiment rating for worst reviews
               'phrase': subset.loc[subset['sentiment'].idxmin()][key] #text for worst review
            },
           'common_phrase': {
               'phrase': '', 
               'num': -1
            }
        }
        # Find the review with the most number of common words aggregated from all key reviews
        for phrase in subset[key]:
            num_words = len([x for word in phrase.split() for x in phrase_words if x in word])
            if  num_words > summary['common_phrase']['num']:
                summary['common_phrase'] = {
                    'phrase': phrase, 
                    'num': num_words
                }

        return summary

                 
