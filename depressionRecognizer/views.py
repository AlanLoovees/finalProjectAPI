from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view
import os
from django.conf import settings
import json
import pandas as pd
import numpy as np
import csv
import tweepy as tw
import csv
import re
from tweepy.auth import OAuthHandler
import nltk.tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn import metrics


accessToken = '2210845584-ChruE1rERcvIRGmVTqn3UDvLrW3h9hXtOodu9Ec'
accessTokenSecret = '3WhULUNaC3Bw98t0osC0iVtYS99fI6Ktd0OozOevVnYD3'
apiKey = 'H6YCAwHAXnEj9Zi1y3pzCTFNh' 
apiSecretKey = 'xu2HNuzupwAp0V49Hk3p3RpkxDnuXDFez3TKCpsSeUJlwWnMMZ'

auth = tw.OAuthHandler(apiKey,apiSecretKey) 
auth.set_access_token(accessToken,accessTokenSecret) 
api = tw.API(auth,wait_on_rate_limit=True)

vectorizer = CountVectorizer(tokenizer=lambda doc: doc, lowercase=False)
tweetClassifier = MultinomialNB()
activityClassifier = MultinomialNB()

datasetReader = pd.read_csv(os.path.join(settings.BASE_DIR, 'smallDataset.csv'))
df = pd.DataFrame(datasetReader)

tweetFeature = vectorizer.fit_transform(datasetReader.Tweet)

# X = np.asarray(df[['Followees', 'Followers', 'No of posts', 'Retweet count', 'Favorite count', 'Positive words', 'Negative words', 'No: of Words']])

# Y = np.asarray(df['Depressed'])

tweetClassifier.fit(tweetFeature, datasetReader.Target)
# activityClassifier.fit(X, Y)

try:
    print("Classifiers ready!\n")
except:
    pass

@api_view(('POST',))
def username(request):
    username = request.POST.get('username')
    tweetList = []
    name = ''
    profileImageURL = ''
    tweetDetails = {'Tweet':{}, "Followees": {}, "Followers": {}, "No of posts": {}, "Retweet count": {}, "Favorite count": {}, "Positive words": {}, "Negative words": {}, "No: of Words": {}}
    dataLists = [[] for i in range(9)]
    tweets = api.user_timeline(screen_name=username ,exclude_replies=True, include_rts=False, tweet_mode='extended')
    for i,tweet in enumerate(tweets):
        pos, neg = posNeg(tweet.full_text)
        countOfWords = countWords(tweet.full_text)
        cleanedTweet = cleaning(tweet.full_text)
        cleanedTweet = toLowerCase(cleanedTweet)
        cleanedTweet = stop_words(cleanedTweet)
        cleanedTweet = stemmingLines(cleanedTweet)
        tweetList.append(tweet.full_text)
        name = tweet.user.name
        profileImageURL = tweet.user.profile_image_url_https

        dataLists[0].append(cleanedTweet)
        dataLists[1].append(api.get_user(username).friends_count)
        dataLists[2].append(api.get_user(username).followers_count)
        dataLists[3].append(api.get_user(username).statuses_count)
        dataLists[4].append(tweet.retweet_count)
        dataLists[5].append(tweet.favorite_count)
        dataLists[6].append(pos)
        dataLists[7].append(neg)
        dataLists[8].append(countOfWords)

    tweetDetails['Tweet'] = dataLists[0]
    tweetDetails['Followees'] = dataLists[1]
    tweetDetails['Followers'] = dataLists[2]
    tweetDetails['No of posts'] = dataLists[3]
    tweetDetails['Retweet count'] = dataLists[4]
    tweetDetails['Favorite count'] = dataLists[5]
    tweetDetails['Positive words'] = dataLists[6]
    tweetDetails['Negative words'] = dataLists[7]
    tweetDetails['No: of Words'] = dataLists[8]

    avg, tally = training(tweetDetails)

    res = {"name": name, "username":username, "profileImage": profileImageURL, "followees":tweetDetails['Followees'][0], "followers":tweetDetails['Followers'][0], "postCount":tweetDetails['No of posts'][0], "depLevel": avg, "tally": tally, "tweets":tweetList}

    return Response(res)

