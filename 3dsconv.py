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

version = '4.1'

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
  --verbose            - Print more information'''.format(
    sys.argv[0],
    'current directory' if output_directory == '' else '"{}"'.format(
        output_directory
    )
)

if len(sys.argv) < 2:
    sys.exit(helptext)

# includes certificate chain, ticket (blank titlekey and title ID),
#   tmd signature with blank header (blank title ID) and blank content info
#   records
# compressed using zlib then encoded with base64
# I should find a better way to store this... this is so ugly
ciainfo = b'''
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'''

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

    if dev_keys:
        print('Devkit keys are being used since `--dev-keys\' was passed. '
              'Note the resulting files will still be encrypted with devkit '
              'keys.')

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
        content_count = b'\x01'
        tmd_size = 0xB34
        content_index = 0x80  # one extra bit in binary for each content
        # this is assuming that a game has a manual if it also has a dlp child
        # I've not seen a case of the opposite yet
        if manual_cfa_offset != 0:
            tmd_padding = bytes(28)
            content_count = b'\x02'
            tmd_size = 0xB64
            content_index = 0xC0
        if dlpchild_cfa_offset != 0:
            tmd_padding = bytes(44)
            content_count = b'\x03'
            tmd_size = 0xB94
            content_index = 0xE0

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

            cia.write(
                # initial CIA header
                struct.pack('<IHHII', 0x2020, 0, 0, 0xA00, 0x350) +
                # tmd size, meta size, content size
                # this is ugly as well
                struct.pack('<III', tmd_size, 0x3AC0, game_cxi_size +
                            manual_cfa_size + dlpchild_cfa_size) +
                # content index
                struct.pack('<IB', 0, content_index) + (bytes(0x201F)) +
                # cert chain, ticket, tmd
                zlib.decompress(base64.b64decode(ciainfo)) + (bytes(0x96C)) +
                # chunk records in tmd + padding
                chunk_records + tmd_padding
            )

            # changing to list to update and hash later
            chunk_records = list(chunk_records)

            # write content count in tmd
            cia.seek(0x2F9F)
            cia.write(content_count)

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

            # Download Play child container CFA
            if dlpchild_cfa_offset != 0:
                cia.seek(0, 2)
                print('Writing Download Play child container CFA...')
                dlpchild_cfa_hash = hashlib.sha256()
                rom.seek(dlpchild_cfa_offset)
                left = dlpchild_cfa_size
                # i am so sorry
                for __ in itertools.repeat(
                        0, int(math.floor((dlpchild_cfa_size
                               / read_size)) + 1)):
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
                cia.seek(0x3934)
                cia.write(dlpchild_cfa_hash.digest())
                chunk_records[0x70:0x90] = list(dlpchild_cfa_hash.digest())

            # update final hashes
            print_v('\nUpdating hashes...')
            chunk_records_hash = hashlib.sha256(bytes(chunk_records))
            print_v('Content chunk records SHA-256 hash:')
            print_v('  {}'.format(chunk_records_hash.hexdigest().upper()))
            cia.seek(0x2FC7)
            cia.write(content_count + chunk_records_hash.digest())

            cia.seek(0x2FA4)
            info_records_hash = hashlib.sha256(
                bytes(3) + content_count + chunk_records_hash.digest()
                + (bytes(0x8DC))
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
