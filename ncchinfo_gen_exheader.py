#!/usr/bin/env python2
# originally based on
# https://github.com/d0k3/Decrypt9WIP/blob/master/scripts/ncchinfo_gen.py

#####
#ncchinfo.bin format
#
#4 bytes = 0xFFFFFFFF Meant to prevent previous versions of padgen from using these new files
#4 bytes   ncchinfo.bin version or'd with 0xF0000000, to prevent previous versions of padgen from using these new files
#4 bytes   Number of entries
#4 bytes   Reserved
#
#entry (168 bytes in size):
#  16 bytes   Counter
#  16 bytes   KeyY
#   4 bytes   Size in MB(rounded up)
#   4 bytes   Reserved
#   4 bytes   Uses 9x SeedCrypto (0 or 1)
#   4 bytes   Uses 7x crypto? (0 or 1)
#   8 bytes   Title ID
# 112 bytes   Output file name in UTF-8 (format used: "/titleId.partitionName.sectionName.xorpad")
#####

import os
import sys
import glob
import struct
from ctypes import *
from binascii import hexlify

mediaUnitSize = 0x200

class ncchHdr(Structure):
	_fields_ = [
		('signature', c_uint8 * 0x100),
		('magic', c_char * 4),
		('ncchSize', c_uint32),
		('titleId', c_uint8 * 0x8),
		('makerCode', c_uint16),
		('formatVersion', c_uint8),
		('formatVersion2', c_uint8),
		('padding0', c_uint32),
		('programId', c_uint8 * 0x8),
		('padding1', c_uint8 * 0x10),
		('logoHash', c_uint8 * 0x20),
		('productCode', c_uint8 * 0x10),
		('exhdrHash', c_uint8 * 0x20),
		('exhdrSize', c_uint32),
		('padding2', c_uint32),
		('flags', c_uint8 * 0x8),
		('plainRegionOffset', c_uint32),
		('plainRegionSize', c_uint32),
		('logoOffset', c_uint32),
		('logoSize', c_uint32),
		('exefsOffset', c_uint32),
		('exefsSize', c_uint32),
		('exefsHashSize', c_uint32),
		('padding4', c_uint32),
		('romfsOffset', c_uint32),
		('romfsSize', c_uint32),
		('romfsHashSize', c_uint32),
		('padding5', c_uint32),
		('exefsHash', c_uint8 * 0x20),
		('romfsHash', c_uint8 * 0x20),
	]

class ncchSection:
	exheader = 1
	exefs = 2
	romfs = 3

class ncch_offsetsize(Structure):
	_fields_ = [
		('offset', c_uint32),
		('size', c_uint32),
	]

class ncsdHdr(Structure):
	_fields_ = [
		('signature', c_uint8 * 0x100),
		('magic', c_char * 4),
		('mediaSize', c_uint32),
		('titleId', c_uint8 * 0x8),
		('padding0', c_uint8 * 0x10),
		('offset_sizeTable', ncch_offsetsize * 0x8),
		('padding1', c_uint8 * 0x28),
		('flags', c_uint8 * 0x8),
		('ncchIdTable', c_uint8 * 0x40),
		('padding2', c_uint8 * 0x30),
	]

ncsdPartitions = [b'Main', b'Manual', b'DownloadPlay', b'Partition3', b'Partition4', b'Partition5', b'N3DSUpdateData', b'O3DSUpdateData']

def roundUp(numToRound, multiple):  #From http://stackoverflow.com/a/3407254
	if (multiple == 0):
		return numToRound

	remainder = abs(numToRound) % multiple
	if (remainder == 0):
		return numToRound
	if (numToRound < 0):
		return -(abs(numToRound) - remainder)
	return numToRound + multiple - remainder

def reverseCtypeArray(ctypeArray): #Reverses a ctype array and converts it to a hex string.
	return ''.join('%02X' % x for x in ctypeArray[::-1])
	#Is there a better way to do this?

