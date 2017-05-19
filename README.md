# 3dsconv
`3dsconv.py` is a Python 3 script that converts Nintendo 3DS CTR Cart Image files (CCI, ".cci", ".3ds") to the CTR Importable Archive format (CIA).

3dsconv can detect if a CCI is decrypted, encrypted using original NCCH (slot 0x2C), or encrypted using zerokey. Encryption requires [pyaes](https://github.com/ricmoo/pyaes) (`pip install pyaes`). Original NCCH encryption requires [a copy of the protected ARM9 bootROM](#encryption).

[Decrypt9WIP](https://github.com/d0k3/Decrypt9WIP) and [GodMode9](https://github.com/d0k3/GodMode9) can dump game cards to CIA directly now, rendering this tool partially obsolete. It can still be used for existing game dumps, however.

## Usage
### Basic use
On Windows, CCIs can be dragged on top of `3dsconv.exe`. See [Encryption](#encryption) for details about encrypted files.

### Advanced options
```bash
python3 3dsconv.py [options] game.3ds [game.3ds ...]
```

* `--output=<dir>` - Save converted files in specified directory; default is current directory or value of variable `output-directory`
* `--boot9=<file>` - Path to dump of protected ARM9 bootROM
* `--overwrite` - Overwrite existing converted files
* `--ignore-bad-hashes` - Ignore invalid hashes and CCI files and convert anyway
* `--verbose` - Print more information

## Encryption
3dsconv requires the Nintendo 3DS full or protected ARM9 bootROM to decrypt files using Original NCCH encryption (slot 0x2C). The file is checked for in the order of:

* Value of option `--boot9=` or variable `boot9_path`, if set
* `boot9.bin` (full) in current working directory
* `boot9_prot.bin` (protected) in current working directory
* `~/.3ds/boot9.bin` (full)
* `~/.3ds/boot9_prot.bin` (protected)

Instructions to dump the bootROM will be put here later.

## Pack into standalone executable for Windows
Using [py2exe for Python 3](https://pypi.python.org/pypi/py2exe/), you can pack the script into a Windows executable, primarily for use on a computer without Python, or for easy use in the Windows Command Prompt. [Python 3.4](https://www.python.org/downloads/release/python-344/) is required, 3.5 or later is currently not supported.

1. Clone or download the repository, or the latest release.
2. Open the Windows Command Prompt (`cmd.exe`) in the current directory.
3. Run `py -3.4 -m py2exe.build_exe 3dsconv.py -b 0`. See the [py2exe page](https://pypi.python.org/pypi/py2exe/) for more options.
4. `3dsconv.exe` will be in `dist` after it finishes. If anything but `0` was used for `-b`/`--bundle-files`, dependencies will also be saved.

## License / Credits
* `3dsconv.py` and [pyaes](https://github.com/ricmoo/pyaes) are under the MIT license.

For versions older than "2.0", see this [Gist](https://gist.github.com/ihaveamac/dfc01fa09483c275f72ad69cd7e8080f).
