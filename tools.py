#!/usr/bin/python
# This file's encoding: UTF-8, so that non-ASCII characters can be used in strings.
#
#		███╗   ███╗ ███╗   ███╗ ██╗    ██╗			-------                                                   -------
#		████╗ ████║ ████╗ ████║ ██║    ██║		 # -=======---------------------------------------------------=======- #
#		██╔████╔██║ ██╔████╔██║ ██║ █╗ ██║		# ~ ~ Written by DRGN of SmashBoards (Daniel R. Cappel);  May, 2020 ~ ~ #
#		██║╚██╔╝██║ ██║╚██╔╝██║ ██║███╗██║		 #            [ Built with Python v2.7.16 and Tkinter 8.5 ]            #
#		██║ ╚═╝ ██║ ██║ ╚═╝ ██║ ╚███╔███╔╝		  # -======---------------------------------------------------======- #
#		╚═╝     ╚═╝ ╚═╝     ╚═╝  ╚══╝╚══╝ 			 ------                                                   ------
#		  -  - Melee Modding Wizard -  -  


# External dependencies
import os
import sys
from tkinter import ttk
import time
import math
import codecs
import psutil
import subprocess
from tkinter import filedialog as tkFileDialog
import tkinter as Tk

from ruamel import yaml
from shutil import copy
from binascii import hexlify
from tkinter.scrolledtext import ScrolledText
from PIL import ImageGrab, Image, ImageTk

if sys.platform == "win32":
    import win32gui
    import win32process

elif sys.platform == "darwin":
    from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID, kCGWindowListOptionAll, kCGNullWindowID, CGWindowListCreateImage, CGRectInfinite, kCGWindowImageBoundsIgnoreFraming

elif sys.platform.startswith("linux"):
    from Xlib import display, X, Xatom

# Internal dependencies
import globalData
import FileSystem.hsdStructures as hsdStructures

from newTkDnD.tkDnD import TkDnD
from FileSystem.disc import Disc
from codeMods import CodeLibraryParser
from FileSystem import CharCostumeFile
from basicFunctions import msg, saveAndShowTempFileData, uHex, cmdChannel, printStatus, humansize
from guiSubComponents import ( 
	BasicWindow, CharacterColorChooser, ColoredLabelButton, 
	VerticalScrolledFrame, cmsg, Dropdown, exportSingleFileWithGui, 
	getNewNameFromUser, LabelButton )


#class NumberConverter( BasicWindow ):


class ImageDataLengthCalculator( BasicWindow ):

	def __init__( self, root ):
		BasicWindow.__init__( self, root, 'Image Data Length Calculator' )

		# Set up the input elements
		# Width
		ttk.Label( self.window, text='Width:' ).grid( column=0, row=0, padx=5, pady=2, sticky='e' )
		self.widthEntry = ttk.Entry( self.window, width=5, justify='center' )
		self.widthEntry.grid( column=1, row=0, padx=5, pady=2 )
		# Height
		ttk.Label( self.window, text='Height:' ).grid( column=0, row=1, padx=5, pady=2, sticky='e' )
		self.heightEntry = ttk.Entry( self.window, width=5, justify='center' )
		self.heightEntry.grid( column=1, row=1, padx=5, pady=2 )
		# Input Type
		ttk.Label( self.window, text='Image Type:' ).grid( column=0, row=2, padx=5, pady=2, sticky='e' )
		self.typeEntry = ttk.Entry( self.window, width=5, justify='center' )
		self.typeEntry.grid( column=1, row=2, padx=5, pady=2 )
		# Result Multiplier
		ttk.Label( self.window, text='Result Multiplier:' ).grid( column=0, row=3, padx=5, pady=2, sticky='e' )
		self.multiplierEntry = ttk.Entry( self.window, width=5, justify='center' )
		self.multiplierEntry.insert( 0, '1' ) # Default
		self.multiplierEntry.grid( column=1, row=3, padx=5, pady=2 )

		# Bind the event listeners for calculating the result
		for inputWidget in [ self.widthEntry, self.heightEntry, self.typeEntry, self.multiplierEntry ]:
			inputWidget.bind( '<KeyRelease>', self.calculateResult )

		# Set the output elements
		ttk.Label( self.window, text='Required File or RAM space:' ).grid( column=0, row=4, columnspan=2, padx=20, pady=5 )
		# In hex bytes
		self.resultEntryHex = ttk.Entry( self.window, width=20, justify='center' )
		self.resultEntryHex.grid( column=0, row=5, padx=5, pady=5 )
		ttk.Label( self.window, text='bytes (hex)' ).grid( column=1, row=5, padx=5, pady=5 )
		# In decimal bytes
		self.resultEntryDec = ttk.Entry( self.window, width=20, justify='center' )
		self.resultEntryDec.grid( column=0, row=6, padx=5, pady=5 )
		ttk.Label( self.window, text='(decimal)' ).grid( column=1, row=6, padx=5, pady=5 )

	def calculateResult( self, event ):
		try:
			widthValue = self.widthEntry.get()
			if not widthValue: return
			elif '0x' in widthValue: width = int( widthValue, 16 )
			else: width = int( widthValue )

			heightValue = self.heightEntry.get()
			if not heightValue: return
			elif '0x' in heightValue: height = int( heightValue, 16 )
			else: height = int( heightValue )

			typeValue = self.typeEntry.get()
			if not typeValue: return
			elif '0x' in typeValue: _type = int( typeValue, 16 )
			else: _type = int( typeValue )

			multiplierValue = self.multiplierEntry.get()
			if not multiplierValue: return
			elif '0x' in multiplierValue: multiplier = int( multiplierValue, 16 )
			else: multiplier = float( multiplierValue )

			# Calculate the final amount of space required.
			imageDataLength = hsdStructures.ImageDataBlock.getDataLength( width, height, _type )
			finalSize = int( math.ceil(imageDataLength * multiplier) ) # Can't have fractional bytes, so we're rounding up

			self.resultEntryHex.delete( 0, 'end' )
			self.resultEntryHex.insert( 0, uHex(finalSize) )
			self.resultEntryDec.delete( 0, 'end' )
			self.resultEntryDec.insert( 0, humansize(finalSize) )
		except:
			self.resultEntryHex.delete( 0, 'end' )
			self.resultEntryHex.insert( 0, 'Invalid Input' )
			self.resultEntryDec.delete( 0, 'end' )