def getNcchAesCounter(header, type): #Function based on code from ctrtool's source: https://github.com/Relys/Project_CTR
	counter = bytearray(b'\x00' * 16)
	if header.formatVersion == 2 or header.formatVersion == 0:
		counter[:8] = bytearray(header.titleId[::-1])
		counter[8:9] = chr(type)
	elif header.formatVersion == 1:
		x = 0
		if type == ncchSection.exheader:
			x = 0x200 #ExHeader is always 0x200 bytes into the NCCH
		if type == ncchSection.exefs:
			x = header.exefsOffset * mediaUnitSize
		if type == ncchSection.romfs:
			x = header.romfsOffset * mediaUnitSize
		counter[:8] = bytearray(header.titleId)
		for i in xrange(4):
			counter[12+i] = chr((x>>((3-i)*8)) & 0xFF)

	return bytes(counter)


def parseNCSD(fh):
	print 'Parsing NCSD in file "%s":' % os.path.basename(fh.name)
	entries = 0
	data = ''

	fh.seek(0)
	header = ncsdHdr()
	fh.readinto(header) #Reads header into structure

	for i in xrange(len(header.offset_sizeTable)):
		if header.offset_sizeTable[i].offset:
			result = parseNCCH(fh, header.offset_sizeTable[i].offset * mediaUnitSize, i, reverseCtypeArray(header.titleId), 0)
			entries += result[0]
			data = data + result[1]
	return [entries, data]

def parseNCCH(fh, offs=0, idx=0, titleId='', standAlone=1):
	tab = '    ' if not standAlone else '  '
	if not standAlone:
		print '  Parsing %s NCCH' % ncsdPartitions[idx]
	else:
		print 'Parsing NCCH in file "%s":' % os.path.basename(fh.name)
	entries = 0
	data = ''

	fh.seek(offs)
	header = ncchHdr()
	fh.readinto(header) #Reads header into structure

	if titleId == '':
		titleId = reverseCtypeArray(header.titleId)

	keyY = bytearray(header.signature[:16])

	if not standAlone:
		print tab + 'NCCH Offset: %08X' % offs
	print tab + 'Product code: ' + str(bytearray(header.productCode)).rstrip('\x00')
	if not standAlone:
		print tab + 'Partition number: %d' % idx
	print tab + 'KeyY: %s' % hexlify(keyY).upper()
	print tab + 'Title ID: %s' % reverseCtypeArray(header.titleId)
	print tab + 'Format version: %d' % header.formatVersion

	ncchFlag3 = bytearray(header.flags)[3]
	if ncchFlag3:
		print tab + 'Uses 7.x NCCH crypto'

	fixed_key_flag = 0
	ncchFlag7 = bytearray(header.flags)[7]
	if ncchFlag7 == 0x20:
		print tab + 'Uses 9.x SEED crypto'
	elif ncchFlag7 == 0x1:
		fixed_key_flag = ncchFlag7
		print tab + 'Uses fixed crypto key'
	elif ncchFlag7 == 0x4:
		ncchFlag7 = 0; # prevent issues with old NCCH padgen
		print tab + 'Uses no crypto'
	elif ncchFlag7 == 0x2:
		print tab + 'Uses no mount ROM fs (?)'
		ncchFlag7 = 0; # prevent issues with old NCCH padgen
	elif ncchFlag7 == 0:
		print tab + 'Standard crypto case'
	else:
		print tab + 'UNKNOWN FLAG DETECTED?'
		ncchFlag7 = 0; # prevent issues with old NCCH padgen

	print ''

	if header.exhdrSize:
		data = data + parseNCCHSection(header, ncchSection.exheader, 0, fixed_key_flag, 1, tab)
		data = data + genOutName(titleId, ncsdPartitions[idx], b'exheader')
		entries += 1
		print ''
	# if header.exefsSize: #We need generate two xorpads for exefs if it uses 7.x crypto, since only a part of it uses the new crypto.
	# 	data = data + parseNCCHSection(header, ncchSection.exefs, 0, fixed_key_flag, 1, tab)
	# 	data = data + genOutName(titleId, ncsdPartitions[idx], b'exefs_norm')
	# 	entries += 1
	# 	if ncchFlag3 or ncchFlag7 == 0x20: #only for SEED crypto || 7x crypto
	# 		data = data + parseNCCHSection(header, ncchSection.exefs, ncchFlag3, ncchFlag7, 0, tab)
	# 		data = data + genOutName(titleId, ncsdPartitions[idx], b'exefs_7x')
	# 		entries += 1
	# 	print ''
	# if header.romfsSize:
	# 	data = data + parseNCCHSection(header, ncchSection.romfs, ncchFlag3, ncchFlag7, 1, tab)
	# 	data = data + genOutName(titleId, ncsdPartitions[idx], b'romfs')
	# 	entries += 1
	# 	print ''

	print ''

	return [entries, data]

