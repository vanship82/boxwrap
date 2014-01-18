# BoxWrap

Wrap your cloud storage securely and save space.

## What is BoxWrap for?

BoxWrap secures and compresses your cloud storage while maintaining the highest compatibility and productivity:

* Save space: compress each file into separate zip archive on the cloud ending with `.boxwrap.zip`
* Protect privacy: encrypt each zip archive on the cloud in ZipCrypto or AES
* Maintain compatibility: unzip individual zip archive with other software even though you don't have BoxWrap
* Keep productivity: work on the original files on your machine and BoxWrap put them on the cloud securely
* Share: back up your files on multiple cloud storages
* and more ...
 
## How does BoxWrap work?

BoxWrap uses [7-zip](http://www.7-zip.org/) to compress and encrypt zip archives. It must work with client sync software provided by your cloud storage providers.

BoxWrap maps and syncs your working directory which contains original files to a wrap directory which sits inside your cloud storage sync directory. The files in the wrap directory are compressed and encrypted into individual zip archives. Then the client sync software syncs the secure archives onto the cloud.

## Why is BoxWrap secure?

BoxWrap does not have any network communication. It only stores your encryption password hash locally for password verification. No one other than you know how to decrypt your archives without the password.

## Which cloud storage providers are supported?

BoxWrap supports any cloud storage providers that have client sync software, including Dropbox, Google Drive, SugerSync, Box, etc.

