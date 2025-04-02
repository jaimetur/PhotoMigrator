# ROADMAP:

## v3.2.0  
### Release Date: (estimated)
  - Alpha version    : 2025-04-07
  - Beta version     : 2025-04-14
  - Release Candidate: 2025-04-25
  - Official Release : 2025-04-30

### TODO:
- [ ] Add option to filter assets in all Immich/Synology/LocalFolder Actions:
    - [x] by Dates
    - [x] by Country
    - [x] by City
    - [ ] by People
    - [ ] by Type
- [x] Added new flag _**-from, --from-date <FROM_DATE>**_ to select the Initial Date of the Assets to download
- [x] Added new flag _**-to, --to-date <TO_DATE>**_ to select the Final Date of the Assets to download
- [x] Added new flag _**-country, --country <COUNTRY_NAME>**_ to select the Country Name of the Assets to download
- [x] Added new flag _**-city, --city <CITY_NAME>**_ to select the City Name of the Assets to download
- [x] Added new flag _**-people, --people <PEOPLE_NAME>**_ to select the People Name of the Assets to download
- [x] Added new flag _**-type, --type = [photos, videos, all]**_ to select the Asset Type to download (default: all)
- [x] Added new flag _**-parallel, --parallel-migration =[true,false]**_ to select the Migration Mode (Parallel or Secuential). Default: true (parallel)
- [x] Include Live Dashboard in secuential Automated Migration
- [x] Test secuential Automated Migration
- [ ] Test Filters in other Synology/Immich Features
- [x] Minor bugs fixing
- [ ] Update Documentation
- [ ] Update README.md
- [ ] Update RELEASES-NOTES.md


## v4.0.0:
### Release Date: (estimated)
  - Alpha version    : (No estimated date)
  - Beta version     : (No estimated date)
  - Release Candidate: (No estimated date)
  - Official Release : (No estimated date)

### TODO:
- [ ] Include Apple Support (initially just for downloading)
    - [ ] Create Class ClassApplePhotos with the same methods and behaviour as ClassSynologyPhotos or ClassImmichPhotos. (volunteers are welcomed)
    - [ ] -adAlb, --apple-download-albums
    - [ ] -adAll, --apple-download-all
    - [ ] -auAlb, --apple-upload-albums
    - [ ] -auAll, --apple-upload-all
- [ ] Include native support for Google Photos through API  
  (See: https://max-coding.medium.com/loading-photos-and-metadata-using-google-photos-api-with-python-7fb5bd8886ef)
    - [ ] Create Class ClassGooglePhotos with the same methods and behaviour as ClassSynologyPhotos or ClassImmichPhotos. (volunteers are welcomed)
    - [ ] -gdAlb, --google-download-albums
    - [ ] -gdAll, --google-download-all
    - [ ] -guAlb, --google-upload-albums
    - [ ] -guAll, --google-upload-all
- [ ] Allow Google Photos and Apple Photos as TARGET in AUTOMATED-MODE
- [ ] Update Documentation
- [ ] Update README.md
- [ ] Update RELEASES-NOTES.md
