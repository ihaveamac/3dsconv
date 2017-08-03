#!/usr/bin/env python3

# 3dsconv.py by ihaveamac
# license: MIT License
# https://github.com/ihaveamac/3dsconv

import base64
import binascii
import glob
import hashlib
import itertools
import math
import os
import struct
import sys
import zlib


def main():
    pass


# check for pyaes which is used for crypto
pyaes_found = False
try:
    import pyaes
    pyaes_found = True
except ImportError:
    pass  # this is handled later

# default paths, relative to cwd
output_directory = ''  # override with --output=
boot9_path = ''  # override with --boot9=

version = '4.2.dev0'

print('3dsconv.py ~ version ' + version)

helptext = '''Convert Nintendo 3DS CCI (.3ds/.cci) to CIA
https://github.com/ihaveamac/3dsconv

Usage: {} [options] <game> [<game>...]

Options:
  --output=<dir>       - Save converted files in specified directory
                           Default: {}
  --boot9=<file>       - Path to dump of ARM9 bootROM, protected or full
  --overwrite          - Overwrite existing converted files
  --ignore-bad-hashes  - Ignore invalid hashes and CCI files and convert anyway
  --verbose            - Print more information
  --dev-keys           - Use developer-unit keys'''.format(
    sys.argv[0],
    'current directory' if output_directory == '' else '"{}"'.format(
        output_directory
    )
)

if len(sys.argv) < 2:
    sys.exit(helptext)

# don't know of a better way to store binary data in a script
# compressed using zlib then encoded with base64

# retail CIA certificate chain
certchain_retail = b'''
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
JWFnDuv/P7kyh1k='''

# ticket (blank titlekey and title ID), tmd signature with blank header
#   (blank title ID) and blank content info records
ticket_tmd = b'''
eJxjYGRgYRgFZIOg/PwSXWdHAwgw1o0IhjKTaW83I+2toJMlBAAjgwiQXAPEIlA2CGgwQFzXAsbM
EMH/BMBAOB8vGM1/FAH0/OccAGUmEacfR/J2AAAmBS75'''

mu = 0x200  # media unit
read_size = 0x800000  # used from padxorer
zerokey = bytes(0x10)


# used from http://www.falatic.com/index.php/108/python-and-bitwise-rotation
# converted to def because pycodestyle complained to me
def rol(val, r_bits, max_bits):
    return (val << r_bits % max_bits) & (2 ** max_bits - 1) | \
        ((val & (2 ** max_bits - 1)) >> (max_bits - (r_bits % max_bits)))


# verbose messages
def print_v(*msg, end='\n'):
    if verbose:
        print(*msg, end=end)


# verbose output, to be added into normal prints
def v(msg):
    if verbose:
        return msg
    return ''


# error messages
def error(*msg):
    print('Error:', *msg)


# show a progress bar
def show_progress(val, maxval):
    # print() didn't do what I wanted so I'm doing this
    minval = min(val, maxval)
    sys.stdout.write('\r  {:>5.1f}% {:>10} / {}'.format(
        (minval / maxval) * 100, minval, maxval)
    )
    sys.stdout.flush()


# options - contains older versions for compatibility reasons
verbose = '--verbose' in sys.argv
overwrite = '--overwrite' in sys.argv
no_convert = any(arg in sys.argv for arg in ('--no-convert', '--noconvert'))
ignore_bad_hashes = '--ignore-bad-hashes' in sys.argv
dev_keys = '--dev-keys' in sys.argv

# deprecated options, used for warnings
# the argument checker after also checks for --xorpads=
use_deprecated = any(arg in sys.argv for arg in ('--gen-ncchinfo',
                                                 '--gen-ncch-all'))

total_files = 0
processed_files = 0

certchain_dev = b''
if dev_keys:
    print('Devkit keys are being used since `--dev-keys\' was passed. Note '
          'the resulting files will still be encrypted with devkit keys, and '
          'only installable on developer units without extra conversion.')
    print('Looking for certchain-dev.bin...')

    def check_path(path):
        global certchain_dev
        if not certchain_dev:
            if os.path.isfile(path):
                with open(path, 'rb') as c:
                    certchain = c.read(0xA00)
                    correct_hash = 'd5c3d811a7eb87340aa9f4ab1841b6c4'
                    if hashlib.md5(certchain).hexdigest() == correct_hash:
                        certchain_dev = certchain

    check_path('certchain-dev.bin')
    check_path(os.path.expanduser('~') + '/.3ds/certchain-dev.bin')

    if not certchain_dev:
        error('Invalid or missing dev certchain. See README for details.')
        sys.exit(1)