def parseNCCHSection(header, type, ncchFlag3, ncchFlag7, doPrint, tab):
	if type == ncchSection.exheader:
		sectionName = 'ExHeader'
		offset = 0x200 #Always 0x200
		sectionSize = header.exhdrSize * mediaUnitSize
	elif type == ncchSection.exefs:
		return
		# sectionName = 'ExeFS'
		# offset = header.exefsOffset * mediaUnitSize
		# sectionSize = header.exefsSize * mediaUnitSize
	elif type == ncchSection.romfs:
		return
		# sectionName = 'RomFS'
		# offset = header.romfsOffset * mediaUnitSize
		# sectionSize = header.romfsSize * mediaUnitSize
	else:
		print 'Invalid NCCH section type was somehow passed in. :/'
		sys.exit()

	counter = getNcchAesCounter(header, type)
	keyY = bytearray(header.signature[:16])
	titleId = struct.unpack('<Q',(bytearray(header.programId[:8])))[0]

	sectionMb = roundUp(sectionSize, 1024*1024) / (1024*1024)
	if sectionMb == 0:
		sectionMb = 1 #Should never happen, but meh.

	if doPrint:
		print tab + '%s offset:  %08X' % (sectionName, offset)
		print tab + '%s counter: %s' % (sectionName, hexlify(counter))
		print tab + '%s Megabytes(rounded up): %d' % (sectionName, sectionMb)

	return struct.pack('<16s16sIIIIQ', str(counter), str(keyY), sectionMb, 0, ncchFlag7, ncchFlag3, titleId)

def genOutName(titleId, partitionName, sectionName):
	outName = b'/%s.%s.%s.xorpad' % (titleId, partitionName, sectionName)
	if len(outName) > 112:
		print "Output file name too large. This shouldn't happen."
		sys.exit()

	return outName + (b'\x00'*(112-len(outName))) #Pad out so whole entry is 160 bytes (48 bytes are set before filename)

if __name__ == "__main__":
	if len(sys.argv) < 2:
		print 'usage: ncchinfo_gen_exheader.py files..'
		print '  Supports parsing both CCI(.3ds) and NCCH files.'
		print '  Wildcards are supported'
		print '  Example: ncchinfo_gen_exheader.py *.ncch SM3DL.3ds'
		sys.exit()

	inpFiles = []
	existFiles = []

	for i in xrange(len(sys.argv)-1):
		inpFiles = inpFiles + glob.glob(sys.argv[i+1].replace('[','[[]')) #Needed for wildcard support on Windows

	for i in xrange(len(inpFiles)):
		if os.path.isfile(inpFiles[i]):
			existFiles.append(inpFiles[i])

	if existFiles == []:
		print "Input files don't exist"
		sys.exit()

	print ''

	entries = 0
	data = ''

	for file in existFiles:
		result = []

		with open(file,'rb') as fh:
			fh.seek(0x100)
			magic = fh.read(4)
			if magic == b'NCSD':
				result = parseNCSD(fh)
				print ''
			elif magic == b'NCCH':
				result = parseNCCH(fh)
				print ''

		if result:
			entries += result[0]
			data = data + result[1]

	#dndFix = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), 'ncchinfo.bin') #Fix drag'n'drop
	dndFix = os.path.join(os.getcwd(), 'ncchinfo.bin')
	with open(dndFix, 'wb') as fh:
		fh.write(struct.pack('<IIII',0xFFFFFFFF, 0xF0000004, entries, 0))
		fh.write(data)

	print 'Done!'
