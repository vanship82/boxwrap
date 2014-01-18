# BoxWrap

A command line sync tool to wrap your cloud storage securely and save space.

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

In a word, keep running the command above whenever you modify the working directory, or Dropbox modifies the wrap directory in its sync directory. There is a plan to run the command automatically and manage it with a GUI, but it is unavailable right now.

**NOTE:** The default encryption method is ZipCrypto, which is not very secure but compatibile with other unzip software. For sensitive data, using AES is recommanded, but the encrypted zip archive may not be decompressed by most unzip software. The initial setup command to use AES256 given the example above is

```bash
python boxwrap.py -m aes256 -p my-wrapbox $HOME/BoxWrap $HOME/Dropbox/BoxWrap
```

You can also remove `-p` so that BoxWrap only compresses the files without encryption.

## Cheatsheet


### Access your secure files on mobile devices and machines without BoxWrap

### Change your password

### Share your secure files with your friend

### Backup files securely onto multiple cloud storages


