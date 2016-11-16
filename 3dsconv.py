#!/usr/bin/env python2

# 3dsconv.py by ihaveamac
# license: MIT License
# https://github.com/ihaveamac/3dsconv

from __future__ import division
import binascii
import glob
import hashlib
import itertools
import math
import os
import struct
import sys
import zlib


def get_file_crc32(path):
  chunksize = 1024 * 1024
  buf = open(path, 'rb')
  chunk = buf.read(chunksize)
  crc = 0
  while chunk:
    crc = zlib.crc32(chunk, crc)
    chunk = buf.read(chunksize)
  crc = crc & 0xffffffff
  return "%08x" % crc

# check for PyCrypto, which is used for zerokey support
pycrypto_found = False
try:
    from Crypto.Cipher import AES
    from Crypto.Util import Counter
    pycrypto_found = True
except ImportError:
    pass  # this is handled later

# default directories (relative to current dir unless you use absolute paths)
# leave as "" for current working directory
# using --xorpads= or --output= will override these
xorpad_directory = ""
output_directory = ""

#################
version = "3.2"

# -- 80-characters wide ------------------------------------------------------ #
helptext = """3dsconv.py ~ version {}
convert a Nintendo 3DS CCI (.3ds/.cci) to a CIA
https://github.com/ihaveamac/3dsconv

usage: 3dsconv.py [options] game.3ds [game.3ds ...]
  --xorpads=<dir>  - use XORpads in the specified directory
                     default is {}
  --output=<dir>   - save converted CIA files in the specified directory
                     default is {}
  --overwrite      - overwrite any existing converted CIA, if it exists
  --gen-ncchinfo   - generate ncchinfo.bin for CCIs without a valid xorpad
  --gen-ncch-all   - generate ncchinfo.bin for all CCIs
                     used with --gen-ncchinfo
  --noconvert      - don't convert CCIs, useful to generate just ncchinfo.bin
  --ignorebadhash  - ignore bad xorpad/corrupt rom and convert anyway
  --verbose        - print more information

- encrypted roms require an ExHeader XORpad with the name format:
    \"<TITLEID>.Main.exheader.xorpad\"
  XORpads should be in {} or the directory specified by --xorpads=<dir>
  XORpads are generated by using ncchinfo.bin with Decrypt9 on a 3DS system
- zerokey encryption is supported with PyCrypto
- encrypted and decrypted roms can be converted at the same time""".format(
    version,
    "current directory" if xorpad_directory == "" else "'{}'".format(xorpad_directory),
    "current directory" if output_directory == "" else "'{}'".format(output_directory),
    "the current directory" if xorpad_directory == "" else "'{}'".format(xorpad_directory)
)

# includes certificate chain, ticket (blank titlekey and title id), and tmd signature + blank header (blank title id)
#    + blank content info records
# compressed using zlib then encoded with base64
# I should find a better way to store this... this is so ugly
ciainfo = """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"""

if len(sys.argv) < 2:
    sys.exit(helptext)

mu = 0x200  # media unit
readsize = 8 * 1024 * 1024  # used from padxorer
zerokey = "\0" * 16

verbose = "--verbose" in sys.argv
overwrite = "--overwrite" in sys.argv
genncchinfo = "--gen-ncchinfo" in sys.argv
genncchall = "--gen-ncch-all" in sys.argv
noconvert = "--noconvert" in sys.argv
ignorebadhash = "--ignorebadhash" in sys.argv


def print_v(msg):
    if verbose:
        print(msg)

if pycrypto_found:
    print_v("- PyCrypto found, zerokey will be supported")
else:
    print_v("- PyCrypto not found, zerokey will not be supported")

ncchinfolist = []
ncchinfo_used_roms = []


