## 📅 ROADMAP
[Planned Roadmap](https://github.com/jaimetur/PhotoMigrator/blob/main/ROADMAP.md) for the following releases
[Changelog](https://github.com/jaimetur/PhotoMigrator/blob/main/CHANGELOG.md) for the past releases

---

## Release: v3.4.0  
- ### Release Date: 2025-06-30
  - Alpha version    : 2025-06-18
  - Beta version     : 2025-06-23
  - Release Candidate: 2025-06-27
  - Official Release : 2025-06-30

- ### Main Changes:
  - #### 🚨 Breaking Changes:
    - [ ] Replaced argument `-gmtf, --google-move-takeout-folder` by `-gKeepTake, --google-keep-takeout-folder` argument and inverted the logic for Google Takeout Processing.
    - [ ] Replaced argument `-gnsa, --google-create-symbolic-albums` by `-gcsa, --google-no-symbolic-albums` argument and inverted the logic for Google Takeout Processing.
    
  - #### 🌟 New Features:
    - [x] Created GitHub Forms on New Issues.
      - [ ] Auto-Update Issues Templates with new published releases.
    - [x] Allow user to define folder name for 'Logs'.
    - [x] Allow user to define folder name for 'Duplicates'.
    - [x] Allow user to define folder name for 'Exiftool Outputs'.
    - [x] Allow user to define folder name for 'Albums'.
    - [x] Allow user to define folder name for 'All Photos'.
    - [x] Allow user to define configuration file (path and name).

  - #### 🚀 Enhancements:
    - [ ] Investigate Performance on Automatic Migration when target=`synology`. 
        
  - #### 🐛 Bug fixes:

  - #### 📚 Documentation:
    - [ ] Updated documentation with all changes.
    
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

