#!/usr/bin/env python2
import sys, os, binascii, math, subprocess, errno, hashlib

# default directories (relative to current dir unless you use absolute paths)
# leave as "" for current working directory
# using --xorpads= or --output= will override these
xorpad_directory = ""
output_directory = ""

#################
version = "2.02d"

helptext = """3dsconv.py ~ version %s
https://github.com/ihaveamac/3dsconv

usage: 3dsconv.py [options] game.3ds [game.cci ...]
  --xorpads=<dir>  - use xorpads in the specified directory
                     default is %s
  --output=<dir>   - save converted CIA files in the specified directory
                     default is %s
  --overwrite      - overwrite any existing converted CIA, if it exists
  --force          - run even if 3dstool/makerom aren't found
  --nocleanup      - don't remove temporary files once finished
  --verbose        - print more information

- 3dstool and make_cia should exist in your PATH
- if a rom is encrypted, an ExHeader XORpad
  should exist in the working directory
  named \"<TITLEID>.Main.exheader.xorpad\"
  or in the directory specified by --xorpads=<dir>
- encrypted and decrypted roms can be converted at the same time"""

cleanup = not "--nocleanup" in sys.argv
verbose = "--verbose" in sys.argv
overwrite = "--overwrite" in sys.argv

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
	silentremove("work/%s-ncchheader.bin" % tid)
	silentremove("work/%s-exheader.bin" % tid)
	silentremove("work/%s-exefs.bin" % tid)
	silentremove("work/%s-romfs.bin" % tid)
	silentremove("work/%s-logo.bcma.lz" % tid)
	silentremove("work/%s-plain.bin" % tid)

if len(sys.argv) < 2:
	print(helptext % (version, ("current directory" if xorpad_directory == "" else "'%s'" % xorpad_directory), ("current directory" if output_directory == "" else "'%s'" % output_directory)))
	sys.exit(1)

if not "--force" in sys.argv:
	fail = False
	if not testcommand("3dstool"):
		print("! 3dstool doesn't appear to be in your PATH.")
		print("  you can get it from here:")
		print("  https://github.com/dnasdw/3dstool")
		fail = True
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
	romf = open(rom, "rb")
	romf.seek(0x100)
	ncsdmagic = romf.read(4)
	romf.seek(0x190)
	tid = binascii.hexlify(romf.read(8)[::-1])
	xorpad = os.path.join(xorpad_directory, "%s.Main.exheader.xorpad" % tid.upper())
	romf.seek(0x418F)
	decrypted = int(binascii.hexlify(romf.read(1))) & 0x04
	romf.close()
	print("- processing: %s (%s)" % (romname, "decrypted" if decrypted else "encrypted"))
	if ncsdmagic != "NCSD":
		print("! %s is probably not a rom." % rom)
		print("  NCSD magic not found.")
		continue
	if not decrypted:
		if not os.path.isfile(xorpad):
			print("! %s couldn't be found." % xorpad)
			print("  use ncchinfo_gen_exheader.py with this rom.")
			continue

	docleanup(tid)

	print_v("- extracting rom")
	runcommand(["3dstool", "-xvt012f", "cci", "work/%s-game-orig.cxi" % tid, "work/%s-manual.cfa" % tid, "work/%s-dlpchild.cfa" % tid, rom])
	cmds = ["3dstool", "-xvtf", "cxi", "work/%s-game-orig.cxi" % tid, "--header", "work/%s-ncchheader.bin" % tid, "--exh", "work/%s-exheader.bin" % tid]
	if not decrypted:
		cmds.extend(["--exh-xor", xorpad])
	runcommand(cmds)

	print_v("- verifying ExHeader SHA-256 hash")
	exh = open("work/%s-exheader.bin" % tid, "r+b")
	ncch = open("work/%s-game-orig.cxi" % tid, "rb")
	# verify the exheader extracted properly
	exh_hash = hashlib.sha256(exh.read(0x400)).hexdigest()
	ncch.seek(0x160)
	ncch_exh_hash = binascii.hexlify(ncch.read(0x20))
	ncch.close()
	if exh_hash != ncch_exh_hash:
		if decrypted:
			print("! this rom might be corrupt.")
		else:
			print("! %s is not the correct xorpad, or is corrupt." % xorpad)
			print("  try using ncchinfo_gen_exheader.py again or find the correct xorpad.")
		print("  ExHeader SHA-256 hash check failed.")
		exh.close()
		if cleanup:
			docleanup(tid)
		continue

	runcommand(["3dstool", "-xvtf", "cxi", "work/%s-game-orig.cxi" % tid, "--exefs", "work/%s-exefs.bin" % tid, "--romfs", "work/%s-romfs.bin" % tid, "--plain", "work/%s-plain.bin" % tid, "--logo", "work/%s-logo.bcma.lz" % tid])

	print_v("- patching ExHeader")
	exh.seek(0xD)
	x = exh.read(1)
	y = ord(x)
	z = y | 2
	print_v("  offset 0xD of ExHeader:")
	print_v("  original: "+hex(y))
	print_v("  shifted:  "+hex(z))
	exh.seek(0xD)
	exh.write(chr(z))
	exh.seek(0x1C0)
	# there has to be a better way to do this...
	savesize = str(int(binascii.hexlify(exh.read(4)[::-1]), 16) / 1024)
	# actually 8 bytes but the TMD only has 4 bytes
	#print(binascii.hexlify(savesize[::-1]))
	exh.close()

	print_v("- rebuilding CXI")
	# CXI
	cmds = ["3dstool", "-cvtf", "cxi", "work/%s-game-conv.cxi" % tid, "--header", "work/%s-ncchheader.bin" % tid, "--exh", "work/%s-exheader.bin" % tid, "--exefs", "work/%s-exefs.bin" % tid, "--not-update-exefs-hash", "--romfs", "work/%s-romfs.bin" % tid, "--not-update-romfs-hash", "--plain", "work/%s-plain.bin" % tid]
	if not decrypted:
		cmds.extend(["--exh-xor", xorpad])
	if os.path.isfile("work/%s-logo.bcma.lz" % tid):
		cmds.extend(["--logo", "work/%s-logo.bcma.lz" % tid])
	runcommand(cmds)
	print_v("- building CIA")
	# CIA
	os.chdir("work") # not doing this breaks make_cia's ability to properly include Manual/DLP Child for some reason
	cmds = ["make_cia", "-o", "%s-game-conv.cia" % tid, "--savesize=%s" % savesize, "--content0=%s-game-conv.cxi" % tid, "--id_0=0", "--index_0=0"]
	if os.path.isfile("%s-manual.cfa" % tid):
		cmds.extend(["--content1=%s-manual.cfa" % tid, "--id_1=1", "--index_1=1"])
	if os.path.isfile("%s-dlpchild.cfa" % tid):
		cmds.extend(["--content2=%s-dlpchild.cfa" % tid, "--id_2=2", "--index_2=2"])
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
else:
	print("* done converting!")
	print("  %i out of %i roms processed" % (processedroms, totalroms))
sys.exit()