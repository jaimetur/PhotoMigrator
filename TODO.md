## TODO:

- [ ] Complete function -ida to download Albums from immich
- [ ] Change -sda and -ida to support wildcards on Albums name to download
- [ ] Allow users to choose the folder where dowonload the assets for option -ida (-sda does not allow this)
- [ ] Allow user to choose between Synology Photos or Immich Photos in --all-in-one mode
- [ ] Add TQDM support on ImmichPhotos.py
- [ ] Ignore @eaDir folders on -suf, -sua, -iuf, -iua
- [ ] Complete function -suf to upload folders (without Albums) to Synology photos
  - [ ] Try to upload folders outside Synology Photos ROOT folder

## DONE:
- [x] Add support to include sidecar files when upload assts to Immich
- [x] Improve authentication speed in Immich
- [x] Get Supported media tipe from Immich using API
- [x] Translate into English all Immich fuctions
- [x] Add release-notes.md file to the distribution package.
