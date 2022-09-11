#! usr/bin/env python3
import praw ,requests
import datetime as dt
from prawcore.exceptions import Forbidden
from os import listdir, remove, environ
from resizeimage import resizeimage
from PIL import Image as PILImage

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm

#TO DO
#fix sorting for archived sites
#something with videos?
#something with external sites?
#get more than the past 1000 new posts
#make sure emoji's work
#add comments

#setup variables that are github secrets
CLIENT_ID = environ.get("CLIENT_ID")
CLIENT_SECRET = environ.get("CLIENT_SECRET")
PASSWORD = environ.get("PASSWORD")
SUBREDDIT = environ.get("SUBREDDIT")

#Setup reddit wrapper
#guide: https://praw.readthedocs.io/en/stable/code_overview/models/submission.html
reddit = praw.Reddit(client_id=CLIENT_ID, \
                     client_secret=CLIENT_SECRET, \
                     user_agent='Econiverse', \
                     username='Econiverse', \
                     password=PASSWORD)

#set subreddit
sub = reddit.subreddit(SUBREDDIT)

#define functions
#function to make the title sutable for a pdf name
def CleanTitle(rawTitle):
    newTitle = ''

    #replace special characters and spaces with _
    for character in rawTitle:
        if(character.isalnum()):
            newTitle = newTitle + character
        else:
            newTitle = newTitle + '_'

    #truncate if necessary for pdf file name
    newTitle = (newTitle[:75]+'..') if len(newTitle) > 75 else newTitle

    return newTitle

#function to save image to a temp file
def SaveImg(url,name):
    #get image data from url and save to file
    img_data = requests.get(url).content

    #write data to file
    with open(name, 'wb') as handler:
       handler.write(img_data)

    #resize image to fit on one page [width,height]
    img = PILImage.open(name)
    img = resizeimage.resize_contain(img, [500,600])
    img.convert('RGB').save(name, img.format)
    img.close()

#variable for pdf styling
styleNormal = getSampleStyleSheet()['Normal']

#create 20 files so there is something to delete later..It would be nice to not have temporary image files, but for another day
for i in range(0,21):
    imgFileName = 'temp' + str(i) + '.png'
    testFile = open(imgFileName, "w+")
    testFile.close()

#get a list of existing files
existingFiles = listdir()

#try first - loop will fail if sub has been locked or removed
try:
    #for each submission when sorting the sub by new - reddit has a limit of 1000
    for submission in sub.new(limit=1000):

        #make the title sutable for a pdf name and add the unix time and reddit id to make it unique
        title = CleanTitle(submission.title)
        title = str(submission.created) + '_' + submission.id + '_' + title

        #check if file already exists and if it doesn't build a pdf
        if not title+'.pdf' in existingFiles:
            #create pdf document
            doc = SimpleDocTemplate(title+'.pdf',pagesize=A4,
                                rightMargin=2*cm,leftMargin=2*cm,
                                topMargin=2*cm,bottomMargin=2*cm)
            #variable used to build content
            content = []

            #build the header
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
                #content.append(Paragraph('Is_self: ' + str(submission.is_self), styleNormal))
            except:
                content.append(Paragraph('HEADER ERROR', styleNormal))
                print('Header Error!')

            #add space between header and body
            content.append(Spacer(1,1*cm))

            #body content
            try:
                #Check what kind of post it is - first check if it is an original text post to that sub
                if submission.is_self is True:
                   content.append(Paragraph(submission.selftext.replace("\n", "<br />"), styleNormal))

                #check if it is a picture post
                elif submission.url.find("i.redd.it") != -1:
                   #get image from url and save to file
                   SaveImg(submission.url,'temp0.png')

                   #add to content
                   content.append(Image('temp0.png'))

                #check if it is a gallery post (aka more than one picture)
                elif submission.url.find("reddit.com/gallery") != -1:
                    #check if it is a linked post by comparing the ids
                    #get permalink id
                    startindex = submission.permalink.find("/comments/")+10
                    endindex = submission.permalink.find("/",startindex)
                    permalinkId = submission.permalink[startindex:endindex]

                    #get url id
                    startindex = submission.url.find("/gallery/")+9
                    endindex = startindex + 6
                    urlId = submission.url[startindex:endindex]

                    #compare them
                    if permalinkId != urlId:
                        submission = reddit.submission(urlId)
                        content.append(Paragraph('Linked Post Content:', styleNormal))

                    #get post metadata
                    image_dict = submission.media_metadata
                    imgCounter = 1

                    #search it for images
                    for image_item in image_dict.values():
                        try:
                            #this can fail for gifs and deleted posts
                            largest_image = image_item['s']
                            image_url = largest_image['u']
                            imgTitle = 'temp' + str(imgCounter) + '.png'

                            #save them as temp images
                            SaveImg(image_url,imgTitle)

                            #add to content
                            content.append(Image(imgTitle))
                        except:
                            print('failed to save image')

                        #add 1 to imgCounter
                        imgCounter = imgCounter + 1

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
                       content.append(Paragraph('Linked Post Content:', styleNormal))
                       content.append(Paragraph(submission.selftext.replace("\n", "<br />"), styleNormal))
                   except Forbidden:
                       content.append(Paragraph('Forbidden!', styleNormal))
            except:
                #if all above fails, print error for the body
                content.append(Paragraph('BODY ERROR!', styleNormal))
                print(title)
                print('Body Error!')

            #build/save the file
            try:
                doc.build(content)
            except:
                print("did not build!")

except:
    print("error with sub")                
                
#remove temp img
for i in range(0,21):
    imgFileName = 'temp' + str(i) + '.png'
    remove(imgFileName)
