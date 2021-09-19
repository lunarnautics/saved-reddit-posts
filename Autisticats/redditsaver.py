#! usr/bin/env python3
import praw
from prawcore.exceptions import Forbidden
import datetime as dt
import requests

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm

from resizeimage import resizeimage
from PIL import Image as PILImage

from os import listdir, remove

#TO DO
#fix sorting for archived sites
#something with videos?
#something with external sites?
#get more than the past 1000 new posts
#make sure emoji's work
#add comments


#Setup reddit wrapper
#guide: https://praw.readthedocs.io/en/stable/code_overview/models/submission.html
reddit = praw.Reddit(client_id=CLIENT_ID, \
                     client_secret=CLIENT_SECRET, \
                     user_agent='Econiverse', \
                     username='Econiverse', \
                     password=PASSWORD)

#set subreddit
sub = reddit.subreddit('Autisticats')

styleNormal = getSampleStyleSheet()['Normal']

imgFileName = 'temp.png'

#create a file so there is something to delete later
testFile = open(imgFileName, "w+")
testFile.close()

existingFiles = listdir()

#reddit has a limit of 1000
for submission in sub.new(limit=10):
    #Setup title
    original_title = submission.title
    title = ''

    #replace special characters and spaces with _
    for character in submission.title:
        if(character.isalnum()):
            title = title + character
        else:
            title = title + '_'

    #truncate if necessary for pdf
    title = (title[:75]+'..') if len(title) > 75 else title
    title = str(submission.created) + '_' + submission.id + '_' + title


    #check if file already exists
    if not title+'.pdf' in existingFiles:
        #create pdf document
        doc = SimpleDocTemplate(title+'.pdf',pagesize=A4,
                            rightMargin=2*cm,leftMargin=2*cm,
                            topMargin=2*cm,bottomMargin=2*cm)
        #add content
        content = []

        #header content
        try:
            content.append(Paragraph('Title: ' + submission.title, styleNormal))

            #Check if the author field is populated
            if submission.author is None:
               content.append(Paragraph('Author: [deleted]', styleNormal))
            else:
               content.append(Paragraph('Author: ' + submission.author.name, styleNormal))

            content.append(Paragraph('Created ' + dt.datetime.utcfromtimestamp(submission.created_utc).strftime('%Y-%m-%d %H:%M:%S')+' UTC', styleNormal))
            content.append(Paragraph('Permalink: ' + submission.permalink, styleNormal))
            content.append(Paragraph('Url: ' + submission.url, styleNormal))
            content.append(Paragraph('Is_self: ' + str(submission.is_self), styleNormal))
        except:
            content.append(Paragraph('HEADER ERROR', styleNormal))

        #add space between header and body
        content.append(Spacer(1,1*cm))

        #body content
        try:
            #Check what kind of post it is - first check if it is an original text post
            if submission.is_self is True:
               content.append(Paragraph(submission.selftext.replace("\n", "<br />"), styleNormal))

            #check if it is a picture post
            elif submission.url.find("i.redd.it") != -1:
               #get image from url and save to file
               img_data = requests.get(submission.url).content
               with open(imgFileName, 'wb') as handler:
                  handler.write(img_data)

               #resize image to fit on one page [width,height]
               img = PILImage.open(imgFileName)
               img = resizeimage.resize_contain(img, [500,600])
               img.convert('RGB').save(imgFileName, img.format)
               img.close()

               #add to content
               content.append(Image(imgFileName))

            #check if it is a gallery post (aka more than one picture)
            elif submission.url.find("reddit.com/gallery") != -1:
               content.append(Paragraph('Body is multiple pictures!', styleNormal))

            #check if it is a video
            elif submission.url.find("v.redd.it") != -1:
               content.append(Paragraph('Post is a video!', styleNormal))

            #check if is a link but not to reddit
            elif submission.url.find("/r/") == -1 and submission.url.find("www.reddit.com") == -1:
               content.append(Paragraph('Post is linked website!', styleNormal))

            #if nothing else, then it must be a reddit linked post
            else:
               #get linked post content id
               startindex = submission.url.find("/comments/")+10
               endindex = submission.url.find("/",startindex)
               linkedid = submission.url[startindex:endindex]

               #set the submission to the original post
               submission = reddit.submission(linkedid)

               #get the body but try first - this can fail if sub is now private or whatever else if forbidden
               try:
                      content.append(Paragraph(submission.selftext.replace("\n", "<br />"), styleNormal))
               except Forbidden:
                   content.append(Paragraph('Forbidden!', styleNormal))
        except:
            #if all above fails, print error for the body
            content.append(Paragraph('BODY ERROR!', styleNormal))

        #build/save the file
        try:
            doc.build(content)
        except:
            print("did not build!")


#remove temp img img
remove(imgFileName)