class AsmToHexConverter( BasicWindow ):

	""" Tool window to convert assembly to hex and vice-verca. """

	def __init__( self, mod=None ):
		BasicWindow.__init__( self, globalData.gui.root, 'ASM <-> HEX Converter', offsets=(160, 100), resizable=True, topMost=False, minsize=(460, 350) )

		# Display info and a few controls
		topRow = ttk.Frame( self.window )
		ttk.Label( topRow, text=('This assembles PowerPC assembly code into raw hex,\nor disassembles raw hex into PowerPC assembly.'
			#"\n\nNote that this functionality is also built into the entry fields for new code in the 'Add New Mod to Library' interface. "
			#'So you can use your assembly source code in those fields and it will automatically be converted to hex during installation. '
			'\nComments preceded with "#" will be ignored.'), wraplength=480 ).grid( column=0, row=0, rowspan=4 )

		ttk.Label( topRow, text='Beautify Hex:' ).grid( column=1, row=0 )
		options = [ '1 Word Per Line', '2 Words Per Line', '3 Words Per Line', '4 Words Per Line', '5 Words Per Line', '6 Words Per Line', 'No Whitespace' ]
		Dropdown( topRow, options, default=options[1], command=self.beautifyChanged ).grid( column=1, row=1 )

		self.assembleSpecialSyntax = Tk.BooleanVar( value=False )
		ttk.Checkbutton( topRow, text='Assemble Special Syntax', variable=self.assembleSpecialSyntax ).grid( column=1, row=2, pady=5 )

		self.assemblyDetectedLabel = ttk.Label( topRow, text='Assembly Detected:      ' ) # Leave space for true/false string
		self.assemblyDetectedLabel.grid( column=1, row=3 )

		topRow.grid( column=0, row=0, padx=40, pady=(7, 7), sticky='ew' )
		
		# Configure the top row, so it expands properly on window-resize
		topRow.columnconfigure( 0, weight=1, minsize=400 )
		topRow.columnconfigure( 0, weight=1 )

		self.lengthString = Tk.StringVar( value='' )
		self.mod = mod
		self.syntaxInfo = []
		self.isAssembly = False
		self.blocksPerLine = 2

		# Create the header row
		headersRow = ttk.Frame( self.window )
		ttk.Label( headersRow, text='ASM' ).grid( row=0, column=0, sticky='w' )
		ttk.Label( headersRow, textvariable=self.lengthString ).grid( row=0, column=1 )
		ttk.Label( headersRow, text='HEX' ).grid( row=0, column=2, sticky='e' )
		headersRow.grid( column=0, row=1, padx=40, pady=(7, 0), sticky='ew' )

		# Configure the header row, so it expands properly on window-resize
		headersRow.columnconfigure( 'all', weight=1 )

		# Create the text entry fields and center conversion buttons
		entryFieldsRow = ttk.Frame( self.window )
		self.sourceCodeEntry = ScrolledText( entryFieldsRow, width=30, height=20 )
		self.sourceCodeEntry.grid( rowspan=2, column=0, row=0, padx=5, pady=7, sticky='news' )
		ttk.Button( entryFieldsRow, text='->', command=self.asmToHexCode ).grid( column=1, row=0, pady=30, sticky='s' )
		ttk.Button( entryFieldsRow, text='<-', command=self.hexCodeToAsm ).grid( column=1, row=1, pady=30, sticky='n' )
		self.hexCodeEntry = ScrolledText( entryFieldsRow, width=30, height=20 )
		self.hexCodeEntry.grid( rowspan=2, column=2, row=0, padx=5, pady=7, sticky='news' )
		entryFieldsRow.grid( column=0, row=2, sticky='nsew' )
		
		# Configure the above columns, so that they expand proportionally upon window resizing
		entryFieldsRow.columnconfigure( 0, weight=1 )
		entryFieldsRow.columnconfigure( 1, weight=0 ) # No weight to this row, since it's just the buttons
		entryFieldsRow.columnconfigure( 2, weight=1 )
		entryFieldsRow.rowconfigure( 'all', weight=1 )

		bottomRow = ttk.Frame( self.window )

		# Add the assembly time display (as an Entry widget so we can select text from it)
		self.assemblyTimeDisplay = Tk.Entry( bottomRow, width=25, borderwidth=0 )
		self.assemblyTimeDisplay.configure( state="readonly" )
		self.assemblyTimeDisplay.grid( column=0, row=0, sticky='w', padx=(25, 0) )

		# Determine the include paths to be used here, and add a button at the bottom of the window to display them
		self.detectContext()
		ttk.Button( bottomRow, text='View Include Paths', command=self.viewIncludePaths ).grid( column=1, row=0, ipadx=7 )
		#ttk.Button( bottomRow, text='Save Hex to File', command=self.saveHexToFile ).grid( column=2, row=0, ipadx=7, sticky='e', padx=40 )
		buttonsFrame = ttk.Frame( bottomRow )
		ColoredLabelButton( buttonsFrame, 'saveToFile', self.saveHexToFile, 'Save Hex to File' ).pack( side='right', padx=8 )
		ColoredLabelButton( buttonsFrame, 'saveToClipboard', self.copyHexToClipboard, 'Copy Hex to Clipboard' ).pack( side='right', padx=8 )
		buttonsFrame.grid( column=2, row=0, ipadx=7, sticky='e', padx=40 )
		bottomRow.grid( column=0, row=3, pady=(2, 6), sticky='ew' )
		bottomRow.columnconfigure( 'all', weight=1 )

		# Add the assembly time display (as an Entry widget so we can select text from it)
		# self.assemblyTimeDisplay = Tk.Entry( self.window, width=25, borderwidth=0 )
		# self.assemblyTimeDisplay.configure( state="readonly" )
		# self.assemblyTimeDisplay.place( x=10, rely=1.0, y=-27 )

		# # Determine the include paths to be used here, and add a button at the bottom of the window to display them
		# self.detectContext()
		# ttk.Button( self.window, text='View Include Paths', command=self.viewIncludePaths ).grid( column=0, row=3, pady=(2, 6), ipadx=7 )
		# ttk.Button( self.window, text='Save Hex to File', command=self.saveHexToFile ).place( relx=1.0, rely=1.0, x=-150, y=-31 )

		# Configure this window's expansion as a whole, so that only the text entry row can expand when the window is resized
		self.window.columnconfigure( 0, weight=1 )
		self.window.rowconfigure( 0, weight=0 )
		self.window.rowconfigure( 1, weight=0 )
		self.window.rowconfigure( 2, weight=1 )
		self.window.rowconfigure( 3, weight=0 )

	def updateAssemblyTimeDisplay( self, textInput ):
		self.assemblyTimeDisplay.configure( state="normal" )
		self.assemblyTimeDisplay.delete( 0, 'end' )
		self.assemblyTimeDisplay.insert( 0, textInput )
		self.assemblyTimeDisplay.configure( state="readonly" )

	def asmToHexCode( self ):
		# Clear the hex code field and info labels
		self.hexCodeEntry.delete( '1.0', 'end' )
		self.updateAssemblyTimeDisplay( '' )
		self.lengthString.set( 'Length: ' )
		self.assemblyDetectedLabel['text'] = 'Assembly Detected:      '

		# Get the ASM to convert
		asmCode = self.sourceCodeEntry.get( '1.0', 'end' )

		# Evaluate the code and pre-process it (scan it for custom syntaxes and assemble everything else)
		tic = time.time()
		results = globalData.codeProcessor.evaluateCustomCode( asmCode, self.includePaths, validateConfigs=False )
		returnCode, codeLength, hexCode, self.syntaxInfo, self.isAssembly = results
		toc = time.time()

		# Check for errors (hexCode should include warnings from the assembler)
		if returnCode not in ( 0, 100 ):
			cmsg( hexCode, 'Assembly Error', parent=self.window )
			return

		# Swap back in custom sytaxes
		if self.syntaxInfo and not self.assembleSpecialSyntax.get():
			hexCode = globalData.codeProcessor.restoreCustomSyntaxInHex( hexCode, self.syntaxInfo, codeLength, self.blocksPerLine )

		# Beautify and insert the new hex code
		elif self.blocksPerLine > 0:
			hexCode = globalData.codeProcessor.beautifyHex( hexCode, blocksPerLine=self.blocksPerLine )

		self.hexCodeEntry.insert( 'end', hexCode )

		# Update the code length display
		self.lengthString.set( 'Length: ' + uHex(codeLength) )
		if self.isAssembly:
			self.assemblyDetectedLabel['text'] = 'Assembly Detected: True '
		else:
			self.assemblyDetectedLabel['text'] = 'Assembly Detected: False'

		# Update the assembly time display with appropriate units
		assemblyTime = round( toc - tic, 9 )
		if assemblyTime > 1:
			units = 's' # In seconds
		else:
			assemblyTime = assemblyTime * 1000
			if assemblyTime > 1:
				units = 'ms' # In milliseconds
			else:
				assemblyTime = assemblyTime * 1000
				units = 'us' # In microseconds
		self.updateAssemblyTimeDisplay( 'Assembly Time:  {} {}'.format(assemblyTime, units) )

	def hexCodeToAsm( self ):
		# Delete the current assembly code, and clear the assembly time label
		self.sourceCodeEntry.delete( '1.0', 'end' )
		self.updateAssemblyTimeDisplay( '' )
		self.assemblyDetectedLabel['text'] = 'Assembly Detected:      '

		# Get the HEX code to disassemble
		hexCode = self.hexCodeEntry.get( '1.0', 'end' )
		
		# Evaluate the code and pre-process it (scan it for custom syntaxes)
		results = globalData.codeProcessor.evaluateCustomCode( hexCode, self.includePaths, validateConfigs=False )
		returnCode, codeLength, hexCode, self.syntaxInfo, self.isAssembly = results
		if returnCode != 0:
			self.lengthString.set( 'Length: ' )
			return
		
		# Disassemble the code into assembly
		asmCode, errors = globalData.codeProcessor.disassemble( hexCode )
		if errors:
			cmsg( errors, 'Disassembly Error', parent=self.window )
			return

		if self.syntaxInfo and not self.assembleSpecialSyntax.get():
			asmCode = self.restoreCustomSyntaxInAsm( asmCode )

		# Replace the current assembly code
		self.sourceCodeEntry.insert( 'end', asmCode )

		# Update the code length display
		self.lengthString.set( 'Length: ' + uHex(codeLength) )
		if self.isAssembly:
			self.assemblyDetectedLabel['text'] = 'Assembly Detected: True '
		else:
			self.assemblyDetectedLabel['text'] = 'Assembly Detected: False'

	def restoreCustomSyntaxInAsm( self, asmLines ):

		""" Swap out assembly code for the original custom syntax line that it came from. """

		# Build a new list of ( offset, wordString ) so we can separate words included on the same line
		specialWords = []
		for offset, length, syntaxType, codeLine, names in self.syntaxInfo:
			if syntaxType == 'sbs' or syntaxType == 'sym':
				specialWords.append( (offset, length, syntaxType, codeLine) )
			else:
				# Extract names (eliminating whitespace associated with names) and separate hex groups
				sectionChunks = codeLine.split( '[[' )
				for i, chunk in enumerate( sectionChunks ):
					if ']]' in chunk:
						varName, chunk = chunk.split( ']]' )
						sectionChunks[i] = '[[]]' + chunk

				# Recombine the string and split on whitespace
				newLine = ''.join( sectionChunks )
				hexGroups = newLine.split() # Will now have something like [ '000000[[]]' ] or [ '40820008', '0000[[]]' ]

				# Process each hex group
				nameIndex = 0
				groupParts = []
				for group in hexGroups:
					if ']]' in group:
						specialWords.append( (offset, length, syntaxType, group.replace('[[]]', '[['+names[nameIndex]+']]')) )
						nameIndex += 1

		newLines = []
		offset = 0

		for line in asmLines.splitlines():
			if specialWords and offset + 4 > specialWords[0][0]:
				info = specialWords.pop( 0 )
				if info[2] == 'opt':
					length = info[1]
					if length == 4:
						newLines.append( '.long ' + info[3] )
					elif length == 2:
						newLines.append( '.word ' + info[3] )
					else:
						newLines.append( '.byte ' + info[3] )
				else:
					newLines.append( info[3] )
			else:
				newLines.append( line )
			offset += 4

		return '\n'.join( newLines )

	def detectContext( self ):

		""" This window should use the same .include context for whatever mod it was opened with. 
			If an associated mod is not found, fall back on the default import directories. """

		if self.mod:
			self.includePaths = self.mod.includePaths
		else:
			libraryFolder = globalData.getModsFolderPath()
			self.includePaths = [ os.path.join(libraryFolder, '.include'), os.path.join(globalData.scriptHomeFolder, '.include') ]

	def viewIncludePaths( self ):

		""" Build and display a message to the user on assembly context and current paths. """

		# Build the message to show the user
		paths = [ os.getcwd() + '          <- Current Working Directory' ]
		paths.extend( self.includePaths )
		paths = '\n'.join( paths )

		message =	( 'Assembly context (for ".include" file imports) has the following priority:'
					  "\n\n1) The current working directory (usually the program root folder)"
					  "\n2) Directory of the mod's code file (or the code's root folder with AMFS)"
					  """\n3) The current Code Library's ".include" directory"""
					  """\n4) The program root folder's ".include" directory""" )

		if self.mod:
			message += ( '\n\n\nThis instance of the converter is using assembly context for .include file imports based on {}. '
					 'The exact paths are as follows:\n\n{}'.format( self.mod.name, paths ) )
		else:
			message += ( '\n\n\nThis instance of the converter is using default assembly context for .include file imports. '
					 'The exact paths are as follows:\n\n' + paths )

		cmsg( message, 'Include Paths', 'left', parent=self.window )

	def saveHexToFile( self, event=None ):

		""" Prompts the user for a save location, and then saves the hex code to file as binary. """

		# Get the hex code and remove whitespace
		hexCode = self.hexCodeEntry.get( '1.0', 'end' )
		hexCode = ''.join( hexCode.split() )

		if not hexCode:
			msg( 'No hex code to save!', 'No Hex Code', warning=True, parent=self.window )
			return

		savePath = tkFileDialog.asksaveasfilename(
			title="Where would you like to export the file?",
			parent=self.window,
			initialdir=globalData.getLastUsedDir(),
			initialfile='Bin.bin',
			defaultextension='bin',
			filetypes=[( "Binary files", '*.bin' ), ( "Data archive files", '*.dat' ), ( "All files", "*.*" )] )

		# The above will return an empty string if the user canceled
		if not savePath:
			globalData.gui.updateProgramStatus( 'File save canceled' )
			return

		# Save the hex code to file as binary
		try:
			with open( savePath, 'wb' ) as binFile:
				binFile.write( bytearray.fromhex(hexCode) )

			globalData.gui.updateProgramStatus( 'File saved to "{}"'.format(savePath) )

		except IOError as e: # Couldn't create the file (likely a permission issue)
			msg( 'Unable to create "' + savePath + '" file! This is likely due to a permissions issue. You might try saving to somewhere else.', 'Error', parent=self.window )
			globalData.gui.updateProgramStatus( 'Unable to save; could not create the file at the destination' )

		except ValueError as e: # Couldn't convert the hex to a bytearray
			msg( 'Unable to convert the hex to binary; you may want to check for illegal characters.', 'Error', parent=self.window )
			globalData.gui.updateProgramStatus( 'Unable to save; hex string could not be converted to bytearray' )

	def copyHexToClipboard( self, event=None ):
		hexCode = self.hexCodeEntry.get( '1.0', 'end' )
		
		globalData.gui.root.clipboard_clear()
		globalData.gui.root.clipboard_append( hexCode )

	def _flushBuffer( self, pureHexBuffer, newLines ):

		""" Helper method to the beautify update method below; this dumps hex code 
			that has been collected so far into the newLines list (properly formatted). """

		if pureHexBuffer:
			# Combine the hex collected so far into one string, and beautify it if needed
			pureHex = ''.join( pureHexBuffer )
			if self.blocksPerLine > 0:
				pureHex = globalData.codeProcessor.beautifyHex( pureHex, blocksPerLine=self.blocksPerLine )

			# Store hex and clear the hex buffer
			newLines.append( pureHex )
			pureHexBuffer = []

		return pureHexBuffer, newLines

	def beautifyChanged( self, widget, newValue ):

		""" Called when the Beautify Hex dropdown option is changed.
			Reformats the HEX output to x number of words per line. """

		# Parse the current dropdown option for a block count
		try:
			self.blocksPerLine = int( newValue.split()[0] )
		except:
			self.blocksPerLine = 0

		# Get hex code currently displayed if there is any
		hexCode = self.hexCodeEntry.get( '1.0', 'end' )
		if not hexCode: return

		# Clear the hex code field and info labels
		self.hexCodeEntry.delete( '1.0', 'end' )
		
		newLines = []
		pureHexBuffer = []
		customSyntaxFound = False

		for rawLine in hexCode.splitlines():
			# Start off by filtering out comments, and skip empty lines
			codeLine = rawLine.split( '#' )[0].strip()
			if not codeLine: continue

			elif CodeLibraryParser.isSpecialBranchSyntax( codeLine ): # e.g. "bl 0x80001234" or "bl <testFunction>"
				customSyntaxFound = True
			
			elif CodeLibraryParser.containsPointerSymbol( codeLine ): # Identifies symbols in the form of <<functionName>>
				customSyntaxFound = True

			elif '[[' in codeLine and ']]' in codeLine: # Identifies configuration option placeholders
				customSyntaxFound = True
			else:
				customSyntaxFound = False

			if customSyntaxFound:
				pureHexBuffer, newLines = self._flushBuffer( pureHexBuffer, newLines )
				newLines.append( codeLine )
			else:
				# Strip out whitespace and store the line
				pureHex = ''.join( codeLine.split() )
				pureHexBuffer.append( pureHex )

		newLines = self._flushBuffer( pureHexBuffer, newLines )[1]

		# Collapse the code lines to a string and reinsert it into the text widget
		hexCode = '\n'.join( newLines )
		self.hexCodeEntry.insert( 'end', hexCode )


