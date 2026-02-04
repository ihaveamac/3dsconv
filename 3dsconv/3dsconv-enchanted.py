#!/usr/bin/env python3

# 3dsconv.py - Enhanced Performance Version
# Based on ihaveamac's 3dsconv & NENO756'S fork
# Optimized for speed (Multiprocessing & pycryptodome)
# license: MIT License

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
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any, BinaryIO
from concurrent.futures import ProcessPoolExecutor, as_completed

try:
    from Crypto.Cipher import AES
    from Crypto.Util import Counter as CryptoCounter
    CRYPTO_BACKEND = 'pycryptodome'
except ImportError:
    try:
        import pyaes
        CRYPTO_BACKEND = 'pyaes'
    except ImportError:
        CRYPTO_BACKEND = None
        print("Warning: Neither pycryptodome nor pyaes found. Encryption support disabled.")

class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    PURPLE = '\033[95m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    END = '\033[0m'

MU = 0x200
READ_SIZE = 0x800000
ZERO_KEY = bytes(0x10)
VERSION = '4.4-enhanced'
DEFAULT_FILE_EXTENSIONS = ('.3ds', '.cci')

CERT_CHAIN_RETAIL = base64.b64decode(
    'eNqVVmtv00AQ/iuW00QpFAsocZuiHlAbojx2CFo7tXASJ4X26nLndY4Tn+2zHSH4EeKTBwgJ'
    'iZ/BD+IXIMZc4jiP+2G8N7Ozs/OdmZ3rJAlnFvPEh9I1KrXGXUC8PCz9iwt/mhXhDHx5fMJx'
    'Fotg8GUsE98CvJpFdxCFbN8P/MjaNfQgHnzM8swfWYe1Wk2NslnCsvE0ZrwIeJ54cQxQzVLM'
    'o6JUCXgc+3ExUwdh9Gm8fJqN3f12fdNQ1Wr1zWw6z7x5jqM0hM9J+oA8f+wd7dWrG4r6oWlM'
    'j7IJL5cZFJ4vQ2BpUOQlQK3KVfyi6cN46oPR9g6XeTme5I7TbppGU2+CA4C4zJYJLy1rU3sL'
    'mj8M0xSIKQvDGq+4u2d96n5y3M+63nbMFjyYswza+s5eu2saulZv6vvt5sejT0dHzW29/ilO'
    '5kyCIA3dbjq91J9m6WQx5yVE/1DfMhxLcBdLQFAl9U0A5jyI/JIHAvUgTiC5sq2Y8iBdZrMo'
    'mwkW5+mUi6BT3zJ1/d3WhqE3zWaz9r5azcr5IuXZLJ8m4RiLd9o7rZ1dU99+b7q+6PSJjBgs'
    '5jW1WtfcazfVv6Vu6geGtd8ybUuzNKP5bqO+qbQam/VNzW63W63ddmujXq/XlFaLiZQo+O3G'
    'dqulG9a23tg+6u7tG3qjuaWbuuP5ruumruM4Bwpw/QcfL9OcR9PJZIog/x3ef7m7vhr6jr3v'
    'OJfXw5PBz7Pz8x/9/vHx9+8n308vzn/2+r3e8cnpxelZ/+z08rR33Pv2/1X/ATe1b6A='
)

TICKET_TMD = base64.b64decode(
    'eJxjYGRgYBgFZIOg/PwSXWdHAwgw1o0IhjKTaW83I+2toJMlBAAjgwiQXAPEIlA2CGgwQFzX'
    'AsbMEMH/BMBAOB8vGM1/FAH0/OccAGUmEacfR/J2AAAmBS75'
)

ORIGINAL_NCCH_KEY_RETAIL = bytes.fromhex('e35bf88330f4f1b2bb6fd5b870a679ca')
ORIGINAL_NCCH_KEY_DEV = bytes.fromhex('49aa32c775608af6298ddc0fc6d18a7e')

def rol(val: int, r_bits: int, max_bits: int) -> int:
    return (val << r_bits % max_bits) & (2 ** max_bits - 1) | \
        ((val & (2 ** max_bits - 1)) >> (max_bits - (r_bits % max_bits)))


def decompress_data(data: bytes) -> bytes:
    try:
        return zlib.decompress(data)
    except:
        return data


class Config:
    def __init__(self):
        self.output_directory = ''
        self.boot9_path = ''
        self.overwrite = False
        self.ignore_bad_hashes = False
        self.verbose = False
        self.dev_keys = False
        self.files: List[Tuple[str, str, str]] = []
        self.certchain_dev = b''
        self.keys_set = False
        self.orig_ncch_key = 0
        self.retail_ncch_key = int.from_bytes(ORIGINAL_NCCH_KEY_RETAIL, byteorder='big')
        self.dev_ncch_key = int.from_bytes(ORIGINAL_NCCH_KEY_DEV, byteorder='big')

class EncryptionHandler:
    def __init__(self, config: Config):
        self.config = config
        self.backend = CRYPTO_BACKEND
        
        if config.dev_keys:
            config.orig_ncch_key = config.dev_ncch_key
        else:
            config.orig_ncch_key = config.retail_ncch_key
        config.keys_set = True
    
    def setup_keys(self, boot9_file: str) -> bool:
        if not os.path.isfile(boot9_file):
            return False
        
        keys_offset = 0
        if os.path.getsize(boot9_file) == 0x10000:
            keys_offset += 0x8000
        if self.config.dev_keys:
            keys_offset += 0x400
        
        try:
            with open(boot9_file, 'rb') as f:
                f.seek(0x59D0 + keys_offset)
                key = f.read(0x10)
                key_hash = hashlib.md5(key).hexdigest()
                correct_hash = ('49aa32c775608af6298ddc0fc6d18a7e' if self.config.dev_keys else
                              'e35bf88330f4f1b2bb6fd5d870a679ca')
                
                if key_hash == correct_hash:
                    if self.config.verbose:
                        print("Correct key found.")
                    self.config.orig_ncch_key = int.from_bytes(key, byteorder='big')
                    self.config.keys_set = True
                    return True
        except Exception as e:
            if self.config.verbose:
                print(f"Error reading boot9: {e}")
        
        return False
    
    def find_boot9(self) -> bool:
        search_paths = []
        
        if self.config.boot9_path:
            search_paths.append(self.config.boot9_path)
        
        search_paths.extend([
            'boot9.bin',
            'boot9_prot.bin',
            os.path.expanduser('~') + '/.3ds/boot9.bin',
            os.path.expanduser('~') + '/.3ds/boot9_prot.bin'
        ])
        
        for path in search_paths:
            if self.config.verbose:
                print(f"Checking {path}...")
            if self.setup_keys(path):
                return True
        
        print("Note: Using built-in encryption keys (for decrypted ROMs only)")
        self.config.keys_set = True
        return False

    def create_ctr_cipher(self, key: bytes, ctr_val: int):
        if self.backend == 'pycryptodome':
            ctr = CryptoCounter.new(128, initial_value=ctr_val)
            return AES.new(key, AES.MODE_CTR, counter=ctr)
        elif self.backend == 'pyaes':
            ctr = pyaes.Counter(initial_value=ctr_val)
            return pyaes.AESModeOfOperationCTR(key, counter=ctr)
        else:
            raise RuntimeError("No encryption library available.")

    def decrypt(self, cipher, data: bytes) -> bytes:
        if self.backend == 'pycryptodome':
            return cipher.decrypt(data)
        elif self.backend == 'pyaes':
            return cipher.decrypt(data)
        return data

    def encrypt(self, cipher, data: bytes) -> bytes:
        if self.backend == 'pycryptodome':
            return cipher.encrypt(data)
        elif self.backend == 'pyaes':
            return cipher.encrypt(data)
        return data


class CCIConverter:
    def __init__(self, config: Config):
        self.config = config
        self.encryption_handler = EncryptionHandler(config)
        
    def print_verbose(self, *msg, end='\n'):
        if self.config.verbose:
            print(*msg, end=end)
    
    def print_error(self, *msg):
        print('Error:', *msg)
    
    def process_file(self, rom_file: Tuple[str, str, str]) -> Tuple[bool, str]:
        input_file, rom_name, cia_name = rom_file
        
        try:
            with open(input_file, 'rb') as rom:
                success = self._process_rom_file(rom, input_file, rom_name, cia_name)
                return success, f"Converted: {rom_name}"
        except Exception as e:
            return False, f"Error processing {input_file}: {e}"
    
    def _process_rom_file(self, rom: BinaryIO, input_file: str, rom_name: str, cia_name: str) -> bool:
        self.print_verbose('----------')
        self.print_verbose(f'Processing {input_file}...')
        
        rom.seek(0x100)
        ncsd_magic = rom.read(4)
        if ncsd_magic != b'NCSD':
            self.print_error(f'"{input_file}" is not a CCI file (missing NCSD magic).')
            return False
        
        rom.seek(0x108)
        title_id = rom.read(8)[::-1]
        title_id_hex = binascii.hexlify(title_id).decode('utf-8').upper()
        self.print_verbose(f'Title ID: {title_id_hex}')
        
        rom.seek(0x120)
        
        game_cxi_offset = struct.unpack('<I', rom.read(4))[0] * MU
        game_cxi_size = struct.unpack('<I', rom.read(4))[0] * MU
        self.print_verbose(f'Game Executable CXI Size: {game_cxi_size:X}')
        
        manual_cfa_offset = struct.unpack('<I', rom.read(4))[0] * MU
        manual_cfa_size = struct.unpack('<I', rom.read(4))[0] * MU
        self.print_verbose(f'Manual CFA Size: {manual_cfa_size:X}')
        
        dlpchild_cfa_offset = struct.unpack('<I', rom.read(4))[0] * MU
        dlpchild_cfa_size = struct.unpack('<I', rom.read(4))[0] * MU
        self.print_verbose(f'Download Play child CFA Size: {dlpchild_cfa_size:X}\n')
        
        rom.seek(game_cxi_offset + 0x100)
        ncch_magic = rom.read(4)
        if ncch_magic != b'NCCH':
            self.print_error(f'"{input_file}" is not a CCI file (missing NCCH magic).')
            return False
        
        rom.seek(game_cxi_offset + 0x18F)
        encryption_bitmask = struct.pack('c', rom.read(1))[0]
        encrypted = not encryption_bitmask & 0x4
        zerokey_encrypted = encryption_bitmask & 0x1
        
        if encrypted:
            if not self.config.keys_set:
                self.print_error(f'"{input_file}" is encrypted but keys are not available.')
                self.print_error(f"Note: This tool can only convert decrypted ROMs without boot9.bin")
                return False
        
        encryption_status = 'zerokey encrypted' if zerokey_encrypted else (
            'encrypted' if encrypted else 'decrypted'
        )
        
        if not self.config.verbose:
             print(f'[{rom_name}] ({encryption_status}) -> Converting...')
        else:
             print(f'Converting {rom_name} ({encryption_status})...')
        
        return self._convert_to_cia(
            rom, input_file, cia_name, title_id, title_id_hex,
            game_cxi_offset, game_cxi_size,
            manual_cfa_offset, manual_cfa_size,
            dlpchild_cfa_offset, dlpchild_cfa_size,
            encrypted, zerokey_encrypted
        )
    
    def _convert_to_cia(self, rom: BinaryIO, input_file: str, cia_name: str,
                       title_id: bytes, title_id_hex: str,
                       game_cxi_offset: int, game_cxi_size: int,
                       manual_cfa_offset: int, manual_cfa_size: int,
                       dlpchild_cfa_offset: int, dlpchild_cfa_size: int,
                       encrypted: bool, zerokey_encrypted: bool) -> bool:
        try:
            key = ZERO_KEY
            ctr_extheader_v = None
            ctr_exefs_v = None
            
            if encrypted:
                if zerokey_encrypted:
                    key = ZERO_KEY
                else:
                    rom.seek(game_cxi_offset)
                    key_y_bytes = rom.read(0x10)
                    key_y = int.from_bytes(key_y_bytes, byteorder='big')
                    key = rol((rol(self.config.orig_ncch_key, 2, 128) ^ key_y) +
                              0x1FF9E9AAC5FE0408024591DC5D52768A, 87,
                              128).to_bytes(0x10, byteorder='big')
                    self.print_verbose('Normal key:', binascii.hexlify(key).decode('utf-8').upper())
                
                ctr_extheader_v = int(title_id_hex + '0100000000000000', 16)
                ctr_exefs_v = int(title_id_hex + '0200000000000000', 16)
            
            extheader_data = self._process_exheader(
                rom, game_cxi_offset, encrypted, key, ctr_extheader_v
            )
            
            if extheader_data is None:
                return False
            
            extheader, new_extheader_hash, dependency_list, save_size = extheader_data
            
            rom.seek(game_cxi_offset)
            ncch_header = list(rom.read(0x200))
            ncch_header[0x160:0x180] = list(new_extheader_hash)
            ncch_header = bytes(ncch_header)
            
            exefs_icon = self._get_exefs_icon(
                rom, game_cxi_offset, ncch_header, encrypted, key, ctr_exefs_v
            )
            
            if exefs_icon is None:
                self.print_error('Icon not found in the ExeFS.')
                return False
            
            return self._write_cia_file(
                rom, cia_name, title_id, save_size, exefs_icon, dependency_list,
                game_cxi_offset, game_cxi_size, manual_cfa_offset, manual_cfa_size,
                dlpchild_cfa_offset, dlpchild_cfa_size,
                ncch_header, extheader, encrypted, key, ctr_extheader_v
            )
            
        except Exception as e:
            self.print_error(f"Error during conversion: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _process_exheader(self, rom: BinaryIO, game_cxi_offset: int,
                         encrypted: bool, key: bytes, ctr_extheader_v: int) -> Optional[Tuple]:
        self.print_verbose('\nVerifying ExtHeader...')
        rom.seek(game_cxi_offset + 0x200)
        extheader = rom.read(0x400)
        
        if encrypted:
            self.print_verbose('Decrypting ExtHeader...')
            if CRYPTO_BACKEND is None:
                print("Error: No crypto library available for decryption")
                return None
            
            cipher = self.encryption_handler.create_ctr_cipher(key, ctr_extheader_v)
            extheader = self.encryption_handler.decrypt(cipher, extheader)
        
        extheader_hash = hashlib.sha256(extheader).digest()
        rom.seek(0x4160)
        ncch_extheader_hash = rom.read(0x20)
        
        if extheader_hash != ncch_extheader_hash:
            print('This file may be corrupt (invalid ExtHeader hash).')
            if not self.config.ignore_bad_hashes:
                return None
            print('Converting anyway because --ignore-bad-hashes was passed.')
        
        self.print_verbose('Patching ExtHeader...')
        extheader_list = list(extheader)
        extheader_list[0xD] |= 2
        extheader = bytes(extheader_list)
        new_extheader_hash = hashlib.sha256(extheader).digest()
        
        dependency_list = extheader[0x40:0x1C0]
        save_size = extheader[0x1C0:0x1C4]
        
        if encrypted:
            self.print_verbose('Re-encrypting ExtHeader...')
            cipher = self.encryption_handler.create_ctr_cipher(key, ctr_extheader_v)
            extheader = self.encryption_handler.encrypt(cipher, extheader)
        
        return extheader, new_extheader_hash, dependency_list, save_size
    
    def _get_exefs_icon(self, rom: BinaryIO, game_cxi_offset: int,
                       ncch_header: bytes, encrypted: bool,
                       key: bytes, ctr_exefs_v: int) -> Optional[bytes]:
        self.print_verbose('Getting SMDH...')
        exefs_offset = struct.unpack('<I', ncch_header[0x1A0:0x1A4])[0] * MU
        rom.seek(game_cxi_offset + exefs_offset)
        exefs_file_header = rom.read(0x40)
        
        if encrypted and CRYPTO_BACKEND:
            self.print_verbose('Decrypting ExeFS Header...')
            cipher_exefs = self.encryption_handler.create_ctr_cipher(key, ctr_exefs_v)
            exefs_file_header = self.encryption_handler.decrypt(cipher_exefs, exefs_file_header)
        
        for header_num in range(4):
            if exefs_file_header[header_num * 0x10:0x8 + (header_num * 0x10)].rstrip(b'\0') == b'icon':
                exefs_icon_offset = struct.unpack(
                    '<I', exefs_file_header[0x8 + (header_num * 0x10):
                                            0xC + (header_num * 0x10)]
                )[0]
                rom.seek(exefs_icon_offset + 0x200 - 0x40, 1)
                exefs_icon = rom.read(0x36C0)
                
                if encrypted and CRYPTO_BACKEND:
                    ctr_exefs_icon_v = ctr_exefs_v + (exefs_icon_offset // 0x10) + 0x20
                    cipher_exefs_icon = self.encryption_handler.create_ctr_cipher(key, ctr_exefs_icon_v)
                    exefs_icon = self.encryption_handler.decrypt(cipher_exefs_icon, exefs_icon)
                
                return exefs_icon
        
        return None
    
    def _write_cia_file(self, rom: BinaryIO, cia_name: str, title_id: bytes,
                       save_size: bytes, exefs_icon: bytes, dependency_list: bytes,
                       game_cxi_offset: int, game_cxi_size: int,
                       manual_cfa_offset: int, manual_cfa_size: int,
                       dlpchild_cfa_offset: int, dlpchild_cfa_size: int,
                       ncch_header: bytes, extheader: bytes,
                       encrypted: bool, key: bytes, ctr_extheader_v: int) -> bool:
        try:
            with open(cia_name, 'wb') as cia:
                content_count = 1
                tmd_size = 0xB34
                content_index = 0b10000000
                
                if manual_cfa_offset != 0:
                    content_count += 1
                    tmd_size += 0x30
                    content_index += 0b01000000
                
                if dlpchild_cfa_offset != 0:
                    content_count += 1
                    tmd_size += 0x30
                    content_index += 0b00100000
                
                chunk_records, content_size = self._prepare_content_records(
                    game_cxi_size, manual_cfa_size, dlpchild_cfa_size
                )
                
                self._write_cia_header(
                    cia, tmd_size, content_size, content_index,
                    self.config.dev_keys, chunk_records, content_count,
                    title_id, save_size
                )
                
                game_cxi_hash = self._write_game_cxi(
                    cia, rom, game_cxi_offset, game_cxi_size,
                    ncch_header, extheader, encrypted, key, ctr_extheader_v
                )
                
                chunk_records_list = list(chunk_records)
                chunk_records_list[0x10:0x30] = list(game_cxi_hash.digest())
                
                cr_offset = 0
                
                if manual_cfa_offset != 0:
                    manual_cfa_hash = self._write_partition(
                        cia, rom, manual_cfa_offset, manual_cfa_size, "Manual CFA", 0x3904
                    )
                    chunk_records_list[0x40:0x60] = list(manual_cfa_hash.digest())
                    cr_offset += 0x30
                
                if dlpchild_cfa_offset != 0:
                    dlpchild_cfa_hash = self._write_partition(
                        cia, rom, dlpchild_cfa_offset, dlpchild_cfa_size,
                        "Download Play child container CFA", 0x3904 + cr_offset
                    )
                    chunk_records_list[0x40 + cr_offset:0x60 + cr_offset] = list(
                        dlpchild_cfa_hash.digest()
                    )
                
                self._update_hashes(cia, bytes(chunk_records_list), content_count)
                
                cia.seek(0, 2)
                cia.write(
                    dependency_list + bytes(0x180) + struct.pack('<I', 0x2) +
                    bytes(0xFC) + exefs_icon
                )
            
            return True
        except Exception as e:
            self.print_error(f"Error writing CIA file: {e}")
            return False
    
    def _prepare_content_records(self, game_cxi_size: int,
                               manual_cfa_size: int,
                               dlpchild_cfa_size: int) -> Tuple[bytes, int]:
        chunk_records = struct.pack('>III', 0, 0, 0)
        chunk_records += struct.pack(">I", game_cxi_size)
        chunk_records += bytes(0x20)
        
        if manual_cfa_size > 0:
            chunk_records += struct.pack('>III', 1, 0x10000, 0)
            chunk_records += struct.pack('>I', manual_cfa_size)
            chunk_records += bytes(0x20)
        
        if dlpchild_cfa_size > 0:
            chunk_records += struct.pack('>III', 2, 0x20000, 0)
            chunk_records += struct.pack('>I', dlpchild_cfa_size)
            chunk_records += bytes(0x20)
        
        content_size = game_cxi_size + manual_cfa_size + dlpchild_cfa_size
        return chunk_records, content_size
    
    def _write_cia_header(self, cia: BinaryIO, tmd_size: int, content_size: int,
                         content_index: int, dev_keys: bool,
                         chunk_records: bytes, content_count: int,
                         title_id: bytes, save_size: bytes):
        self.print_verbose('Writing CIA header...')
        
        tmd_padding = bytes(12)
        if content_count > 1:
            tmd_padding += bytes((content_count - 1) * 16)
        
        certchain = CERT_CHAIN_RETAIL if not dev_keys else self.config.certchain_dev
        
        cia.write(
            struct.pack('<IHHII', 0x2020, 0, 0, 0xA00, 0x350) +
            struct.pack('<III', tmd_size, 0x3AC0, content_size) +
            struct.pack('<IB', 0, content_index) + (bytes(0x201F)) +
            certchain +
            TICKET_TMD +
            (bytes(0x96C)) +
            chunk_records + tmd_padding
        )
        
        cia.seek(0x2F9F)
        cia.write(bytes([content_count]))
        
        cia.seek(0x2C1C)
        cia.write(title_id)
        cia.seek(0x2F4C)
        cia.write(title_id)
        
        cia.seek(0x2F5A)
        cia.write(save_size)
    
    def _write_game_cxi(self, cia: BinaryIO, rom: BinaryIO,
                       game_cxi_offset: int, game_cxi_size: int,
                       ncch_header: bytes, extheader: bytes,
                       encrypted: bool, key: bytes, ctr_extheader_v: int):
        cia.seek(0, 2)
        game_cxi_hash = hashlib.sha256()
        game_cxi_hash.update(ncch_header)
        game_cxi_hash.update(extheader)
        cia.write(ncch_header + extheader)
        
        self.print_verbose('Writing Game Executable CXI...')
        rom.seek(game_cxi_offset + 0x200 + 0x400)
        left = game_cxi_size - 0x200 - 0x400
        
        while left > 0:
            to_read = min(READ_SIZE, left)
            data = rom.read(to_read)
            game_cxi_hash.update(data)
            cia.write(data)
            left -= to_read
        
        self.print_verbose('Game Executable CXI SHA-256 hash:')
        self.print_verbose(f'  {game_cxi_hash.hexdigest()}')
        
        cia.seek(0x38D4)
        cia.write(game_cxi_hash.digest())
        
        return game_cxi_hash
    
    def _write_partition(self, cia: BinaryIO, rom: BinaryIO,
                        offset: int, size: int,
                        desc: str, hash_position: int):
        cia.seek(0, 2)
        self.print_verbose(f'Writing {desc}...')
        
        partition_hash = hashlib.sha256()
        rom.seek(offset)
        left = size
        
        while left > 0:
            to_read = min(READ_SIZE, left)
            data = rom.read(to_read)
            partition_hash.update(data)
            cia.write(data)
            left -= to_read
        
        self.print_verbose(f'{desc} SHA-256 hash:')
        self.print_verbose(f'  {partition_hash.hexdigest()}')
        
        cia.seek(hash_position)
        cia.write(partition_hash.digest())
        
        return partition_hash
    
    def _update_hashes(self, cia: BinaryIO, chunk_records: bytes, content_count: int):
        self.print_verbose('\nUpdating hashes...')
        
        chunk_records_hash = hashlib.sha256(chunk_records)
        self.print_verbose('Content chunk records SHA-256 hash:')
        self.print_verbose(f'  {chunk_records_hash.hexdigest().upper()}')
        
        cia.seek(0x2FC7)
        cia.write(bytes([content_count]) + chunk_records_hash.digest())
        
        cia.seek(0x2FA4)
        info_records_hash = hashlib.sha256(
            bytes(3) + bytes([content_count]) +
            chunk_records_hash.digest() + (bytes(0x8DC))
        )
        
        self.print_verbose('Content info records SHA-256 hash:')
        self.print_verbose(f'  {info_records_hash.hexdigest().upper()}')
        
        cia.write(info_records_hash.digest())


def process_wrapper(args):
    input_file, rom_name, cia_name, config_dict = args
    
    config = Config()
    config.__dict__.update(config_dict)
    
    converter = CCIConverter(config)
    return converter.process_file((input_file, rom_name, cia_name))


class FileSelectorCLI:
    
    @staticmethod
    def select_files_cli() -> List[str]:
        print()
        print(f"{Colors.PURPLE}.3ds file selector/converter (NENO756'S fork){Colors.END}")
        print()
        print("Please select files to convert:")
        print()
        print(f"{Colors.BLUE}1. Enter file paths manually{Colors.END}")
        print(f"{Colors.BLUE}2. Search for 3DS/CCI files in current directory{Colors.END}")
        print(f"{Colors.BLUE}3. Exit{Colors.END}")
        print()
        
        while True:
            try:
                choice = input("Enter your choice (1-3): ").strip()
                
                if choice == '1':
                    return FileSelectorCLI.select_files_manual()
                elif choice == '2':
                    return FileSelectorCLI.search_files_current_dir()
                elif choice == '3':
                    return []
                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                return []
            except EOFError:
                print("\nEnd of input.")
                return []
    
    @staticmethod
    def select_files_manual() -> List[str]:
        files = []
        print()
        print("Manual File Entry")
        print("Enter file paths (one per line). Press Enter twice or 'done' to finish.")
        
        while True:
            try:
                file_path = input("Enter file path: ").strip()
                
                if not file_path or file_path.lower() == 'done':
                    return files if files else []
                else:
                    expanded = glob.glob(file_path)
                    for f in expanded:
                        if os.path.isfile(f):
                            if f not in files:
                                files.append(f)
                                print(f"Added: {f}")
                            else:
                                print(f"Skipped duplicate: {f}")
                        else:
                            print(f"Not found: {f}")
            except KeyboardInterrupt:
                return []
            except EOFError:
                break
        return files
    
    @staticmethod
    def search_files_current_dir() -> List[str]:
        print()
        print("Searching for 3DS/CCI files in current directory...")
        
        files = []
        for ext in DEFAULT_FILE_EXTENSIONS:
            files.extend(glob.glob(f"*{ext}"))
            files.extend(glob.glob(f"*{ext.upper()}"))
        
        if not files:
            print("No files found.")
            return []
        
        files = sorted(list(set(files)))
        
        print(f"Found {len(files)} file(s):")
        for i, f in enumerate(files, 1):
            size_mb = os.path.getsize(f) / (1024 * 1024)
            print(f"  {i:2d}. {Colors.BOLD}{f}{Colors.END} ({size_mb:.2f} MB)")
        
        return FileSelectorCLI.select_from_list(files)
    
    @staticmethod
    def select_from_list(files: List[str]) -> List[str]:
        print()
        print(f"{Colors.GREEN}Select files to convert:{Colors.END}")
        print(f"  - Numbers separated by spaces (e.g., '1 3 5')")
        print(f"  - 'all' to select all, 'none' for none, 'back' to menu")
        print()
        
        try:
            selection = input("Enter selection: ").strip().lower()
            
            if selection == 'back': return []
            if selection == 'all': return files
            if selection == 'none': return []
            
            selected_files = []
            for num_str in selection.split():
                try:
                    num = int(num_str)
                    if 1 <= num <= len(files):
                        selected_files.append(files[num-1])
                except ValueError:
                    pass
            
            return selected_files
        except (KeyboardInterrupt, EOFError):
            return []

def print_help():
    print(f'''3dsconv.py ~ version {VERSION}
Convert Nintendo 3DS CCI (.3ds/.cci) to CIA

USAGE:
  python 3dsconv.py [options] <game.3ds> [<game2.3ds>...]
  python 3dsconv.py  # Interactive mode

OPTIONS:
  --output=<dir>       - Save converted files in specified directory
  --boot9=<file>       - Path to dump of ARM9 bootROM
  --overwrite          - Overwrite existing converted files
  --ignore-bad-hashes  - Ignore invalid hashes and convert anyway
  --verbose            - Print more information (slightly slower)
  --dev-keys           - Use developer-unit keys
''')


def parse_arguments() -> Config:
    config = Config()
    
    if len(sys.argv) == 1:
        print_help()
        print("\nNo files specified. Opening file selector...")
        files = FileSelectorCLI.select_files_cli()
        
        for f in files:
            rom_name = os.path.basename(os.path.splitext(f)[0])
            cia_name = os.path.join(config.output_directory, rom_name + '.cia')
            config.files.append((f, rom_name, cia_name))
        return config
    
    if '--help' in sys.argv or '-h' in sys.argv:
        print_help()
        sys.exit(0)
    
    config.verbose = '--verbose' in sys.argv
    config.overwrite = '--overwrite' in sys.argv
    config.ignore_bad_hashes = '--ignore-bad-hashes' in sys.argv
    config.dev_keys = '--dev-keys' in sys.argv
    
    for arg in sys.argv[1:]:
        if arg.startswith('--'):
            if arg.startswith('--output='): config.output_directory = arg[9:]
            elif arg.startswith('--boot9='): config.boot9_path = arg[8:]
        else:
            expanded = glob.glob(arg)
            for f in expanded:
                rom_name = os.path.basename(os.path.splitext(f)[0])
                cia_name = os.path.join(config.output_directory, rom_name + '.cia')
                
                if not config.overwrite and os.path.isfile(cia_name):
                    print(f'Skipping (exists): {cia_name}')
                else:
                    config.files.append((f, rom_name, cia_name))
    
    return config

def setup_environment(config: Config):
    print(f'3dsconv.py ~ version {VERSION}')
    
    if CRYPTO_BACKEND:
        print(f'Using backend: {CRYPTO_BACKEND} (Fast)')
    else:
        print('Warning: No encryption library found. Encrypted ROMs will not work.')
    
    encryption_handler = EncryptionHandler(config)
    
    if CRYPTO_BACKEND:
        if not encryption_handler.find_boot9():
            print('Note: boot9.bin not found, using built-in keys (Decrypted ROMs only)')
    else:
        print('Using built-in keys (Decrypted ROMs only)')

    if config.dev_keys:
        print('Warning: Using developer keys.')
    
    if config.output_directory:
        os.makedirs(config.output_directory, exist_ok=True)

def main():
    config = parse_arguments()
    
    if not config.files:
        print('No files selected. Exiting.')
        sys.exit(0)
    
    setup_environment(config)
    
    work_items = []
    for (input_file, rom_name, cia_name) in config.files:
        work_items.append((input_file, rom_name, cia_name, config.__dict__))
    
    print(f"\nStarting conversion of {len(config.files)} file(s) using parallel processing...")
    
    processed_count = 0
    
    max_workers = min(os.cpu_count() or 4, len(config.files))
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(process_wrapper, item): item[1] 
            for item in work_items
        }
        
        for future in as_completed(future_to_file):
            rom_name = future_to_file[future]
            try:
                success, message = future.result()
                if success:
                    processed_count += 1
                    print(f"{Colors.GREEN}[DONE]{Colors.END} {message}")
                else:
                    print(f"{Colors.RED}[FAIL]{Colors.END} {message}")
            except Exception as e:
                print(f"{Colors.RED}[ERROR]{Colors.END} Exception for {rom_name}: {e}")
    
    print()
    print(f"CONVERSION COMPLETE: {processed_count} out of {len(config.files)} files converted successfully.")

if __name__ == "__main__":
    main()