files = []
for arg in sys.argv[1:]:
    if arg[:2] != '--':
        to_add = glob.glob(arg)
        if len(to_add) == 0:
            error('"{}" doesn\'t exist.'.format(arg))
            total_files += 1
        else:
            for input_file in to_add:
                rom_name = os.path.basename(os.path.splitext(input_file)[0])
                cia_name = os.path.join(output_directory, rom_name + '.cia')
                if not overwrite and os.path.isfile(cia_name):
                    error('"{}" already exists. Use `--overwrite\' to force'
                          'conversion.'.format(cia_name))
                    continue
                total_files += 1
                files.append([input_file, rom_name, cia_name])
    elif arg[:9] == '--output=':
        output_directory = arg[9:]
    elif arg[:8] == '--boot9=':
        boot9_path = arg[8:]
    # deprecated option
    elif arg[:9] == '--xorpads':
        use_deprecated = True

if use_deprecated:
    print('Note: Deprecated options are being used. XORpads are no longer '
          'supported. See the README at https://github.com/ihaveamac/3dsconv '
          'for more details.')

# print if pyaes is found, and search for boot9 if it is
# then get the original NCCH key from it
boot9_found = False
keys_set = False
orig_ncch_key = 0
if pyaes_found:
    print_v('pyaes found, Searching for protected ARM9 bootROM')

    def set_keys(boot9_file):
        keys_offset = 0
        if os.path.getsize(boot9_file) == 0x10000:
            keys_offset += 0x8000
        if dev_keys:
            keys_offset += 0x400
        with open(boot9_file, 'rb') as f:
            global keys_set, orig_ncch_key
            # get Original NCCH (slot 0x2C key X)
            f.seek(0x59D0 + keys_offset)
            key = f.read(0x10)
            key_hash = hashlib.md5(key).hexdigest()
            correct_hash = ('49aa32c775608af6298ddc0fc6d18a7e' if dev_keys else
                            'e35bf88330f4f1b2bb6fd5b870a679ca')
            if key_hash == correct_hash:
                print_v('Correct key found.')
                orig_ncch_key = int.from_bytes(key, byteorder='big')
                keys_set = True
                return
            print_v('Corrupt file (invalid key).')

    def check_path(path):
        if not keys_set:
            print_v('... {}: '.format(path), end='')
            if os.path.isfile(path):
                set_keys(path)
            else:
                print_v('File doesn\'t exist.')

    # check supplied path by boot9_path or --boot9=
    if boot9_path != '':
        check_path(boot9_path)
    check_path('boot9.bin')
    check_path('boot9_prot.bin')
    check_path(os.path.expanduser('~') + '/.3ds/boot9.bin')
    check_path(os.path.expanduser('~') + '/.3ds/boot9_prot.bin')
    if not keys_set:
        error('bootROM not found, encryption will not be supported')
else:
    error('pyaes not found, encryption will not be supported')

# create output directory if it doesn't exist
if output_directory != '':
    os.makedirs(output_directory, exist_ok=True)

if not total_files:
    error('No files were given.')
    sys.exit(1)
if not files:
    error('No inputted files exist.')
    sys.exit(1)