@api_view(('POST',))
def tweet(request):
    tweet = request.POST.get('tweet')
    username = ''
    name = ''
    profileImageURL = ''
    tweetData = tw.Cursor(api.search, q = tweet, lang ='en', exclude='retweets').items(1)
    tweetDetails = {'Tweet':{}, "Followees": {}, "Followers": {}, "No of posts": {}, "Retweet count": {}, "Favorite count": {}, "Positive words": {}, "Negative words": {}, "No: of Words": {}}
    
    for i in tweetData:
        username = i.user.screen_name
        tweet = i.text
        name = i.user.name
        profileImageURL = i.user.profile_image_url_https

        pos, neg = posNeg(tweet)
        countOfWords = countWords(tweet)
        cleanedTweet = cleaning(tweet)
        cleanedTweet = toLowerCase(cleanedTweet)
        cleanedTweet = stop_words(cleanedTweet)
        cleanedTweet = stemmingLines(cleanedTweet)

        tweetDetails['Tweet'] = cleanedTweet
        tweetDetails['Followees'] = api.get_user(username).friends_count
        tweetDetails['Followers'] = api.get_user(username).followers_count
        tweetDetails['No of posts'] = api.get_user(username).statuses_count
        tweetDetails['Retweet count'] = i.retweet_count
        tweetDetails['Favorite count'] = i.favorite_count
        tweetDetails['Positive words'] = pos
        tweetDetails['Negative words'] = neg
        tweetDetails['No: of Words'] = countOfWords

    avg, tally = training(tweetDetails)

    res = {"name": name, "username":username, "profileImage": profileImageURL, "followees":tweetDetails['Followees'], "followers":tweetDetails['Followers'], "postCount":tweetDetails['No of posts'], "tweet":tweet, "depLevel": avg}
    return Response(res)

@api_view(('POST',))
def keywords(request):
    keywords = request.POST.get('keywords')
    noOfTweets = int(request.POST.get('noOfTweets'))
    # noOfTweets = 5
    tweetList = []
    userList = []
    usernameList = []
    profileList = []
    tweetDetails = {'Tweet':{}, "Followees": {}, "Followers": {}, "No of posts": {}, "Retweet count": {}, "Favorite count": {}, "Positive words": {}, "Negative words": {}, "No: of Words": {}}
    dataLists = [[] for i in range(9)]

    tweets = tw.Cursor(api.search, q = keywords, lang ='en', exclude='retweets').items(noOfTweets)
    
    for i,tweet in enumerate(tweets):
        pos, neg = posNeg(tweet.text)
        countOfWords = countWords(tweet.text)
        cleanedTweet = cleaning(tweet.text)
        cleanedTweet = toLowerCase(cleanedTweet)
        cleanedTweet = stop_words(cleanedTweet)
        cleanedTweet = stemmingLines(cleanedTweet)

        # print(tweet)

        tweetList.append(tweet.text)
        userList.append(tweet.user.name)
        usernameList.append(tweet.user.screen_name)
        profileList.append(tweet.user.profile_image_url)

        dataLists[1].append(api.get_user(tweet.user.screen_name).friends_count)
        dataLists[2].append(api.get_user(tweet.user.screen_name).followers_count)
        dataLists[3].append(api.get_user(tweet.user.screen_name).statuses_count)
        dataLists[4].append(tweet.retweet_count)
        dataLists[5].append(tweet.favorite_count)
        dataLists[6].append(pos)
        dataLists[7].append(neg)
        dataLists[8].append(countOfWords)
        dataLists[0].append(cleanedTweet)

    tweetDetails['Tweet'] = dataLists[0]
    tweetDetails['Followees'] = dataLists[1]
    tweetDetails['Followers'] = dataLists[2]
    tweetDetails['No of posts'] = dataLists[3]
    tweetDetails['Retweet count'] = dataLists[4]
    tweetDetails['Favorite count'] = dataLists[5]
    tweetDetails['Positive words'] = dataLists[6]
    tweetDetails['Negative words'] = dataLists[7]
    tweetDetails['No: of Words'] = dataLists[8]

    avg, tally = training(tweetDetails)

    res = {"keywords":keywords, "noOfTweets":noOfTweets, "Tweets":tweetList , "depTally": tally, "users": userList, "usernames": usernameList, "profilePictures": profileList}
    return Response(res)