class CodeLookup( BasicWindow ):

	def __init__( self ):
		BasicWindow.__init__( self, globalData.gui.root, 'Code Lookup', resizable=True, minsize=(520, 300) )

		pady = 6

		mainFrame = ttk.Frame( self.window )
		controlPanel = ttk.Frame( mainFrame )

		# Set up offset/address input
		ttk.Label( controlPanel, text='Enter a DOL Offset or RAM Address:' ).grid( column=0, row=0, columnspan=2, padx=5, pady=(25, pady) )
		validationCommand = globalData.gui.root.register( self.locationUpdated )
		self.location = Tk.Entry( controlPanel, width=13, 
				justify='center', 
				relief='flat', 
				highlightbackground='#b7becc', 	# Border color when not focused
				borderwidth=1, 
				highlightthickness=1, 
				highlightcolor='#0099f0', 
				validate='key', 
				validatecommand=(validationCommand, '%P') )
		self.location.grid( column=0, row=1, columnspan=2, padx=5, pady=pady )
		self.location.bind( "<KeyRelease>", self.initiateSearch )

		ttk.Label( controlPanel, text='Function Name:' ).grid( column=0, row=2, columnspan=2, padx=30, pady=(pady, 0), sticky='w' )
		self.name = Tk.Text( controlPanel, width=40, height=3, state="disabled" )
		self.name.grid( column=0, row=3, columnspan=2, sticky='ew', padx=5, pady=pady )

		ttk.Label( controlPanel, text='DOL Offset:' ).grid( column=0, row=4, padx=5, pady=pady )
		self.dolOffset = Tk.Entry( controlPanel, width=24, borderwidth=0, state="disabled" )
		self.dolOffset.grid( column=1, row=4, sticky='w', padx=(7, 0) )

		ttk.Label( controlPanel, text='RAM Address:' ).grid( column=0, row=5, padx=5, pady=pady )
		self.ramAddr = Tk.Entry( controlPanel, width=24, borderwidth=0, state="disabled" )
		self.ramAddr.grid( column=1, row=5, sticky='w', padx=(7, 0) )

		ttk.Label( controlPanel, text='Length:' ).grid( column=0, row=6, padx=5, pady=pady )
		self.length = Tk.Entry( controlPanel, width=8, borderwidth=0, state="disabled" )
		self.length.grid( column=1, row=6, sticky='w', padx=(7, 0) )

		ttk.Label( controlPanel, text='Includes\nCustom Code:', justify='center' ).grid( column=0, row=7, padx=5, pady=pady )
		self.hasCustomCode = Tk.StringVar()
		ttk.Label( controlPanel, textvariable=self.hasCustomCode ).grid( column=1, row=7, sticky='w', padx=(7, 0) )

		controlPanel.grid( column=0, row=0, rowspan=2, padx=4, sticky='n' )

		ttk.Label( mainFrame, text='Function Code:' ).grid( column=1, row=0, padx=42, pady=2, sticky='ew' )
		self.code = ScrolledText( mainFrame, width=28, state="disabled" )
		self.code.grid( column=1, row=1, rowspan=2, sticky='nsew', padx=(12, 0) )

		mainFrame.pack( expand=True, fill='both' )

		# Configure this window's resize behavior
		mainFrame.columnconfigure( 0, weight=0 )
		mainFrame.columnconfigure( 1, weight=1 )
		mainFrame.rowconfigure( 0, weight=0 )
		mainFrame.rowconfigure( 1, weight=1 )

		# Get and load a DOL file for reference
		if globalData.disc:
			self.dol = globalData.disc.dol
			self.dolIsVanilla = False
			gameId = globalData.disc.gameId
		else:
			# Try the vanilla disc path
			vanillaDiscPath = globalData.getVanillaDiscPath()
			if not vanillaDiscPath:
				warningMessage = 'No disc reference is available. One is required in order to look up code.'
				msg( warningMessage, 'No reference disc', parent=self.window, warning=True )
				self.close()
				return
			vanillaDisc = Disc( vanillaDiscPath )
			vanillaDisc.loadGameCubeMediaFile()
			gameId = vanillaDisc.gameId

			self.dol = vanillaDisc.dol
			self.dolIsVanilla = True
		self.dol.load()
		
		# Collect function symbols info from the map file
		symbolMapPath = os.path.join( globalData.paths['maps'], gameId + '.map' )
		with open( symbolMapPath, 'r' ) as mapFile:
			self.symbols = mapFile.read()
		self.symbols = self.symbols.splitlines()

	def updateEntry( self, widget, textInput ):
		widget.configure( state="normal" )
		widget.delete( 0, 'end' )
		widget.insert( 0, textInput )
		widget.configure( state="readonly" )

	def updateScrolledText( self, widget, textInput ):

		""" For Text or ScrolledText widgets. """

		widget.configure( state="normal" )
		widget.delete( 1.0, 'end' )
		widget.insert( 1.0, textInput )
		widget.configure( state="disabled" )

	# def clearControlPanel( self ):
		
	# 	self.dolOffset.configure( state="normal" )
	# 	self.dolOffset.delete( 0, 'end' )
	# 	self.dolOffset.configure( state="readonly" )
	# 	self.ramAddr.configure( state="normal" )
	# 	self.ramAddr.delete( 0, 'end' )
	# 	self.ramAddr.configure( state="readonly" )
	# 	self.length.configure( state="normal" )
	# 	self.length.delete( 0, 'end' )
	# 	self.length.configure( state="readonly" )

	def locationUpdated( self, locationString ):

		""" Validates text input into the offset/address entry field, whether entered 
			by the user or programmatically. Ensures there are only hex characters.
			If there are hex characters, this function will deny them from being entered. """

		try:
			if not locationString: # Text erased
				return True

			# Attempt to convert the hex string to decimal
			int( locationString, 16 )

			return True
		except:
			return False

	def initiateSearch( self, event ):

		locationString = self.location.get().strip().lstrip( '0x' )

		# Get both the DOL offset and RAM address
		cancelSearch = False
		try:
			if len( locationString ) == 8 and locationString.startswith( '8' ):
				address = int( locationString, 16 )
				offset = self.dol.offsetInDOL( address )

				if address > self.dol.maxRamAddress:
					cancelSearch = True
			else:
				offset = int( locationString, 16 )
				address = self.dol.offsetInRAM( offset )

				if offset < 0x100:
					cancelSearch = True
		except:
			cancelSearch = True

		if cancelSearch:
			self.updateScrolledText( self.name, '' )
			self.updateScrolledText( self.code, '' )
			self.updateEntry( self.dolOffset, '' )
			self.updateEntry( self.ramAddr, '' )
			self.updateEntry( self.length, '' )
			self.hasCustomCode.set( '' )
			return

		elif offset == -1:
			self.updateScrolledText( self.name, '' )
			self.updateScrolledText( self.code, '{} not found in the DOL'.format(self.location.get().strip()) )
			self.updateEntry( self.dolOffset, '' )
			self.updateEntry( self.ramAddr, '' )
			self.updateEntry( self.length, '' )
			self.hasCustomCode.set( '' )
			return

		# Look up info on this function in the map file
		for i, line in enumerate( self.symbols ):
			line = line.strip()
			if not line or line.startswith( '.' ):
				continue

			# Parse the line (split on only the first 4 instances of a space)
			functionStart, length, _, _, symbolName = line.split( ' ', 4 )
			functionStart = int( functionStart, 16 )
			length = int( length, 16 )

			# Check if this is the target function
			if address >= functionStart and address < functionStart + length:
				dolFunctionStart = self.dol.offsetInDOL( functionStart )
				break

		else: # Above loop didn't break; symbol not found
			self.updateScrolledText( self.name, '' )
			self.updateScrolledText( self.code, 'Unable to find {} in the map file'.format(self.location.get().strip()) )
			self.updateEntry( self.dolOffset, '' )
			self.updateEntry( self.ramAddr, '' )
			self.updateEntry( self.length, '' )
			self.hasCustomCode.set( 'N/A' )
			return

		self.updateScrolledText( self.name, symbolName )
		self.updateEntry( self.dolOffset, uHex(dolFunctionStart) + ' - ' + uHex(dolFunctionStart+length) )
		self.updateEntry( self.ramAddr, uHex(functionStart) + ' - ' + uHex(functionStart+length) )
		self.updateEntry( self.length, uHex(length) )

		# Get the target function as a hex string
		functionCode = self.dol.getData( dolFunctionStart, length )
		hexCode = hexlify( functionCode )
	
		# Disassemble the code into assembly
		asmCode, errors = globalData.codeProcessor.disassemble( hexCode )
		if errors:
			self.updateScrolledText( self.code, 'Disassembly Error:\n\n' + errors )
		else:
			self.updateScrolledText( self.code, asmCode )

		# Update text displaying whether this is purely vanilla code
		if self.dolIsVanilla:
			self.hasCustomCode.set( 'No' )
		else: # todo
			self.hasCustomCode.set( 'Unknown' )


