# 3dsconv-Enchanted
This another version of `3dsconv` uses [pycryptodome](https://github.com/Legrandin/pycryptodome) It's a library written in the C lang ،I tested in some .3ds files, and I see it's faster than [pyaes](https://github.com/ricmoo/pyaes) in convert and processing so this better version of 3dsconv build with [pycryptodome](https://github.com/Legrandin/pycryptodome) and i added a some fixes for processing the file

`3dsconv-enchanted.py` is a Python 3 script that converts Nintendo 3DS CTR Cart Image files (CCI, ".cci", ".3ds") to the CTR Importable Archive format (CIA).

3dsconv-enchantexd can detect if a CCI is decrypted, encrypted using original NCCH (slot 0x2C), or encrypted using zerokey. Encryption requires [pycryptodome](https://github.com/Legrandin/pycryptodome) (`pip install pycryptodome`). Original NCCH encryption requires [a copy of the protected ARM9 bootROM](#encryption).

[Decrypt9WIP](https://github.com/d0k3/Decrypt9WIP) and [GodMode9](https://github.com/d0k3/GodMode9) can dump game cards to CIA directly now, rendering this tool partially obsolete. It can still be used for existing game dumps, however.

## Usage
### Basic use
Install python ( any version up to 3.X )
### Advanced options
3dsconv-enchanted can be used as a standalone script only

```bash
python 3dsconv-enchanted.py [options] game.3ds [game.3ds ...]
```
you can type just `python 3dsconv-enchanted.py` and see new menu with file selector to auto select the .3ds file no need to type the name of .3ds file

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

BOOT9STRAP IS REQUIRED TO DUMP. Setup can be found at [3DS Guide](https://3ds.guide/). Hold START+SELECT+X at boot to dump to `sdmc:/boot9strap/boot9.bin`.

boot9 SHA256: `2f88744feed717856386400a44bba4b9ca62e76a32c715d4f309c399bf28166f`  
boot9_prot SHA256: `7331f7edece3dd33f2ab4bd0b3a5d607229fd19212c10b734cedcaf78c1a7b98`
boot9.bin SHA256:
`2f88744feed717856386400a44bba4b9ca62e76a32c715d4f309c399bf28166f`

## Developer titles (not fully tested)
Conversion for developer-unit systems is possible with `--dev-keys`. This is required for titles encrypted using dev-unit keys (only seems to be used for SystemUpdater). Titles encrypted with retail keys can't be converted this way without external decryption.
And it often doesn't work for all .3ds

This does not decrypt or change the encryption of the output file, therefore CIAs will still only work on dev-units without separate decryption or changing encryption.

The dev certchain must be provided. The file is searched for is `certchain-dev.bin` in current working directory, or `~/.3ds/certchain-dev.bin`.

To extract from a dev CIA, use `ctrtool --certs=certchain-dev.bin title.cia`.

SHA256: `7921ae82c9dcf411351314f2fe2c67378c6a872d2524f71b3c002b4d4a56846f`

## Pack into standalone executable for Windows
I can't..

## License / Credits
* `3dsconv.py` and [pycryptodome](https://github.com/Legrandin/pycryptodome) are under the MIT license.