def cleaning(tweet):
	tweet = re.sub('@[\w]+','',tweet)
	tweetCleaned = re.sub(r"http\S+", "", tweet)
	tweetWithoutSpChars = re.sub(r'[^\w\s]','',tweetCleaned)
	return tweetWithoutSpChars

def readwords(filename):
    f = open(os.path.join(settings.BASE_DIR, filename))
    words = [ line.rstrip() for line in f.readlines()]
    return words

def toLowerCase(line):
  return line.lower()

def tokenize(line):
	return nltk.tokenize.word_tokenize(line)
	
def stop_words(line):
	swords = set(stopwords.words('english')) 

	words = line.split() 
	f=[]
	for i in words: 
		if not i in swords: 
			f.append(i)
	return f

def stemmingLines(line):  
  ps = PorterStemmer()
  output=[]
  for w in line:
    output.append(ps.stem(w))
  return output

def posNeg(paragraph):
	positive = readwords('./positive.txt')
	negative = readwords('./negative.txt')
	punctuations = '''!()-[]{};:'"\,<>./?@#$%^&*_~'''
	no_punct = ""
	for char in paragraph:
	   if char not in punctuations:
		   no_punct = no_punct + char		   
	words=no_punct.split()
	pos = 0
	neg = 0
	for w in words:
		if w in positive:
		    pos += 1
		if w in negative:
		    neg += 1
	return pos,neg

def countWords(tweet):
	tweetList = tweet.split(" ")
	return(len(tweetList))

def training(tweetDetails):
    
    testTweetFeature = vectorizer.transform(tweetDetails['Tweet'])

    # Xt = np.asarray([tweetDetails['Followees'],tweetDetails['Followers'],tweetDetails['No of posts'],tweetDetails['Retweet count'],tweetDetails['Favorite count'],tweetDetails['Positive words'],tweetDetails['Negative words'],tweetDetails['No: of Words']])

    # if(Xt.ndim == 1):
    #     Xt = Xt.reshape(1,-1)
    # else:
    #     Xt = Xt.transpose()

    prediction1 = tweetClassifier.predict_proba(testTweetFeature)
    # prediction2 = activityClassifier.predict_proba(Xt)

    # pos = []
    # weight = 0.01

    # Logarithmic addition for combining probabilities
    # for i in range(len(prediction2)):
    #     res = [np.exp(np.log(prediction1[i][0]) + np.log(prediction2[i][0]+weight)),np.exp(np.log(prediction1[i][1]) + np.log(prediction2[i][1]+weight)),np.exp(np.log(prediction1[i][2]) + np.log(prediction2[i][2]+weight))]
    #     pos.append(res)

    tally = []

    # Adding the tally of resutls to a tally list

    for i in prediction1:
        if i[0] > i[1]:
            if i[0] > i[2]:
                tally.append(4)
            else:
                tally.append(0)
        else:
            if i[1] > i[2]:
                tally.append(2)
            else:
                tally.append(0)

    try:
        print(tally)
    except:
        pass

    avg = 0

    for i in tally:
        avg += i

    avg = avg/len(tally)

    return avg, tally