# see this for ncchinfo.bin format:
# https://github.com/d0k3/Decrypt9WIP/blob/master/scripts/ncchinfo_gen.py
# this only does ExHeader stuff
# so I think I can get away with hard-coding some things
def ncchinfoadd(rom_ncchinfo):
    if rom_ncchinfo not in ncchinfolist:
        print_v("- adding {} to ncchinfo.bin".format(rom_ncchinfo))
        with open(rom_ncchinfo, "rb") as romf_ncchinfo:
            romf_ncchinfo.seek(0x108)
            tid_ncchinfo = romf_ncchinfo.read(8)
            romf_ncchinfo.seek(0x120)
            romf_ncchinfo.seek(struct.unpack("<I", romf_ncchinfo.read(4))[0] * mu)  # first partition offset
            keyy_ncchinfo = romf_ncchinfo.read(16)
            ncchinfolist.append(
                tid_ncchinfo[::-1] + "\x01" + ("\0" * 14) + keyy_ncchinfo + "\x01" + ("\0" * 15) +
                tid_ncchinfo + (
                    "/{}.Main.exheader.xorpad".format(binascii.hexlify(tid_ncchinfo[::-1]).upper())
                ).ljust(112, "\0")
            )
        ncchinfo_used_roms.append(rom_ncchinfo)


def showprogress(val, maxval):
    # crappy workaround I bet, but print() didn't do what I wanted
    minval = min(val, maxval)
    sys.stdout.write("\r  {:>5.1f}% {:>10} / {}".format((minval / maxval) * 100, minval, maxval))
    sys.stdout.flush()

totalroms = 0
processedroms = 0

# probably should've used argparse
files = []
for arg in sys.argv[1:]:
    if arg[:2] != "--":
        toadd = glob.glob(arg)
        if len(toadd) == 0:
            print("! {} doesn't exist.".format(arg))
            totalroms += 1
        else:
            for inputf in toadd:
                romname = os.path.basename(os.path.splitext(inputf)[0])
                cianame = os.path.join(output_directory, romname + ".cia")
                if not overwrite and os.path.isfile(cianame):
                    print("! {} already exists.".format(cianame))
                    print("  to force conversion and overwriting this, use --overwrite")
                    continue
                files.append([inputf, romname, cianame])
    elif arg[:10] == "--xorpads=":
        xorpad_directory = arg[10:]
    elif arg[:9] == "--output=":
        output_directory = arg[9:]

if output_directory != "":
    try:
        os.makedirs(output_directory)
    except OSError:
        if not os.path.isdir(output_directory):
            raise

if not files:
    sys.exit("! no inputted files exist.")

