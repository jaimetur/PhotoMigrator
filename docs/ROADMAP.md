# ROADMAP:

## v3.3.0  
### Release Date:
  - Alpha version    : 2025-05-16
  - Beta version     : 2025-05-23
  - Release Candidate: 2025-05-30
  - Official Release : 2025-05-30

### TODO:
- [x] Add Feature to Merge Albums with the same name and different assets. 
- [x] Add new flags _**-sMergAlb, --synology-merge-suplicates-albums**_ and _**-iMergAlb, --immich-merge-suplicates-albums**_ to activate this feature.
- [ ] Rename Albums using regular expresions. 


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
