# Python Code to download iCloud Photos
# D.G. Marlow
# 2022.06.20

#
# Import Libraries
#
import pytz
import os
import sys
import click
from datetime import datetime
from configparser import ConfigParser
from pyicloud2 import PyiCloudService

#
# Read Config Variables
#

configur = ConfigParser()
if len(sys.argv[1:]) == 0:
    configur.read('config.ini')
    print("Using Configuration File: ['config.ini']")
else:
    configur.read(sys.argv[1:])
    print("Using Configuration File: ",sys.argv[1:])



#
# Load and Set Local Variables
#
downloadedphotos = 0
skippedphotos = 0
photofileexists = 0
maxphotos = configur.getint('Photos', 'max_photos')
myid = configur.get('User','appleid')
mypass = configur.get('User','applepwd')
alb = configur.get('Photos','album')
mdld = configur.get('Photos','to_directory')
from_date = configur.get('Photos','date_from')
to_date = configur.get('Photos','date_to')
asset_from = configur.get('Photos','asset_from')
asset_to = configur.get('Photos','asset_to')
mytz = configur.get('TimeZone','timezone')

#
# Convert Dates for Photos into TZ Aware Dates
#

tz = pytz.timezone(mytz)
from_date = datetime.fromisoformat(from_date)
from_date = tz.localize(from_date, is_dst=None).astimezone(pytz.utc)
to_date = datetime.fromisoformat(to_date)
to_date = tz.localize(to_date, is_dst=None).astimezone(pytz.utc)
asset_from = datetime.fromisoformat(asset_from)
asset_from = tz.localize(asset_from, is_dst=None).astimezone(pytz.utc)
asset_to = datetime.fromisoformat(asset_to)
asset_to = tz.localize(asset_to, is_dst=None).astimezone(pytz.utc)

#
# Login to iCloud
#
api = PyiCloudService(myid,mypass)

#
# If Two-Factor Auth is needed
#
if api.requires_2fa:
    print("Two-factor authentication required.")
    code = input("Enter the code you received of one of your approved devices: ")
    result = api.validate_2fa_code(code)
    print("Code validation result: %s" % result)

    if not result:
        print("Failed to verify security code")
        sys.exit(1)

    if not api.is_trusted_session:
        print("Session is not trusted. Requesting trust...")
        result = api.trust_session()
        print("Session trust result %s" % result)

        if not result:
            print("Failed to request trust. You will likely be prompted for the code again in the coming weeks")
elif api.requires_2sa:
    import click
    print("Two-step authentication required. Your trusted devices are:")

    devices = api.trusted_devices
    for i, device in enumerate(devices):
        print(
            "  %s: %s" % (i, device.get('deviceName',
            "SMS to %s" % device.get('phoneNumber')))
        )

    device = click.prompt('Which device would you like to use?', default=0)
    device = devices[device]
    if not api.send_verification_code(device):
        print("Failed to send verification code")
        sys.exit(1)

    code = click.prompt('Please enter validation code')
    if not api.validate_verification_code(device, code):
        print("Failed to verify verification code")
        sys.exit(1)

#
# Old 2 factor
#
#if api.requires_2fa:
#    print("Two-factor authentication required. Your trusted devices are:")
#
#    devices = api.trusted_devices
#    for i, device in enumerate(devices):
#        print(
#            "  %s: %s"
#            % (i, device.get("deviceName", "SMS to %s" % device.get("phoneNumber")))
#        )
#
#    device = click.prompt("Which device would you like to use?", default=0)
#    device = devices[device]
#    if not api.send_verification_code(device):
#        print("Failed to send verification code")
#        sys.exit(1)
#
#    code = click.prompt("Please enter validation code")
#    if not api.validate_verification_code(device, code):
#        print("Failed to verify verification code")
#        sys.exit(1)
#

#
# Start the Download of Photos, set start time for process
#
timefordownload = datetime.now()
print("Date of Photos to download from:",from_date.strftime("%b %d, %Y"))
print("Album(s) to download:",alb)
print()
print("START DOWNLOADING PHOTO FILES")

#
# Print off Libraries
#
#print("Find Libraries")
#for library_name, album in api.photos.libraries.items():
#    print(f'Library, Album: {library_name}, {album}')

#main_library = 'SharedSync-E1243494-2790-4767-9CC3-2F8A27FEFE68'
#    for photo in album:
#        print(f'{photo.asset_date} {photo} {photo.filename}')

#
# Set album or all photos
#
if alb == 'all':
    photo = iter(api.photos.all)
else:
    photo = iter(api.photos.albums[alb])


#
# Process Photos from iCloud
#
while(True):

    #
    # Process Next Photo
    #
    dlphoto = next(photo, 'end')

    #
    # Set Condition to stop processing photos.  And exit if met.
    #
    exitloopcondition = (downloadedphotos >= maxphotos) \
                        or (not hasattr(dlphoto,'added_date')) \
                        or (dlphoto.added_date <= from_date)

    if exitloopcondition:
        totaltime = datetime.now()-timefordownload
        print()
        print(downloadedphotos,"PHOTO FILE(S) DOWNLOADED")
        print(skippedphotos, "PHOTO FILE(S) SKIPPED")
        print(photofileexists, "DUPLICATE PHOTO FILE(S) SKIPPED")
        print("PROCESS COMPLETED, TOTAL TIME FOR DOWNLOAD PROCESS:", totaltime)
        break

    #
    # if exit condition was not met, process photo to download (or not download)
    #
    else:

        #
        # break out asset created date for creating directory structure and file name
        #
        dlyear = str(dlphoto.asset_date)[0:4]
        dlmonth = str(dlphoto.asset_date)[5:7]
        dlday = str(dlphoto.asset_date)[8:10]
        dldirectory = mdld + dlyear + "/" + dlmonth + "/" + dlday + "/"
        dlfullfile = dldirectory + dlphoto.filename

        #
        # If the file does not exist in the target directory, and it is within the
        # requested asset date range in the config.ini file, start to download
        # the photo, or else loop.  Start timer on the process for downloading.
        #
        validdate = asset_to >= dlphoto.asset_date >= asset_from
        if (not os.path.exists(dlfullfile)) and (validdate):

            print("DOWNLOADING: ",dlfullfile)

            #
            # If the directory does not exist, create the directory
            #
            if not os.path.isdir(dldirectory):
                os.makedirs(dldirectory)

            #
            # Download file and write into directory and
            # Increment downloaded photo variable
            #
            download = dlphoto.download()
            with open(dlfullfile, 'wb') as opened_file:
                opened_file.write(download.raw.read())
            downloadedphotos = downloadedphotos + 1

        else:

            #
            # Increment skipped photo variable if photo was not downloaded
            #
            skippedphotos = skippedphotos + 1
            if os.path.exists(dlfullfile):
                photofileexists = photofileexists + 1

#
# Code End
#
