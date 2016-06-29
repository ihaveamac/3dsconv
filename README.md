# 3dsconv
`3dsconv.py` is a Python 2.7 script that converts Nintendo 3DS CTR Cart Image files (CCI, ".3ds") to the CTR Importable Archive format (CIA).

3dsconv can detect if a CCI is decrypted or encrypted. Decrypted is preferred and does not require any extra files. Encrypted requires Extended Header (ExHeader) XORpads, with the filename `<TITLEID>.Main.exheader.xorpad`.

[makerom](https://github.com/profi200/Project_CTR) is required in the PATH, or in the same folder on Windows systems.

This does not work with Python 3.

The recommended tool for dumping game cards is [Decrypt9WIP](https://github.com/d0k3/Decrypt9WIP). The recommended option is "Dump & Decrypt Cart (trim)", which dumps a decrypted and trimmed image which can be quickly converted.

## Usage
### Basic use
On Windows, decrypted ROMs can be dragged on top of `3dsconv.exe`. Encrypted ROMs should be decrypted, or have the proper ExHeader XORpads in the same folder.

### Advanced options
```bash
python2 3dsconv.py [options] game.3ds [game.3ds ...]
```
* `--xorpads=<dir>` - use XORpads in the specified directory  
  default is current directory or what is set as `xorpad-directory`
* `--output=<dir>` - save converted CIA files in the specified directory  
  default is current directory or what is set as `output-directory`
* `--overwrite` - overwrite any existing converted CIA, if it exists
* `--gen-ncchinfo` - generate `ncchinfo.bin` for ROMs that don't have a valid xorpad
* `--gen-ncch-all` - use with `--gen-ncchinfo` to generate an `ncchinfo.bin` for all ROMs
* `--noconvert` - don't convert ROMs, useful if you just want to generate `ncchinfo.bin`
* `--force` - run even if makerom isn't found
* `--nocleanup` - don't remove temporary files once finished
* `--verbose` - print more information

## Generating XORpads
If your ROM is encrypted, you must generate ExHeader XORpads with a 3DS system and the ability to use [Decrypt9](https://github.com/d0k3/Decrypt9WIP).

1. Use `--gen-ncchinfo` with the ROMs you want to generate them for.  
   By default, only ROMs without valid XORpads will be added into `ncchinfo.bin`. To add all given ROMs, add `--gen-ncch-all`.
2. Place `ncchinfo.bin` at the root or `/Decrypt9` on your 3DS SD card.
3. Run Decrypt9, and go to "XORpad Generator Options" and "NCCH Padgen".

XORpads can then be placed anywhere (use `--xorpads=<dir>` if it's not the current working directory)

## Converting .py to standalone .exe (Windows)
Using [py2exe](http://www.py2exe.org/), you can pack the script into a Windows executable, for use on a computer without Python, or for easy use in the Windows command prompt.

1. Clone or download the repository, or the latest release + `setup.py` from the repository.
2. Open the Windows command prompt (`cmd.exe`) in the current directory.
3. Edit `setup.py` to change any options, if wanted.
4. Run `python setup.py py2exe`. Make sure Python 2.7 is being used.
5. `3dsconv.exe` and its dependencies will be in `dist` after it finishes.

## License / Credits
* `3dsconv.py` is under the MIT license.
* `ncchinfo.bin` generation is based on [Decrypt9WIP's `ncchinfo_gen.py`](https://github.com/d0k3/Decrypt9WIP/blob/master/scripts/ncchinfo_gen.py).

For versions older than "2.0", see this [Gist](https://gist.github.com/ihaveamac/dfc01fa09483c275f72ad69cd7e8080f).