class TriCspCreator( object ):

	def __init__( self ):

		self.config = {}
		self.gimpDir = ''
		self.gimpExe = ''

		# Analyze the version of GIMP installed
		self.checkGimpPath()
		self.checkGimpProgramVersion()
		self.checkGimpPluginDirectory()

		# Update installed scripts (then no need to check version)
		# todo

		# Delete old GIMP .pyc plugins (I don't think GIMP will automatically re-build them if the scripts are updated)
		# todo

		# Double-check plugin versions
		self.createCspScriptVersion = self.getScriptVersion( self.pluginDir, 'python-fu-create-tri-csp.py' )
		self.finishCspScriptVersion = self.getScriptVersion( self.pluginDir, 'python-fu-finish-csp.py' )
		
		# Load the CSP Configuration file, and assemble other needed paths
		try:
			self.triCspFolder = globalData.paths['triCsps']
			self.pluginsFolder = os.path.join( self.triCspFolder, 'GIMP plug-ins' )
			configFilePath = os.path.join( self.triCspFolder, 'CSP Configuration.yml' )
			configFileName = os.path.basename( configFilePath )

			# Read the config file (this method should allow for utf-8 encoding, and preserve comments when saving/dumping back to file)
			with codecs.open( configFilePath, 'r', encoding='utf-8' ) as stream:
				self.config = yaml.load( stream, Loader=yaml.RoundTripLoader )

			self.settingsFiles = [
				os.path.join( self.triCspFolder, 'Debugger.ini' ),
				os.path.join( self.triCspFolder, 'Dolphin.ini' ),
				os.path.join( self.triCspFolder, 'GFX.ini' )
			]
			self.configLoadErr = ''
		except IOError: # Couldn't find the configuration file
			self.configLoadErr = """Couldn't find the CSP config file at "{}".""".format( configFilePath )
		except Exception as err: # Problem parsing the file
			self.configLoadErr = 'There was an error while parsing the {} file:\n\n{}'.format(configFileName, err)
		
		# Print out version info
		print( '' )
		print( '  Tri-CSP Creator version info:' )
		print( '  GIMP:                    ' + self.gimpVersion )
		print( '  create-tri-csp script:   ' + self.createCspScriptVersion )
		print( '  finish-csp script:       ' + self.finishCspScriptVersion )
		print( '' )
		print( 'GIMP executable directory: ' + self.gimpDir )
		print( 'GIMP Plug-ins directory:   ' + self.pluginDir )
		print( '' )
		if self.configLoadErr:
			print( self.configLoadErr )
		else:
			print( 'Tri-CSP Configuration file loaded successfully.' )

	def initError( self ):

		""" Assesses how the initialization methods went to determine if there are any problems. 
			If there are any problems, an error message will be returned. Returns an empty string on success. """

		errorMsg = ''

		if not self.gimpDir:
			errorMsg = ( 'GIMP does not appear to be installed; ')

		elif not self.gimpExe:
			errorMsg = 'Unable to find the GIMP console executable in "{}".'.format( self.gimpDir )

		elif self.configLoadErr: # Unable to load the CSP configuration file
			errorMsg = self.configLoadErr
		
		elif self.createCspScriptVersion != '2.1' or self.finishCspScriptVersion != '2.3': #todo: remove hardcoding!
			errorMsg = 'Differing versions of the GIMP plug-in scripts detected!'

		return errorMsg

	def checkGimpPath( self ):

		""" Determines the absolute file path to the GIMP console executable 
			(the exe filename varies based on program version). """
		
		# Check for the GIMP program folder
		gimpExecutable = find_gimp_executable()
		if gimpExecutable != None:
			self.gimpDir = os.path.dirname(gimpExecutable)
		
		# Check the files in the program folder for a 'console' executable
		for fileOrFolderName in os.listdir( directory ):
			if fileOrFolderName.startswith( 'gimp-console' ) and fileOrFolderName.endswith( '.exe' ):
				self.gimpExe = fileOrFolderName
				return

		else: # The loop above didn't break; unable to find the exe
			self.gimpDir = ''
			self.gimpExe = ''
			return

	def checkGimpProgramVersion( self ):
		returnCode, versionText = cmdChannel( '"{}\{}" --version'.format(self.gimpDir, self.gimpExe) )
		if returnCode == 0:
			self.gimpVersion = versionText.split()[-1]
		else:
			print( versionText ) # Should be an error message in this case
			self.gimpVersion = '-1'
		
	def checkGimpPluginDirectory( self ):

		""" Checks known directory paths for GIMP versions 2.8 and 2.10. If both appear 
			to be installed, we'll check the version of the executable that was found. """

		userFolder = os.path.expanduser( '~' ) # Resolves to "C:\Users\[userName]"
		v8_Path = os.path.join( userFolder, '.gimp-2.8\\plug-ins' )
		v10_Path = os.path.join( userFolder, 'AppData\\Roaming\\GIMP\\2.10\\plug-ins' )

		if os.path.exists( v8_Path ) and os.path.exists( v10_Path ):
			# Both versions seem to be installed. Use Gimp's version to decide which to use
			major, minor, _ = self.gimpVersion.split( '.' )
			if major != '2':
				self.pluginDir = ''
			if minor == '8':
				self.pluginDir = v8_Path
			else: # Hoping this path is good for other versions as well
				self.pluginDir = v10_Path

		elif os.path.exists( v8_Path ): self.pluginDir = v8_Path
		elif os.path.exists( v10_Path ): self.pluginDir = v10_Path
		else: self.pluginDir = ''

	def getScriptVersion( self, pluginDir, scriptFile ):

		""" Scans the given script (a filename) for a line like "version = 2.2\n" and parses it. """

		scriptPath = os.path.join( pluginDir, scriptFile )

		if os.path.exists( scriptPath ):
			with open( scriptPath, 'r' ) as script:
				for line in script:
					line = line.strip()

					if line.startswith( 'version' ) and '=' in line:
						return line.split( '=' )[-1].strip()
			
		return '-1'

	def createSideImage( self, microMelee, charId, costumeId, charExtension ):

		""" Installs code mods to the given Micro Melee disc image required for capturing CSP images, 
			and then launches Dolphin to collect a screenshot of a specific character costume. """

		# Get target action states and frames for the screenshots
		try:
			characterDict = self.config[charId]
			actionState = characterDict['actionState']
			targetFrame = characterDict['frame']
			faceLeft = characterDict.get( 'faceLeft', False )
			grounded = characterDict.get( 'grounded', False )
			camX = characterDict['camX']
			camY = characterDict['camY']
			camZ = characterDict['camZ']
			targetFrameId = targetFrame >> 16 # Just need the first two bytes of the float for this
		except KeyError as err:
			msg( 'Unable to find CSP "{}" info for character ID 0x{:X} in "CSP Configuration.yml".'.format(err.message, charId), 'CSP Config Error' )
			return ''

		# Replace the character in the Micro Melee disc with the 20XX skin
		origFile = microMelee.files[microMelee.gameId + '/' + microMelee.constructCharFileName(charId, costumeId, 'dat')]
		newFile = globalData.disc.files[globalData.disc.gameId + '/' + globalData.disc.constructCharFileName(charId, costumeId, charExtension)]
		microMelee.replaceFile( origFile, newFile )

		# Copy over Nana too, if ICies are selected
		if charId == 0xE: # Ice Climbers
			colorAbbr = globalData.costumeSlots['Nn'][costumeId]
			origFile = microMelee.files[microMelee.gameId + '/PlNn' + colorAbbr + '.dat' ]
			newFile = globalData.disc.files[globalData.disc.gameId + '/PlNn' + colorAbbr + '.' + charExtension]
			microMelee.replaceFile( origFile, newFile )

		# Parse the Core Codes library for the codes needed for booting to match and setting up a pose
		coreCodes = CodeLibraryParser()
		coreCodesFolder = globalData.paths['coreCodes']
		includePaths = [ os.path.join(coreCodesFolder, '.include'), os.path.join(globalData.scriptHomeFolder, '.include') ]
		coreCodes.processDirectory( coreCodesFolder, includePaths )
		codesToInstall = []

		# Customize the Asset Test mod to load the chosen characters/costumes
		assetTest = coreCodes.getModByName( 'Asset Test' )
		if not assetTest:
			msg( 'Unable to find the Asset Test mod in the Core Codes library!', warning=True )
			return ''
		assetTest.configure( "Player 1 Character", charId )
		assetTest.configure( "P1 Costume ID", costumeId )
		assetTest.configure( "Player 2 Character", charId )
		assetTest.configure( "P2 Costume ID", costumeId )
		if charId == 0x13: # Special case for Sheik (for different lighting direction)
			assetTest.configure( "Stage", 3 ) # Selecting Pokemon Stadium
		else:
			assetTest.configure( "Stage", 32 ) # Selecting FD
		if faceLeft:
			assetTest.configure( 'P1 Facing Direction', -1 )
			assetTest.configure( 'P2 Facing Direction', -1 )
		else:
			assetTest.configure( 'P1 Facing Direction', 1 )
			assetTest.configure( 'P2 Facing Direction', 1 )
		codesToInstall.append( assetTest )

		# Parse the Pose Codes
		poseCodes = CodeLibraryParser()
		poseCodesFolder = globalData.paths['triCsps']
		includePaths = [ os.path.join(poseCodesFolder, '.include'), os.path.join(globalData.scriptHomeFolder, '.include') ]
		poseCodes.processDirectory( poseCodesFolder, includePaths )
		
		# Check for a pose code specific to this character in the Pose Codes file
		poseCodeName = globalData.charList[charId] + ' Pose Code'
		poseCode = poseCodes.getModByName( poseCodeName )

		if poseCode:
			codesToInstall.append( poseCode )
		else: # No specific, custom code for this character; use the general approach

		# Configure code for setting the appropriate action state
		# if charId == 1: # DK
		# 	actionStateMod = coreCodes.getModByName( 'DK CSP Double-Jump' )
		# 	if not actionStateMod:
		# 		msg( 'Unable to find the DK CSP Double-Jump mod in the Core Codes library!', warning=True )
		# 		return
		#if charId == 1 or charId == 6: # DK or Link
			# actionStateMod = coreCodes.getModByName( 'Force Jump for CSP' )
			# if not actionStateMod:
			# 	msg( 'Unable to find the Force Jump mod in the Core Codes library!', warning=True )
			# 	return
			# codesToInstall.append( actionStateMod )

			# actionStateMod = coreCodes.getModByName( 'Enter Action State On Match Start' )
			# if not actionStateMod:
			# 	msg( 'Unable to find the Enter Action State On Match Start mod in the Core Codes library!', warning=True )
			# 	return
			# actionStateMod.configure( 'Action State ID', actionState )
			# actionStateMod.configure( 'Start Frame', 0 )

			# codesToInstall.append( coreCodes.getModByName('Zero-G Mode') )
		# else:
			actionStateMod = coreCodes.getModByName( 'Enter Action State On Match Start' )
			if not actionStateMod:
				msg( 'Unable to find the "Enter Action State On Match Start" mod in the Core Codes library!', warning=True )
				return ''

		# Convert the pose target frame to an int start frame
		# startFrame = struct.unpack( '>f', struct.pack('>I', targetFrame) )[0]
		# if startFrame <= 5:
		# 	startFrame = 0
		# else:
		# 	startFrame = int( startFrame - 5 )
		
			actionStateMod.configure( 'Action State ID', actionState )
			actionStateMod.configure( 'Start Frame', 0 )

			codesToInstall.append( actionStateMod )

			# If the move should be done in the air, apply a code so they hover on spawn
			if grounded:
				# Increase delay to start the move so the characters have time to fall to the ground
				actionStateMod.configure( 'Delay', 102 ) # Default is 72
			else:
				codesToInstall.append( coreCodes.getModByName('Zero-G Mode') )
		
		# Customize Action State Freeze
		actionStateFreeze = coreCodes.getModByName( 'Action State Freeze' )
		if not actionStateFreeze:
			msg( 'Unable to find the "Action State Freeze" mod in the Core Codes library!', warning=True )
			return ''
		actionStateFreeze.configure( 'Action State ID', actionState )
		actionStateFreeze.configure( 'Frame ID', targetFrameId )
		codesToInstall.append( actionStateFreeze )

		codesToInstall.append( coreCodes.getModByName('Modified Camera Info Flag Initialization') )
		codesToInstall.append( coreCodes.getModByName('Standard Pause Camera in Dev-Mode Match') )
		codesToInstall.append( coreCodes.getModByName('Disable Pause HUD') )

		# Configure the camera
		cameraMod = coreCodes.getModByName( 'CSP Camera' )
		cameraMod.configure( 'X Coord', camX )
		cameraMod.configure( 'Y Coord', camY )
		cameraMod.configure( 'Z Coord', camZ )
		codesToInstall.append( cameraMod )

		# Configure the camera pause time
		pauseMod = coreCodes.getModByName( 'Auto-Pause' )
		pauseMod.configure( 'Target Frame', 252 ) # 72 (to leave entry platform) + 180 (max anim time)
		codesToInstall.append( pauseMod )

		# Shut down all instances of Dolphin to ensure the disc can be saved to
		dc = globalData.dolphinController
		dc.stopAllDolphinInstances()

		# Restore the disc's DOL data to vanilla and then install the necessary codes
		if not microMelee.restoreDol( countAsNewFile=False ):
			return ''
		microMelee.installCodeMods( codesToInstall )
		microMelee.save()

		# Engage emulation
		dc.start( microMelee )

		time.sleep( 5 )
		screenshotPath = dc.getScreenshot( charExtension )

		# Stop emulation
		dc.stop()

		return screenshotPath

	def createTriCsp( self, leftImagePath, centerImagePath, rightImagePath, charConfigDict, outputPath, saveHighRes ):
		
		""" Construct a gimp-script command-line argument and send it to GIMP to create a finished Tri-CSP image.
			The GIMP options used are as follows:
				-d = "--no-data", prevents loading of brushes, gradients, palettes, patterns, ...
				-f = "--no-fonts", prevents loading of fonts
				-i = "--no-interface", prevents loading of main GUI
				-g = "--gimprc", applies setting preferences from a file (must be a full path). In this case, it's just used to prevent exporting a color profile
				-b "" specifies a script-fu command to be run in gimp """

		printStatus( 'Compositing CSP Image...', forceUpdate=True )

		# Assemble needed paths and replace backslashes
		gimpExePath = os.path.join( self.gimpDir, self.gimpExe )
		gimprcPath = os.path.join( self.triCspFolder, 'gimprcTCC' ).replace( '\\', '/' )
		leftImagePath = leftImagePath.replace( '\\', '/' )
		centerImagePath = centerImagePath.replace( '\\', '/' )
		rightImagePath = rightImagePath.replace( '\\', '/' )
		outputPath = outputPath.replace( '\\', '/' )
		
		# Convert the boolean flags to strings
		if charConfigDict['reverseSides']: reverseSidesFlag = '1'
		else: reverseSidesFlag = '0'
		if saveHighRes: saveHighResFlag = '1'
		else: saveHighResFlag = '0'

		# Construct the list of CSP configuration arguments and cast them to a string
		try:
			configArgsList = [
				charConfigDict['threshold'], 
				charConfigDict['centerImageXOffset'], charConfigDict['centerImageYOffset'], charConfigDict['centerImageScaling'], 
				charConfigDict['sideImagesXOffset'], charConfigDict['sideImagesYOffset'], charConfigDict['sideImagesScaling']
			]
		except KeyError as err:
			raise Exception( 'Missing CSP configuration: ' + err.message )
		configurationArgs = [ str(arg) for arg in configArgsList ]

		command = (
			#'start /B /D "{}"'.format( gimpExeFolder ) # Starts a new process. /B prevents creating a new window, and /D sets the working directory
			'"{}" -d -f -i -g "{}"'.format( gimpExePath, gimprcPath ) # Call the gimp executable with the arguments described above
			+ ' -b "(python-fu-create-tri-csp 1' # Extra param, "1", to run in NON-INTERACTIVE mode
			' \\"' + leftImagePath + '\\"'
			' \\"' + centerImagePath + '\\"'
			' \\"' + rightImagePath + '\\"'
			' \\"\\" \\"\\"' # Mask image path & Config file path (not used here)
			' \\"' + outputPath + '\\"'
			#+ ' '.join( configurationArgs ) + ' ' + reverseSidesFlag + ' ' + saveHighResFlag + ' 0)" -b "(gimp-quit 0)"'
			' {} {} {} 0)" -b "(gimp-quit 0)"'.format( ' '.join( configurationArgs ), reverseSidesFlag, saveHighResFlag )
		)

		# Send the command to the Tri-CSP creator script and parse its output
		stderr = cmdChannel( command, returnStderrOnSuccess=True )[1]
		returnCode, errMsg = self.parseScriptOutput( stderr )
		if returnCode != 0:
			msg( 'There was an error in creating the Tri-CSP (exit code {}):\n\n{}'.format(returnCode, errMsg), 'Tri-CSP Compositing Error', error=True )
			globalData.gui.updateProgramStatus( 'Error during Tri-CSP creation', error=True )

		return returnCode

	def parseScriptOutput( self, stderr ):

		""" Can't get normal exit/return codes from python-fu scripts, 
			so instead we'll parse custom messages from stderr. """

		for line in stderr.splitlines():
			if line.startswith( 'Create Tri-CSP-Warning: Return Code:' ): # e.g. "Create Tri-CSP-Warning: Return Code: 1: Some error happened"
				returnCode, message = line.split( ':' )[2:]
				return ( int(returnCode), message.strip() )
		else: # The above loop didn't break; Unknown error
			return ( -1, stderr )


