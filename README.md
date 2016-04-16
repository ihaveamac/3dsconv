# 3dsconv
`3dsconv.py` is a Python script that "converts" a Nintendo 3DS rom (.3ds, .cci) to an installable CIA.

It supports using only an ExHeader XORpad, as well as decrypted roms. The ExHeader XORpad name format is `<TITLEID>.Main.exheader.xorpad`.

It requires [3dstool](https://github.com/dnasdw/3dstool) and [make_cia](https://github.com/ihaveamac/ctr_toolkit) in the PATH.

This does not work with Python 3.x.

## Generating XORpads
If your rom is encrypted, you must generate ExHeader XORpads with a 3DS system and the ability to use Decrypt9. Use `--gen-ncchinfo` with the roms you want to generate them for. Place `ncchinfo.bin` at the root or `/Decrypt9` on your 3DS SD card, run Decrypt9, and go to "XORpad Generator Options" and "NCCH Padgen". XORpads can then be placed anywhere (use `--xorpads=<dir>` if it's not the current working directory)

## Usage
```bash
python2 3dsconv.py [options] game.3ds [game.3ds ...]
```
* `--xorpads=<dir>` - use xorpads in the specified directory, default is current directory or what is set as `xorpad-directory`
* `--output=<dir>` - save converted CIA files in the specified directory, default is current directory or what is set as `output-directory`
* `--overwrite` - overwrite any existing converted CIA, if it exists
* `--gen-ncchinfo` - generate ncchinfo.bin for roms that don't have a valid xorpad
* `--gen-ncch-all` - use with `--gen-ncchinfo` to generate an ncchinfo.bin for all roms
* `--noconvert` - don't convert roms, useful if you just want to generate ncchinfo.bin
* `--force` - run even if 3dstool/makerom aren't found
* `--nocleanup` - don't remove temporary files once finished
* `--verbose` - print more information

## License / Credits
* `3dsconv.py` is under the MIT license.
* `ncchinfo_gen_exheader.py` is from [Decrypt9WIP](https://github.com/d0k3/Decrypt9WIP/blob/master/scripts/ncchinfo_gen.py), modified to generate an `ncchinfo.bin` file that only generates ExHeader XORpads.

For versions older than "2.0", see this [Gist](https://gist.github.com/ihaveamac/dfc01fa09483c275f72ad69cd7e8080f).