# 3dsconv
`3dsconv.py` is a Python 3 script that converts Nintendo 3DS CTR Cart Image files (CCI, ".cci", ".3ds") to the CTR Importable Archive format (CIA).

3dsconv can detect if a CCI is decrypted, encrypted using original NCCH (slot 0x2C), or encrypted using zerokey. Encryption requires [pyaes](https://github.com/ricmoo/pyaes) (`pip install pyaes`). Original NCCH encryption requires [a copy of the protected ARM9 bootROM](#encryption).

[Decrypt9WIP](https://github.com/d0k3/Decrypt9WIP) and [GodMode9](https://github.com/d0k3/GodMode9) can dump game cards to CIA directly now, rendering this tool partially obsolete. It can still be used for existing game dumps, however.

## Usage
### Basic use
On Windows, CCIs can be dragged on top of `3dsconv.exe`. See [Encryption](#encryption) for details about encrypted files.

### Advanced options
3dsconv can be used as a standalone script, or installed using `python3 setup.py install`.

```bash
python3 3dsconv.py [options] game.3ds [game.3ds ...]
```

* `--output=<dir>` - Save converted files in specified directory; default is current directory or value of variable `output-directory`
* `--boot9=<file>` - Path to dump of protected ARM9 bootROM
* `--overwrite` - Overwrite existing converted files
* `--ignore-bad-hashes` - Ignore invalid hashes and CCI files and convert anyway
* `--ignore-encryption` - Ignore the encryption header value, assume the ROM as unencrypted
* `--verbose` - Print more information
* `--dev-keys` - Use developer-unit keys

## Encryption
3dsconv requires the Nintendo 3DS full or protected ARM9 bootROM to decrypt files using Original NCCH encryption (slot 0x2C). The file is checked for in the order of:

* Value of option `--boot9=` or variable `boot9_path`, if set
* `boot9.bin` (full) in current working directory
* `boot9_prot.bin` (protected) in current working directory
* `~/.3ds/boot9.bin` (full)
* `~/.3ds/boot9_prot.bin` (protected)

boot9strap is required to dump. Setup can be found at [3DS Guide](https://3ds.guide/). Hold START+SELECT+X at boot to dump to `sdmc:/boot9strap/boot9.bin`.

boot9 SHA256: `2f88744feed717856386400a44bba4b9ca62e76a32c715d4f309c399bf28166f`  
boot9_prot SHA256: `7331f7edece3dd33f2ab4bd0b3a5d607229fd19212c10b734cedcaf78c1a7b98`

## Developer titles (not fully tested)
Conversion for developer-unit systems is possible with `--dev-keys`. This is required for titles encrypted using dev-unit keys (only seems to be used for SystemUpdater). Titles encrypted with retail keys can't be converted this way without external decryption.

This does not decrypt or change the encryption of the output file, therefore CIAs will still only work on dev-units without separate decryption or changing encryption.

The dev certchain must be provided. The file is searched for is `certchain-dev.bin` in current working directory, or `~/.3ds/certchain-dev.bin`.

To extract from a dev CIA, use `ctrtool --certs=certchain-dev.bin title.cia`.

SHA256: `7921ae82c9dcf411351314f2fe2c67378c6a872d2524f71b3c002b4d4a56846f`

## Pack into standalone executable for Windows
Using [py2exe for Python 3](https://pypi.python.org/pypi/py2exe/), you can pack the script into a Windows executable, primarily for use on a computer without Python, or for easy use in the Windows Command Prompt. [Python 3.4](https://www.python.org/downloads/release/python-344/) is required, 3.5 or later is currently not supported.

1. Clone or download the repository, or the latest release.
2. Open the Windows Command Prompt (`cmd.exe`) in the current directory.
3. Run `py -3.4 -m py2exe.build_exe 3dsconv.py -b 0`. See the [py2exe page](https://pypi.python.org/pypi/py2exe/) for more options.
4. `3dsconv.exe` will be in `dist` after it finishes. If anything but `0` was used for `-b`/`--bundle-files`, dependencies will also be saved.

## License / Credits
* `3dsconv.py` and [pyaes](https://github.com/ricmoo/pyaes) are under the MIT license.

For versions older than "2.0", see this [Gist](https://gist.github.com/ihaveamac/dfc01fa09483c275f72ad69cd7e8080f).
