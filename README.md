# 3dsconv
`3dsconv.py` is a Python script that "converts" a Nintendo 3DS rom (.3ds, .cci) to an installable CIA.

It supports using only an ExHeader XORpad, as well as decrypted roms.

It requires [3dstool](https://github.com/dnasdw/3dstool) and [makerom](https://github.com/profi200/Project_CTR) in the PATH.

This has not been tested with Python 3.x.

## Usage
```bash
3dsconv.py [options] game.3ds [game.cci ...]
```
* `--xorpads=<dir>` - use xorpads in the specified directory, default is current directory
* `--output=<dir>` - save converted CIA files in the specified directory, default is current directory
* `--force` - run even if 3dstool/makerom aren't found
* `--nocleanup` - don't remove temporary files once finished
* `--verbose` - print more information

## License / Credits
* `3dsconv.py` is under the MIT license.
* `ncchinfo_gen_exheader.py` is from [Decrypt9WIP](https://github.com/d0k3/Decrypt9WIP/blob/master/scripts/ncchinfo_gen.py), modified to generate an `ncchinfo.bin` file that only generates ExHeader XORpads.