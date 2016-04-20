#!/usr/bin/env python2
import sys, os, binascii, math, subprocess, errno, hashlib, itertools

# default directories (relative to current dir unless you use absolute paths)
# leave as "" for current working directory
# using --xorpads= or --output= will override these
xorpad_directory = ""
output_directory = ""

#################
version = "2.1"

helptext = """3dsconv.py ~ version %s
https://github.com/ihaveamac/3dsconv

usage: 3dsconv.py [options] game.3ds [game.3ds ...]
  --xorpads=<dir>  - use xorpads in the specified directory
                     default is %s
  --output=<dir>   - save converted CIA files in the specified directory
                     default is %s
  --overwrite      - overwrite any existing converted CIA, if it exists
  --gen-ncchinfo   - generate ncchinfo.bin for roms that don't have a valid xorpad
  --gen-ncch-all   - use with --gen-ncchinfo to generate an ncchinfo.bin for all roms
  --noconvert      - don't convert roms
                     useful if you just want to generate ncchinfo.bin
  --force          - run even if make_cia isn't found
  --nocleanup      - don't remove temporary files once finished
  --verbose        - print more information

- make_cia should exist in your PATH
- if a rom is encrypted, an ExHeader XORpad
  should exist in the working directory
  named \"<TITLEID>.Main.exheader.xorpad\"
  or in the directory specified by --xorpads=<dir>
- encrypted and decrypted roms can be converted at the same time"""

mu = 0x200 # media unit
readsize = 8*1024*1024 # used from padxorer

cleanup = not "--nocleanup" in sys.argv
verbose = "--verbose" in sys.argv
overwrite = "--overwrite" in sys.argv
genncchinfo = "--gen-ncchinfo" in sys.argv
genncchall = "--gen-ncch-all" in sys.argv
noconvert = "--noconvert" in sys.argv

def print_v(msg):
	if verbose:
		print(msg)

