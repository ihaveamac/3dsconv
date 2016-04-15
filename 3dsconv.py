#!/usr/bin/env python2
import sys, os, binascii, math, subprocess, errno
version = "2.0"

def print_v(msg):
	if verbose:
		print(msg)

def testcommand(cmd):
	try:
		proc = subprocess.Popen([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE).wait()
		return True
	except OSError as e:
		if e.errno != 2:
			raise
		return False
def runcommand(cmdargs):
	print_v("$ %s" % " ".join(cmdargs))
	proc = subprocess.Popen(cmdargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	proc.wait()
	#print(proc.returncode)
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
	print("3dsconv.py ~ version %s" % version)
	print("https://github.com/ihaveamac/3dsconv")
	print("")
	print("usage: 3dsconv.py [options] game.3ds [game.cci ...]")
	print("  --xorpads=<dir>  - use xorpads in the specified directory")
	print("                     default is current directory")
	print("  --output=<dir>   - save converted CIA files in the specified directory")
	print("                     default is current directory")
	print("  --force          - run even if 3dstool/makerom aren't found")
	print("  --nocleanup      - don't remove temporary files once finished")
	print("  --verbose        - print more information")
	print("")
	print("- 3dstool and makerom should exist in your PATH")
	print("- if a rom is encrypted, an ExHeader XORpad")
	print("  should exist in the working directory")
	print("  named \"<TITLEID>.Main.exheader.xorpad\"")
	print("  or in the directory specified by --xorpads=<dir>")
	print("- encrypted and decrypted roms can be converted at the same time")
	sys.exit(1)

fail = False
if not testcommand("3dstool") and not "--force" in sys.argv:
	print("! 3dstool doesn't appear to be in your PATH.")
	print("  you can get it from here:")
	print("  https://github.com/dnasdw/3dstool")
	fail = True
if not testcommand("makerom") and not "--force" in sys.argv:
	print("! makerom doesn't appear to be in your PATH.")
	print("  you can get it from here:")
	print("  https://github.com/profi200/Project_CTR")
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

cleanup = not "--nocleanup" in sys.argv
verbose = "--verbose" in sys.argv

# probably should've used argparse
xorpaddir = ""
outputdir = ""
for arg in sys.argv[1:]:
	if arg[:2] != "--":
		continue
	if arg[:10] == "--xorpads=":
		xorpaddir = arg[10:]
	if arg[:9] == "--output=":
		outputdir = arg[9:]

if outputdir != "":
	try:
		os.makedirs(outputdir)
	except OSError:
		if not os.path.isdir(outputdir):
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
	romf = open(rom, "rb")
	romf.seek(0x100)
	ncsdmagic = romf.read(4)
	romf.seek(0x190)
	tid = binascii.hexlify(romf.read(8)[::-1])
	xorpad = os.path.join(xorpaddir, "%s.Main.exheader.xorpad" % tid.upper())
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

	print_v("- extracting")
	runcommand(["3dstool", "-xvt012f", "cci", "work/%s-game-orig.cxi" % tid, "work/%s-manual.cfa" % tid, "work/%s-dlpchild.cfa" % tid, rom])
	cmds0 = ["3dstool", "-xvtf", "cxi", "work/%s-game-orig.cxi" % tid, "--header", "work/%s-ncchheader.bin" % tid, "--exh", "work/%s-exheader.bin" % tid, "--exefs", "work/%s-exefs.bin" % tid, "--romfs", "work/%s-romfs.bin" % tid, "--plain", "work/%s-plain.bin" % tid, "--logo", "work/%s-logo.bcma.lz" % tid]
	if not decrypted:
		cmds0.extend(["--exh-xor", xorpad])
	runcommand(cmds0)

	print_v("- patching")
	exh = open("work/%s-exheader.bin" % tid, "r+b")
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
	savesize = exh.read(4)
	# actually 8 bytes but the TMD only has 4 bytes
	#print(binascii.hexlify(savesize[::-1]))
	exh.close()

	print_v("- rebuilding")
	# CXI
	cmds1 = ["3dstool", "-cvtf", "cxi", "work/%s-game-conv.cxi" % tid, "--header", "work/%s-ncchheader.bin" % tid, "--exh", "work/%s-exheader.bin" % tid, "--exefs", "work/%s-exefs.bin" % tid, "--not-update-exefs-hash", "--romfs", "work/%s-romfs.bin" % tid, "--not-update-romfs-hash", "--plain", "work/%s-plain.bin" % tid]
	if not decrypted:
		cmds1.extend(["--exh-xor", xorpad])
	if os.path.isfile("work/%s-logo.bcma.lz" % tid):
		cmds1.extend(["--logo", "work/%s-logo.bcma.lz" % tid])
	runcommand(cmds1)
	# CIA
	cmds2 = ["makerom", "-f", "cia", "-o", "work/%s-game-conv.cia" % tid, "-content", "work/%s-game-conv.cxi:0:0" % tid]
	if os.path.isfile("work/%s-manual.cfa" % tid):
		cmds2.extend(["-content", "work/%s-manual.cfa:1:1" % tid])
	if os.path.isfile("work/%s-dlpchild.cfa" % tid):
		cmds2.extend(["-content", "work/%s-dlpchild.cfa:2:2" % tid])
	runcommand(cmds2)

	# makerom doesn't accept custom SaveDataSize for some reason
	# but make_cia makes a bad CIA that doesn't support the Manual or DLP child

	# Archive Header Size
	cia = open("work/%s-game-conv.cia" % tid, "r+b")
	cia.seek(0x0)
	cia_h_ahs = binascii.hexlify(cia.read(0x4)[::-1])
	cia_h_ahs_align = int(math.ceil(int(cia_h_ahs, 16) / 64.0) * 64.0)
	# Certificate chain size
	cia.seek(0x8)
	cia_h_cetks = binascii.hexlify(cia.read(0x4)[::-1])
	cia_h_cetks_align = int(math.ceil(int(cia_h_cetks, 16) / 64.0) * 64.0)
	# Ticket size
	cia.seek(0xC)
	cia_h_tiks = binascii.hexlify(cia.read(0x4)[::-1])
	cia_h_tiks_align = int(math.ceil(int(cia_h_tiks, 16) / 64.0) * 64.0)
	tmdoffset = cia_h_ahs_align + cia_h_cetks_align + cia_h_tiks_align
	cia.seek(tmdoffset + 0x140 + 0x5a)
	cia.write(savesize)
	cia.close()

	os.rename("work/%s-game-conv.cia" % tid, os.path.join(outputdir, romname+".cia"))
	if cleanup:
		docleanup(tid)

	processedroms += 1

print("* done converting!")
print("  %i out of %i roms processed" % (processedroms, totalroms))