for rom_file in files:
    with open(rom_file[0], 'rb') as rom:
        print_v('----------\nProcessing {}...'.format(rom_file[0]))
        # check for NCSD magic
        # 3DS NAND dumps also have this
        rom.seek(0x100)
        ncsd_magic = rom.read(4)
        if ncsd_magic != b'NCSD':
            error('"{}" is not a CCI file (missing NCSD magic).'.format(
                rom_file[0]
            ))
            continue

        # get title ID
        rom.seek(0x108)
        title_id = rom.read(8)[::-1]
        title_id_hex = binascii.hexlify(title_id).decode('utf-8').upper()
        print_v('\nTitle ID:', format(title_id_hex))

        # get partition sizes
        rom.seek(0x120)

        # find Game Executable CXI
        game_cxi_offset = struct.unpack('<I', rom.read(4))[0] * mu
        game_cxi_size = struct.unpack('<I', rom.read(4))[0] * mu
        print_v('\nGame Executable CXI Size: {:X}'.format(game_cxi_size))

        # find Manual CFA
        manual_cfa_offset = struct.unpack('<I', rom.read(4))[0] * mu
        manual_cfa_size = struct.unpack('<I', rom.read(4))[0] * mu
        print_v('Manual CFA Size: {:X}'.format(manual_cfa_size))

        # find Download Play child CFA
        dlpchild_cfa_offset = struct.unpack('<I', rom.read(4))[0] * mu
        dlpchild_cfa_size = struct.unpack('<I', rom.read(4))[0] * mu
        print_v('Download Play child CFA Size: {:X}\n'.format(
            dlpchild_cfa_size
        ))

        # check for NCCH magic
        # prevents NAND dumps from being "converted"
        rom.seek(game_cxi_offset + 0x100)
        ncch_magic = rom.read(4)
        if ncch_magic != b'NCCH':
            error('"{}" is not a CCI file (missing NCCH magic).'.format(
                rom_file[0]
            ))
            continue

        # get the encryption type
        rom.seek(game_cxi_offset + 0x18F)
        # pay no mind to this ugliness...
        encryption_bitmask = struct.pack('c', rom.read(1))[0]
        encrypted = not encryption_bitmask & 0x4
        zerokey_encrypted = encryption_bitmask & 0x1

        if encrypted:
            if not keys_set:
                error('"{}" is encrypted using Original NCCH and pyaes or '
                      'the bootROM were not found, therefore this can not be '
                      'converted. See the README at '
                      'https://github.com/ihaveamac/3dsconv for details.'
                      .format(rom_file[0]))
                continue
            else:
                # get normal key to decrypt parts of the file
                key = b''
                ctr_extheader_v = int(title_id_hex + '0100000000000000', 16)
                ctr_exefs_v = int(title_id_hex + '0200000000000000', 16)
                if zerokey_encrypted:
                    key = zerokey
                else:
                    rom.seek(game_cxi_offset)
                    key_y_bytes = rom.read(0x10)
                    key_y = int.from_bytes(key_y_bytes, byteorder='big')
                    key = rol((rol(orig_ncch_key, 2, 128) ^ key_y) +
                              0x1FF9E9AAC5FE0408024591DC5D52768A, 87,
                              128).to_bytes(0x10, byteorder='big')
                    print_v('Normal key:',
                            binascii.hexlify(key).decode('utf-8').upper())

        print('Converting {} ({})...'.format(
            rom_file[1], 'zerokey encrypted' if zerokey_encrypted else (
                'encrypted' if encrypted else 'decrypted'
            )
        ))

        # Game Executable fist-half ExtHeader
        print_v('\nVerifying ExtHeader...')
        rom.seek(game_cxi_offset + 0x200)
        extheader = rom.read(0x400)
        if encrypted:
            print_v('Decrypting ExtHeader...')
            ctr_extheader = pyaes.Counter(initial_value=ctr_extheader_v)
            cipher_extheader = pyaes.AESModeOfOperationCTR(
                key, counter=ctr_extheader)
            extheader = cipher_extheader.decrypt(extheader)
        extheader_hash = hashlib.sha256(extheader).digest()
        rom.seek(0x4160)
        ncch_extheader_hash = rom.read(0x20)
        if extheader_hash != ncch_extheader_hash:
            print('This file may be corrupt (invalid ExtHeader hash).')
            if ignore_bad_hashes:
                print('Converting anyway because --ignore-bad-hashes was '
                      'passed.')
            else:
                continue

        # patch ExtHeader to make an SD title
        print_v('Patching ExtHeader...')
        extheader_list = list(extheader)
        extheader_list[0xD] |= 2
        extheader = bytes(extheader_list)
        new_extheader_hash = hashlib.sha256(extheader).digest()

        # get dependency list for meta region
        dependency_list = extheader[0x40:0x1C0]

        # get save data size for tmd
        save_size = extheader[0x1C0:0x1C4]

        if encrypted:
            print_v('Re-encrypting ExtHeader...')
            ctr_extheader = pyaes.Counter(initial_value=ctr_extheader_v)
            cipher_extheader = pyaes.AESModeOfOperationCTR(
                key, counter=ctr_extheader)
            extheader = cipher_extheader.encrypt(extheader)

        # Game Executable NCCH Header
        print_v('\nReading NCCH Header of Game Executable...')
        rom.seek(game_cxi_offset)
        ncch_header = list(rom.read(0x200))
        ncch_header[0x160:0x180] = list(new_extheader_hash)
        ncch_header = bytes(ncch_header)

        # get icon from ExeFS
        print_v('Getting SMDH...')
        exefs_offset = struct.unpack('<I', ncch_header[0x1A0:0x1A4])[0] * mu
        rom.seek(game_cxi_offset + exefs_offset)
        # exefs can contain up to 10 file headers but only 4 are used normally
        exefs_file_header = rom.read(0x40)
        if encrypted:
            print_v('Decrypting ExeFS Header...')
            ctr_exefs = pyaes.Counter(initial_value=ctr_exefs_v)
            cipher_exefs = pyaes.AESModeOfOperationCTR(
                key, counter=ctr_exefs)
            exefs_file_header = cipher_exefs.encrypt(exefs_file_header)
        for header_num in range(0, 4):
            if exefs_file_header[header_num * 0x10:0x8 + (header_num * 0x10)]\
                    .rstrip(b'\0') == b'icon':  # wtf indentation
                exefs_icon_offset = struct.unpack(
                    '<I', exefs_file_header[0x8 + (header_num * 0x10):
                                            0xC + (header_num * 0x10)])[0]
                rom.seek(exefs_icon_offset + 0x200 - 0x40, 1)
                exefs_icon = rom.read(0x36C0)
                if encrypted:
                    ctr_exefs_icon_v = ctr_exefs_v +\
                        (exefs_icon_offset // 0x10) + 0x20
                    ctr_exefs_icon = pyaes.Counter(
                        initial_value=ctr_exefs_icon_v)
                    cipher_exefs_icon = pyaes.AESModeOfOperationCTR(
                        key, counter=ctr_exefs_icon)
                    exefs_icon = cipher_exefs_icon.decrypt(exefs_icon)
                break
        if not exefs_icon:
            error('Icon not found in the ExeFS.')
            continue

        # since we will only have three possible results to these, these are
        #   hardcoded variables for convenience
        # these could be generated but given this, I'm not doing that
        # I made it a little better
        tmd_padding = bytes(12)  # padding to add at the end of the tmd
        content_count = 1
        tmd_size = 0xB34
        content_index = 0b10000000
        if manual_cfa_offset != 0:
            tmd_padding += bytes(16)
            content_count += 1
            tmd_size += 0x30
            content_index += 0b01000000
        if dlpchild_cfa_offset != 0:
            tmd_padding += bytes(16)
            content_count += 1
            tmd_size += 0x30
            content_index += 0b00100000

        # CIA
        with open(rom_file[2], 'wb') as cia:
            print_v('Writing CIA header...')

            # 1st content: ID 0x, Index 0x0
            chunk_records = struct.pack('>III', 0, 0, 0)
            chunk_records += struct.pack(">I", game_cxi_size)
            chunk_records += bytes(0x20)  # SHA-256 to be added later
            if manual_cfa_offset != 0:
                # 2nd content: ID 0x1, Index 0x1
                chunk_records += struct.pack('>III', 1, 0x10000, 0)
                chunk_records += struct.pack('>I', manual_cfa_size)
                chunk_records += bytes(0x20)  # SHA-256 to be added later
            if dlpchild_cfa_offset != 0:
                # 3nd content: ID 0x2, Index 0x2
                chunk_records += struct.pack('>III', 2, 0x20000, 0)
                chunk_records += struct.pack('>I', dlpchild_cfa_size)
                chunk_records += bytes(0x20)  # SHA-256 to be added later

            content_size = game_cxi_size + manual_cfa_size + dlpchild_cfa_size

            cia.write(
                # initial CIA header
                struct.pack('<IHHII', 0x2020, 0, 0, 0xA00, 0x350) +
                # tmd size, meta size, content size
                # this is ugly as well
                struct.pack('<III', tmd_size, 0x3AC0, content_size) +
                # content index
                struct.pack('<IB', 0, content_index) + (bytes(0x201F)) +
                # cert chain
                (certchain_dev if dev_keys else
                 zlib.decompress(base64.b64decode(certchain_retail))) +
                # ticket, tmd
                zlib.decompress(base64.b64decode(ticket_tmd)) +
                (bytes(0x96C)) +
                # chunk records in tmd + padding
                chunk_records + tmd_padding
            )

            # changing to list to update and hash later
            chunk_records = list(chunk_records)

            # write content count in tmd
            cia.seek(0x2F9F)
            cia.write(bytes([content_count]))

            # write title ID in ticket and tmd
            cia.seek(0x2C1C)
            cia.write(title_id)
            cia.seek(0x2F4C)
            cia.write(title_id)

            # write save size in tmd
            cia.seek(0x2F5A)
            cia.write(save_size)

            # Game Executable CXI NCCH Header + first-half ExHeader
            cia.seek(0, 2)
            game_cxi_hash = hashlib.sha256(ncch_header + extheader)
            cia.write(ncch_header + extheader)

            # Game Executable CXI second-half ExHeader + contents
            print('Writing Game Executable CXI...')
            rom.seek(game_cxi_offset + 0x200 + 0x400)
            left = game_cxi_size - 0x200 - 0x400
            tmpread = ''
            for __ in itertools.repeat(
                    0, int(math.floor((game_cxi_size / read_size)) + 1)):
                to_read = min(read_size, left)
                tmpread = rom.read(to_read)
                game_cxi_hash.update(tmpread)
                cia.write(tmpread)
                left -= read_size
                show_progress(game_cxi_size - left, game_cxi_size)
                if left <= 0:
                    print('')
                    break
            print_v('Game Executable CXI SHA-256 hash:')
            print_v('  {}'.format(game_cxi_hash.hexdigest().upper()))
            cia.seek(0x38D4)
            cia.write(game_cxi_hash.digest())
            chunk_records[0x10:0x30] = list(game_cxi_hash.digest())

            cr_offset = 0

            # Manual CFA
            if manual_cfa_offset != 0:
                cia.seek(0, 2)
                print('Writing Manual CFA...')
                manual_cfa_hash = hashlib.sha256()
                rom.seek(manual_cfa_offset)
                left = manual_cfa_size
                for __ in itertools.repeat(
                        0, int(math.floor((manual_cfa_size / read_size)) + 1)):
                    to_read = min(read_size, left)
                    tmpread = rom.read(to_read)
                    manual_cfa_hash.update(tmpread)
                    cia.write(tmpread)
                    left -= read_size
                    show_progress(manual_cfa_size - left, manual_cfa_size)
                    if left <= 0:
                        print('')
                        break
                print_v('Manual CFA SHA-256 hash:')
                print_v('  {}'.format(manual_cfa_hash.hexdigest().upper()))
                cia.seek(0x3904)
                cia.write(manual_cfa_hash.digest())
                chunk_records[0x40:0x60] = list(manual_cfa_hash.digest())
                cr_offset += 0x30

            # Download Play child container CFA
            if dlpchild_cfa_offset != 0:
                cia.seek(0, 2)
                print('Writing Download Play child container CFA...')
                dlpchild_cfa_hash = hashlib.sha256()
                rom.seek(dlpchild_cfa_offset)
                left = dlpchild_cfa_size
                # i am so sorry
                for __ in itertools.repeat(
                        0, int(math.floor((dlpchild_cfa_size /
                               read_size)) + 1)):
                    to_read = min(read_size, left)
                    tmpread = rom.read(to_read)
                    dlpchild_cfa_hash.update(tmpread)
                    cia.write(tmpread)
                    left -= read_size
                    show_progress(dlpchild_cfa_size - left, dlpchild_cfa_size)
                    if left <= 0:
                        print('')
                        break
                print_v('- Download Play child container CFA SHA-256 hash:')
                print_v('  {}'.format(dlpchild_cfa_hash.hexdigest().upper()))
                cia.seek(0x3904 + cr_offset)
                cia.write(dlpchild_cfa_hash.digest())
                chunk_records[0x40 + cr_offset:0x60 + cr_offset] = list(
                    dlpchild_cfa_hash.digest()
                )

            # update final hashes
            print_v('\nUpdating hashes...')
            chunk_records_hash = hashlib.sha256(bytes(chunk_records))
            print_v('Content chunk records SHA-256 hash:')
            print_v('  {}'.format(chunk_records_hash.hexdigest().upper()))
            cia.seek(0x2FC7)
            cia.write(bytes([content_count]) + chunk_records_hash.digest())

            cia.seek(0x2FA4)
            info_records_hash = hashlib.sha256(
                bytes(3) + bytes([content_count]) +
                chunk_records_hash.digest() + (bytes(0x8DC))
            )
            print_v('Content info records SHA-256 hash:')
            print_v('  {}'.format(info_records_hash.hexdigest().upper()))
            cia.write(info_records_hash.digest())

            # write Meta region
            cia.seek(0, 2)
            cia.write(
                dependency_list + bytes(0x180) + struct.pack('<I', 0x2) +
                bytes(0xFC) + exefs_icon
            )

    processed_files += 1

print("Done converting {} out of {} files.".format(processed_files,
                                                   total_files))
