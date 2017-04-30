#!/usr/bin/env python2
import os
import time
from datetime import datetime
from datetime import timedelta
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.compat import xmlrpc_client
from wordpress_xmlrpc.methods import media, posts
from wordpress_xmlrpc.methods.posts import NewPost
from PIL import Image

# A script to automate processing of recorded weather satellite signals (recorded as raw audio files from rtl_fm)
# Written by Andy Webster, G7UHN

# On Raspbian/ Raspberry Pi 3, this script requires the following dependencies to be installed:
# lsof, sox, wxtoimg (ARM version)


### Uncomment the "wp = Client..." line to use the example WordPress upload function!
### Also requires the python-wordpress-xmlrpc module to be installed e.g. '$ sudo pip install python-wordpress-xmlrpc'
### Set the following WordPress details (blog address for xmlrpc, user, password, replace with your own details...)
##wp = Client('http://alloutput.com/xmlrpc.php', 'user', 'password')

# Set the following sub-directories
dir1 = "./recorded"
dir2 = "./resampled"
dir2a = "./archived-recordings"
dir3 = "./image"
dir3a = "./archived-images"
dir4 = "./map"
dir5 = "./display"

# Main Loop
while True:
    print('Starting loop', str(datetime.now()))
    # set up the sub-directories if they are not already present
    if os.path.exists(dir1) == False:
        os.system("mkdir recorded")
    if os.path.exists(dir2) == False:
        os.system("mkdir resampled")
    if os.path.exists(dir2a) == False:
        os.system("mkdir archived-recordings")
    if os.path.exists(dir3) == False:
        os.system("mkdir image")
    if os.path.exists(dir3a) == False:
        os.system("mkdir archived-images")
    if os.path.exists(dir4) == False:
        os.system("mkdir map")
    if os.path.exists(dir5) == False:
        os.system("mkdir display")

    # check for any new recordings
    newfiles = os.listdir(dir1)
    # if any new recordings are found in dir1, perform the following actions
    for file in newfiles:
        basefilename = os.path.splitext(file)[0]
        if os.system("lsof | grep %s" % file) != 0:   # check if the recording has finished...

            # resample the recorded file to 11.025 kHz
            os.system("sox -t raw -r 40000 -es -b16 -c1 -V1 ./recorded/%s ./resampled/%s_11025.wav rate 11025" % (file, basefilename))
            # ...note the options after "sox" are matched to the rtl_fm recording settings e.g. rate/bandwidth = 40000
            # this figure will need changing if the rtl_fm recording bandwidth is adjusted
            print('Recording has been resampled to 11.025kHz', str(datetime.now()))
            time.sleep(5)

            # copy the original recording's file attributes to the new resampled file
            # (wxtoimg looks at file modified times to determine a matching satellite pass, generate map, etc.)
            os.system("touch -r ./recorded/%s ./resampled/%s_11025.wav" % (file, basefilename))
            print('File properties matched', str(datetime.now()))
            time.sleep(5)
            
            # delete the original recorded file (these files will take a lot of space and we have the resampled recording to work with now)
            os.system("rm ./recorded/%s" % file)
            print('Original recording deleted', str(datetime.now()))
            time.sleep(5)
          
            # trigger wxmap to generate map overlay image
            timestamp=os.path.getmtime('./resampled/%s_11025.wav' % basefilename)
            print('timestamp=', timestamp)
            modtime=datetime.fromtimestamp(timestamp).strftime("%d %m %Y %H:%M")
            print('modtime=', modtime)
            print("wxmap %s ./map/%s.png" % (modtime, basefilename))
            os.system('wxmap -T "NOAA 19" -T "NOAA 15" -T "NOAA 18" -H ~/.wxtoimg/weather.txt -L "51.054/-0.888/60" "%s" ./map/%s.png' % (modtime, basefilename))
            # (adjust LAT/LON/ALT data after "-L" in the line above to your own station...)

            # trigger wxtoimg to decode the new resampled file into a basic image
            os.system("wxtoimg -e class -m ./map/%s.png -A ./resampled/%s_11025.wav ./image/%s.jpg" % (basefilename, basefilename, basefilename))
            print('Wxtoimg operation complete', str(datetime.now()))
            time.sleep(5)
            
            # archive the original resampled file (these files will take a lot of space so we'll look to delete old files at some point...)
            os.system("mv ./resampled/%s_11025.wav ./archived-recordings/%s_11025.wav" % (basefilename, basefilename))
            os.system("rm ./map/%s.png" % basefilename)
            print ('Audio file archived', str(datetime.now()))
            time.sleep(5)

            imagefile = ('./image/%s.jpg' % basefilename)
            im = Image.open(imagefile)
            
            if im.size[1] > 1000:          # if image height is >1000px then publish it (avoids very short, low passes being published)

##            #----WordPress stuff starts here------
##            #----(Uncomment section to enable)----
##            # This section publishes the basic image to my WordPress site
##                        
##                # ...prepare metadata for the image...
##                data = {
##                    'name': ('%s.jpg' % basefilename),
##                    'type': 'image/jpg',
##                }
##            
##                # ...read the binary file and let the XMLRPC library encode it into base64
##                with open(imagefile, 'rb') as img:
##                    data['bits'] = xmlrpc_client.Binary(img.read())
##
##                response = wp.call(media.UploadFile(data))
##                attachment_url = response['url']
##                attachment_id = response['id']
##            
##                # get system uptime
##                with open('/proc/uptime', 'r') as f:
##                    uptime_seconds = float(f.readline().split()[0])
##                    uptime_string = str(timedelta(seconds = uptime_seconds))
##            
##                # ...construct and publish the post
##                post = WordPressPost()
##                post.title = basefilename
##                post.content = ('<a href="%s"><img class="alignright size-large wp-image-1381" src="%s" alt="" width="960" height="852" /></a><br><p>System uptime is %s</p>' % (attachment_url, attachment_url, uptime_string))
##                post.post_status = 'publish'
##                post.terms_names = {
##                    'category': ['WXSAT-auto']
##                    }
##                wp.call(NewPost(post))
##                print('New post uploaded', str(datetime.now()))    
##            #-----WordPress stuff stops here-----

                # copy the new image to the display folder
                os.system("rm ./display/*.jpg")         # remove previous image(s) from the display folder
                os.system("cp ./image/%s.jpg ~/wxsat/display/%s.jpg" % (basefilename, basefilename))   # copy the new image to the display folder

            # archive the original image file (these files will take a lot of space so we'll look to delete old files at some point...)
            os.system("mv ./image/%s.jpg ./archived-images/%s.jpg" % (basefilename, basefilename))
            print('Image file archived', str(datetime.now()))


    print('Finished loop', str(datetime.now()))
    print('...waiting 2 minutes...')         
    time.sleep(120)   # wait 2 minutes before checking dir1 for any new recordings