def testcommand(cmd):
	print_v("- testing: %s" % cmd)
	try:
		proc = subprocess.Popen([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		proc.stdout.close()
		proc.stderr.close()
		proc.wait()
		return True
	except OSError as e:
		if e.errno != 2:
			raise
		return False
def runcommand(cmdargs):
	print_v("$ %s" % " ".join(cmdargs))
	proc = subprocess.Popen(cmdargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	proc.wait()
	procoutput = proc.communicate()[0]
	print_v(procoutput)
	if proc.returncode != 0:
		print("! %s had an error." % cmdargs[0])
		# prevent printing twice
		if not verbose:
			print("- full command: %s" % " ".join(cmdargs))
			print("- output:")
			print(procoutput)

# used from http://stackoverflow.com/questions/10840533/most-pythonic-way-to-delete-a-file-which-may-not-exist
def silentremove(filename):
	try:
		os.remove(filename)
	except OSError as e: # this would be "except OSError, e:" before Python 2.6
		if e.errno != errno.ENOENT: # errno.ENOENT = no such file or directory
			raise # re-raise exception if a different error occured
def docleanup(tid):
	silentremove("work/%s-game-orig.cxi" % tid)
	silentremove("work/%s-game-conv.cxi" % tid)
	silentremove("work/%s-manual.cfa" % tid)
	silentremove("work/%s-dlpchild.cfa" % tid)
	# silentremove("work/%s-ncchheader.bin" % tid)
	# silentremove("work/%s-exheader.bin" % tid)
	# silentremove("work/%s-exefs.bin" % tid)
	# silentremove("work/%s-romfs.bin" % tid)
	# silentremove("work/%s-logo.bcma.lz" % tid)
	# silentremove("work/%s-plain.bin" % tid)

if len(sys.argv) < 2:
	print(helptext % (version, ("current directory" if xorpad_directory == "" else "'%s'" % xorpad_directory), ("current directory" if output_directory == "" else "'%s'" % output_directory)))
	sys.exit(1)

if not "--force" in sys.argv:
	fail = False
	if not testcommand("make_cia"):
		print("! make_cia doesn't appear to be in your PATH.")
		print("  you can get it from here:")
		print("  https://github.com/ihaveamac/ctr_toolkit")
		fail = True
	if fail:
		print("- if you want to force the script to run,")
		print("  add --force as one of the arguments.")
		sys.exit(1)

try:
	os.makedirs("work")
except OSError:
	if not os.path.isdir("work"):
		raise

# probably should've used argparse
for arg in sys.argv[1:]:
	if arg[:2] != "--":
		continue
	if arg[:10] == "--xorpads=":
		xorpad_directory = arg[10:]
	if arg[:9] == "--output=":
		output_directory = arg[9:]

if output_directory!= "":
	try:
		os.makedirs(output_directory)
	except OSError:
		if not os.path.isdir(output_directory):
			raise

ncchinfolist = []
# this only does ExHeader stuff
# so I think I can get away with hard-coding some things
def ncchinfoadd(rom):
	romf = open(rom, "rb")
	romf.seek(0x108)
	tid = romf.read(8)
	romf.seek(0x4000)
	keyY = romf.read(16)
	ncchinfolist.extend([tid[::-1] + "\x01\x00\x00\x00\x00\x00\x00\x00" + keyY + "\x01\x00\x00\x00" + "\x00\x00\x00\x00" + "\x00\x00\x00\x00" + "\x00\x00\x00\x00" + tid + ("/%s.Main.exheader.xorpad" % binascii.hexlify(tid[::-1]).upper()).ljust(112, "\x00")])
	romf.close()

# used from http://stackoverflow.com/questions/4566498/python-file-iterator-over-a-binary-file-with-newer-idiom
#def read_in_chunks(infile, chunk_size=buffersize):
#	chunk = infile.read(chunk_size)
#	while chunk:
#		yield chunk
#		chunk = infile.read(chunk_size)

# used from http://www.gossamer-threads.com/lists/python/python/163938
def bytes2int(string):
	i = 0
	for ch in string:
		i = 256*i + ord(ch)
	return i

totalroms = 0
processedroms = 0

for rom in sys.argv[1:]:
	if rom[:2] == "--":
		continue
	totalroms += 1
	if not os.path.isfile(rom):
		print("! %s doesn't exist." % rom)
		continue
	romname = os.path.basename(os.path.splitext(rom)[0])
	cianame = os.path.join(output_directory, romname+".cia")
	if not overwrite and os.path.isfile(cianame):
		print("! %s already exists." % cianame)
		print("  to force conversion and overwriting this, use --overwrite")
		continue
	if genncchinfo and genncchall:
		ncchinfoadd(rom)
	romf = open(rom, "rb")
	romf.seek(0x100)
	ncsdmagic = romf.read(4)
	romf.seek(0x108)
	tid = binascii.hexlify(romf.read(8)[::-1])
	xorpad = os.path.join(xorpad_directory, "%s.Main.exheader.xorpad" % tid.upper())
	romf.seek(0x418F)
	decrypted = int(binascii.hexlify(romf.read(1))) & 0x04
	if ncsdmagic != "NCSD":
		print("! %s is probably not a rom." % rom)
		print("  NCSD magic not found.")
		romf.close()
		continue
	if noconvert:
		print("- not converting %s (%s) because --noconvert was used" % (romname, "decrypted" if decrypted else "encrypted"))
		if cleanup:
			docleanup(tid)
		romf.close()
		continue
	if not decrypted:
		if not os.path.isfile(xorpad):
			print("! %s couldn't be found." % xorpad)
			if not genncchinfo:
				print("  use --gen-ncchinfo with this rom.")
			ncchinfoadd(rom)
			romf.close()
			continue

	docleanup(tid)

	print_v("- verifying ExHeader")
	romf.seek(0x4200)
	exh = romf.read(0x400)
	xor = ""
	if not decrypted:
		print_v("- decrypting ExHeader")
		xorfile = open(xorpad, "rb")
		xor = xorfile.read(0x400)
		xorfile.close()
		xored = ""
		for byte_f, byte_x in zip(exh, xor):
			xored += chr(ord(byte_f) ^ ord(byte_x))
		exh = xored
	exh_hash = hashlib.sha256(exh).digest()
	romf.seek(0x4160)
	ncch_exh_hash = romf.read(0x20)
	if exh_hash != ncch_exh_hash:
		if decrypted:
			print("! this rom might be corrupt.")
		else:
			print("! %s is not the correct xorpad, or is corrupt." % xorpad)
			if not genncchinfo:
				print("  try using --gen-ncchinfo again or find the correct xorpad.")
			ncchinfoadd(rom)
		print("  ExHeader SHA-256 hash check failed.")
		exh.close()
		if cleanup:
			docleanup(tid)
		continue

	print("- processing: %s (%s)" % (romname, "decrypted" if decrypted else "encrypted"))

	#runcommand(["3dstool", "-xvtf", "cxi", "work/%s-game-orig.cxi" % tid, "--exefs", "work/%s-exefs.bin" % tid, "--romfs", "work/%s-romfs.bin" % tid, "--plain", "work/%s-plain.bin" % tid, "--logo", "work/%s-logo.bcma.lz" % tid])

	print_v("- patching ExHeader")
	exh_list = list(exh)
	x = exh_list[0xD]
	y = ord(x)
	z = y | 2
	print_v("  offset 0xD of ExHeader:")
	print_v("  original: %s" % hex(y))
	print_v("  shifted:  %s" % hex(z))
	z = chr(z)
	exh_list[0xD:0xE] = z
	exh = "".join(exh_list)
	# there really has to be a better way to do this...
	savesize = str(int(binascii.hexlify(exh[0x1C0:0x1C8][::-1]), 16) / 1024)

	new_exh_hash = hashlib.sha256(exh).hexdigest()
	romf.seek(0x124)
	gamecxi_size = bytes2int(romf.read(0x4)[::-1]) * mu
	gamecxi = open("work/%s-game-conv.cxi" % tid, "wb")
	left = gamecxi_size

	# Game Executable CXI
	romf.seek(0x4000)
	print_v("- extracting Game Executable CXI")
	for _ in itertools.repeat(0, int(math.floor((gamecxi_size / readsize)) + 1)):
		toread = min(readsize, left)
		gamecxi.write(romf.read(toread))
		left -= readsize
		if left <= 0:
			break

	# Manual CFA
	romf.seek(0x128)
	manualcfa_offset = bytes2int(romf.read(0x4)[::-1]) * mu
	if manualcfa_offset != 0:
		romf.seek(0x12C)
		print_v("- extracting Manual CFA")
		manualcfa_size = bytes2int(romf.read(0x4)[::-1]) * mu
		romf.seek(manualcfa_offset)
		manualcfa = open("work/%s-manual.cfa" % tid, "wb")
		left = manualcfa_size
		for _ in itertools.repeat(0, int(math.floor((manualcfa_size / readsize)) + 1)):
			toread = min(readsize, left)
			manualcfa.write(romf.read(toread))
			left -= readsize
			if left <= 0:
				break

	# Download Play child container CFA
	romf.seek(0x130)
	dlpchildcfa_offset = bytes2int(romf.read(0x4)[::-1]) * mu
	if dlpchildcfa_offset != 0:
		romf.seek(0x134)
		print_v("- extracting Download Play child container CFA")
		dlpchildcfa_size = bytes2int(romf.read(0x4)[::-1]) * mu
		romf.seek(dlpchildcfa_offset)
		dlpchildcfa = open("work/%s-dlpchild.cfa" % tid, "wb")
		left = dlpchildcfa_size
		for _ in itertools.repeat(0, int(math.floor((dlpchildcfa_size / readsize)) + 1)):
			toread = min(readsize, left)
			dlpchildcfa.write(romf.read(toread))
			left -= readsize
			if left <= 0:
				break
	romf.close()

	gamecxi.seek(0x160)
	gamecxi.write(hashlib.sha256(exh).digest())
	# re-encrypt exheader and write the byte at 0x20D
	gamecxi.seek(0x20D)
	if decrypted:
		gamecxi.write(exh[0xD:0xE])
	else:
		gamecxi.write(chr(ord(exh[0xD:0xE]) ^ ord(xor[0xD:0xE])))
	gamecxi.close()

	print_v("- building CIA")
	os.chdir("work") # not doing this breaks make_cia's ability to properly include Manual/DLP Child for some reason
	cmds = ["make_cia", "-o", "%s-game-conv.cia" % tid, "--savesize=%s" % savesize, "--content0=%s-game-conv.cxi" % tid, "--id_0=0", "--index_0=0"]
	if manualcfa_offset != 0:
		cmds.extend(["--content1=%s-manual.cfa" % tid, "--index_1=1"])
	if dlpchildcfa_offset != 0:
		cmds.extend(["--content2=%s-dlpchild.cfa" % tid, "--index_2=2"])
	runcommand(cmds)
	os.chdir("..")

	# apparently if the file exists, it will throw an error on Windows
	silentremove(cianame)
	os.rename("work/%s-game-conv.cia" % tid, cianame)
	if cleanup:
		docleanup(tid)

	processedroms += 1

if totalroms == 0:
	print(helptext % (version, ("current directory" if xorpad_directory == "" else "'%s'" % xorpad_directory), ("current directory" if output_directory == "" else "'%s'" % output_directory)))
	sys.exit(1)
else:
	print("* done converting!")
	print("  %i out of %i roms processed" % (processedroms, totalroms))
	if genncchinfo and len(ncchinfolist) != 0:
		print("- saving ncchinfo.bin")
		ncchinfo = open("ncchinfo.bin", "wb")
		ncchinfo.write("\xFF\xFF\xFF\xFF\x04\x00\x00\xF0")
		# this is bad, I know
		ncchinfo.write(binascii.unhexlify(format(len(ncchinfolist), 'x').rjust(8, '0'))[::-1])
		ncchinfo.write("\x00\x00\x00\x00")
		for i in ncchinfolist:
			ncchinfo.write(i)
		ncchinfo.close()
		print("- use Decrypt9 on a 3DS system to generate the xorpads.")
		print("  place the file at the root or in a folder called \"Decrypt9\".")
		print("  view the Decrypt9 README and download releases at")
		print("  https://github.com/d0k3/Decrypt9WIP")