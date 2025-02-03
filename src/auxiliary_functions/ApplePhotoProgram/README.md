# ApplePhotoProgram
Script to download photos from Apple's Photo application in iCloud

DGM 2024.01.02 -

Updated the script to be able to also download pictures that you have put in a shared directory on Apple Photos on iCloud. In the ini file, you will see where you can add the shared directory name. Each library will have a different name in iCloud. The main library (not shared) will be PrimarySync. I had to add another python program to be able to set a global variable to send the specific library to the pyicloudservice which requires it. No need to add anything to the program, but just needs to be there in the same folder.
About 1/2 down the code in main.py there is a commented out section that will print out the different libraries so you know the actual names of each library.
Also, I fixed the 2-step security logon to make that work more consistantly. So it will ask for the numbers that are sent to one of your other icloud devices instead of asking for a specific device.
I will do some more work on this program in the coming weeks, but wanted to get this version out there first.
I have created a quick python program to download your Apple Photos direct from icloud to your NAS. It works great for me, but do remember that this is not a formal licensed program but instead is just a python script used for my own purposes and as such no guarantees or rights, etc... It is two files, main.py which is the python program and then config.ini which holds the configuration items. Since this post does not let me attach them as files, I will add the text below and you can cut and past into files and then run them with python to do your bidding.

The program does require some libraries to be installed via pip (see the import section) if you have not loaded them. The major one being "pip install pytz pyicloud". This one lets you get into icloud and of course is called pyicloud and is a great library and does more than just icloud photos. I am running the beta version of Python 3.9 as some of the imports are 3.7 and above I believe. I just run it via python main.py and it goes. It is a little verbose as again it is just me getting started with the program.

A few items to keep in mind. In the config file there are two ways to download photos. One is all photos based on their added date (the date added to your library in photos on icloud) back to the "date_from" date in config.ini. The format is specific year-month-day so keep to that format (shown in the ini file). The other way is by album, but also constrained by the added date as all photos would be. So if you want all photos in the album, just put an old date out there.

Another constraint which is in there to keep me from messing up is a parameter in the ini file for maxphotos. This limits the number of photos downloaded during a session. I set it low when I started to ensure it was doing what I wanted.

As far as where the photos go, it will go to the directory that you add in ini file and then automatically builds a structure based on the photo's created date /directory/2022/06/21/... That is sadly hard coded in the program, so feel free to change that if you want.