class DolphinController( object ):

	""" Wrapper the Dolphin emulator, to handle starting/stopping 
		the game, file I/O, and option configuration. """

	def __init__( self ):
		self._exePath = ''
		self._rootFolder = ''
		self._userFolder = ''
		self.process = None

	@property
	def exePath( self ):

		""" Set up initial filepaths. This should be done just once, on the first path request. 
			This is not done in the init method because program settings were not loaded then. """

		if self._exePath:
			return self._exePath
		
		self._exePath = globalData.getEmulatorPath()
		if not self._exePath:
			self._rootFolder = ''
			self._userFolder = ''
			return ''

		self._rootFolder = os.path.dirname( self._exePath )
		self._userFolder = os.path.join( self._rootFolder, 'User' )

		# Make sure that Dolphin is in 'portable' mode
		portableFile = os.path.join( self._rootFolder, 'portable.txt' )
		if not os.path.exists( portableFile ):
			try:
				with open( portableFile, 'w' ) as newFile:
					pass
			except:
				msg( "Dolphin is not in portable mode, and 'portable.txt' could not be created. Be sure that this program "
					 "has write permissions in the Dolphin root directory.", 'Non-portable Dolphin', globalData.gui.root, warning=True )
				return

		if not os.path.exists( self._userFolder ):
			self.start( '' ) # Will open, create the user folder, and close? todo: needs testing
			# time.sleep( 4 )
			# self.stop()

		return self._exePath

	@property
	def rootFolder( self ):
		if not self._rootFolder:
			self.exePath
		return self._rootFolder

	@property
	def userFolder( self ):
		if not self._userFolder:
			self.exePath
		return self._userFolder

	# @property
	# def screenshotFolder( self ):
	# 	return os.path.join( self.userFolder, 'ScreenShots' )

	@property
	def isRunning( self ):
		if not self.process: # Hasn't been started
			return False

		return ( self.process.poll() == None ) # None means the process is still running; anything else is an exit code

	def getVersion( self ):
		
		if not self.exePath:
			return '' # User may have canceled the prompt

		returnCode, output = cmdChannel( '"{}" --version'.format(self.exePath) )

		if returnCode == 0:
			return output
		else:
			return 'N/A'

	def backupAndReplaceSettings( self, fileList ):

		""" Backs up current Dolphin settings files, and replaces them with the given files. """

		settingsFolder = os.path.join( self.userFolder, 'Config' )

		for filepath in fileList:
			origFile = os.path.join( settingsFolder, os.path.basename(filepath) )
			# debuggerSettingsFile = os.path.join( settingsFolder, 'Debugger.ini' )
			# dolphinSettingsFile = os.path.join( settingsFolder, 'Dolphin.ini' )
			# gfxSettingsFile = os.path.join( settingsFolder, 'GFX.ini' )
			try:
				# os.rename( debuggerSettingsFile, debuggerSettingsFile + '.bak' )
				# os.rename( dolphinSettingsFile, dolphinSettingsFile + '.bak' )
				os.rename( origFile, origFile + '.bak' )
			except WindowsError: # Likely the backup files already exist
				pass # Keep the old backup files; do not replace

			# Copy over the Dolphin settings files for CSP creation
			# copy( cspCreator.debuggerSettingsFile, debuggerSettingsFile )
			# copy( cspCreator.dolphinSettingsFile, dolphinSettingsFile )
			copy( filepath, origFile )

	def restoreSettings( self, fileList ):
		
		""" Restores Dolphin settings previously backed-up, replacing them with the original files. """

		settingsFolder = os.path.join( self.userFolder, 'Config' )
		
		for filepath in fileList:
			origFile = os.path.join( settingsFolder, os.path.basename(filepath) )
			os.remove( origFile )
			os.rename( origFile + '.bak', origFile )
	
	def start( self, discObj ):

		""" Starts running an instance of Dolphin with the given disc. 
			'--exec' loads the specified file. (Using '--exec' because '/e' is incompatible with Dolphin 5+, while '-e' is incompatible with Dolphin 4.x)
			'--batch' will prevent dolphin from unnecessarily scanning game/ISO directories, and will shut down Dolphin when the game is stopped. """

		if not self.exePath:
			return # User may have canceled the prompt

		# Make sure there are no prior instances of Dolphin running
		self.stopAllDolphinInstances()
		
		printStatus( 'Booting {} in emulator....'.format(discObj.gameId) )

		# Pass along the filepath to the DOL file if this is a root folder
		if discObj.isRootFolder:
			bootFile = discObj.dol.extPath
		else:
			bootFile = discObj.filePath

		# Construct the command with the disc or DOL filepath and send it to Dolphin
		if globalData.checkSetting( 'runDolphinInDebugMode' ):
			command = '"{}" --debugger --exec="{}"'.format( self.exePath, bootFile )
		else:
			command = '"{}" --batch --exec="{}"'.format( self.exePath, bootFile )
		self.process = subprocess.Popen( command, stderr=subprocess.STDOUT, creationflags=0x08000000 )

	def stop( self ):

		""" Stop an existing Dolphin process that was spawned from this controller. """

		if self.isRunning:
			self.process.terminate()
			time.sleep( 2 )

	def stopAllDolphinInstances( self ):
		self.stop()

		# Check for other running instances of Dolphin
		processFound = False
		for process in psutil.process_iter():
			if process.name() == 'Dolphin.exe':
				process.terminate()
				processFound = True
				printStatus( 'Stopped an older Dolphin process not started by this module' )
		
		if processFound:
			time.sleep( 2 )

	# def getLatestScreenshot( self, gameId ):
	# 	screenshotFolder = os.path.join( self.userFolder, 'ScreenShots', gameId )

	def getSettings( self, settingsDict ):

		""" Read the main Dolphin settings file and graphics settings 
			file to collect and return current settings. """

		# Check the general settings file
		settingsFilePath = os.path.join( self.userFolder, 'Config', 'Dolphin.ini' )
		with open( settingsFilePath, 'r' ) as settingsFile:
			for line in settingsFile.readlines():
				if not '=' in line: continue

				name, value = line.split( '=' )
				name = name.strip()
				value = value.strip()

				if name in settingsDict:
					settingsDict['name'] = value
		
		# Check the general settings file
		settingsFilePath = os.path.join( self.userFolder, 'Config', 'GFX.ini' )
		with open( settingsFilePath, 'r' ) as settingsFile:
			for line in settingsFile.readlines():
				if not '=' in line: continue

				name, value = line.split( '=' )
				name = name.strip()
				value = value.strip()

				if name in settingsDict:
					settingsDict['name'] = value

		return settingsDict
	
	def setSettings( self, settingsDict ):

		""" Open the main Dolphin settings file and graphics settings 
			and change settings to those given. """

		# Read the general settings file
		settingsFilePath = os.path.join( self.userFolder, 'Config', 'Dolphin.ini' )
		with open( settingsFilePath, 'r' ) as settingsFile:
			fileContents = settingsFile.read()
		
		with open( settingsFilePath, 'w' ) as settingsFile:
			for line in fileContents.readlines():
				if not '=' in line: continue

				name, _ = line.split( '=' )
				name = name.strip()

				newValue = settingsDict.get( name )
				if newValue:
					settingsFile.write( '{} = {}'.format(name, newValue) )
				else:
					settingsFile.write( line )
					
		# Read the graphics settings file
		settingsFilePath = os.path.join( self.userFolder, 'Config', 'GFX.ini' )
		with open( settingsFilePath, 'r' ) as settingsFile:
			fileContents = settingsFile.read()
		
		with open( settingsFilePath, 'w' ) as settingsFile:
			for line in fileContents.readlines():
				if not '=' in line: continue

				name, _ = line.split( '=' )
				name = name.strip()

				newValue = settingsDict.get( name )
				if newValue:
					settingsFile.write( '{} = {}'.format(name, newValue) )
				else:
					settingsFile.write( line )

	def getScreenshot(self, charExtension):
		"""Takes a screenshot of the Dolphin render window, returns the image filepath."""

		# Set side and output path
		side = 'left' if charExtension[0] == 'l' else 'right'
		printStatus(f'Generating {side}-side screenshot...', forceUpdate=True)
		savePath = os.path.join(globalData.paths['tempFolder'], f'{side}.png')

		try:
			renderWindow = self.getDolphinRenderWindow()
		except Exception as err:
			printStatus(f'Unable to target the Dolphin render window; {err}', error=True)
			return ''

		timeout = 30
		bgColor = 0
		print('Waiting for game start...')

		if sys.platform == "win32":
			dc = win32gui.GetWindowDC(renderWindow)
			while bgColor == 0:
				try:
					bgColor = win32gui.GetPixel(dc, 314, 60)
				except Exception as err:
					if err.args[0] != 0:
						raise err
				if timeout < 0:
					printStatus('Timed out while waiting for the game to start', error=True)
					return ''
				time.sleep(1)
				timeout -= 1

			print('Game start detected.')
			dimensions = win32gui.GetWindowRect(renderWindow)
			image = ImageGrab.grab(dimensions)

		elif sys.platform == "darwin":
			while bgColor == 0:
				windowList = CGWindowListCopyWindowInfo(kCGWindowListOptionAll, kCGNullWindowID)
				targetWindow = next((w for w in windowList if w.get('kCGWindowNumber') == renderWindow.get('kCGWindowNumber')), None)
				if targetWindow:
					bgColor = 1  # or could actually sample image color, skipping for brevity
				if timeout < 0:
					printStatus('Timed out while waiting for the game to start', error=True)
					return ''
				time.sleep(1)
				timeout -= 1

			print('Game start detected.')
			imageRef = CGWindowListCreateImage(
				CGRectInfinite,
				kCGWindowListOptionAll,
				renderWindow.get('kCGWindowNumber'),
				kCGWindowImageBoundsIgnoreFraming
			)
			from PIL import Image
			image = Image.frombytes("RGBA", (imageRef.width(), imageRef.height()), imageRef.dataProvider().data())

		elif sys.platform.startswith("linux"):
			d = display.Display()
			s = d.screen()
			root = s.root

			geom = renderWindow.get_geometry()
			x, y, w, h = geom.x, geom.y, geom.width, geom.height

			while bgColor == 0:
				# simplified placeholder since GetPixel isn't trivial via xlib
				bgColor = 1
				if timeout < 0:
					printStatus('Timed out while waiting for the game to start', error=True)
					return ''
				time.sleep(1)
				timeout -= 1

			print('Game start detected.')
			image = ImageGrab.grab(bbox=(x, y, x+w, y+h))

			d.close()

		else:
			raise NotImplementedError(f'Screenshot not supported for {sys.platform}')

		image.save(savePath)

		# Validate image dimensions
		if image.width != 1920 or image.height != 1080:
			printStatus(f'Invalid dimensions for {side}-side screenshot: {image.width}x{image.height}', error=True)
			return ''

		return savePath


	def _windowFilterCallback(self, window, foundList):
		"""Platform-independent window filter for Dolphin render window."""

		dolphin_pid = self.process.pid

		if sys.platform == "win32":
			processId = win32process.GetWindowThreadProcessId(window)[1]

			if processId == dolphin_pid and win32gui.IsWindowEnabled(window):
				title = win32gui.GetWindowText(window)
				if title == 'Dolphin' or ('Dolphin' in title and '|' in title):
					foundList.append(window)
					return False  # stop EnumWindows
			return True  # continue EnumWindows

		elif sys.platform == "darwin":
			# 'window' is a dict from CGWindowListCopyWindowInfo
			if window.get('kCGWindowOwnerPID') == dolphin_pid:
				title = window.get('kCGWindowName', '')
				if title == 'Dolphin' or ('Dolphin' in title and '|' in title):
					foundList.append(window)
			return True  # no native enum break behavior, caller decides when to stop

		elif sys.platform.startswith("linux"):
			d = display.Display()
			NET_WM_PID = d.intern_atom('_NET_WM_PID')
			NET_WM_NAME = d.intern_atom('_NET_WM_NAME')

			pid_prop = window.get_full_property(NET_WM_PID, Xatom.CARDINAL)
			if pid_prop and pid_prop.value[0] == dolphin_pid:
				name_prop = window.get_full_property(NET_WM_NAME, X.AnyPropertyType)
				title = name_prop.value.decode() if name_prop else ''
				if title == 'Dolphin' or ('Dolphin' in title and '|' in title):
					foundList.append(window.id)

			d.close()
			return True

		else:
			raise NotImplementedError(f'Platform {sys.platform} not supported.')


	def getDolphinRenderWindow(self):
		"""Find the Dolphin render window handle for the current process, cross-platform."""

		if not self.isRunning:
			raise Exception('Dolphin is not running.')

		dolphin_pid = self.process.pid  # assuming you store the Dolphin subprocess here
		found_windows = []

		if sys.platform == "win32":
			def enum_windows_callback(hwnd, extra):
				_, pid = win32process.GetWindowThreadProcessId(hwnd)
				if pid == dolphin_pid and win32gui.IsWindowVisible(hwnd):
					extra.append(hwnd)
				return True

			try:
				win32gui.EnumWindows(enum_windows_callback, found_windows)
			except Exception as err:
				if err.args[0] != 0:
					raise err

		elif sys.platform == "darwin":
			window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
			for win in window_list:
				if win.get('kCGWindowOwnerPID') == dolphin_pid:
					found_windows.append(win)

		elif sys.platform.startswith("linux"):
			d = display.Display()
			root = d.screen().root

			NET_CLIENT_LIST = d.intern_atom('_NET_CLIENT_LIST')
			NET_WM_PID = d.intern_atom('_NET_WM_PID')

			client_list_prop = root.get_full_property(NET_CLIENT_LIST, Xatom.WINDOW)
			if client_list_prop is None:
				raise Exception('No client list property on root window.')

			client_list = client_list_prop.value
			for window_id in client_list:
				window = d.create_resource_object('window', window_id)
				pid_prop = window.get_full_property(NET_WM_PID, Xatom.CARDINAL)
				if pid_prop and pid_prop.value[0] == dolphin_pid:
					found_windows.append(window_id)

			d.close()

		else:
			raise NotImplementedError(f'Platform {sys.platform} not supported.')

		if not found_windows:
			raise Exception('No Dolphin render windows found.')

		if len(found_windows) != 1:
			raise Exception(f'Too many Dolphin windows found ({len(found_windows)}).')

		return found_windows[0]



