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

# Also requires the python-wordpress-xmlrpc module to be installed e.g. '$ pip install python-wordpress-xmlrpc'

# Uncomment the "wp = Client..." line to use the example WordPress upload function!
# Set the following WordPress details (blog address for xmlrpc, user, password, replace with your own details...)
wp = Client('http://alloutput.com/wxsat/xmlrpc.php', 'wxsat_receiver', 'g7uhnwxsa')

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
            # generate ZA enhancement
            os.system("wxtoimg -e ZA -c -m ./map/%s.png ./resampled/%s_11025.wav ./image/%s-ZA.jpg" % (basefilename, basefilename, basefilename))
            # generate MSA enhancement
            os.system("wxtoimg -e MSA -c -m ./map/%s.png ./resampled/%s_11025.wav ./image/%s-MSA.jpg" % (basefilename, basefilename, basefilename))
            # generate MSA with precipitation enhancement
            os.system("wxtoimg -e MSA-precip -c -m ./map/%s.png ./resampled/%s_11025.wav ./image/%s-MSA-precip.jpg" % (basefilename, basefilename, basefilename))
            # generate Thermal enhancement
            os.system("wxtoimg -e therm -c -m ./map/%s.png ./resampled/%s_11025.wav ./image/%s-Thermal.jpg" % (basefilename, basefilename, basefilename))   
            print('Wxtoimg operation complete', str(datetime.now()))
            time.sleep(5)
            
            # archive the original resampled file (these files will take a lot of space so we'll look to delete old files at some point...)
            os.system("mv ./resampled/%s_11025.wav ./archived-recordings/%s_11025.wav" % (basefilename, basefilename))
            os.system("rm ./map/%s.png" % basefilename)
            print ('Audio file archived', str(datetime.now()))
            time.sleep(5)

            imagefile1 = ('./image/%s.jpg' % basefilename)
            im1 = Image.open(imagefile1)
            imagefile2 = ('./image/%s-ZA.jpg' % basefilename)
            im2 = Image.open(imagefile2)
            imagefile3 = ('./image/%s-MSA.jpg' % basefilename)
            im3 = Image.open(imagefile3)
            imagefile4 = ('./image/%s-MSA-precip.jpg' % basefilename)
            im4 = Image.open(imagefile4)
            imagefile5 = ('./image/%s-Thermal.jpg' % basefilename)
            im5 = Image.open(imagefile5)
            
            if im1.size[1] > 1000:          # if image height is >1000px then publish it (avoids very short, low passes being published)

            #----WordPress stuff starts here------
            #----(Uncomment section to enable)----
            # This section publishes the basic image to my WordPress site
                        
                ##### Image 1 #####
                # ...prepare metadata for the image...
                data = {
                    'name': ('%s.jpg' % basefilename),
                    'type': 'image/jpg',
                }            
                # ...read the binary file and let the XMLRPC library encode it into base64
                with open(imagefile1, 'rb') as img1:
                    data['bits'] = xmlrpc_client.Binary(img1.read())
                # ...upload the image data to WordPress and read the image URL/ID    
                response = wp.call(media.UploadFile(data))
                attachment1_url = response['url']
                attachment1_id = response['id']
                
                ##### Image 2 #####
                # ...prepare metadata for the image...
                data = {
                    'name': ('%s-ZA.jpg' % basefilename),
                    'type': 'image/jpg',
                }            
                # ...read the binary file and let the XMLRPC library encode it into base64
                with open(imagefile2, 'rb') as img2:
                    data['bits'] = xmlrpc_client.Binary(img2.read())
                # ...upload the image data to WordPress and read the image URL/ID    
                response = wp.call(media.UploadFile(data))
                attachment2_url = response['url']
                attachment2_id = response['id']
                
                ##### Image 3 #####
                # ...prepare metadata for the image...
                data = {
                    'name': ('%s-MSA.jpg' % basefilename),
                    'type': 'image/jpg',
                }            
                # ...read the binary file and let the XMLRPC library encode it into base64
                with open(imagefile3, 'rb') as img3:
                    data['bits'] = xmlrpc_client.Binary(img3.read())
                # ...upload the image data to WordPress and read the image URL/ID    
                response = wp.call(media.UploadFile(data))
                attachment3_url = response['url']
                attachment3_id = response['id']
                
                ##### Image 4 #####
                # ...prepare metadata for the image...
                data = {
                    'name': ('%s-MSA-precip.jpg' % basefilename),
                    'type': 'image/jpg',
                }            
                # ...read the binary file and let the XMLRPC library encode it into base64
                with open(imagefile4, 'rb') as img4:
                    data['bits'] = xmlrpc_client.Binary(img4.read())
                # ...upload the image data to WordPress and read the image URL/ID    
                response = wp.call(media.UploadFile(data))
                attachment4_url = response['url']
                attachment4_id = response['id']
                
                ##### Image 5 #####
                # ...prepare metadata for the image...
                data = {
                    'name': ('%s-Thermal.jpg' % basefilename),
                    'type': 'image/jpg',
                }            
                # ...read the binary file and let the XMLRPC library encode it into base64
                with open(imagefile5, 'rb') as img5:
                    data['bits'] = xmlrpc_client.Binary(img5.read())
                # ...upload the image data to WordPress and read the image URL/ID    
                response = wp.call(media.UploadFile(data))
                attachment5_url = response['url']
                attachment5_id = response['id']
            
                # get system uptime
                with open('/proc/uptime', 'r') as f:
                    uptime_seconds = float(f.readline().split()[0])
                    uptime_string = str(timedelta(seconds = uptime_seconds))
            
                # ...construct and publish the post
                post = WordPressPost()
                post.title = basefilename
                post.content = ('Class enhancement:<br><a href="%s"><img class="wxsat" src="%s" alt="" /></a><br>\
                                ZA enhancement:<br><a href="%s"><img class="wxsat" src="%s" alt="" /></a><br>\
                                MSA enhancement:<br><a href="%s"><img class="wxsat" src="%s" alt="" /></a><br>\
                                MSA-precip enhancement:<br><a href="%s"><img class="wxsat" src="%s" alt="" /></a><br>\
                                Thermal enhancement:<br><a href="%s"><img class="wxsat" src="%s" alt="" /></a><br>\
                                <p>System uptime is %s</p>' % (attachment1_url, attachment1_url, attachment2_url, attachment2_url, attachment3_url, attachment3_url, attachment4_url, attachment4_url, attachment5_url, attachment5_url, uptime_string))
                post.post_status = 'publish'
                post.thumbnail = attachment1_id
                post.terms_names = {
                    'category': ['WXSAT-auto']
                    }
                wp.call(NewPost(post))
                print('New post uploaded', str(datetime.now()))    
            #-----WordPress stuff stops here-----

                # copy the new images to the display folder
                os.system("rm ./display/*")         # remove previous image(s) from the display folder
                os.system("cp ./image/* ~/wxsat/display/")   # copy the new images to the display folder

            # archive the original image file (these files will take a lot of space so we'll look to delete old files at some point...)
            os.system("mv ./image/* ./archived-images/")
            print('Image files archived', str(datetime.now()))


    print('Finished loop', str(datetime.now()))
    print('...waiting 2 minutes...')         
    time.sleep(120)   # wait 2 minutes before checking dir1 for any new recordings
