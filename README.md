# BoxWrap

A command line sync tool to wrap your cloud storage securely and save space using zip archives.

## What is BoxWrap for?

BoxWrap secures and compresses your cloud storage while maintaining the highest compatibility and productivity:

* **Save space:** compress each file into separate zip archive on the cloud ending with `.boxwrap.zip`
* **Protect privacy:** encrypt each zip archive on the cloud in ZipCrypto or AES
* **Maintain compatibility**: unzip individual zip archive with other software even though you don't have BoxWrap
* **Keep productivity**: work on the original files on your machine and BoxWrap put them on the cloud securely
* **Share**: back up your files on multiple cloud storages
* and more ...
 
## How does BoxWrap work?

BoxWrap uses [7-zip](http://www.7-zip.org/) to compress and encrypt zip archives. It must work with client sync software provided by your cloud storage providers.

BoxWrap maps and syncs your working directory which contains original files to a wrap directory which sits inside your cloud storage sync directory. The files in the wrap directory are compressed and encrypted into individual zip archives. Then the client sync software syncs the secure archives onto the cloud.

## Why is BoxWrap secure?

BoxWrap does not have any network communication. It only stores your encryption password hash locally for password verification. No one other than you know how to decrypt your archives without the password.

## Which cloud storage providers are supported?

BoxWrap supports any cloud storage providers that have client sync software, including Dropbox, Google Drive, SugerSync, Box, etc.

## Basic usage

Suppose that you has installed Dropbox and set up the sync directory at `$HOME/Dropbox`.

You create two directories `$HOME/BoxWrap` as the working directory, `$HOME/Dropbox/BoxWrap` as the wrap directory sitting inside Dropbox sync directory. The directory structures is then like

```
$HOME
  |--BoxWrap
  |--Dropbox
       |--BoxWrap
```

To use BoxWrap, first clone it

```bash
git clone https://github.com/vanship82/boxwrap
```

To perform a sync for the first time, you need to run the following command one time

```bash
python boxwrap.py -p my-wrapbox $HOME/BoxWrap $HOME/Dropbox/BoxWrap
```

in which `my-wrapbox` is profile name for future quick access, `$HOME/BoxWrap` is your working directory, `$HOME/Dropbox/BoxWrap` is the wrap directory to be synced to, and `-p` means that you want to encrypt the wrap directory with a password.

After the initial command finishes, it will create a profile directory `my-wrapbox` under `$HOME/.boxwrap/` for quick access and keeping the current directories information. Since both directories are empty, the sync performs nothing.

Then you can modify your working directory, for example

```bash
echo "Hello World!" > $HOME/BoxWrap/hello.txt
```

To sync the changes to the wrap directory, you run BoxWrap again with the profile `my-wrapbox`, i.e.,

```bash
python boxwrap.py my-wrapbox
```

After typing the correct password, BoxWrap will sync file `hello.txt` in the working directory to `hello.txt.boxwrap.zip` in the wrap directory.

In a word, keep running the command above whenever you modify the working directory, or Dropbox modifies the wrap directory in its sync directory. There is a plan to run the command automatically and manage it with a GUI, but it is unavailable right now. For complete usage, please run

```bash
python boxwrap.py -h
```

**NOTE:** The default encryption method is ZipCrypto, which is not very secure but compatibile with other unzip software. For sensitive data, using AES is recommanded, but the encrypted zip archive may not be decompressed by most unzip software. The initial setup command to use AES256 given the example above is

```bash
python boxwrap.py -m aes256 -p my-wrapbox $HOME/BoxWrap $HOME/Dropbox/BoxWrap
```

You can also remove `-p` so that BoxWrap only compresses the files without encryption.

## Cheatsheet

### Access your secure files on mobile devices and machines without BoxWrap

Currently, BoxWrap is only a python script and not ported to mobile devices. However, it does not mean that you cannot access your files secured and compressed by BoxWrap on mobile device and machines without BoxWrap. In fact, BoxWrap thrives in compatibility, that is, you can access the files everywhere.

On mobile device, for example, suppose you have Dropbox app installed. You open the wrap directory in Dropbox app, and you can find all you files with `.boxwrap.zip` subfix. Download any of them, open it with any unzip software to decompress the original content.

**NOTE:** Most unzip software can only deal with ZipCrypto. If you choose to use AES in BoxWrap to encrypt your files, they may not be opened unless you have an app that supports AES encryption from 7-zip.

### Change your password

All zip archives in a wrap directory use the same encryption password. To change the password, or change encryption method, you need to resync everything. Currently, this is doable but only for advanced users.

First, you make sure that all the files are correctly synced. Also you need to make sure that the client sync software for the cloud storage won't update any file before password change is done. Otherwise, the result may be unexpected.

Second, delete all contents in the wrap directory, because the current zip archives are using the old password.

Third, delete the profile directory of the profile name, located in `$HOME/.boxwrap` by default.

Finally, rerun the initial setup command to reinitialize the profile with a different password or encryption method.

### Share your secure files with other trusted people

Sharing is an important feature for cloud storage. BoxWrap also supports that. To share the secure wrap directory with somebody, you just share the wrap directory in your cloud storage, and tell him/her the password to decrypt the files. 

Then he/she can
* Simply decompress the individual file with any supported unzip software and the password, or
* Download BoxWrap and set up a working directory synced from the shared wrap directory with the password.

**NOTE:** You need to tell them your password. It is recommend that you map the portion of working directory to be shared into another wrap directory with a different password. In this way, you won't need to tell them your precious password that applies to every file.

### Backup files securely onto multiple cloud storages

Another advantage of BoxWrap is that it can map the same working directory to multiple wrap directories. So it allows you to backup files securely onto multiple cloud storages.

In the scenario of basic usage with Dropbox, you also want to sync your working directory securely to Google Drive. Assume that Google Drive client software has set up sync directory in `$HOME/Google Drive`. Then just create another profile to map the same working directory in `$HOME/BoxWrap` to Google Drive as follows:

```bash
python boxwrap.py -p my-wrapbox-google $HOME/BoxWrap "$HOME/Google Drive/BoxWrap"
```

Then you sync your working directory to both Dropbox and Google Drive, with compression and encryption. Moreover, you can supply a different password for Google Drive to keep the backup more secure.