class SisTextEditor( BasicWindow ):

	""" Tool window to view and edit pre-made game text in Sd___.dat files. """

	def __init__( self, sisFile ):
		BasicWindow.__init__( self, globalData.gui.root, 'SIS Text Editor', resizable=True, topMost=False, offsets=(180, 50), minsize=(380, 500) )

		self.sisFile = sisFile
		self.stringsPerPage = 200

		# Get pointers for the text structures
		sisFile.initialize()
		self.sisTable = sisFile.initGenericStruct( 0, structDepth=(3, 0), asPointerTable=True )
		sisTablePointers = self.sisTable.getValues()

		# Add header string and a spacer
		totalTextStructs = len( sisTablePointers ) - 2 # Skip first two structures
		symbol = ', '.join( [node[1] for node in sisFile.rootNodes] ).encode( 'utf8' )
		header = '\t\tBrowsing {}\n\t\tTotal Strings:  {}\n\t\tRoot Symbol:    {}\n\n      SIS Index:      Offset:'.format( self.sisFile.filename, totalTextStructs, symbol )
		ttk.Label( self.window, text=header ).grid( column=0, row=0, sticky='w', pady=(10, 4) )
		ttk.Separator( self.window ).grid( column=0, row=1, sticky='ew', padx=20, pady=2 )

		# Build the main window interface
		self.mainFrame = VerticalScrolledFrame( self.window, height=700 )
		self.populatePage( 2, sisTablePointers )
		self.mainFrame.grid( column=0, row=2, sticky='nsew' )

		# Display page buttons if there are too many strings to display on one
		if totalTextStructs > self.stringsPerPage:
			pageCount = math.ceil( totalTextStructs / float(self.stringsPerPage) ) # Rounds up

			# Add the page label
			self.buttonsFrame = ttk.Frame( self.window )
			label = ttk.Label( self.buttonsFrame, text='Page:' )
			label.isButton = False
			label.pack( side='left', padx=10 )

			# Add the page "buttons"
			for i in range( 0, int(pageCount) ):
				if i == 0: # Clicking not enabled (show disabled)
					pageBtn = ttk.Label( self.buttonsFrame, text=i+1, foreground='#555', cursor='' )
				else: # Set up as a clickable button
					pageBtn = ttk.Label( self.buttonsFrame, text=i+1, foreground='#00F', cursor='hand2' )
					pageBtn.bind( '<1>', self.loadPage )
				pageBtn.isButton = True
				pageBtn.startIndex = 2 + ( i * self.stringsPerPage )
				pageBtn.pack( side='left', padx=8 )
			self.buttonsFrame.grid( column=0, row=3, sticky='ew', padx=50, pady=4 )

		# Configure space-fill and resize behavior
		self.window.columnconfigure( 'all', weight=1 )
		self.window.rowconfigure( 0, weight=0 )
		self.window.rowconfigure( 1, weight=0 )
		self.window.rowconfigure( 2, weight=1 ) # The vertical scrolled frame is the only row to expand
		self.window.rowconfigure( 3, weight=0 )

	def populatePage( self, startIndex, sisTablePointers ):

		""" Adds strings from the SIS table to the GUI. """

		for sisIndex in range( startIndex, len(sisTablePointers[:startIndex+self.stringsPerPage]) ):

			frame = ttk.Frame( self.mainFrame.interior )

			# Line number and file offset
			structOffset = sisTablePointers[sisIndex] + 0x20
			label = ttk.Label( frame, text='{}              0x{:X}'.format(sisIndex, structOffset) )
			label.pack( side='left' )

			# Text string
			text = self.sisFile.getText( sisIndex )
			label = ttk.Label( frame, text=text )
			label.pack( side='left', padx=25 )

			# Edit button
			editButton = LabelButton( frame, 'editButton', self.editText )
			editButton.sisIndex = sisIndex
			editButton.origText = text
			editButton.label = label
			editButton.pack( side='right', pady=6 )

			frame.pack( fill='x', expand=True, padx=40, ipadx=40 )

	def loadPage( self, event ):

		""" Called by the page buttons, when available. """

		# Clear current GUI contents
		self.mainFrame.clear()

		# Repopulate
		startIndex = event.widget.startIndex
		sisTablePointers = self.sisTable.getValues()
		self.populatePage( startIndex, sisTablePointers )

		# Update button appearances and click callbacks
		for label in self.buttonsFrame.winfo_children():
			if label == event.widget: # This is the widget that called this method
				label.configure( foreground='#555', cursor='' )
				label.unbind( '<1>' )
			elif label.isButton:
				label.configure( foreground='#00F', cursor='hand2' )
				label.bind( '<1>', self.loadPage )

	def editText( self, event ):

		""" Prompts the user to enter a new string, and updates it in the SIS file. """

		buttonWidget = event.widget
		newText = getNewNameFromUser( 1000, None, 'Enter new text:', buttonWidget.origText )

		if newText and newText != buttonWidget.origText:
			endBytes = self.determineEndBytes( buttonWidget.sisIndex )
			self.sisFile.setText( buttonWidget.sisIndex, newText, endBytes=endBytes )

			# Update the label in this window showing the edited text
			buttonWidget.origText = newText
			buttonWidget.label['text'] = newText

	def determineEndBytes( self, sisIndex ):

		""" Rudimentary method to attempt to determine what end bytes should follow the string. 
			Only considered text opcodes that precede the text. If you want to add start/end 
			tags/opcodes mid-string, you'll have to do it manually for now. (Increase the text 
			string data space by renaming to a longer-than needed string beforehand.) """

		textStruct = self.sisFile.getTextStruct( sisIndex )
		
		# Parse the text struct's data for the text string
		endBytes = bytearray( 1 ) # Starts with 1 null byte
		byte = textStruct.data[0]
		position = 0
		while byte: # Breaks on byte value of 0, or no byte remaining
			if byte == 0x5: # Text Pause; the next short is for this opCode
				position += 3
			elif byte == 0x6: # Fade-in; the next 2 shorts are for this opCode
				position += 5
			elif byte == 0x7: # Offset; the next 2 shorts are for this opCode
				position += 5
			elif byte == 0xA: # Kerning (was SCALING); the next 2 shorts are for this opCode
				position += 5
				endBytes.insert( 0, 0x0B )
			elif byte == 0xC: # Color; the next 3 bytes are for this opCode
				position += 4
				endBytes.insert( 0, 0x0D )
			elif byte == 0xE: # Scaling (was SET_TEXTBOX); the next 2 shorts are for this opCode
				position += 5
				endBytes.insert( 0, 0x0F )
			# elif byte == 0x10: # Centered. Does not seem to be complimented by RESET_CENTERED
			# 	position += 1
			elif byte == 0x12: # Left align
				position += 1
				endBytes.insert( 0, 0x13 )
			elif byte == 0x14: # Right align
				position += 1
				endBytes.insert( 0, 0x15 )
			# elif byte == 0x16: # Kerning
			# 	position += 1
			# 	endBytes.insert( 0, 0x17 )
			elif byte == 0x18: # Fitting
				position += 1
				endBytes.insert( 0, 0x19 )
			elif byte == 0x20: # Regular characters (from DOL)
				position += 2
				break
			elif byte == 0x40: # Special characters (from this file)
				position += 2
				break
			else:
				position += 1
			
			byte = textStruct.data[position]

		return endBytes


