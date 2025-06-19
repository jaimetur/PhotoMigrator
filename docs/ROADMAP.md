## 📅 ROADMAP
[Planed Roadmap](https://github.com/jaimetur/PhotoMigrator/blob/main/docs/ROADMAP.md) for the following releases

---

## Release: v3.3.4
- ### Release Date   : (estimated)
  - Alpha version    : 2025-06-20
  - Beta version     : (No estimated date)
  - Release Candidate: (No estimated date)
  - Official Release : (No estimated date)

- ### TODO:
  - #### 🌟 New Features:
    - [ ] Include Input/Output folder size in Google Takeout Statistics. 
    - [ ] Speed up Counting files. 
    - [ ] Add argumenr `-gSkipPrep,--google-skip-preprocess` to Skipp Preproces steps during Google Takeout Processing feature. 
    - [ ] Replace `-gmtf,--google-move-takeout-folder` argument by `-gCopy,--google-copy-takeout-folder` argument and implement the logic for Google Takeout Processing. 
    - [ ] Call GPTH with `--verbose` when PhotoMigrator logLevel is VERBOSE or DEBUG. 
    - [ ] Auto-Update Issues Templates with new published releases. 
  - #### 📚 Documentation:
    - [ ] Move /doc/* into root folder?  
    - [ ] Analyze and report any issue detected during GPTH execution. 
    
---

## Release: v4.0.0 
- ### Release Date   : (estimated)
  - Alpha version    : (No estimated date)
  - Beta version     : (No estimated date)
  - Release Candidate: (No estimated date)
  - Official Release : (No estimated date)

- ### TODO:
  - #### 🌟 New Features:
    - [ ] Include Apple Support (initially just for downloading)
        - [ ] Create Class ClassApplePhotos with the same methods and behaviour as ClassSynologyPhotos or ClassImmichPhotos. (volunteers are welcomed)
    - [ ] Include native support for Google Photos through API  
      (See [this link](https://max-coding.medium.com/loading-photos-and-metadata-using-google-photos-api-with-python-7fb5bd8886ef))
        - [ ] Create Class ClassGooglePhotos with the same methods and behaviour as ClassSynologyPhotos or ClassImmichPhotos. (volunteers are welcomed)
    - [ ] Include Nextcloud Support (initially just for downloading)
        - [ ] Create Class ClassNextCloud with the same methods and behaviour as ClassSynologyPhotos or ClassImmichPhotos. (volunteers are welcomed)
    - [ ] Allow Google Photos and Apple Photos as TARGET in AUTOMATIC-MODE
    - [ ] Include Test Cases to check all features
    - [ ] Add Github Action to execute all Test Cases

