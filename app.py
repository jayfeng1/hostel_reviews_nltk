# -*- coding: utf-8 -*-
"""
Created on Sat Nov  7 14:08:15 2015

@author: jay

TWITTER API CLIENT
Summary: Reads in twitter timeline and responds to tweets 
that are about hostels and a keyword. 
"""
import os
#os.chdir("path_to_HostelReview")
from hostel_review import HostelReview
import logging
import tweepy
import requests
import numpy as np
import pickle
    
def login():
    """Login with api keys"""
    keys = pickle.load(open("twitter_oauth.p", "rb"))
    CONSUMER_KEY, CONSUMER_SECRET, oauth_token, oauth_token_secret = [key for key in keys] #read in tokens
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(oauth_token, oauth_token_secret)    
    return auth

def hostel_main(url, key):
    """ Run the main analysis program of the hostel
        Scrapes the url and returns a dictionary of analysis of the hostel
        Explanation in blog
    """
    ht =        HostelReview(url) #initiate hostel review class
    logger.info('Hostel instantiated')
    first_url = ht.url + "1?period=all" 
    xml =       ht.request_xml(first_url) #get xml of first page
    pages =     ht.find_end(xml) #extract the number of pages to scrape
    df =        ht.scrape_to_df(ht.url, pages) #scape pages and transpose to dataframe
    df =        ht.count_amenities(df, key) #create a new column for the keyword features
    return      ht.sentiment_analysis(key, df) #return dictionary of analysis
    
def get_word(txt):
    """ Find keyword within the tweet, else return None """
    for word in txt:
        for amen in ['wifi', 'breakfast', 'bathroom', 'shower', 'noise']:
            if amen in word.lower():
                return amen

def get_tweet_url(txt):
    """ Find url in tweet, else return None """
    for word in txt:
        if 'https://t.co' in word:
            return check_url_format(requests.get(word).url)

def check_url_format(url):
    """ Check that the url is correct else raise error flag """
    if "hostelworld.com" in url:
        if "www" not in url:
            url = url.replace("t.hostelworld.com", "www.hostelworld.com")
        return url.split('?')[0] + '/reviews/'
    else:
        return "no"
    
def get_params(tweet):
    """ Takes in a tweet object and returns screen name, id, url, and keyword """
    txt = tweet.text.split()
    return '@' + tweet.user.screen_name, tweet.id, get_tweet_url(txt), get_word(txt)

def compute_status(analysis, screen_name, key):
    """ Takes results json analysis and creates a tweet that aggregates the information
        without taking over 140 characters
    """
    hostel_key_rating = str(np.round(analysis['key_avg'],0))
    tweet_status = screen_name + " " + key + " rating: " + hostel_key_rating + "/100. Positive: " + \
        str(analysis['positive']) + " Negative: " + str(analysis['negative']) + ' "' + analysis['common_phrase']['phrase'] + '"'
    if len(tweet_status) > 140:
        tweet_status = tweet_status[0:139]
    return tweet_status
    
def get_unread_statuses(all_tweets):
    """ Passes in the tweepy api and reads from the timeline to return
        which tweets have been answered before
    """
    seen_ids = pickle.load(open("seen_twitter.p", "rb"))
    return [x for x in all_tweets if x.id not in seen_ids]

def store_tweet_ids(all_tweets):
    """ Take all tweet ids on timeline and store them in a pickle file """
    tweet_ids = [x.id for x in all_tweets]
    pickle.dump(tweet_ids, open("seen_twitter.p", "wb"))
    
def catch_errors(url, key, screen_name):
    """ Throw error messages for wrong inputs into tweets """
    if url is None:
        return screen_name + " Can't find a url buddy"
    elif url == 'no':
        return screen_name + " Not the right url buddy"
    elif key is None:
        return screen_name + " Can't find an amenity to search for buddy, or you are a bad speller"
    

def update_hostel_status(api, tweet):
    """ update status for each tweet """
    screen_name, reply_id, url, key = get_params(tweet)
    status_errors = catch_errors(url, key, screen_name)
    if status_errors is not None: #check for errors in tweet mention
        tweet_status = status_errors
    else: 
        try:
            analysis = hostel_main(url, key) #call hostel main function
            tweet_status = compute_status(analysis, screen_name, key) 
        except:
            tweet_status = screen_name + ' YOU BROKE SOMETHING' #adhoc message for breaking the program
    api.update_status(status = tweet_status, in_reply_to_status_id = reply_id)

            
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO) #initiate logging
    logger = logging.getLogger()
    
    auth = login() #login 
    api = tweepy.API(auth)
    all_tweets = api.mentions_timeline() #grab all tweets from timeline
    tweets = get_unread_statuses(all_tweets) #save the unread mentions
    for tweet in tweets: 
        update_hostel_status(api, tweet) #reply to each mention
    store_tweet_ids(all_tweets) #store tweets so it doesn't repeat next time