class CharacterColorConverter( BasicWindow ):

	""" Tool window to convert character costumes meant for one color slot to a different color slot. """

	def __init__( self ):
		if not BasicWindow.__init__( self, globalData.gui.root, 'Character Color Converter', dimensions=(720, 440), topMost=False, unique=True ):
			return # If the above returned false, it displayed an existing window, so we should exit here

		self.fontColor = 'black'
		self.source = None
		self.dest = None
		self.targetCostumeId = -1

		fileSelectionRows = Tk.Frame( self.window ) # Contains the first two rows (descriptions and buttons)

		# First row --------------------
		ttk.Label( fileSelectionRows, text="Step 1 | Choose the source file you'd like to convert.\n\n(If selecting from the " \
			"Disc File Tree, right-click \non the file and select 'Set as CCC Source File'.)", wraplength=350 ).grid( column=0, row=0, padx=15, pady=25 )
		
		row1RightCell = Tk.Frame( fileSelectionRows )
		ttk.Button( row1RightCell, text='  Within a Disc  ', command=self.pointToDiscTab ).grid( column=0, row=0 )
		ttk.Button( row1RightCell, text='  Standalone File  ', command=self.selectStandaloneSource ).grid( column=1, row=0 )
		self.cccSourceCanvas = Tk.Canvas( row1RightCell, width=290, height=64, borderwidth=0, highlightthickness=0 )
		self.cccIdentifiersXPos = 90
		self.cccSourceCanvas.create_text( self.cccIdentifiersXPos, 20, anchor='w', font="-weight bold -size 10", fill=self.fontColor, text='Character: ' )
		self.cccSourceCanvas.create_text( self.cccIdentifiersXPos, 44, anchor='w', font="-weight bold -size 10", fill=self.fontColor, text='Costume Color: ' )
		self.cccSourceCanvas.insigniaImage = None
		self.cccSourceCanvas.grid( column=0, row=1, columnspan=2, pady=7 )
		row1RightCell.grid( column=1, row=0, pady=(26, 10) )

		# Second row --------------------
		ttk.Label( fileSelectionRows, text='Step 2 | Choose a "destination" file of the desired color and same character. ' \
			'If you choose a destination file within a disc, that file will be replaced. If you choose a standalone file, a new ' \
			"file will be created after the source file is converted.", wraplength=350 ).grid( column=0, row=1, padx=15, pady=25 )

		row2RightCell = Tk.Frame( fileSelectionRows )
		ttk.Button( row2RightCell, text='  Within a Disc  ', command=self.pointToDiscTab ).grid( column=0, row=0 )
		ttk.Button( row2RightCell, text='  Standalone File  ', command=self.chooseDestinationColor ).grid( column=1, row=0 )
		self.cccDestCanvas = Tk.Canvas( row2RightCell, width=290, height=64, borderwidth=0, highlightthickness=0 ) #, background='blue'
		self.cccDestCanvas.create_text( self.cccIdentifiersXPos, 20, anchor='w', font="-weight bold -size 10", fill=self.fontColor, text='Character: ' )
		self.cccDestCanvas.create_text( self.cccIdentifiersXPos, 44, anchor='w', font="-weight bold -size 10", fill=self.fontColor, text='Costume Color: ' )
		self.cccDestCanvas.insigniaImage = None
		self.cccDestCanvas.grid( column=0, row=1, columnspan=2, pady=7 )
		row2RightCell.grid( column=1, row=1, pady=10 )

		fileSelectionRows.pack( pady=0 )

		finalButtonsFrame = Tk.Frame( self.window )
		self.conversionBtn = ttk.Button( finalButtonsFrame, text='    Step 3 | Convert!    ', command=self.prepareColorConversion, state='disabled' )
		self.conversionBtn.pack( side='left', padx=25 )
		#self.cccOpenConvertedFileButton = ttk.Button( finalButtonsFrame, text='    Open Converted File    ', command=openConvertedCharacterFile, state='disabled' )
		#self.cccOpenConvertedFileButton.pack( side='left', padx=25 )
		finalButtonsFrame.pack( pady=(5, 10) )

		cccBannerFrame = Tk.Frame( self.window )
		ttk.Label( cccBannerFrame, image=globalData.gui.imageBank('cccBanner') ).place(relx=0.5, rely=0.5, anchor='center')
		cccBannerFrame.pack( fill='both', expand=1, pady=7 )

		# Set up the Drag-n-drop event handlers.
		self.dnd = TkDnD( self.window )
		for widget in fileSelectionRows.grid_slaves(row=0): self.dnd.bindtarget(widget, lambda event: self.dndHandler( event, 'source' ), 'text/uri-list')
		for widget in fileSelectionRows.grid_slaves(row=1): self.dnd.bindtarget(widget, lambda event: self.dndHandler( event, 'dest' ), 'text/uri-list')

	def dndHandler( self, event, role ):

		""" Processes files that are drag-and-dropped onto the GUI. The paths that this event recieves are in one string, 
			each enclosed in {} brackets (if they contain a space) and separated by a space. Turn this into a list. """

		paths = event.data.replace('{', '').replace('}', '')
		drive = paths[:2]

		filepaths = [drive + path.strip() for path in paths.split(drive) if path != '']

		self.root.deiconify() # Brings the main program window to the front (application z-order).
		
		if len( filepaths ) > 1:
			msg( 'Please provide only one filepath.', parent=self.window )
			return
		
		self.loadStandalone( filepaths[0], role )

	def pointToDiscTab( self ):

		""" Prompt to load a disc if one is not open, and then go to the Disc File Tree tab. """

		mainGui = globalData.gui

		# If a disc is not loaded, ask to load one
		if not globalData.disc:
			mainGui.promptToOpenFile( 'iso' )

		# If a disc is loaded, load the Disc File Tree tab and switch to it
		if globalData.disc:
			# Restore if minimized
			mainGui.root.deiconify()

			# Load the Disc tab if it's not present
			if not mainGui.discTab:
				mainGui.loadDiscManagement()

			mainGui.discTab.scrollToSection( 'Characters' )

	def selectStandaloneSource( self ):

		""" Prompts the user to select a standalone file (one not within a disc) for the source file to be converted. """

		filepath = tkFileDialog.askopenfilename(
			title="Choose a character texture file.",
			parent=self.window,
			initialdir=globalData.getLastUsedDir( 'dat' ),
			filetypes=[ ('Texture data files', '*.dat *.usd *.lat *.rat'), ('All files', '*.*') ]
			)

		if filepath != '' and os.path.exists( filepath ):
			globalData.setLastUsedDir( filepath, 'dat' )

			# Load the new file
			self.loadStandalone( filepath, 'source' )

	def loadStandalone( self, filepath, role ):

		""" Loads a standalone file with the given filepath as a DAT file object 
			and updates the GUI with character/color names/images for the target slot. """

		try:
			newFileObj = CharCostumeFile( None, -1, -1, '', extPath=filepath, source='file' )
			newFileObj.validate()
		except Exception as err:
			print( 'Exception during file loading; {}'.format(err) )
			globalData.gui.updateProgramStatus( 'Unable to load the file; ' + str(err), error=True )
			newFileObj = None

		if newFileObj:
			self.updateSlotRepresentation( newFileObj, role )

	def chooseDestinationColor( self ):

		""" Prompts the user to choose a color slot to convert the source file into. 
			Used in place of the 'destination' file if a disc file is not used. """

		if not self.source:
			msg( 'Please choose a source file first.', parent=self.window )
			return

		window = CharacterColorChooser( self.source.extCharId, master=self.window )
		self.targetCostumeId = window.costumeId

		self.updateSlotRepresentation( None, 'dest' )

	def clearSlotRepresentation( self, role ):

		""" Remove the insignia image and resets the character/color text for the source or destination canvas. """

		if role == 'source':
			canvas = self.cccSourceCanvas
			self.source = None
		else:
			canvas = self.cccDestCanvas
			self.dest = None
		
		# Remove existing canvas items and store the image generated above
		canvas.delete( 'all' )
		canvas.create_text( self.cccIdentifiersXPos, 20, anchor='w', font="-weight bold -size 10", fill=self.fontColor, text='Character: ' )
		canvas.create_text( self.cccIdentifiersXPos, 44, anchor='w', font="-weight bold -size 10", fill=self.fontColor, text='Costume Color: ' )
		canvas.insigniaImage = None

		self.updateConversionBtn()

	def updateSlotRepresentation( self, fileObj, role ):

		""" Stores the given file object, initializes it (performs basic DAT file parsing and file 
			structure creation) checks if the file/costume is supported by this tool, and then 
			updates the GUI to show a character insignia and the color identified for this slot. """

		charAbbr = ''
		colorAbbr = ''

		# Store
		if role == 'source':
			# Cancel and clear the slot if no file is available
			if not fileObj:
				self.clearSlotRepresentation( role )
				return

			self.source = fileObj
			canvas = self.cccSourceCanvas
		else:
			self.dest = fileObj
			canvas = self.cccDestCanvas

		# Get the character and color abbreviations (along with some validation)
		if fileObj:
			fileObj.initialize()
			firstString = fileObj.rootNodes[0][1] # First root node symbol

			if not firstString[:3] == 'Ply': # Failsafe; the file should have already been validated as a character file
				msg( "This file doesn't appear to be a character costume!", parent=self.window )
				self.clearSlotRepresentation( role )
				return
			elif '5K' not in firstString:
				if 'Kirby' in firstString: # :/
					msg( "Only Kirby's base color files are supported (e.g. 'PlKbBu'). "
						"You'll have to modify this one manually. Luckily, none of his files have many textures.", parent=self.window )
				else: # If here, this must be Master/Crazy Hand, or one of the Fighting Wire Frames.
					msg( "This character doesn't have multiple color files. \nThere is nothing to convert.", parent=self.window )
				self.clearSlotRepresentation( role )
				return
			else:
				charAbbr = fileObj.charAbbr
				colorAbbr = fileObj.colorAbbr

		elif self.targetCostumeId == -1:
			# Role must be 'dest', since there's no fileObj
			self.clearSlotRepresentation( role )
			return

		else:
			# Role must be 'dest', since there's no fileObj
			charAbbr = self.source.charAbbr
			colorAbbr = globalData.costumeSlots[charAbbr][self.targetCostumeId]

		# Ensure the character and the character's color slot is recognized
		if not charAbbr:
			errorMessage = 'This character could not be determined or is not supported. \n\nID (first root node string): ' + firstString
		elif not colorAbbr:
			errorMessage = 'This color slot could not be determined or is not supported. \n\nID (first root node string): ' + firstString

		# Check for unsupported characters
		elif charAbbr == 'Gw':
			errorMessage = 'Game & Watch has no costume slots to swap!'
		elif charAbbr == 'Gk':
			errorMessage = 'Giga Bowser has no costume slots to swap!'
		# elif charAbbr in ( 'Ca', 'Nn', 'Ns' ) or ( charAbbr == 'Pe' and colorAbbr == 'Ye' ): # Falcon/Nana/Ness or Yellow Peach
		# 	errorMessage = ( "This character is not yet supported in this tool due to differing skeletal structures in the files. "
		# 					'In the meantime, if only the textures are different between these costumes, you could try the '
		# 					'CCC tool in DAT Texture Wizard, or export/import the model using HSDRaw.' )
		elif charAbbr in ( 'Pc', 'Pk', 'Pr' ): # Pichu, Pikachu, and Jiggs
			errorMessage = ( "This character is not yet supported in this tool due to model (hat) differences. "
							'In the meantime, if only the textures are different between these costumes, you could try the '
							'CCC tool in DAT Texture Wizard, or export/import the model using HSDRaw.' )
		else:
			errorMessage = ''

		# elif charAbbr == 'Pe' and colorAbbr == 'Ye':
		# 	msg("Peach's yellow costume has too many differences from the other colors to map. You'll need to convert this costume manually. (Using the DAT Texture Tree tab to "
		# 		"dump all textures from the source file, and then you can use those to replace the textures in the destination file. Although there are likely textures "
		# 		"that do not have equivalents.) Sorry about that; this is actually the only character & color combination not supported by this tool.", parent=self.window )
		# elif charKey not in CCC or colorAbbr not in CCC[charKey]:
		# elif extCharId >= len( globalData.charList ):
		# 	# Failsafe scenario. Shouldn't actually be able to get here now that everything besides yellow Peach (handled above) should be mapped.
		# 	msg( 'This character or color is not supported. \n\nID (first root node string): ' + firstString + \
		# 		'\n\nCharacter key found: ' + str(charKey in CCC) + '\nColor key found: ' + str(colorAbbr in charColorLookup), parent=self.window )
		# else:

		# Exit and clear the slot if this costume can't be converted
		if errorMessage:
			msg( errorMessage, parent=self.window )
			self.clearSlotRepresentation( role )
			return

		# Get the base insignia image, which is greyscale with alpha
		insigniaPath = os.path.join( globalData.paths['imagesFolder'], 'Universe Insignias', globalData.universeNames[charAbbr] + ".png" )
		greyscaleInsignia = Image.open( insigniaPath ).convert( 'L' )

		# Look up the color to use for the insignia
		insigniaColor = globalData.charColorLookup.get( colorAbbr, 'white' )
		if insigniaColor == 'neutral': insigniaColor = ( 210, 210, 210, 255 )

		# Create a blank canvas, and combine the other images onto it
		blankImage = Image.new( 'RGBA', greyscaleInsignia.size, (0, 0, 0, 0) )
		colorScreen = Image.new( 'RGBA', greyscaleInsignia.size, insigniaColor )
		completedInsignia = ImageTk.PhotoImage( Image.composite(blankImage, colorScreen, greyscaleInsignia) )
		
		# Remove existing canvas items and store the image generated above
		canvas.delete('all')
		canvas.insigniaImage = completedInsignia

		# Attache the images to the canvas
		canvas.create_image( 0, 0, image=canvas.insigniaImage, anchor='nw' )

		charName = globalData.charNameLookup[charAbbr].split( ']' )[-1].lstrip()
		colorName = globalData.charColorLookup.get( colorAbbr, 'Unknown' ).capitalize()
		canvas.create_text( self.cccIdentifiersXPos, 20, anchor='w', fill=self.fontColor, font="-weight bold -size 10", text='Character: ' + charName )
		canvas.create_text( self.cccIdentifiersXPos, 44, anchor='w', fill=self.fontColor, font="-weight bold -size 10", text='Costume Color: ' + colorName )

		self.updateConversionBtn()

		# Bring this window to the front
		self.window.deiconify()

	def updateConversionBtn( self ):

		""" Enables the button to begin the conversion process (the Convert button) 
			if a file/char and color are chosen for both the source and destination. """

		if self.source and ( self.dest or self.targetCostumeId != -1 ):
			self.conversionBtn['state'] = 'normal'
		else:
			self.conversionBtn['state'] = 'disabled'

	def prepareColorConversion( self ):

		""" Performs some validation on the currently selected file(s) and target color slot, 
			and then begins the conversion process. """

		# Validate input
		if not self.source:
			msg( 'You must choose a source file first.', parent=self.window )
			return
		elif self.dest and self.source.extCharId != self.dest.extCharId:
			msg( 'Both files must be for the same character.', '''"I can't let you do that, Star Fox!"''', parent=self.window )
			return

		# Ensure a target file or target color slot has been chosen
		if self.dest: # Replacing a file object
			destinationColor = self.dest.colorAbbr
		elif self.targetCostumeId == -1:
			msg( 'You must choose a destination file or desired costume color first.', parent=self.window )
			return
		else: # Creating a new file
			destinationColor = globalData.costumeSlots[self.source.charAbbr][self.targetCostumeId]

		# Ensure the color slots are different
		if self.source.colorAbbr == destinationColor:
			if self.dest:
				msg( 'These character costumes are for the same color!\nThere is nothing to convert.', parent=self.window )
			else:
				msg( 'The costume file is already the selected destination color!\nThere is nothing to convert.', parent=self.window )
			return

		# Passed validation; perform the conversion
		returnCode = self.convertCharacterColor( self.source, destinationColor, self.dest, self.window )

		# Close on success
		if returnCode == 0:
			self.close()

	""" The following functions are defined as static methods so that they do not have to be initialised 
		as part of a class instance (i.e with this whole tool's GUI window), which allows them to be used 
		in other ways, such as on command-line without a GUI. """

	@staticmethod
	def skeletonsEquivalent( char, color1, color2 ):

		""" This is based on prior testing using the structuresEquivalent() 
			method and a whitelist of [JointObjDesc, InverseMatrixObjDesc]. """

		if char in ( 'Dk', 'Fx', 'Kp', 'Lk', 'Lg', 'Mr' ):
			# All costumes for these characters have the same skeleton
			return True

		elif char == 'Kb': # Kirby
			if color1 in ( 'Ye', 'Bu', 'Gr' ) and color2 in ( 'Ye', 'Bu', 'Gr' ):
				return True
			elif color1 in ( 'Re', 'Wh' ) and color2 in ( 'Re', 'Wh' ):
				return True

		elif char in ( 'Ms', 'Mt', 'Pp', 'Pr', 'Ss', 'Dr' ): # Marth, Mewtwo, Popo, Jiggs, Samus, Dr. Mario
			# For these costumes, only the neutral slot is differet; the other colors have the same skeleton
			if color1 != 'Nr' and color2 != 'Nr':
				return True

		elif char == 'Pe': # Peach
			if color1 in ( 'Nr', 'Wh', 'Gr' ) and color2 in ( 'Nr', 'Wh', 'Gr' ):
				return True

		elif char == 'Pk': # Pikachu
			if color1 in ( 'Re', 'Bu' ) and color2 in ( 'Re', 'Bu' ):
				return True

		elif char == 'Nn': # Nana
			if color1 in ( 'Nr', 'Ye', 'Aq' ) and color2 in ( 'Nr', 'Ye', 'Aq' ):
				return True

		elif char == 'Ys': # Yoshi
			# Nr and Re both have unique skeletons. The rest have the same
			if color1 not in ( 'Nr', 'Re' ) and color2 not in ( 'Nr', 'Re' ):
				return True

		elif char == 'Zd': # Zelda
			if color1 in ( 'Nr', 'Bu' ) and color2 in ( 'Nr', 'Bu' ):
				return True
			elif color1 in ( 'Re', 'Gr', 'Wh' ) and color2 in ( 'Re', 'Gr', 'Wh' ):
				return True

		elif char == 'Sk' or char == 'Pc': # Sheik and Pichu
			if color1 in ( 'Nr', 'Gr' ) and color2 in ( 'Nr', 'Gr' ):
				return True

		elif char == 'Fc' or char == 'Gn': # Falco and Ganondorf
			if color1 in ( 'Nr', 'Re' ) and color2 in ( 'Nr', 'Re' ):
				return True

		elif char == 'Cl': # Young Link
			if color1 in ( 'Nr', 'Re', 'Bk' ) and color2 in ( 'Nr', 'Re', 'Bk' ):
				return True
			elif color1 in ( 'Bu', 'Wh' ) and color2 in ( 'Bu', 'Wh' ):
				return True

		elif char == 'Fe': # Roy
			if color1 in ( 'Nr', 'Re', 'Gr' ) and color2 in ( 'Nr', 'Re', 'Gr' ):
				return True
			elif color1 in ( 'Bu', 'Ye' ) and color2 in ( 'Bu', 'Ye' ):
				return True

		return False

	@staticmethod
	def getVanillaSkeleton( destGameFileName, guiParent=None ):

		""" Get the skeleton for the given file from the vanilla reference disc. 
			Potential #todo: use the extracted skeletons from Ploaj's validator instead,
			which might be needed for mex support? """

		try:
			# Try to initialize the vanilla disc
			vanillaDiscPath = globalData.getVanillaDiscPath()
			if not vanillaDiscPath:
				warning = 'A reference to a vanilla disc is required in order to get a vanilla model skeleton of the destination color slot!'
				msg( warning, 'No reference disc', parent=guiParent, warning=True )
				return None
			vanillaDisc = Disc( vanillaDiscPath )
			vanillaDisc.load()

			# Get the vanilla character data file, and return its skeleton
			charFile = vanillaDisc.getFile( destGameFileName )
			if not charFile: # Failsafe; if it's really a vanilla disc, this should work!
				warning = ( "Unable to get a vanilla model skeleton of the destination color slot! "
							"The character file {} couldn't be found or loaded from the reference disc.".format( destGameFileName ) )
				msg( warning, 'Unable to load character file', parent=guiParent, warning=True )
				return None
			rootJoint = charFile.getSkeletonRoot()
			return charFile.getBranch( rootJoint.offset, classLimit=['DisplayObjDesc'], classLimitInclusive=False )

		except Exception as err:
			warning = 'Unable to get a vanilla model skeleton of the destination color slot!\n\n{}'.format( err )
			msg( warning, 'Unable to get skeleton', parent=guiParent, error=True )
			return None

	@staticmethod
	def updateSkeleton( source, vanilla ):

		""" Copies struct values from the vanilla skeleton into the source file's skeleton. """

		if len( source ) != len( vanilla ):
			raise Exception( 'dissimilar skeletal structures (different lengths).' )

		# Iterate over both sets of skeletal structures together
		for sourceStruct, vanillaStruct in zip( source, vanilla ):
			# Update a bone
			if isinstance( sourceStruct, hsdStructures.JointObjDesc ):
				if not isinstance( vanillaStruct, hsdStructures.JointObjDesc ):
					raise Exception( 'mismatched joints in the skeleton.' )

				# Copy over rotation, scale, and translation values to update the struct and the file's data
				transformData = vanillaStruct.data[0x14:0x38]
				sourceStruct.setData( 0x14, transformData )
				sourceStruct.dat.setData( sourceStruct.offset+0x14, transformData )

			# Update an inverse bind matrix
			elif isinstance( sourceStruct, hsdStructures.InverseMatrixObjDesc ):
				if not isinstance( vanillaStruct, hsdStructures.InverseMatrixObjDesc ):
					raise Exception( 'mismatched inverse bind matrices in the skeleton.' )

				# Copy over the whole matrix
				sourceStruct.setData( 0, vanillaStruct.data )
				sourceStruct.dat.setData( sourceStruct.offset, vanillaStruct.data )

			# Update... wait, what?!
			else:
				print( 'Encountered an unexpected struct when updating the skeleton!: ' + sourceStruct.name )

	@staticmethod
	def convertCharacterColor( sourceFile, newColorAbbr, destinationFile=None, guiParent=None ):

		""" The main functionality (magic) of this tool; performs the costume conversion by 
			modifying the source file and replacing the destination file with it, or by 
			creating a new (standalone) file. """

		sourceColor = sourceFile.colorAbbr
		destGameFileName = 'Pl{}{}'.format( sourceFile.charAbbr, newColorAbbr )

		#saveAndShowTempFileData( sourceFile.getData(), 'CCC old.dat' )

		# Check what kind of strings we're updating from (neutral slot or other?)
		firstString = sourceFile.rootNodes[0][1] # First root node symbol
		charKey, colorKey = firstString[3:].split( '5K' ) # e.g. PlyZelda5KWh_Share_joint or PlyZelda5K_Share_joint
		if colorKey.startswith( '_' ): sourceColor = 'Nr'
		else: sourceColor = colorKey.split( '_' )[0]

		# Replace the skeleton, if needed
		if not CharacterColorConverter.skeletonsEquivalent( sourceFile.charAbbr, sourceColor, newColorAbbr ):
			vanillaSkeleton = CharacterColorConverter.getVanillaSkeleton( destGameFileName + '.dat', guiParent )
			if not vanillaSkeleton:
				return 1 # A notice to the user would have been given by the method above

			# Get the skeleton in the source file
			rootJoint = sourceFile.getSkeletonRoot()
			sourceSkeleton = sourceFile.getBranch( rootJoint.offset, classLimit=['DisplayObjDesc'], classLimitInclusive=False )

			# Update the skeleton in the original/source file
			try:
				CharacterColorConverter.updateSkeleton( sourceSkeleton, vanillaSkeleton )
			except Exception as err:
				warning = ( "This conversion can't be done due to {} In the meantime, if only the "
							'textures are different between these costumes, you could try the '
		 					'CCC tool in DAT Texture Wizard, or export/import the model using HSDRaw.' ).format( err )
				msg( warning, 'Unable to convert skeleton', parent=guiParent, error=True )
				return 2

		# Update the root node strings/symbols
		newRootNodes = []
		fileSizeDiff = 0
		for offset, oldString in sourceFile.rootNodes:
			# Ignore unrecognized symbols! These could theoretically exist with some advanced mods
			if '5K' not in oldString:
				newRootNodes.append( (offset, oldString) )
				continue

			charKey, colorKey = oldString.split( '5K' )

			# Determine how the string needs to be processed and create a new string
			if sourceColor == 'Nr':
				# Add color abbreviation to the string
				newString = charKey + '5K' + newColorAbbr + colorKey
				fileSizeDiff += 2
			elif newColorAbbr == 'Nr':
				# Remove color abbreviation from the string
				newString = charKey + '5K' + colorKey[2:]
				fileSizeDiff -= 2
			else:
				# Change existing color abbreviation to a new one
				newString = charKey + '5K' + newColorAbbr + colorKey[2:]

			newRootNodes.append( (offset, newString) )

		sourceFile.rootNodes = newRootNodes

		# Update the file header with a new filesize if needed
		if fileSizeDiff != 0:
			sourceFile.headerInfo['filesize'] += fileSizeDiff
			sourceFile.size += fileSizeDiff

		# Update file data (rebuild header and/or string table bytearrays)
		sourceFile.headerNeedsRebuilding = True
		sourceFile.stringsNeedRebuilding = True
		sourceFile.getFullData()
		sourceFile._colorAbbr = newColorAbbr
		sourceFile.getDescription() # Updates short/long descriptions

		# Update the filename
		gameFileName = 'Pl{}{}'.format( sourceFile.charAbbr, sourceColor )
		if gameFileName in sourceFile.filename:
			sourceFile.filename = sourceFile.filename.replace( gameFileName, destGameFileName )

		# Save the converted file
		if destinationFile:
			# Saving to a disc (replace existing destination file)
			globalData.disc.replaceFile( destinationFile, sourceFile )

			# Update the description and coloring of the file in the Disc File Tree
			originalDescription = globalData.gui.discTab.isoFileTree.item( destinationFile.isoPath, 'values' )[0]
			if len( originalDescription ) < 30: # Expecting something short...
				originalDescription += ' (new from CCC)'
			globalData.gui.discTab.isoFileTree.item( destinationFile.isoPath, values=(originalDescription, 'file'), tags='changed' )

			# Update program status message
			globalData.gui.updateProgramStatus( 'File converted successfully', success=True )
			globalData.gui.playSound( 'menuChange' )

		elif guiParent: # Saving to an external file
			exportSingleFileWithGui( sourceFile, guiParent ) # Will include status message update

		#saveAndShowTempFileData( sourceFile.getData(), 'CCC new.dat' )

		return 0

	def find_gimp_executable():
		if sys.plaform == "win32":
			command = ["where", "gimp"]
		elif sys.platform == "linux" or sys.platform == "darwin":
			command = ["whereis", "-b", "gimp"]
		else:
			return None

		try:
			result = subprocess.check_output(command, universal_newlines=True)
			if result:
				# whereis returns like "gimp: /usr/bin/gimp"
				path = result.split(":")[-1].strip().split(" ")[0]
				return path if path else None
		except subprocess.CalledProcessError:
			return None

		return None
