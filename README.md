# 3dsconv
`3dsconv.py` is a Python script that "converts" a Nintendo 3DS rom (.3ds, .cci) to an installable CIA.

It supports using only an ExHeader XORpad, as well as decrypted roms.

It requires [3dstool](https://github.com/dnasdw/3dstool) and [makerom](https://github.com/profi200/Project_CTR) in the PATH.

This does not work with Python 3.x.

## Generating XORpads
If your rom is encrypted, you must generate ExHeader XORpads with a 3DS system and the ability to use Decrypt9. Use `ncchinfo_gen_exheader.py.`
```bash
python2 ncchinfo_gen_exheader.py game.3ds [game.cci ...]
```
Place `ncchinfo.bin` at the root or `/Decrypt9` on your 3DS SD card, run Decrypt9, and go to "XORpad Generator Options" and "NCCH Padgen". XORpads can then be placed anywhere (use `--xorpads=<dir>` if it's not the current working directory)

## Usage
```bash
python2 3dsconv.py [options] game.3ds [game.cci ...]
```
* `--xorpads=<dir>` - use xorpads in the specified directory, default is current directory or what is set as `xorpad-directory`
* `--output=<dir>` - save converted CIA files in the specified directory, default is current directory or what is set as `output-directory`
* `--force` - run even if 3dstool/makerom aren't found
* `--nocleanup` - don't remove temporary files once finished
* `--verbose` - print more information

## License / Credits
* `3dsconv.py` is under the MIT license.
* `ncchinfo_gen_exheader.py` is from [Decrypt9WIP](https://github.com/d0k3/Decrypt9WIP/blob/master/scripts/ncchinfo_gen.py), modified to generate an `ncchinfo.bin` file that only generates ExHeader XORpads.

For versions older than "2.0", see this [Gist](https://gist.github.com/ihaveamac/dfc01fa09483c275f72ad69cd7e8080f).