for rom in files:
    if genncchinfo and genncchall:
        ncchinfoadd(rom[0])
    totalroms += 1
    crc32 = get_file_crc32(rom[0])

    with open(rom[0], "rb") as romf:
        romf.seek(0x100)
        ncsdmagic = romf.read(4)
        if ncsdmagic != "NCSD":
            print("! {} is probably not a Nintendo 3DS CCI.".format(rom[0]))
            print_v("  NCSD magic not found (offset 0x100)")
            continue
        romf.seek(0x108)
        tid_bin = romf.read(8)[::-1]
        tid = binascii.hexlify(tid_bin)

        # find xorpad file
        xorpad = False
        xorpad_default = '%s.Main.exheader.xorpad' % tid.upper()
        xorpad_with_crc32 = '%s.%s.Main.exheader.xorpad' % (tid.upper(), crc32)

        for root, dirnames, filenames in os.walk(xorpad_directory):
          for filename in filenames:
            if filename.lower() == xorpad_with_crc32.lower():
              # exact match with crc32.
              xorpad = os.path.join(root, filename)
              break
            if filename.lower() == xorpad_default.lower():
              # title match, but could potentially still see an exact crc32 match.
              xorpad = os.path.join(root, filename)

        if xorpad:
          print("- found xorpad file %s" % os.path.basename(xorpad))


        # find Game Executable CXI
        romf.seek(0x120)
        gamecxi_offset = struct.unpack("<I", romf.read(4))[0] * mu
        gamecxi_size = struct.unpack("<I", romf.read(4))[0] * mu
        # find Manual CFA
        romf.seek(0x128)
        manualcfa_offset = struct.unpack("<I", romf.read(4))[0] * mu
        manualcfa_size = struct.unpack("<I", romf.read(4))[0] * mu
        # find Download Play child container CFA
        romf.seek(0x130)
        dlpchildcfa_offset = struct.unpack("<I", romf.read(4))[0] * mu
        dlpchildcfa_size = struct.unpack("<I", romf.read(4))[0] * mu

        romf.seek(gamecxi_offset + 0x18F)

        # Check NCCH flag 7 for FixedCryptoKey (0x1) and NoCrypto (0x4)
        bitmask = int(binascii.hexlify(romf.read(1)))
        decrypted = bitmask & 0x4
        zerokey_enc = bitmask & 0x1

        print("- processing: {} ({})".format(
            rom[1], "decrypted" if decrypted else ("zerokey" if zerokey_enc else "encrypted")
        ))
        if noconvert:
            print("- not converting {} ({}) because --noconvert was used".format(
                rom[1], "decrypted" if decrypted else "encrypted"
            ))
            if genncchinfo:
                ncchinfoadd(rom[0])
            continue
        if not decrypted and not zerokey_enc:
            if not xorpad:
                print("! no xorpad file found. looking for %s or %s" % (xorpad_default, xorpad_with_crc32))
                if not genncchinfo:
                    print("  use --gen-ncchinfo with this CCI.")
                else:
                    ncchinfoadd(rom[0])
                continue
        elif zerokey_enc and not pycrypto_found:
            print("! PyCrypto is required to convert zerokey-encrypted roms.")
            continue

        # Game Executable first-half ExHeader
        print_v("- verifying ExHeader")
        romf.seek(0x4200)
        exh = romf.read(0x400)
        xor = ""
        if not decrypted:
            if zerokey_enc:
                print_v("- decrypting ExHeader, using zerokey")
                ctr = Counter.new(128, initial_value=long(tid + "0100000000000000", 16))
                ctrmode = AES.new(zerokey, AES.MODE_CTR, counter=ctr)
                exh = ctrmode.decrypt(exh)
            else:
                print_v("- decrypting ExHeader, using XORpad")
                with open(xorpad, "rb") as xorfile:
                    xor = xorfile.read(0x400)
                xored = ""
                for byte_f, byte_x in zip(exh, xor):
                    xored += chr(ord(byte_f) ^ ord(byte_x))
                exh = xored
        exh_hash = hashlib.sha256(exh).digest()
        romf.seek(0x4160)
        ncch_exh_hash = romf.read(0x20)
        if exh_hash != ncch_exh_hash:
            if decrypted:
                print("! this CCI might be corrupt.")
            else:
                print("! {} is not the correct XORpad, or is corrupt.".format(xorpad))
                if not genncchinfo:
                    print("  try using --gen-ncchinfo again or find the correct XORpad.")
                else:
                    ncchinfoadd(rom[0])
            print_v("  ExHeader SHA-256 hash check failed.")
            if ignorebadhash:
                print("  converting anyway because --ignorebadhash was used")
            else:
                continue

        # probably should calculate these but I'm lazy this is easier
        tmdpadding = "\0" * 12  # padding to add at the end of the tmd
        contentcount = "\x01"  # for convenience later since this has to be written a few times
        tmdsize = "\x34\x0B\0\0\0\0\0\0"  # for convenience when writing the CIA header
        contentindex = "\x80"  # some weird thing in the CIA header
        if manualcfa_offset != 0:
            tmdpadding = "\0" * 28
            contentcount = "\x02"
            tmdsize = "\x64\x0B\0\0\0\0\0\0"
            contentindex = "\xC0"
        if dlpchildcfa_offset != 0:
            tmdpadding = "\0" * 44
            contentcount = "\x03"
            tmdsize = "\x94\x0B\0\0\0\0\0\0"
            contentindex = "\xE0"

        print_v("- patching ExHeader")
        print_v("  offset 0xD of ExHeader:")
        exh_list = list(exh)
        x = ord(exh_list[0xD])
        print_v("  original: {}".format(hex(x)))
        x |= 2
        print_v("  shifted:  {}".format(hex(x)))
        exh_list[0xD:0xE] = chr(x)
        exh = "".join(exh_list)
        savesize = exh[0x1C0:0x1C4]
        new_exh_hash = hashlib.sha256("".join(exh)).digest()

        if not decrypted:
            if zerokey_enc:
                print_v("- re-encrypting ExHeader, using zerokey")
                ctr = Counter.new(128, initial_value=long(tid + "0100000000000000", 16))
                ctrmode = AES.new(zerokey, AES.MODE_CTR, counter=ctr)
                exh = ctrmode.encrypt(exh)
                pass
            else:
                print_v("- re-encrypting ExHeader, using XORpad")
                xored = ""
                for byte_f, byte_x in zip(exh_list, xor):
                    xored += chr(ord(byte_f) ^ ord(byte_x))
                exh = xored

        # Game Executable NCCH Header
        print_v("- reading NCCH header of Game Executable CXI")
        romf.seek(gamecxi_offset)
        ncch_header = list(romf.read(0x200))
        ncch_header[0x160:0x180] = list(new_exh_hash)
        ncch_header = "".join(ncch_header)

        # CIA
        with open(rom[2], "wb") as cia:
            print_v("- writing CIA header")
            chunkrecords = "\0" * 0xC  # 1st content: ID 0x00000000, Index 0x0000
            chunkrecords += struct.pack(">I", gamecxi_size)
            chunkrecords += "\0" * 0x20  # sha256 hash to be filled in later
            if manualcfa_offset != 0:
                chunkrecords += binascii.unhexlify("000000010001000000000000")  # 2nd content: ID 0x1, Index 0x1
                chunkrecords += struct.pack(">I", manualcfa_size)
                chunkrecords += "\0" * 0x20  # sha256 hash to be filled in later
            if dlpchildcfa_offset != 0:
                chunkrecords += binascii.unhexlify("000000020002000000000000")  # 3nd content: ID 0x2, Index 0x2
                chunkrecords += struct.pack(">I", dlpchildcfa_size)
                chunkrecords += "\0" * 0x20  # sha256 hash to be filled in later

            cia.write(
                binascii.unhexlify("2020000000000000000A000050030000") + tmdsize +
                struct.pack("<I", gamecxi_size + manualcfa_size + dlpchildcfa_size) +
                ("\0" * 4) + contentindex + ("\0" * 0x201F) +
                zlib.decompress(ciainfo.decode('base64')) + ("\0" * 2412) +
                chunkrecords + tmdpadding
            )

            chunkrecords = list(chunkrecords)  # to update hashes in it, then calculate the hash over the entire thing

            cia.seek(0x2F9F)
            cia.write(contentcount)

            cia.seek(0x2C1C)
            cia.write(tid_bin)
            cia.seek(0x2F4C)
            cia.write(tid_bin)

            cia.seek(0x2F5A)
            cia.write(savesize)

            # Game Executable CXI NCCH Header + first-half ExHeader
            cia.seek(0, 2)
            gamecxi_hash = hashlib.sha256(ncch_header + exh)
            cia.write(ncch_header + exh)

            # Game Executable CXI second-half ExHeader + contents
            print("- writing Game Executable CXI")
            print_v("  offset: {}".format(hex(gamecxi_offset)))
            print_v("  size:   {}".format(hex(gamecxi_size)))
            romf.seek(gamecxi_offset + 0x200 + 0x400)
            left = gamecxi_size - 0x200 - 0x400
            tmpread = ""
            for __ in itertools.repeat(0, int(math.floor((gamecxi_size / readsize)) + 1)):
                toread = min(readsize, left)
                tmpread = romf.read(toread)
                gamecxi_hash.update(tmpread)
                cia.write(tmpread)
                left -= readsize
                showprogress(gamecxi_size - left, gamecxi_size)
                if left <= 0:
                    print("")
                    break
            print_v("- Game Executable CXI SHA-256 hash:")
            gamecxi_hashdigest = gamecxi_hash.hexdigest().upper()
            print_v("  {}\n  {}".format(gamecxi_hashdigest[0:0x20], gamecxi_hashdigest[0x20:0x40]))
            cia.seek(0x38D4)
            cia.write(gamecxi_hash.digest())
            chunkrecords[0x10:0x30] = list(gamecxi_hash.digest())

            # Manual CFA
            if manualcfa_offset != 0:
                cia.seek(0, 2)
                print("- writing Manual CFA")
                manualcfa_hash = hashlib.sha256()
                print_v("  offset: {}".format(hex(manualcfa_offset)))
                print_v("  size:   {}".format(hex(manualcfa_size)))
                romf.seek(manualcfa_offset)
                left = manualcfa_size
                for __ in itertools.repeat(0, int(math.floor((manualcfa_size / readsize)) + 1)):
                    toread = min(readsize, left)
                    tmpread = romf.read(toread)
                    manualcfa_hash.update(tmpread)
                    cia.write(tmpread)
                    left -= readsize
                    showprogress(manualcfa_size - left, manualcfa_size)
                    if left <= 0:
                        print("")
                        break
                print_v("- Manual CFA SHA-256 hash:")
                manualcfa_hashdigest = manualcfa_hash.hexdigest().upper()
                print_v("  {}\n  {}".format(manualcfa_hashdigest[0:0x20], manualcfa_hashdigest[0x20:0x40]))
                cia.seek(0x3904)
                cia.write(manualcfa_hash.digest())
                chunkrecords[0x40:0x60] = list(manualcfa_hash.digest())

            # Download Play child container CFA
            if dlpchildcfa_offset != 0:
                cia.seek(0, 2)
                print("- writing Download Play child container CFA")
                dlpchildcfa_hash = hashlib.sha256()
                print_v("  offset: {}".format(hex(dlpchildcfa_offset)))
                print_v("  size:   {}".format(hex(dlpchildcfa_size)))
                romf.seek(dlpchildcfa_offset)
                left = dlpchildcfa_size
                for __ in itertools.repeat(0, int(math.floor((dlpchildcfa_size / readsize)) + 1)):
                    toread = min(readsize, left)
                    tmpread = romf.read(toread)
                    dlpchildcfa_hash.update(tmpread)
                    cia.write(tmpread)
                    left -= readsize
                    showprogress(dlpchildcfa_size - left, dlpchildcfa_size)
                    if left <= 0:
                        print("")
                        break
                print_v("- Download Play child container CFA SHA-256 hash:")
                dlpchildcfa_hashdigest = dlpchildcfa_hash.hexdigest().upper()
                print_v("  {}\n  {}".format(dlpchildcfa_hashdigest[0:0x20], dlpchildcfa_hashdigest[0x20:0x40]))
                cia.seek(0x3934)
                cia.write(dlpchildcfa_hash.digest())
                chunkrecords[0x70:0x90] = list(dlpchildcfa_hash.digest())

            print_v("- updating hashes")
            chunkrecords_hash = hashlib.sha256("".join(chunkrecords))
            print_v("- Content chunk records SHA-256 hash:")
            chunkrecords_hashdigest = chunkrecords_hash.hexdigest().upper()
            print_v("  {}\n  {}".format(chunkrecords_hashdigest[0:0x20], chunkrecords_hashdigest[0x20:0x40]))

            cia.seek(0x2FC7)
            cia.write(contentcount + chunkrecords_hash.digest())

            cia.seek(0x2FA4)
            inforecords_hash = hashlib.sha256("\0\0\0" + contentcount + chunkrecords_hash.digest() + ("\0"*0x8DC))
            print_v("- Content info records SHA-256 hash:")
            inforecords_hashdigest = inforecords_hash.hexdigest().upper()
            print_v("  {}\n  {}".format(inforecords_hashdigest[0:0x20], inforecords_hashdigest[0x20:0x40]))
            cia.write(inforecords_hash.digest())

    processedroms += 1

if totalroms == 0:
    sys.exit(helptext)
else:
    if genncchinfo and len(ncchinfolist) != 0:
        print("- saving ncchinfo.bin")
        with open("ncchinfo.bin", "wb") as ncchinfo:
            ncchinfo.write("\xFF\xFF\xFF\xFF\x04\0\0\xF0")
            # this is bad, I know
            ncchinfo.write(binascii.unhexlify(format(len(ncchinfolist), 'x').rjust(8, '0'))[::-1])
            ncchinfo.write("\0" * 4)
            for i in ncchinfolist:
                ncchinfo.write(i)
        print("- use Decrypt9WIP on a 3DS system to generate the XORpads.")
        print("  place the file at the root or in a folder called \"files9\".")
        print("  view the Decrypt9WIP README and download releases at")
        print("  https://github.com/d0k3/Decrypt9WIP")
    print("* done converting!")
    print("  {} out of {} roms processed".format(processedroms, totalroms))
