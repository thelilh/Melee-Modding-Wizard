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

# External logic dependencies
import os
import time
import math
import random
import webbrowser
from binascii import hexlify

# External GUI dependencies
from tkinter import ttk
from tkinter import filedialog as tkFileDialog
import tkinter as Tk
from PIL import Image, ImageTk
from tkinter.messagebox import askyesno

from FileSystem.charFiles import CharCostumeFile
from FileSystem.hsdFiles import StageFile

# Internal dependencies
import globalData
from audioManager import AudioManager
from FileSystem import fileFactory, SisFile, MusicFile, CharDataFile, CharAnimFile
from FileSystem.disc import Disc
from FileSystem.fileBases import FileBase
from basicFunctions import (
    grammarfyList, msg, printStatus, copyToClipboard, removeIllegalCharacters, 
    uHex, humansize, createFolders, saveAndShowTempFileData
)
from guiSubComponents import (
    ClickText,
    cmsg,
    exportSingleTexture,
    importGameFiles,
    importSingleTexture,
    exportSingleFileWithGui,
    importSingleFileWithGui,
    getNewNameFromUser,
    DisguisedEntry,
    ToolTip, NeoTreeview
)
from textureEditing import TexturesEditor
from tools import CharacterColorConverter, SisTextEditor



class DiscTab( ttk.Frame ):

	def __init__( self, parent, mainGui ):

		self.debugMode = False

		ttk.Frame.__init__( self, parent ) #, padding="11 0 0 11" ) # Padding order: Left, Top, Right, Bottom.
		
		# Add this tab to the main GUI, and add drag-and-drop functionality
		mainGui.mainTabFrame.add( self, text=' Disc File Tree ' )
		mainGui.dnd.bindtarget( self, mainGui.dndHandler, 'text/uri-list' )

		# Disc shortcut links
		fileTreeColumn = ttk.Frame( self, width=350 )
		isoQuickLinks = Tk.Frame( fileTreeColumn )
		ttk.Label( isoQuickLinks, text='Disc Shortcuts:' ).pack( side='left', padx=4 )
		ttk.Label( isoQuickLinks, text='System', foreground='#00F', cursor='hand2' ).pack( side='left', padx=4 )
		ttk.Label( isoQuickLinks, text='|' ).pack( side='left', padx=4 )
		ttk.Label( isoQuickLinks, text='Characters', foreground='#00F', cursor='hand2' ).pack( side='left', padx=4 )
		ttk.Label( isoQuickLinks, text='|' ).pack( side='left', padx=4 )
		ttk.Label( isoQuickLinks, text='Menus', foreground='#00F', cursor='hand2' ).pack( side='left', padx=4 )
		ttk.Label( isoQuickLinks, text='|' ).pack( side='left', padx=4 )
		ttk.Label( isoQuickLinks, text='Stages', foreground='#00F', cursor='hand2' ).pack( side='left', padx=4 )
		ttk.Label( isoQuickLinks, text='|' ).pack( side='left', padx=4 )
		ttk.Label( isoQuickLinks, text='Strings', foreground='#00F', cursor='hand2' ).pack( side='left', padx=4 )
		for label in isoQuickLinks.winfo_children():
			if label['text'] != '|': label.bind( '<1>', self.quickLinkClicked )
		isoQuickLinks.pack( pady=3 )

		# File Tree start
		isoFileTreeWrapper = Tk.Frame( fileTreeColumn ) # Contains just the ISO treeview and its scroller (since they need a different packing than the above links).
		self.isoFileScroller = Tk.Scrollbar( isoFileTreeWrapper )
		self.isoFileTree = NeoTreeview( isoFileTreeWrapper, columns=('description'), yscrollcommand=self.isoFileScroller.set )
		self.isoFileTree.heading( '#0', anchor='center', text='File     (Sorted by FST)' ) # , command=lambda: treeview_sort_column(self.isoFileTree, 'file', False)
		self.isoFileTree.column( '#0', anchor='center', minwidth=160, stretch=1, width=180 ) # "#0" is implicit in the columns definition above.
		self.isoFileTree.heading( 'description', anchor='center', text='Description' )
		self.isoFileTree.column( 'description', anchor='w', minwidth=180, stretch=1, width=330 )
		self.isoFileTree.tag_configure( 'changed', foreground='red' )
		self.isoFileTree.tag_configure( 'changesSaved', foreground='#292' ) # The 'save' green color
		self.isoFileTree.tag_configure( 'cFolder', foreground='#006ea9' )
		self.isoFileTree.tag_configure( 'nFolder', foreground='#006ea9' )
		self.isoFileTree.grid( column=0, row=0, sticky='nsew' )
		self.isoFileScroller.config( command=self.isoFileTree.yview )
		self.isoFileScroller.grid( column=1, row=0, sticky='ns' )

		# Add the background image to the file tree
		self.isoFileTreeBg = Tk.Label( self.isoFileTree, image=mainGui.imageBank('dndTarget'), borderwidth=0, highlightthickness=0 )
		self.isoFileTreeBg.place( relx=0.5, rely=0.5, anchor='center' )

		# Add treeview event handlers
		self.isoFileTree.bind( '<<TreeviewSelect>>', self.onFileTreeSelect )
		self.isoFileTree.bind( '<Double-1>', self.browseTexturesFromDisc )
		self.isoFileTree.bind( "<3>", self.createContextMenu ) # Right-click

		isoFileTreeWrapper.pack( fill='both', expand=1 )
		isoFileTreeWrapper.columnconfigure( 0, weight=1 )
		isoFileTreeWrapper.columnconfigure( 1, weight=0 )
		isoFileTreeWrapper.rowconfigure( 0, weight=1 )
		fileTreeColumn.pack( side='left', fill='both', expand=1 )
		fileTreeColumn.pack_propagate( False )

				# ISO File Tree end, and ISO Information panel begins here

		isoOpsPanel = ttk.Frame( self, padding='0 9 0 0' ) # Padding order: Left, Top, Right, Bottom.

		# Display the Game ID and banner image
		self.isoOverviewFrame = Tk.Frame( isoOpsPanel )
		self.gameIdText = Tk.StringVar()
		ttk.Label( self.isoOverviewFrame, textvariable=self.gameIdText, font="-weight bold" ).grid( column=0, row=0, padx=20, sticky='e' )
		self.updatingBanner = False
		self.stopAndReloadBanner = False
		self.bannerCanvas = Tk.Canvas( self.isoOverviewFrame, width=96, height=32, borderwidth=0, highlightthickness=0 )
		self.bannerCanvas.pilImage = None
		self.bannerCanvas.bannerGCstorage = None
		self.bannerCanvas.canvasImageItem = None
		self.bannerCanvas.grid( column=1, row=0, padx=20, sticky='w' )
		self.isoOverviewFrame.columnconfigure( 0, weight=1 )
		self.isoOverviewFrame.columnconfigure( 1, weight=1 )
		self.isoOverviewFrame.pack( fill='x', ipadx=8, pady=(22, 18) )

		# Display a shortend disc path
		self.isoPathShorthand = Tk.StringVar()
		self.isoPathShorthandLabel = ttk.Label( isoOpsPanel, textvariable=self.isoPathShorthand )
		self.isoPathShorthandLabel.pack()

		# Add the button to open Disc Details
		ttk.Button( isoOpsPanel, text='Edit Disc Details', command=self.addDiscDetailsTab, width=20 ).pack( pady=(18, 8) )

		# Selected file details
		internalFileDetails = ttk.Labelframe( isoOpsPanel, text='  File Details  ', labelanchor='n' )
		self.isoOffsetText = Tk.StringVar()
		self.isoOffsetText.set( 'Disc Offset: ' )
		ttk.Label( internalFileDetails, textvariable=self.isoOffsetText, width=27, anchor='w' ).pack( padx=15, pady=4 )
		self.internalFileSizeText = Tk.StringVar()
		self.internalFileSizeText.set( 'File Size: ' )
		ttk.Label( internalFileDetails, textvariable=self.internalFileSizeText, width=27, anchor='w' ).pack( padx=15, pady=0 )
		self.internalFileSizeLabelSecondLine = Tk.StringVar()
		self.internalFileSizeLabelSecondLine.set( '' )
		ttk.Label( internalFileDetails, textvariable=self.internalFileSizeLabelSecondLine, width=27, anchor='w' ).pack( padx=15, pady=0 )
		internalFileDetails.pack( padx=15, pady=16, ipady=4 )

		# Primary ISO operation buttons
		self.isoOpsPanelButtons = Tk.Frame( isoOpsPanel )
		ttk.Button( self.isoOpsPanelButtons, text="Export", command=self.exportIsoFiles, state='disabled' ).grid( row=0, column=0, padx=7 )
		ttk.Button( self.isoOpsPanelButtons, text="Import", command=self.importSingleFile, state='disabled' ).grid( row=0, column=1, padx=7 )
		ttk.Button( self.isoOpsPanelButtons, text="Restore to Vanilla", command=self.restoreFiles, state='disabled', width=20 ).grid( row=1, column=0, columnspan=2, pady=(7,0) )
		ttk.Button( self.isoOpsPanelButtons, text="Browse Textures", command=self.browseTexturesFromDisc, state='disabled', width=20 ).grid( row=2, column=0, columnspan=2, pady=(7,0) )
		#ttk.Button( self.isoOpsPanelButtons, text="Analyze Structure", command=self.analyzeFileFromDisc, state='disabled', width=18 ).grid( row=3, column=0, columnspan=2, pady=(7,0) )
		self.isoOpsPanelButtons.pack( pady=2 )

		# Add the Magikoopa image
		kamekFrame = Tk.Frame( isoOpsPanel )
		ttk.Label( kamekFrame, image=mainGui.imageBank('magikoopa') ).place( relx=0.5, rely=0.5, anchor='center' )
		kamekFrame.pack( fill='both', expand=1 )

		isoOpsPanel.pack( side='left', fill='both', expand=1 )
		isoOpsPanel.pack_propagate( False )

	def addDiscDetailsTab( self ):

		""" Adds the Disc Details tab to the GUI, if it has not already been added, 
			populates it, and then switches to it. """

		mainGui = globalData.gui
		
		# Add/initialize the Disc Details tab, and load the disc's info into it
		if not mainGui.discDetailsTab:
			mainGui.discDetailsTab = DiscDetailsTab( mainGui.mainTabFrame, mainGui )
		
		mainGui.discDetailsTab.loadDiscDetails()

		# Switch to the new tab
		mainGui.discTab.updateBanner( mainGui.discDetailsTab )
		mainGui.mainTabFrame.select( mainGui.discDetailsTab )

	def clear( self ):

		""" Clears the GUI of the currently loaded disc. """

		globalData.disc.unsavedChanges = []
		self.isoFileTreeBg.place_forget() # Removes the background image if present

		# Delete the current items in the tree
		for item in self.isoFileTree.get_children():
			self.isoFileTree.delete( item )

		# If desired, temporarily show the user that all items have been removed (Nice small indication that the iso is actually being loaded)
		globalData.gui.root.update_idletasks()

		# Disable buttons in the iso operations panel. They're re-enabled later if all goes well
		for widget in self.isoOpsPanelButtons.winfo_children():
			#if widget.winfo_class() == 'TButton':
				widget.config( state='disabled' ) # Will stay disabled if there are problems loading a disc.

		# Set the GUI's other values back to default.
		self.isoOffsetText.set( 'Disc Offset: ' )
		self.internalFileSizeText.set( 'File Size: ' )
		self.internalFileSizeLabelSecondLine.set( '' )

	def updateBanner( self, targetTab ):

		""" Updates the displayed banner image on this tab or the Disc Details tab. 
			If the targetTab is currently in-view/selected, an animation will be used to replace the image. """
			
		# Prevent conflicts with an instance of this function that may already be running (let that instance finish its current iteration and call this function again)
		if targetTab.updatingBanner:
			targetTab.stopAndReloadBanner = True
			return
		targetTab.updatingBanner = True

		# Check current visibility to see if there's a canvas that should be animated
		currentlySelectedTab = globalData.gui.root.nametowidget( globalData.gui.mainTabFrame.select() )
		canvas = targetTab.bannerCanvas

		# Remove the current banner image
		if currentlySelectedTab == targetTab and canvas.bannerGCstorage and not self.debugMode:
			# Remove the banner on the current disc tab using a vertical fade
			width, height = canvas.pilImage.size
			pixels = canvas.pilImage.load()
			bandHeight = 30
			for y in range( height + bandHeight ):

				# Restart if this function is called while already in-progress
				if targetTab.stopAndReloadBanner:
					targetTab.updatingBanner = False
					targetTab.stopAndReloadBanner = False
					self.updateBanner( self )
					return

				for bandSegment in range( bandHeight ): # This will modify the current row, and then prior rows (up to the bandHeight)
					targetRow = y - bandSegment
					if targetRow >= 0 and targetRow < height:
						for x in range( width ):
							initialAlpha = pixels[x, targetRow][3]
							newAlpha = int( initialAlpha - ( float(bandSegment)/bandHeight * initialAlpha ) )
							#if x == 0: print 'row', targetRow, ':', initialAlpha, 'to', newAlpha
							pixels[x, targetRow] = pixels[x, targetRow][:3] + (newAlpha,)
						canvas.bannerGCstorage = ImageTk.PhotoImage( canvas.pilImage )
						canvas.itemconfig( canvas.canvasImageItem, image=canvas.bannerGCstorage )
						canvas.update() # update_idletasks
						time.sleep( .0005 ) # 500 us
			
			canvas.delete( 'all' )
			time.sleep( .4 )

		else: # Banner not currently visible. Clear the canvas
			canvas.delete( 'all' )

		# Load the banner file and get the banner image
		if targetTab == globalData.gui.discDetailsTab and globalData.gui.discTab.bannerCanvas.pilImage:
			# The Disc Tree tab should have already been loaded/updated; so we can use that instead
			bannerImage = globalData.gui.discTab.bannerCanvas.pilImage
		else:
			bannerFile = globalData.disc.getBannerFile()
			bannerImage = bannerFile.getTexture( 0x20, getAsPilImage=True )
		canvas.pilImage = bannerImage
		canvas.bannerGCstorage = ImageTk.PhotoImage( bannerImage )

		# Add the new banner image to the canvas
		if currentlySelectedTab == targetTab and not self.debugMode:
			# Add the banner on the current tab using a dissolve fade.
			# First, create a blank image on the canvas
			width, height = 96, 32
			dissolvingImage = Image.new( 'RGBA', (width, height), (0,0,0,0) )
			canvas.canvasImageItem = canvas.create_image( 0, 0, image=ImageTk.PhotoImage(dissolvingImage), anchor='nw' )
			dessolvingPixels = dissolvingImage.load()

			# Display the converted image
			bannerPixels = canvas.pilImage.load()
			pixelsToUpdatePerPass = 172
			pixelsNotShown = [ (x, y) for x in range(width) for y in range(height) ] # Creates a list of all possible pixel coordinates for the banner image
			while pixelsNotShown:

				# Restart if this function is called while already in-progress
				if targetTab.stopAndReloadBanner:
					targetTab.updatingBanner = False
					targetTab.stopAndReloadBanner = False
					self.updateBanner( self )
					return

				# Randomly pick out some pixels to show
				pixelsToShow = []
				while len( pixelsToShow ) < pixelsToUpdatePerPass and pixelsNotShown:
					randomIndex = random.randint( 0, len(pixelsNotShown) - 1 )
					pixelsToShow.append( pixelsNotShown[randomIndex] )
					del pixelsNotShown[randomIndex]
				if pixelsToUpdatePerPass > 2: pixelsToUpdatePerPass -= math.sqrt( pixelsToUpdatePerPass )/2

				# Update the chosen pixels
				for pixelCoords in pixelsToShow:
					dessolvingPixels[pixelCoords] = bannerPixels[pixelCoords]

				# Update the GUI
				canvas.bannerGCstorage = ImageTk.PhotoImage( dissolvingImage )
				canvas.itemconfig( canvas.canvasImageItem, image=canvas.bannerGCstorage )
				canvas.update()
				time.sleep( .022 )

			canvas.canvasImageItem = canvas.create_image( 0, 0, image=canvas.bannerGCstorage, anchor='nw' )

		else: # No animation; just add the banner to the GUI
			canvas.canvasImageItem = canvas.create_image( 0, 0, image=canvas.bannerGCstorage, anchor='nw' )

		targetTab.updatingBanner = False
	
	def updateIids( self, iids ): # Simple function to change the Game ID for all iids in a given list or tuple

		""" Updates the Game ID for all isoPaths/iids in the given list or tuple. """

		disc = globalData.disc
		updatedList = []

		for iid in iids:
			if '/' in iid: updatedList.append( disc.gameId + '/' + '/'.join(iid.split('/')[1:]) )
			else: updatedList.append( iid )

		return tuple( updatedList )

	def loadDisc( self, updateStatus=True, preserveTreeState=False, switchTab=False, updatedFiles=None ):

		""" Clears and repopulates the Disc File Tree. Generally, population of the Disc Details Tab is also called by this.

				- updateStatus: 		Allows or prevents the program status to be updated after this method runs. 
				- preserveTreeState:	Restores the current state of the treeview after reload, including 
										open folders, file/folder selections and focus, and scroll position.
				- switchTab:			
				- updatedFiles:			If provided, this will be a list of iids (isoPaths) that were updated during a save operation.
										These files (and their parent folders) will be highlighted green to indicate changes. """

		disc = globalData.disc

		if preserveTreeState:
			self.isoFileTree.saveState()

		# Remember the current Game ID in case it has changed (iids collected above will need to be updated before restoration)
		rootItems = self.isoFileTree.get_children()
		if rootItems:
			originalGameId = rootItems[0]
		else:
			originalGameId = disc.gameId
			
		self.clear()

		# Switch to this tab if it or the Disc Details tab are not currently selected
		if switchTab:
			currentlySelectedTab = globalData.gui.root.nametowidget( globalData.gui.mainTabFrame.select() )
			if currentlySelectedTab != self and currentlySelectedTab != globalData.gui.discDetailsTab:
				globalData.gui.mainTabFrame.select( self ) # Switch to the Disc File Tree tab

		# Update the Game ID text and a shortened disc path string that will fit well in less space
		self.gameIdText.set( disc.gameId )
		self.isoOverviewFrame.update_idletasks()
		frameWidth = self.isoOverviewFrame.winfo_width()
		accumulatingName = ''
		for character in reversed( disc.filePath ):
			accumulatingName = character + accumulatingName
			self.isoPathShorthand.set( accumulatingName )
			if self.isoPathShorthandLabel.winfo_reqwidth() > frameWidth:
				# Reduce the path to the closest folder (that fits in the given space)
				normalizedPath = os.path.normpath( accumulatingName[1:] )
				if '\\' in normalizedPath: self.isoPathShorthand.set( '\\' + '\\'.join( normalizedPath.split('\\')[1:] ) )
				else: self.isoPathShorthand.set( '...' + normalizedPath[3:] ) # Filename is too long to fit; show as much as possible
				break
		ToolTip( self.isoPathShorthandLabel, disc.filePath, delay=500, wraplength=400, follow_mouse=1 )

		# Add the root (GameID) entry
		rootParent = disc.gameId
		self.isoFileTree.insert( '', 'end', iid=rootParent, text=' ' + disc.gameId + '  (root)', open=True, image=globalData.gui.imageBank('meleeIcon'), values=('', 'cFolder') )
		
		# Add the disc's files to the Disc File Tree tab
		usingConvenienceFolders = globalData.checkSetting( 'useDiscConvenienceFolders' ) # Avoiding having to look this up many times
		if usingConvenienceFolders:
			self.isoFileTree.insert( rootParent, 'end', iid=rootParent + '/sys', text=' System files', image=globalData.gui.imageBank('folderIcon'), values=('', 'cFolder'), tags=('cFolder',) )
		for discFile in disc.files.itervalues():
			self.addFileToFileTree( discFile, usingConvenienceFolders )

		# Ad-hoc test code
		# count = 0
		# totalSize = 0
		# for discFile in disc.files.itervalues():
		# 	if discFile.__class__.__name__ == 'StageFile':
		# 		discFile.initialize()
		# 		print( discFile.filename, discFile.mapHead.getGeneralPoints() )
		# 	if issubclass( discFile.__class__, CharCostumeFile ):
		# 		if not discFile.charAbbr in ( 'Bo', 'Gl', 'Mh', 'Ch', 'Gk', 'Sb' ) \
		# 			and not ( discFile.filename.startswith( 'PlKb' ) and 'Cp' in discFile.filename ):
		# 			count += 1
		# 			totalSize += discFile.size
		# print( 'Total files of type: ' + str(count) )
		# print( 'Total size: ' + humansize(totalSize) )

		# Enable the GUI's buttons and update other labels
		for widget in self.isoOpsPanelButtons.winfo_children():
			widget.config( state='normal' )
		if updateStatus: globalData.gui.updateProgramStatus( 'Disc Scan Complete' )
			
		# Recreate the prior state of the treeview (open folders, selection/focus, and scroll position)
		if preserveTreeState:
			# Update the file/folder selections and focus iids with the new game Id if it has changed.
			if originalGameId != disc.gameId:
				self.isoFileTree.openFolders = self.updateIids( self.isoFileTree.openFolders )
				self.isoFileTree.selectionState = self.updateIids( self.isoFileTree.selectionState )
				if '/' in self.isoFileTree.focusState:
					self.isoFileTree.focusState = disc.gameId + '/' + '/'.join(self.isoFileTree.focusState.split('/')[1:])

			# Restore state
			self.isoFileTree.restoreState()

		# Highlight recently updated files in green
		if updatedFiles:
			# Update the file iids with the new gameId if it has changed.
			if originalGameId != disc.gameId:
				updatedFiles = self.updateIids( updatedFiles )

			# Add save highlighting tags to the given items
			for iid in updatedFiles:
				if self.isoFileTree.exists( iid ):
					# Add a tag to highlight this item
					self.isoFileTree.item( iid, tags='changesSaved' )

					# Add tags to highlight the parent (folder) items
					parent = self.isoFileTree.parent( iid )
					while parent != disc.gameId:
						self.isoFileTree.item( parent, tags='changesSaved' )
						parent = self.isoFileTree.parent( parent )
						
		# Update the treeview's header text and its function call for the next (reversed) sort.
		self.isoFileTree.heading( '#0', text='File     (Sorted by FST)' )
		# self.isoFileTree.heading( '#0', command=lambda: treeview_sort_column(self.isoFileTree, 'file', False) )
		# self.isoFileTree.heading( '#0', command=self.sortTreeviewItems )

	def addFolderToFileTree( self, isoPath ):

		""" Adds the given folder to the disc file tree, and recursively adds all parent folders it may require. 
			These folders are native to (actually exist in) the disc's file structure, not convenience folders. 
			The isoPath argument should be a disc folder filesystem path, like "GALE01/audio/us" (no file name or ending slash). """

		assert isoPath[-1] != '/', 'Invalid input to addFolderToFileTree(): ' + isoPath

		parent, folderName = os.path.split( isoPath )

		# Make sure the parent exists first (it could also be a folder that needs adding)
		if not self.isoFileTree.exists( parent ):
			self.addFolderToFileTree( parent )

		if folderName == 'audio':
			description = '\t\t --< Music and Sound Effects >--'
			iconImage = globalData.gui.imageBank( 'audioIcon' )
		else:
			description = ''
			iconImage = globalData.gui.imageBank( 'folderIcon' )

		self.isoFileTree.insert( parent, 'end', iid=isoPath, text=' ' + folderName, values=(description, 'nFolder'), image=iconImage, tags=('nFolder',) )

	def addFileToFileTree( self, discFile, usingConvenienceFolders ):

		""" Adds files and any folders they may need to the Disc File Tree, including convenience folders. """

		entryName = discFile.filename

		# Get the parent item that the current item should be added to
		parent = os.path.dirname( discFile.isoPath )

		# Create any native folders (those actually in the disc) that may be needed
		if not self.isoFileTree.exists( parent ):
			self.addFolderToFileTree( parent )

		# Add convenience folders (those not actually in the disc's file system)
		if globalData.disc.isMelee and usingConvenienceFolders:
			# System files
			if entryName in ( 'Boot.bin', 'Bi2.bin', 'ISO.hdr', 'AppLoader.img', 'Start.dol', 'Game.toc' ):
				parent = discFile.isoPath.split( '/' )[0] + '/sys' # Adding to the System Files folder ([GAMEID]/sys)

			# "Hex Tracks"; 20XX's custom tracks, e.g. 01.hps, 02.hps, etc.
			elif discFile.__class__.__name__ == 'MusicFile' and discFile.isHexTrack:
				if not self.isoFileTree.exists( 'hextracks' ):
					self.isoFileTree.insert( parent, 'end', iid='hextracks', text=' Hex Tracks', values=('\t\t --< 20XX Custom Tracks >--', 'cFolder'), image=globalData.gui.imageBank('musicIcon'), tags=('cFolder',) )
				parent = 'hextracks'

			# Original audio folder
			elif parent.split('/')[-1] == 'audio' and entryName.startswith( 'ff_' ):
				if not self.isoFileTree.exists( 'fanfare' ):
					self.isoFileTree.insert( parent, 'end', iid='fanfare', text=' Fanfare', values=('\t\t --< Victory Audio Clips >--', 'cFolder'), image=globalData.gui.imageBank('audioIcon'), tags=('cFolder',) )
				parent = 'fanfare'

			# Character Effect files
			elif entryName.startswith( 'Ef' ):
				if not self.isoFileTree.exists( 'ef' ):
					self.isoFileTree.insert( parent, 'end', iid='ef', text=' Ef__Data.dat', values=('\t\t --< Character Graphical Effects >--', 'cFolder'), image=globalData.gui.imageBank('folderIcon'), tags=('cFolder',) )
				parent = 'ef'
			
			# Congratulations Screens
			elif entryName.startswith( 'GmRegend' ):
				if not self.isoFileTree.exists( 'gmregend' ):
					self.isoFileTree.insert( parent, 'end', iid='gmregend', text=' GmRegend__.thp', values=("\t\t --< 'Congratulation' Screens (1P) >--", 'cFolder'), image=globalData.gui.imageBank('folderIcon'), tags=('cFolder',) )
				parent = 'gmregend'
			elif entryName.startswith( 'GmRstM' ): # Results Screen Animations
				if not self.isoFileTree.exists( 'gmrstm' ):
					self.isoFileTree.insert( parent, 'end', iid='gmrstm', text=' GmRstM__.dat', values=('\t\t --< Results Screen Animations >--', 'cFolder'), image=globalData.gui.imageBank('folderIcon'), tags=('cFolder',) )
				parent = 'gmrstm'
			elif globalData.disc.is20XX and entryName.startswith( 'IfCom' ): # 20XX HP Infographics (originally the "Coming Soon" screens)
				if not self.isoFileTree.exists( 'infos' ):
					self.isoFileTree.insert( parent, 'end', iid='infos', text=' IfCom__.dat', values=('\t\t --< Infographics >--', 'cFolder'), image=globalData.gui.imageBank('folderIcon'), tags=('cFolder',) )
				parent = 'infos'
			elif discFile.__class__.__name__ == 'StageFile':
				if not self.isoFileTree.exists( 'gr' ):
					self.isoFileTree.insert( parent, 'end', iid='gr', text=' Gr__.dat', values=('\t\t --< Stage Files >--', 'cFolder'), image=globalData.gui.imageBank('stageIcon'), tags=('cFolder',) )
				parent = 'gr'
				
				# Check for Target Test stages (second case in parenthesis is for Luigi's, which ends in 0at in 20XX; last case is for the "TEST" stage)
				if entryName[2] == 'T' and ( discFile.ext == '.dat' or entryName == 'GrTLg.0at' ) and entryName != 'GrTe.dat':
					# Create a folder for target test stage files (if not already created)
					if not self.isoFileTree.exists( 't' ):
						self.isoFileTree.insert( parent, 'end', iid='t', text=' GrT__.dat', values=('\t - Target Test Stages', 'cFolder'), image=globalData.gui.imageBank('folderIcon'), tags=('cFolder',) )
					parent = 't'
				elif entryName[2:5] in globalData.onePlayerStages: # For 1-Player modes,like 'Adventure'
					if not self.isoFileTree.exists( '1p' ):
						self.isoFileTree.insert( parent, 'end', iid='1p', text='Gr___.___', values=('\t - 1P-Mode Stages', 'cFolder'), image=globalData.gui.imageBank('folderIcon'), tags=('cFolder',) )
					parent = '1p'
				elif discFile.isRandomNeutral():
					# Modern versions of 20XX (4.06+) have multiple variations of each neutral stage, the 'Random Neutrals' (e.g. GrSt.0at through GrSt.eat)
					iid = discFile.shortName.lower()

					# Add the convenience folder if not already added
					if not self.isoFileTree.exists( iid ):
						if discFile.shortName == 'GrP': # For Stadium
							folderName = ' {}_.usd'.format( discFile.shortName )
						else: folderName = ' {}._at'.format( discFile.shortName )
						self.isoFileTree.insert( 'gr', 'end', iid=iid, text=folderName, values=(discFile.longName + ' (RN)', 'cFolder'), image=globalData.gui.imageBank('folderIcon'), tags=('cFolder',) )
					parent = iid
			elif discFile.ext == '.mth': # a video file
				if entryName.startswith( 'MvEnd' ): # 1-P Ending Movie
					if not self.isoFileTree.exists('mvend'):
						self.isoFileTree.insert( parent, 'end', iid='mvend', text=' MvEnd__.dat', values=('\t\t --< 1P Mode Ending Movies >--', 'cFolder'), image=globalData.gui.imageBank('folderIcon'), tags=('cFolder',) )
					parent = 'mvend'
			elif entryName.startswith( 'Pl' ) and entryName != 'PlCo.dat': # Character file
				if not self.isoFileTree.exists( 'pl' ):
					self.isoFileTree.insert( parent, 'end', iid='pl', text=' Pl__.dat', values=('\t\t --< Character Files >--', 'cFolder'), image=globalData.gui.imageBank('charIcon'), tags=('cFolder',) )
				character = globalData.charNameLookup.get( entryName[2:4], 'Unknown ({})'.format(entryName[:4]) )
				# Create a folder for the character (and the copy ability files if this is Kirby) if one does not already exist.
				charFolderIid = 'pl' + character.replace(' ', '').replace('[','(').replace(']',')') # Spaces or brackets can't be used in the iid.
				if not self.isoFileTree.exists( charFolderIid ):
					self.isoFileTree.insert( 'pl', 'end', iid=charFolderIid, text=' ' + character, values=('', 'cFolder'), image=globalData.gui.imageBank('folderIcon'), tags=('cFolder',) )
				if entryName.endswith( 'DViWaitAJ.dat' ):
					discFile.shortDescription = '1P mode wait animation'
					if character.endswith( 's' ):
						discFile.longDescription = character + "' " + discFile.shortDescription
					else:
						discFile.longDescription = character + "'s " + discFile.shortDescription
					parent = charFolderIid
				elif charFolderIid == 'plKirby' and isinstance( discFile, CharDataFile ) and 'Cp' in discFile.filename:
					if not self.isoFileTree.exists( 'plKirbyData' ):
						self.isoFileTree.insert( 'plKirby', 'end', iid='plKirbyData', text=' Copy power ftData files', values=('', 'cFolder'), image=globalData.gui.imageBank('folderIcon'), tags=('cFolder',) )
					parent = 'plKirbyData'
				else:
					parent = charFolderIid
			elif entryName.startswith( 'Sd' ): # Menu text files
				if not self.isoFileTree.exists( 'sd' ):
					self.isoFileTree.insert( parent, 'end', iid='sd', text=' Sd__.dat', values=('\t\t --< UI Text Files >--', 'cFolder'), image=globalData.gui.imageBank('folderIcon'), tags=('cFolder',) )
				parent = 'sd'
			elif entryName.startswith( 'Ty' ): # Trophy file
				if not self.isoFileTree.exists( 'ty' ):
					self.isoFileTree.insert( parent, 'end', iid='ty', text=' Ty__.dat', values=('\t\t --< Trophies >--', 'cFolder'), image=globalData.gui.imageBank('folderIcon'), tags=('cFolder',) )
				parent = 'ty'

		if usingConvenienceFolders:
			# Add extra space to indent the name from the parent folder name
			description = '     ' + discFile.shortDescription
		else:
			description = discFile.longDescription

		try:
			# The following commented-out code is occasionally used for ad-hoc testing

			# altPath = 'GALE01/' + discFile.filename.replace( '.usd', '.dat' )
			# if discFile.filename.endswith( '.usd' ) and altPath in globalData.disc.files:
			# 	print discFile.filename, humansize(discFile.size)
			# if discFile.filename.endswith( '.mth' ):
			# 	print discFile.filename

			# if discFile.filename == 'PlCa.dat':# or discFile.filename == 'PlCa.sat':
			# 	table = discFile.getActionTable()
			# 	print 'Fighter Action Tables:'
			# 	print discFile.filename, hex( table.offset + 0x20 )

			# 	for i, values in table.iterateEntries():
			# 		actionName = discFile.getString( values[0] )
			# 		# offsetInTable = table.entryIndexToOffset( i )
			# 		# print '\t', i, ' | ', uHex( offsetInTable + 0x20 ), actionName	# show subAction struct offsets
			# 		print '\t', i, ' | ', uHex( values[3] + 0x20 ), actionName		# show subAction table entry offsets

			# if discFile.filename.endswith( 'AJ.dat') and 'Wait' not in discFile.filename:
			# 	print discFile.filename, hex(discFile.size)

			# if ( discFile.filename.endswith( 'at' ) or  discFile.filename.endswith( 'sd' ) ) and discFile.size > 4000000:
			# 	print( discFile.filename, ': ', hex(discFile.size), discFile.size )

			# if issubclass( discFile.__class__, DatFile ):
			# if issubclass( discFile.__class__, CharCostumeFile ):
			# 	discFile.initialize()
			# 	if discFile.headerInfo and discFile.headerInfo['rtEntryCount'] > 10000:
			# 		print( discFile.filename, ': ', discFile.headerInfo['rtEntryCount'] )

			# if discFile.filename == 'PlFxNr.dat':
			# 	discFile.initialize()
			# 	shareJoint = discFile.getStructByLabel( 'PlyFox5K_Share_joint' )
			# 	dobj = shareJoint.DObj
			# 	pobj = dobj.PObj
			# 	pobj.decodeGeometry()
			# 	s1 = discFile.getStruct( 0xAC64 )
			# 	#s1 = discFile.getSkeletonRoot()
			# 	s2 = discFile.getStruct( 0xA9FC )
			# 	structsEquivalent = discFile.structuresEquivalent( s1, s2, False )
			# 	print( '0x{:x} equivalent to 0x{:x}: {}'.format(s1.offset, s2.offset, structsEquivalent) )

			# if issubclass( discFile.__class__, CharCostumeFile ) and not discFile.filename.endswith( 'Nr.dat' ):# and discFile.filename.startswith( 'PlCaGr' ):
			# # if issubclass( discFile.__class__, CharCostumeFile ) and discFile.filename.startswith( 'PlCaGr' ):
			# 	# Check for Nr costume
			# 	defaultCostume = globalData.disc.files.get( 'GALE01/Pl' + discFile.charAbbr + 'Nr.dat' )
			# 	if defaultCostume:
			# 		JointObjDesc = globalData.fileStructureClasses.get( 'JointObjDesc' )
			# 		InverseMatrixObjDesc = globalData.fileStructureClasses.get( 'InverseMatrixObjDesc' )
			# 		#structsEquivalent = discFile.structuresEquivalent( defaultCostume.getSkeletonRoot(), discFile.getSkeletonRoot(), True, [DisplayObjDesc] )
			# 		structsEquivalent = discFile.structuresEquivalent( defaultCostume.getSkeletonRoot(), discFile.getSkeletonRoot(), True, None, [JointObjDesc, InverseMatrixObjDesc] )
			# 		print( discFile.charAbbr + discFile.colorAbbr + ' skele equivalent to Nr costume: ' + str(structsEquivalent) )


				# rootJoint = discFile.getSkeletonRoot()
				# structures = discFile.getBranch( rootJoint.offset, classLimit=['DisplayObjDesc'], classLimitInclusive=False )
				# offsets = [ s.offset for s in structures ]

				# #print( [hex(0x20+s.offset) for s in structures] )
				# print( len(offsets) )
				# print( len(set(offsets)))
				# # print( 'total size: ' + hex(rootJoint.getBranchSize()) )
				# # print( 'total size: ' + hex(sum([s.length for s in structures])) )

				# low = min( offsets ) - 0x200
				# high = max( offsets ) + 0x200
				# print(hex(low))
				# print(hex(high))

				# for i, offset in enumerate( discFile.structureOffsets ):
				# 	if offset >= low and offset < high:
				# 		s = discFile.getStruct( offset )

				# 		if offset in offsets:
				# 			print( s.name )
				# 		else:
				# 			print( s.name + '  !!' )

				# 		nextStructOffset = discFile.structureOffsets[i+1]
				# 		print( 'space to next struct: ' + hex(nextStructOffset-(s.offset+s.length)) )

			# if discFile.__class__.__name__ == 'CharDataFile':
			# 	lookupTable = discFile.getModelLookupTable()
			# 	print( discFile.filename + ' | ' + discFile.charName )
			# 	print( lookupTable.getValues() )
			
			# Add the file to the treeview (all files in the treeview should be added with the line below, but may be modified elsewhere)
			self.isoFileTree.insert( parent, 'end', iid=discFile.isoPath, text=' ' + entryName, values=(description, 'file') )
		except Exception as err:
			printStatus( u'Unable to add {} to the Disc File Tree; {}'.format(discFile.longDescription, err) )

	def updateDescription( self, isoPath, description, alt='' ):

		""" Updates the description of a file in the treeview (second column). 
			If 'alt' is given, it will be used in cases where the option,
			'useDiscConvenienceFolders' is False (typically a longer description). """

		# Add the file to the treeview (all files in the treeview should be added with the line below, but may be modified elsewhere)
		if globalData.checkSetting( 'useDiscConvenienceFolders' ):
			# Add extra space to indent the name from the parent folder name
			description = '     ' + description
		elif alt:
			description = alt

		self.isoFileTree.item( isoPath, values=(description, 'file'), tags='changed' )

	def scanDiscItemForStats( self, iidSelectionsTuple, folderContents ):

		""" This is a recursive helper function to get the file size of 
			all files in a given folder, along with total file count. """

		discFiles = globalData.disc.files
		totalFileSize = 0
		fileCount = 0

		for iid in folderContents:
			if iid not in iidSelectionsTuple: # Ensures that nothing is counted twice.
				fileItem = discFiles.get( iid, None )

				if fileItem:
					totalFileSize += int( fileItem.size )
					fileCount += 1
				else: # Must be a folder if not found in the disc's file dictionary
					# Search the inner folder, and add the totals of the children within to the current count.
					folderSize, folderFileCount = self.scanDiscItemForStats( iidSelectionsTuple, self.isoFileTree.get_children(iid) )
					totalFileSize += folderSize
					fileCount += folderFileCount

		return totalFileSize, fileCount

	def quickLinkClicked( self, event ):

		""" Scrolls the treeview in the Disc File Tree tab directly to a specific section.
			If a disc is not already loaded, the most recent disc that has been loaded in
			the program is loaded, and then scrolled to the respective section. """

		discNewlyLoaded = False

		# Load the most recent disc if one is not loaded (todo: depricate this? not possible atm)
		if not globalData.disc: # todo: remove this? may never be the case anymore that this tab exists without a disc being loaded
			# Check that there are any recently loaded discs (in the settings file).
			recentISOs = globalData.getRecentFilesLists()[0] # The resulting list is a list of tuples, of the form (path, dateLoaded)

			if not recentISOs:
				# No recent discs found. Prompt to open one.
				globalData.gui.promptToOpenFile( 'iso' )
				discNewlyLoaded = True

			else: # ISOs found. Load the most recently used one
				recentISOs.sort( key=lambda recentInfo: recentInfo[1], reverse=True )
				pathToMostRecentISO = recentISOs[0][0].replace('|', ':')

				# Confirm the file still exists in the same place
				if os.path.exists( pathToMostRecentISO ):
					# Path validated. Load it. Don't update the details tab yet, since that will incur waiting for the banner animation
					globalData.gui.fileHandler( [pathToMostRecentISO], updateDefaultDirectory=False, updateDetailsTab=False )
					discNewlyLoaded = True

				else: # If the file wasn't found above, prompt if they'd like to remove it from the remembered files list.
					if askyesno( 'Remove Broken Path?', 'The following file could not be found:\n"' + pathToMostRecentISO + '" .\n\nWould you like to remove it from the list of recent files?' ):
						# Update the list of recent ISOs in the settings object and settings file.
						globalData.settings.remove_option( 'Recent Files', pathToMostRecentISO.replace(':', '|') )
						with open( globalData.paths['settingsFile'], 'w') as theSettingsFile: globalData.settings.write( theSettingsFile )
					return

		# Scroll to the appropriate section
		target = event.widget['text']
		self.scrollToSection( target )

		# If the disc was just now loaded, the banner and disc details will still need to be updated.
		# The function to scan the ISO will have deliberately skipped this step during the loading above,
		# so that scrolling will happen without having to wait on the banner animation.
		# if discNewlyLoaded:
		# 	self.isoFileTree.update() # Updates the GUI first so that the scroll position is instanly reflected
		# 	populateDiscDetails()

	def scanDiscForFile( self, searchString, parentToSearch='' ):
		
		""" Recursively searches the given string in all file name portions of iids in the file tree. """

		foundIid = ''

		for iid in self.isoFileTree.get_children( parentToSearch ):
			if iid.split( '/' )[-1].startswith( searchString ):
				return iid

			if self.isoFileTree.item( iid, 'values' )[1] != 'file': # May be "file", "nFolder" (native folder), or "cFolder" (convenience folder)
				foundIid = self.scanDiscForFile( searchString, iid ) # This might be a folder, try scanning its children
				if foundIid: break

		# If looking for one of the header files, but it wasn't found, try for "ISO.hdr" instead (used in place of boot.bin/bi2.bin by discs built by GCRebuilder)
		# if not foundIid and ( searchString == 'boot.bin' or searchString == 'bi2.bin' ):
		# 	foundIid = scanDiscForFile( 'iso.hdr' )

		return foundIid

	def scrollToSection( self, target ):

		""" Used primarily by the 'quick links' at the top of the 
			Disc File Tree to jump to a specific section.
			
			The "target" may be any of the following:
				System
				Characters
				Menus
				Stages
				Or any existing iid/isoPath in the treeview
		"""

		isoFileTreeChildren = self.isoFileTree.get_children()
		if not isoFileTreeChildren: return

		rootParent = isoFileTreeChildren[0]
		#self.isoFileTree.item( rootParent, open=True )
		self.isoFileTree.see( rootParent )
		globalData.gui.root.update()
		indexOffset = 19
		iid = ''

		# Determine the iid of the file to move the scroll position to
		if target == 'System':
			self.isoFileTree.yview_moveto( 0 )
			iid = rootParent + '/Start.dol'

		elif target == 'Characters':
			# Check for the complimentary folder
			if self.isoFileTree.exists( 'pl' ):
				iidTuple = self.isoFileTree.get_children( 'pl' )
				if len( iidTuple ) > 0:
					iid = iidTuple[0]
			else:
				iid = self.scanDiscForFile( 'Pl' ) # previously: 'plgk.dat'

		elif target == 'Menus':
			iid = self.scanDiscForFile( 'MnExtAll.' )
			indexOffset = 14

		elif target == 'Stages':
			# Check for the complimentary folder
			if self.isoFileTree.exists( 'gr' ):
				iidTuple = self.isoFileTree.get_children( 'gr' )
				if len( iidTuple ) > 0:
					iid = iidTuple[0]
			else:
				iid = self.scanDiscForFile( 'Gr' )
				#if not iid: iid = self.scanDiscForFile( 'grcn.dat' )

		elif target == 'Strings':
			# Check for the complimentary folder
			if self.isoFileTree.exists( 'sd' ):
				iidTuple = self.isoFileTree.get_children( 'sd' )
				if len( iidTuple ) > 0:
					iid = iidTuple[0]
			else:
				iid = self.scanDiscForFile( 'Sd' )

		elif self.isoFileTree.exists( target ):
			iid = target

		# If an item target was determined, scroll to it
		if iid:
			targetItemIndex = self.isoFileTree.index( iid ) + indexOffset # Offset applied so that the target doesn't actually end up exactly in the center

			# Target the parent folder if it's in one
			if self.isoFileTree.parent( iid ) == globalData.disc.gameId: # Means the target file is in root, not in a folder
				iidToSelect = iid
			else:
				iidToSelect = self.isoFileTree.parent( iid )

			# Set the current selection and keyboard focus
			self.isoFileTree.selection_set( iidToSelect )
			self.isoFileTree.focus( iidToSelect )
			targetItemSiblings = self.isoFileTree.get_children( self.isoFileTree.parent( iid ) )

			# Scroll to the target section (folders will be opened as necessary for visibility)
			if targetItemIndex > len( targetItemSiblings ): self.isoFileTree.see( targetItemSiblings[-1] )
			else: self.isoFileTree.see( targetItemSiblings[targetItemIndex] )

	def onFileTreeSelect( self, event ):

		""" Called when an item (file or folder) in the Disc File Tree is selected. Iterates over 
			the selected items, calculates total file(s) size, and displays it in the GUI. """

		iidSelectionsTuple = self.isoFileTree.selection()
		if len( iidSelectionsTuple ) == 0:
			return

		discFiles = globalData.disc.files
		totalFileSize = 0
		fileCount = 0

		# Get the collective size of all items currently selected
		for iid in iidSelectionsTuple:
			discFile = discFiles.get( iid, None )

			if discFile:
				totalFileSize += int( discFile.size )
				fileCount += 1
			else: # Must be a folder if not found in the disc's file dictionary
				folderSize, folderFileCount = self.scanDiscItemForStats( iidSelectionsTuple, self.isoFileTree.get_children(iid) )
				totalFileSize += folderSize
				fileCount += folderFileCount

		# Update the Offset and File Size values in the GUI.
		if len( iidSelectionsTuple ) == 1 and discFile: # If there's only one selection and it's a file.
			if discFile.offset == -1: self.isoOffsetText.set( 'Disc Offset:  N/A (External)' ) # Must be a standalone (external) file
			else: self.isoOffsetText.set( 'Disc Offset:  ' + uHex(discFile.offset) )
			self.internalFileSizeText.set( 'File Size:  {0:,} bytes'.format(totalFileSize) ) # Formatting in decimal with thousands delimiter commas
			self.internalFileSizeLabelSecondLine.set( '' )

		else: # A folder or multiple selections
			self.isoOffsetText.set( 'Disc Offset:  N/A' )
			self.internalFileSizeText.set( 'File Size:  {0:,} bytes'.format(totalFileSize) ) # Formatting in decimal with thousands delimiter commas
			self.internalFileSizeLabelSecondLine.set( '    (Totaled from {0:,} files)'.format(fileCount) )

	def getDiscPath( self, isoPath, useConvenienceFolders, includeRoot=True, addDolphinSubs=False ):

		""" Builds a disc path, like isoPath, but includes convenience folders if they are turned on. 
			Only if not using convenience folders may the "sys"/"files" folders be included. """

		if useConvenienceFolders:
			# Scan for 'convenience folders' (those not actually in the disc), and add them to the path; they won't exist in isoPath
			rootIid = self.isoFileTree.get_children()[0]
			isoParts = isoPath.split( '/' )
			pathParts = [ isoParts[-1] ] # Creating a list, starting with just the filename
			parentIid = self.isoFileTree.parent( isoPath )

			while parentIid and parentIid != rootIid: # End at the root/GameID folder (first condition is a failsafe)
				parentFolderText = self.isoFileTree.item( parentIid, 'text' ).strip()

				# for character in ( '\\', '/', ':', '*', '?', '"', '<', '>', '|' ): # Remove illegal characters
				# 	parentFolderText = parentFolderText.replace( character, '-' )
				parentFolderText = removeIllegalCharacters( parentFolderText )
				pathParts.insert( 0, parentFolderText )

				parentIid = self.isoFileTree.parent( parentIid )

			if includeRoot:
				pathParts.insert( 0, isoParts[0] )

			return '/'.join( pathParts )

		elif not includeRoot: # Return the full path, but without the root (GameID)
			pathParts = isoPath.split( '/' )

			# if addDolphinSubs and pathParts[-1] in Disc.systemFiles:
			# 	return 'sys/' + pathParts[-1]
			# elif addDolphinSubs:
			# 	return 'files/' + pathParts[-1]
			# else:
			return '/'.join( pathParts[1:] ) # Just removes the GameID

		# elif addDolphinSubs: # Include root and sys folder for system files
		# 	pathParts = isoPath.split( '/' )

		# 	if pathParts[-1] in Disc.systemFiles:
		# 		return pathParts[0] + '/sys/' + pathParts[-1]
		# 	else:
		# 		return pathParts[0] + '/files/' + pathParts[-1]
		else:
			return isoPath

	def exportItemsInSelection( self, selection, isoBinary, directoryPath, exported, failedExports, addDolphinSubs ):

		""" This is a recursive helper function for self.exportIsoFiles(). The open isoBinary file object is
			passed so that we can get file data from it directly and avoid opening it multiple times. """

		useConvenienceFolders = globalData.checkSetting( 'useConvenienceFoldersOnExport' )

		for iid in selection: # The iids will be isoPaths and/or folder iids
			# Attempt to get a file for this iid (isoPath)
			fileObj = globalData.disc.files.get( iid )

			if fileObj:
				globalData.gui.updateProgramStatus( 'Exporting File ' + str(exported + failedExports + 1) + '...', forceUpdate=True )

				try:
					# Retrieve the file data.
					if fileObj.source == 'disc':
						# Can perform the getData method ourselves for efficiency, since we have the open isoBinary file object
						assert fileObj.offset != -1, 'Invalid file offset for disc export: -1'
						assert fileObj.size != -1, 'Invalid file size for disc export: -1'
						isoBinary.seek( fileObj.offset )
						datData = isoBinary.read( fileObj.size )
					else: # source == 'file' or 'self'
						datData = fileObj.getData()

					# Construct a file path for saving, and destination folders if they don't exist
					if addDolphinSubs and fileObj.filename in Disc.systemFiles:
						savePath = directoryPath + '/sys/' + self.getDiscPath( fileObj.isoPath, useConvenienceFolders, includeRoot=False )
					elif addDolphinSubs:
						savePath = directoryPath + '/files/' + self.getDiscPath( fileObj.isoPath, useConvenienceFolders, includeRoot=False )
					else:
						savePath = directoryPath + '/' + self.getDiscPath( fileObj.isoPath, useConvenienceFolders, includeRoot=False )
					createFolders( os.path.split(savePath)[0] )

					# Save the data to a new file.
					with open( savePath, 'wb' ) as newFile:
						newFile.write( datData )
					exported += 1

				except:
					failedExports += 1

			else: # Item is a folder.
				print( 'Unable to get this file!: ' + str(iid) )
			# 	exported, failedExports = self.exportItemsInSelection( self.isoFileTree.get_children(iid), iidSelectionsTuple, isoBinary, directoryPath, exported, failedExports )

		return exported, failedExports

	def exportIsoFiles( self, addDolphinSubs=False ):

		""" Called by the Export button and Export File(s) menu option. This doesn't use the disc's 
			normal file export method so that we can include the convenience folders in the save path. """

		# Check that there's something selected to export
		iidSelections = self.isoFileTree.getItemsInSelection()[1] # Extends selection to also include all files within folders that may be selected
		if not iidSelections:
			globalData.gui.updateProgramStatus( 'Hm?' )
			msg( 'Please first select a file or folder to export.' )
			return

		# A disc or root folder path must have been loaded at this point (to populate the GUI); make sure its path is still valid
		elif not os.path.exists( globalData.disc.filePath ):
			if globalData.disc.isRootFolder:
				globalData.gui.updateProgramStatus( 'Export Error. Unable to find the currently loaded root folder path', error=True )
				msg( "Unable to find the root folder path. Be sure that the path is correct and that the folder hasn't been moved or deleted.", 'Root Folder Not Found' )
			else:
				globalData.gui.updateProgramStatus( 'Export Error. Unable to find the currently loaded disc file path', error=True )
				msg( "Unable to find the disc image. Be sure that the file path is correct and that the file hasn't been moved or deleted.", 'Disc Not Found' )
			return
		
		iid = next( iter(iidSelections) )
		fileObj = globalData.disc.files.get( iid )

		# Check the selection to determine if a single or multiple files need to be exported
		if len( iidSelections ) == 1 and fileObj:
			# Prompt for a place to save the file, save it, and update the GUI
			exportSingleFileWithGui( fileObj )

		else: # A folder or multiple files are selected to be exported. Prompt for a directory to save them to.
			directoryPath = tkFileDialog.askdirectory(
				title='Where would you like to save these files?',
				parent=globalData.gui.root,
				initialdir=globalData.getLastUsedDir(),
				mustexist=True )

			# The above will return an empty string if the user canceled
			if not directoryPath: return

			exported = 0
			failedExports = 0

			# Not using the disc's file export method so we can include the convenience folders in the save path
			with open( globalData.disc.filePath, 'rb' ) as isoBinary:
				exported, failedExports = self.exportItemsInSelection( iidSelections, isoBinary, directoryPath, exported, failedExports, addDolphinSubs )

			if failedExports == 0:
				globalData.gui.updateProgramStatus( 'Files exported successfully', success=True )
			elif exported > 0: # Had some exports fail
				globalData.gui.updateProgramStatus( '{} file(s) exported successfully. However, {} file(s) failed to export'.format(exported, failedExports), error=True )
			else:
				globalData.gui.updateProgramStatus( 'Unable to export', error=True )

			# Update the default directory to start in when opening or exporting files.
			globalData.setLastUsedDir( directoryPath )

	def goodDiscPath( self ):
		
		""" A disc or root folder path must have been loaded by this point; 
			this checks that the path is still valid. """
		
		if os.path.exists( globalData.disc.filePath ):
			return True
		else:
			if globalData.disc.isRootFolder:
				globalData.gui.updateProgramStatus( 'Import Error. Unable to find the currently loaded root folder path', error=True )
				msg( "Unable to find the root folder path. Be sure that the path is correct and that the folder hasn't been moved or deleted.", 'Root Folder Not Found', error=True )
			else:
				globalData.gui.updateProgramStatus( 'Import Error. Unable to find the currently loaded disc file path', error=True )
				msg( "Unable to find the disc image. Be sure that the file path is correct and that the file hasn't been moved or deleted.", 'Disc Not Found', error=True )
			return False

	def getSingleFileSelection( self, showWarnings=True ):

		""" Checks that only a single item is selected in the treeview, 
			and returns it if that's True. Otherwise returns None. 
			Notifies the user when a single file is not selected. """
		
		# Check that there's something selected
		iidSelectionsTuple = self.isoFileTree.selection()
		if not iidSelectionsTuple:
			if showWarnings:
				globalData.gui.updateProgramStatus( 'Hm?' )
				msg( 'Please select a file to use this feature.', 'No File is Selected' )
			return None

		elif len( iidSelectionsTuple ) != 1:
			if showWarnings:
				globalData.gui.updateProgramStatus( 'Hm?' )
				msg( 'Please select just one file to load.', 'Too Many Files Selected' )
			return None

		# Check what kind of item is selected. May be "file", "nFolder" (native folder), or "cFolder" (convenience folder)
		isoPath = iidSelectionsTuple[0]
		itemType = self.isoFileTree.item( isoPath, 'values' )[1]
		if itemType != 'file':
			if showWarnings:
				msg( 'A folder is selected. Please select just one file to load.', 'Folder Selected' )
			return None

		fileObj = globalData.disc.files.get( isoPath )
		assert fileObj, 'IsoFileTree displays a missing file! ' + isoPath

		if self.goodDiscPath():
			return fileObj
	
	def importSingleFile( self ):

		""" Called by the Import button and Import File(s) menu option. This doesn't use the 
			disc's file export method so we can include the convenience folders in the save path. """

		# Check that there's something selected to import over (replace)
		fileObj = self.getSingleFileSelection()
		if not fileObj: return

		# Prompt the user to replace the selected file
		importSingleFileWithGui( fileObj, "Choose a game file to import (replaces the currently selected file)" )

	def importMultipleFiles( self ):

		""" Import multiple files (selected by the user). Unlike with the single-file import method above, 
			this doesn't use a current selection to determine a file to import over. Instead, each file 
			will be identified by dat file symbols or file name to determine a file to replace. """

		if not self.goodDiscPath():
			return

		# Prompt the user to select some external/standalone files
		filePaths = importGameFiles( multiple=True, title='Choose one or more files to load into the disc (replaces originals by the same name)', category='dat' )

		# Check if the user canceled; in which case the above will return an empty list
		if not filePaths: return False

		tic = time.time()

		# Attempt to import the files
		failedImports = []
		for path in filePaths:
			filename = os.path.split( path )[1]

			# Check for this file in the disc
			discFile = globalData.disc.getFile( filename )
			if not discFile:
				failedImports.append( filename )
				continue

			# Initialize and replace the file
			newFile = FileBase( globalData.disc, -1, -1, discFile.isoPath, extPath=path, source='file' )
			globalData.disc.replaceFile( discFile, newFile, countAsNewFile=False )
			newFile.recordChange( 'New file', 'New file' )
			
		toc = time.time()
		print( 'time to import: ' + str(toc-tic) )

		# Notify the user of the results
		if len( failedImports ) == len( filePaths ): # No success
			printStatus( 'Imports failed', error=True )
			msg( 'Unable to import any of these files; they could not be found in the disc.', 'Unable to Import', error=True )
		elif failedImports: # Some success
			printStatus( 'Imports complete (with some failures)', warning=True )
			msg( 'Unable to import; files by these names were not found in the disc:\n\n' + grammarfyList(failedImports), 'Unimported Files', warning=True )
		else:
			printStatus( 'Imports complete ({} files imported)'.format(len(filePaths)), success=True )

	# def importMultipleTextures( self ):

	# 	# Prompt the user to import one or more textures
	# 	textureFilePaths = importMultipleTextures()
	# 	if not textureFilePaths:
	# 		return

	def restoreFiles( self ):

		""" Replaces the currently selected file(s) with vanilla (unmodified originals) 
			from a vanilla disc. """

		currentDisc = globalData.disc

		# Check that there's something selected to restore
		iidSelections = self.isoFileTree.getItemsInSelection()[1] # Extends selection to also include all files within selected folders
		if not iidSelections:
			globalData.gui.updateProgramStatus( 'Hm?' )
			msg( 'Please first select a file or folder to restore.' )
			return

		# A disc or root folder path must have been loaded at this point (to populate the GUI); make sure its path is still valid
		elif not os.path.exists( currentDisc.filePath ):
			if currentDisc.isRootFolder:
				globalData.gui.updateProgramStatus( 'Restoration Error. Unable to find the currently loaded root folder path', error=True )
				msg( "Unable to find the root folder path. Be sure that the path is correct and that the folder hasn't been moved or deleted.", 'Root Folder Not Found', error=True )
			else:
				globalData.gui.updateProgramStatus( 'Restoration Error. Unable to find the currently loaded disc file path', error=True )
				msg( "Unable to find the disc image. Be sure that the file path is correct and that the file hasn't been moved or deleted.", 'Disc Not Found', error=True )
			return

		# Try to initialize the vanilla disc
		vanillaDiscPath = globalData.getVanillaDiscPath()
		if not vanillaDiscPath:
			globalData.gui.updateProgramStatus( 'Unable to restore the file(s) without a vanilla disc to source from', warning=True )
			return
		vanillaDisc = Disc( vanillaDiscPath )
		vanillaDisc.load()

		# Rather than using built-in disc methods, open the disc ourselves so it doesn't have to be opened repeatedly
		missingFiles = []
		with open( vanillaDiscPath, 'rb' ) as vDisc:
		
			# Iterate over the files to restore
			for isoPath in iidSelections:
				# Get info on this file, and then get it from the disc
				vanillaFile = vanillaDisc.getFile( isoPath.split('/', 1)[1] ) # Will likely be uninitialized, meaning it won't have data
				if not vanillaFile:
					missingFiles.append( isoPath.split('/', 1) )
					continue
				elif not vanillaFile.data:
					vDisc.seek( vanillaFile.offset )
					vanillaFile.data = bytearray( vDisc.read(vanillaFile.size) )

				# Update the data in the current disc with this new one
				origFile = currentDisc.files.get( isoPath )
				currentDisc.replaceFile( origFile, vanillaFile, countAsNewFile=False )
				vanillaFile.recordChange( 'Restored to vanilla', 'Restored to vanilla' )

		# Notify the user of the results
		if len( missingFiles ) == len( iidSelections ): # No success
			printStatus( 'Restoration failed', error=True )
			msg( 'Unable to restore any of these files; they could not be found in the vanilla disc.', 'Unable to Restore', error=True )
		elif missingFiles: # Some success
			printStatus( 'Restoration complete (with some failures)', warning=True )
			msg( 'Unable to restore these files; they could not be found in the vanilla disc:\n\n' + grammarfyList(missingFiles), 'Unrestored Files', warning=True )
		else:
			printStatus( 'Restoration complete ({} files restored)'.format(len(iidSelections)), success=True )

	def browseTexturesFromDisc( self, event=None ):
		mainGui = globalData.gui

		if event: # Reached this by double-clicking (user might be trying to open a folder)
			showWarnings = False
		else:
			showWarnings = True
		fileObj = self.getSingleFileSelection( showWarnings )
		if not fileObj: return

		# Get the selected file and check whether it has textures (has a method to get them)
		if not hasattr( fileObj, 'identifyTextures' ):
			printStatus( 'Uhh...', warning=True )
			msg( "This type of file doesn't appear to have any textures." )
			return

		# Load the tab if it's not already present
		if not mainGui.texturesTab:
			mainGui.texturesTab = TexturesEditor( mainGui.mainTabFrame, mainGui )

		# Switch to the tab
		mainGui.mainTabFrame.select( mainGui.texturesTab )
		
		# Add a tab for the current file and populate it
		mainGui.playSound( 'menuSelect' )
		mainGui.texturesTab.addTab( fileObj )

	def analyzeFileFromDisc( self ):
		mainGui = globalData.gui
		fileObj = self.getSingleFileSelection()
		if not fileObj: return
		print( 'Not yet implemented' )

	def deleteIsoFiles( self, iids ):

		""" Removes (deletes) files from the disc, and from the isoFileTree. Folders will 
			automatically be removed from a disc object if all files within it are removed. 
			Note that the iids which the isoFileTree widget uses are isoPaths. """

		folderIids, fileIids = self.isoFileTree.getItemsInSelection( iids )
		discFiles = globalData.disc.files
		fileObjects = []
		reloadAudioTab = False

		# Make sure there are no system files included
		sysFiles = set( globalData.disc.systemFiles )
		sysFiles = { globalData.disc.gameId + '/' + filename for filename in sysFiles } # Need to add the parent name for comparisons
		if set.intersection( sysFiles, fileIids ):
			msg( 'System files cannot be removed from the disc!', 'Invalid Operation' )
			return

		# Collect file objects for the isoPaths collected above
		for isoPath in fileIids:
			# Collect a file object from the disc for this path, and remove it from the GUI
			fileObj = discFiles.get( isoPath )
			assert fileObj, 'IsoFileTree displays a missing file! ' + isoPath
			fileObjects.append( fileObj )
			self.isoFileTree.delete( isoPath )

			if fileObj.__class__.__name__ == 'MusicFile':
				reloadAudioTab = True

		# Remove the folders from the GUI
		for iid in folderIids:
			try: self.isoFileTree.delete( iid )
			except: pass # May have already been removed alongside a parent folder

		# Remove the files from the disc
		globalData.disc.removeFiles( fileObjects )
		
		# Update the Disc Details Tab
		detailsTab = globalData.gui.discDetailsTab
		if detailsTab:
			detailsTab.isoFileCountText.set( "{:,}".format(len(globalData.disc.files)) )
			#detailsTab # todo: disc size as well

		# Update the Audio Manager tab
		audioTab = globalData.gui.audioManagerTab
		if audioTab and reloadAudioTab:
			audioTab.loadFileList()
		
		if len( fileObjects ) == 1:
			globalData.gui.updateProgramStatus( '1 file removed from the disc' )
		else:
			globalData.gui.updateProgramStatus( '{} files removed from the disc'.format(len(fileObjects)) )
	
	def createContextMenu( self, event ):

		""" Spawns a context menu at the mouse's current location. """

		contextMenu = DiscMenu( globalData.gui.root, tearoff=False )
		contextMenu.repopulate()
		contextMenu.post( event.x_root, event.y_root )

	def determineNewFileInsertionKey( self ):

		""" Determines where new files should be added into the disc file and FST. If the user has a 
			file selected in the GUI (in the Disc File Tree), the new files will be added just before it. 
			If a folder is selected, it's presumed that they would like to add it to the end of that folder. 
			However, since it's likely a convenience folder (one not actually in the disc), the best attempt 
			is to add to the disc before the first file following the folder. """

		targetIid = self.isoFileTree.selection()

		# If there's a current selection in the treeview, use that file as a reference point, and insert the new file above it
		if targetIid:
			targetIid = targetIid[-1] # Simply selects the lowest position item selected (if there are multiple)
			parent = self.isoFileTree.parent( targetIid )
			
			if globalData.checkSetting( 'alwaysAddFilesAlphabetically' ):
				return parent, ''

			# # Remove the last portion of the disc path if it's a file or Convenience Folder
			itemType = self.isoFileTree.item( targetIid, 'values' )[1] # May be "file", "nFolder" (native folder), or "cFolder" (convenience folder)
			if itemType == 'file':
				iidToAddBefore = targetIid
			else: # Folder selected
				# Seek out the first file not in this folder
				inFolder = False
				for isoPath in globalData.disc.files.iterkeys():
					parent = self.isoFileTree.parent( isoPath )
					if parent == targetIid:
						inFolder = True
					elif inFolder: # Parent is no longer the target (currently selected) iid
						iidToAddBefore = isoPath
						break
				else: # Loop above didn't break; reached the end
					iidToAddBefore = 'end'

		elif globalData.checkSetting( 'alwaysAddFilesAlphabetically' ):
			parent = globalData.disc.gameId
			iidToAddBefore = ''

		else:
			parent = globalData.disc.gameId
			iidToAddBefore = 'end'

		return parent, iidToAddBefore


class DiscDetailsTab( ttk.Frame ):

	def __init__( self, parent, mainGui ):

		ttk.Frame.__init__( self, parent )
		
		# Add this tab to the main GUI, and add drag-and-drop functionality
		mainGui.mainTabFrame.add( self, text=' Disc Details ' )
		mainGui.dnd.bindtarget( self, mainGui.dndHandler, 'text/uri-list' )

		self.mainGui = mainGui
		
		# Row 1 | Disc file path entry
		row1 = ttk.Frame( self, padding='20 20 20 10' ) # Padding order: Left, Top, Right, Bottom.
		ttk.Label( row1, text=" ISO / GCM:" ).pack( side='left' )
		self.isoDestination = Tk.StringVar()
		isoDestEntry = ttk.Entry( row1, textvariable=self.isoDestination ) #, takefocus=False
		isoDestEntry.pack( side='left', fill='x', expand=1, padx=12 )
		isoDestEntry.bind( '<Return>', self.openIsoDestination )
		row1.grid( column=0, row=0, sticky='ew' )

		# Row 2, Column 0 & 1 | Game ID
		self.row2 = ttk.Frame( self, padding='10 10 100 10' )
		self.row2.padx = 5
		self.row2.gameIdLabel = ttk.Label( self.row2, text='Game ID:' )
		self.row2.gameIdLabel.grid( column=0, row=0, rowspan=4, padx=self.row2.padx )
		self.gameIdText = Tk.StringVar()
		self.gameIdTextEntry = DisguisedEntry( self.row2, respectiveLabel=self.row2.gameIdLabel, 
												background=mainGui.defaultSystemBgColor, textvariable=self.gameIdText, width=8 )
		self.gameIdTextEntry.grid( column=1, row=0, rowspan=4, padx=self.row2.padx )
		self.gameIdTextEntry.offset = 0
		self.gameIdTextEntry.maxByteLength = 6
		self.gameIdTextEntry.updateName = 'Game ID'
		self.gameIdTextEntry.file = 'boot.bin'
		self.gameIdTextEntry.bind( '<Return>', self.saveImageDetails )

		# Row 2, Column 2/3/4 | Game ID break-down
		ttk.Label( self.row2, image=mainGui.imageBank('gameIdBreakdownImage') ).grid( column=2, row=0, rowspan=4, padx=self.row2.padx )
		self.consoleCodeText = Tk.StringVar()
		self.gameCodeText = Tk.StringVar()
		self.regionCodeText = Tk.StringVar()
		self.makerCodeText = Tk.StringVar()
		ttk.Label( self.row2, text='Console Code:' ).grid( column=3, row=0, sticky='e', padx=self.row2.padx )
		ttk.Label( self.row2, textvariable=self.consoleCodeText, width=3 ).grid( column=4, row=0, sticky='w', padx=self.row2.padx )
		ttk.Label( self.row2, text='Game Code:' ).grid( column=3, row=1, sticky='e', padx=self.row2.padx )
		ttk.Label( self.row2, textvariable=self.gameCodeText, width=3 ).grid( column=4, row=1, sticky='w', padx=self.row2.padx )
		ttk.Label( self.row2, text='Region Code:' ).grid( column=3, row=2, sticky='e', padx=self.row2.padx )
		ttk.Label( self.row2, textvariable=self.regionCodeText, width=3 ).grid( column=4, row=2, sticky='w', padx=self.row2.padx )
		ttk.Label( self.row2, text='Maker Code:' ).grid( column=3, row=3, sticky='e', padx=self.row2.padx )
		ttk.Label( self.row2, textvariable=self.makerCodeText, width=3 ).grid( column=4, row=3, sticky='w', padx=self.row2.padx )

		ttk.Separator( self.row2, orient='vertical' ).grid( column=5, row=0, sticky='ns', rowspan=4, padx=self.row2.padx+4, pady=6 )

		ClickText( self.row2, 'Code Reference', lambda event: webbrowser.open('https://wiki.dolphin-emu.org/index.php?title=GameIDs') ).grid( column=6, row=0 )

		# Row 2, Column 6 | Banner Image
		self.bannerCanvas = Tk.Canvas( self.row2, width=96, height=32, borderwidth=0, highlightthickness=0 )
		self.updatingBanner = False
		self.stopAndReloadBanner = False
		self.bannerCanvas.pilImage = None
		self.bannerCanvas.bannerGCstorage = None
		self.bannerCanvas.canvasImageItem = None
		self.bannerCanvas.grid( column=6, row=1, rowspan=2, padx=self.row2.padx )

		# Banner Export/Import buttons
		bannerImportExportFrame = ttk.Frame( self.row2 )
		ClickText( bannerImportExportFrame, 'Export', self.exportBanner ).pack( side='left', padx=(0, 5) )
		ClickText( bannerImportExportFrame, 'Import', self.importBanner ).pack( side='left', padx=(5, 0) )
		bannerImportExportFrame.grid( column=6, row=3, padx=self.row2.padx )

		ttk.Separator( self.row2, orient='vertical' ).grid( column=7, row=0, sticky='ns', rowspan=4, padx=self.row2.padx+4, pady=6 )

		# Row 2, Column 8/9 | Disc Revision, 20XX Version, and Disc Size
		self.isoRevisionText = Tk.StringVar()
		self.projectLabelText = Tk.StringVar()
		self.projectVerstionText = Tk.StringVar()
		self.isoFileCountText = Tk.StringVar()
		self.isoFilesizeText = Tk.StringVar()
		self.isoFilesizeTextLine2 = Tk.StringVar()
		ttk.Label( self.row2, text='Disc Revision:' ).grid( column=8, row=0, sticky='e', padx=self.row2.padx )
		ttk.Label( self.row2, textvariable=self.isoRevisionText ).grid( column=9, row=0, sticky='w', padx=self.row2.padx )
		projectLabel = ttk.Label( self.row2, textvariable=self.projectLabelText )
		projectLabel.grid( column=8, row=1, sticky='e', padx=self.row2.padx )
		projectVersion = ttk.Label( self.row2, textvariable=self.projectVerstionText )
		projectVersion.grid( column=9, row=1, sticky='w', padx=self.row2.padx )
		ttk.Label( self.row2, text='Total File Count:' ).grid( column=8, row=2, sticky='e', padx=self.row2.padx )
		ttk.Label( self.row2, textvariable=self.isoFileCountText ).grid( column=9, row=2, sticky='w', padx=self.row2.padx )
		ttk.Label( self.row2, text='Disc Size:' ).grid( column=8, row=3, sticky='e', padx=self.row2.padx )
		ttk.Label( self.row2, textvariable=self.isoFilesizeText ).grid( column=9, row=3, sticky='w', padx=self.row2.padx )
		ttk.Label( self.row2, textvariable=self.isoFilesizeTextLine2 ).grid( column=8, row=4, columnspan=2, sticky='e', padx=self.row2.padx )
		self.row2.grid( column=0, row=1, padx=15 )

		# potential todo: Add Nkit info/support; https://wiki.gbatemp.net/wiki/NKit/NKitFormat

		# Set cursor hover bindings for the help text
		previousLabelWidget = ( None, '' )
		for widget in self.row2.winfo_children(): # Widgets will be listed in the order that they were added to the parent

			if widget.winfo_class() == 'TLabel' and ':' in widget['text']: # Bindings for the preceding Label
				updateName = widget['text'].replace(':', '')
				widget.bind( '<Enter>', lambda event, helpTextName=updateName: self.setHelpText(helpTextName) )
				if updateName not in ( 'Console Code', 'Region Code', 'Maker Code' ):
					widget.bind( '<Leave>', self.setHelpText )
				previousLabelWidget = ( widget, updateName )

			elif widget == projectLabel or widget == projectVersion:
				if globalData.disc and globalData.disc.is20XX:
					widget.bind( '<Enter>', lambda event: self.setHelpText('20XX Version') )
					widget.bind( '<Leave>', self.setHelpText )

			elif previousLabelWidget[0]: # Bindings for the entry widgets displaying the value/info
				widget.bind( '<Enter>', lambda event, helpTextName=previousLabelWidget[1]: self.setHelpText(helpTextName) )
				if updateName not in ( 'Console Code', 'Region Code', 'Maker Code' ):
					widget.bind( '<Leave>', self.setHelpText )
				previousLabelWidget = ( None, '' )

			elif widget.grid_info()['row'] == '4': # For the second label for isoFilesize
				widget.bind( '<Enter>', lambda event: self.setHelpText('Disc Size') )
				widget.bind( '<Leave>', self.setHelpText )

		# Enable resizing for the above grid columns
		self.row2.columnconfigure( 2, weight=0 ) # Allows the middle column (the actual text input fields) to stretch with the window
		self.row2.columnconfigure( 4, weight=1 )
		self.row2.columnconfigure( 5, weight=0 )
		self.row2.columnconfigure( 6, weight=1 )
		self.row2.columnconfigure( 7, weight=0 )
		self.row2.columnconfigure( 8, weight=1 )
		virtualLabel = ttk.Label( self, text='0,000,000,000 bytes' ) # Used to figure out how much space various fonts/sizes will require
		predictedComfortableWidth = int( virtualLabel.winfo_reqwidth() * 1.2 ) # This should be plenty of space for the total disc size value.
		self.row2.columnconfigure( 9, weight=1, minsize=predictedComfortableWidth )

		# The start of row 3
		self.row3 = ttk.Frame( self, padding='10 0 10 10' ) # Uses a grid layout for its children
		self.shortTitle = Tk.StringVar()
		self.shortMaker = Tk.StringVar()
		self.longTitle = Tk.StringVar()
		self.longMaker = Tk.StringVar()

		borderColor1 = '#b7becc'; borderColor2 = '#0099f0'
		ttk.Label( self.row3, text='Image Name:' ).grid( column=0, row=0, sticky='e' )
		self.imageNameTextField = Tk.Text( self.row3, height=3, highlightbackground=borderColor1, highlightcolor=borderColor2, highlightthickness=1, borderwidth=0 )
		gameName1FieldScrollbar = Tk.Scrollbar( self.row3, command=self.imageNameTextField.yview ) # This is used instead of just a ScrolledText widget because getattr() won't work on the latter
		self.imageNameTextField['yscrollcommand'] = gameName1FieldScrollbar.set
		self.imageNameTextField.grid( column=1, row=0, columnspan=2, sticky='ew' )
		gameName1FieldScrollbar.grid( column=3, row=0 )
		self.imageNameTextField.offset = 0x20; self.imageNameTextField.maxByteLength = 992; self.imageNameTextField.updateName = 'Image Name'; self.imageNameTextField.file = 'boot.bin'
		imageNameCharCount = ttk.Label( self.row3, text='992' )
		imageNameCharCount.grid( column=4, row=0, padx=5 )
		self.imageNameTextField.bind( '<<Modified>>', lambda event, label=imageNameCharCount: self.textModified(event, label) )
		self.imageNameTextField.bind( '<KeyRelease>', lambda event, label=imageNameCharCount: self.textModified(event, label) )
		textWidgetFont = self.imageNameTextField['font']

		ttk.Label( self.row3, text='Short Title:' ).grid( column=0, row=1, sticky='e' )
		gameName2Field = Tk.Entry( self.row3, width=32, textvariable=self.shortTitle, highlightbackground=borderColor1, highlightcolor=borderColor2, highlightthickness=1, borderwidth=0, font=textWidgetFont )
		gameName2Field.grid( column=1, row=1, columnspan=2, sticky='w' )
		gameName2Field.offset = 0x1820; gameName2Field.maxByteLength = 32; gameName2Field.updateName = 'Short Title'; gameName2Field.file = 'opening.bnr'
		shortTitleCharCount = ttk.Label( self.row3, text='32' )
		shortTitleCharCount.grid( column=4, row=1 )

		ttk.Label( self.row3, text='Short Maker:' ).grid( column=0, row=2, sticky='e' )
		developerField = Tk.Entry( self.row3, width=32, textvariable=self.shortMaker, highlightbackground=borderColor1, highlightcolor=borderColor2, highlightthickness=1, borderwidth=0, font=textWidgetFont )
		developerField.grid( column=1, row=2, columnspan=2, sticky='w' )
		developerField.offset = 0x1840; developerField.maxByteLength = 32; developerField.updateName = 'Short Maker'; developerField.file = 'opening.bnr'
		shortMakerCharCount = ttk.Label( self.row3, text='32' )
		shortMakerCharCount.grid( column=4, row=2 )

		ttk.Label( self.row3, text='Long Title:' ).grid( column=0, row=3, sticky='e' )
		fullGameTitleField = Tk.Entry( self.row3, width=64, textvariable=self.longTitle, highlightbackground=borderColor1, highlightcolor=borderColor2, highlightthickness=1, borderwidth=0, font=textWidgetFont )
		fullGameTitleField.grid( column=1, row=3, columnspan=2, sticky='w' )
		fullGameTitleField.offset = 0x1860; fullGameTitleField.maxByteLength = 64; fullGameTitleField.updateName = 'Long Title'; fullGameTitleField.file = 'opening.bnr'
		longTitleCharCount = ttk.Label( self.row3, text='64' )
		longTitleCharCount.grid( column=4, row=3 )

		ttk.Label( self.row3, text='Long Maker:' ).grid( column=0, row=4, sticky='e' )
		devOrDescField = Tk.Entry( self.row3, width=64, textvariable=self.longMaker, highlightbackground=borderColor1, highlightcolor=borderColor2, highlightthickness=1, borderwidth=0, font=textWidgetFont )
		devOrDescField.grid( column=1, row=4, columnspan=2, sticky='w' )
		devOrDescField.offset = 0x18a0; devOrDescField.maxByteLength = 64; devOrDescField.updateName = 'Long Maker'; devOrDescField.file = 'opening.bnr'
		longMakerCharCount = ttk.Label( self.row3, text='64' )
		longMakerCharCount.grid( column=4, row=4 )

		ttk.Label( self.row3, text='Comment:' ).grid( column=0, row=5, sticky='e' )
		self.gameDescField = Tk.Text( self.row3, height=2, highlightbackground=borderColor1, highlightcolor=borderColor2, highlightthickness=1, borderwidth=0 )
		self.gameDescField.grid( column=1, row=5, columnspan=2, sticky='ew' )
		self.gameDescField.offset = 0x18e0; self.gameDescField.maxByteLength = 128; self.gameDescField.updateName = 'Comment'; self.gameDescField.file = 'opening.bnr'
		commentCharCount = ttk.Label( self.row3, text='128' )
		commentCharCount.grid( column=4, row=5 )
		self.gameDescField.bind( '<<Modified>>', lambda event, label=commentCharCount: self.textModified(event, label) )
		self.gameDescField.bind( '<KeyRelease>', lambda event, label=commentCharCount: self.textModified(event, label) )

		# Add event handlers for the updating function and help/hover text (also sets x/y padding)
		children = self.row3.winfo_children()
		previousWidget = children[0]
		for widget in children:
			widget.grid_configure( padx=4, pady=3 )
			updateName = getattr( widget, 'updateName', None )

			if updateName:
				# Cursor hover bindings for the preceding Label
				previousWidget.bind( '<Enter>', lambda event, helpTextName=updateName: self.setHelpText(helpTextName) )
				previousWidget.bind( '<Leave>', self.setHelpText )

				# Data entry (pressing 'Enter') and cursor hover bindings for the text entry field
				# if updateName == 'Image Name':
				widget.bind( '<Return>', self.saveImageDetails )
				# else:
				# 	widget.bind( '<Return>', self.saveBannerFileDetails )
				widget.bind( '<Enter>', lambda event, helpTextName=updateName: self.setHelpText(helpTextName) )
				widget.bind( '<Leave>', self.setHelpText )
			previousWidget = widget

		# Encoding switch
		encodingLabel = ttk.Label( self.row3, text='Encoding:' )
		encodingLabel.grid( column=0, row=6, sticky='e' )
		self.encodingFrame = ttk.Frame( self.row3 )
		self.encoding = Tk.StringVar()
		self.encoding.set( 'latin_1' ) # This is just a default. Officially set when a disc is loaded
		Tk.Radiobutton( self.encodingFrame, text=' English/EU  (Latin_1)', variable=self.encoding, value='latin_1', command=self.populateTexts ).pack( side='left', padx=(9,6) )
		Tk.Radiobutton( self.encodingFrame, text=' Japanese  (Shift_JIS)', variable=self.encoding, value='shift_jis', command=self.populateTexts ).pack( side='left', padx=6 )
		self.encodingFrame.grid( column=1, row=6, sticky='w' )
		ttk.Label( self.row3, text='Max Characters ^  ' ).grid( column=2, row=6, columnspan=3, sticky='e' )

		self.row3.columnconfigure( 1, weight=1 ) # Allows the middle column (the actual text input fields) to stretch with the window
		self.row3.grid( column=0, row=2, sticky='ew', padx=25 )

		# Hover event handlers for encoding
		for widget in [encodingLabel] + self.encodingFrame.winfo_children():
			widget.bind( '<Enter>', lambda event: self.setHelpText('Encoding') )
			widget.bind( '<Leave>', self.setHelpText )

		# The start of row 4
		ttk.Separator( self, orient='horizontal' ).grid( column=0, row=3, sticky='ew', padx=30, pady=10 )
		self.row4 = ttk.Frame( self, padding='0 0 0 12' ) # Padding order: Left, Top, Right, Bottom
		self.helpText = Tk.StringVar()
		self.helpText.set( "Hover over an item to view information on it.\nPress 'Enter' to submit changes in a text input field before saving." )
		self.helpTextLabel = ttk.Label( self.row4, textvariable=self.helpText, wraplength=680 ) #, background='white'
		self.helpTextLabel.pack( expand=1, pady=0 )
		self.helpLink = None
		self.row4.grid( column=0, row=4, sticky='nsew', padx=15, pady=4 )
		
		self.columnconfigure( 'all', weight=1 )
		self.rowconfigure( 0, weight=0 )
		self.rowconfigure( 1, weight=1 )
		self.rowconfigure( 2, weight=1 )
		self.rowconfigure( 3, weight=0 )
		self.rowconfigure( 4, weight=1, minsize=120 )

		# Establish character length validation, and updates for the GameID components
		self.gameIdText.trace( 'w', lambda nm, idx, mode, var=self.gameIdText: self.validateInput(var, 6) )
		self.shortTitle.trace( 'w', lambda nm, idx, mode, var=self.shortTitle, w=shortTitleCharCount: self.validateInput(var, 32, w) )
		self.shortMaker.trace( 'w', lambda nm, idx, mode, var=self.shortMaker, w=shortMakerCharCount: self.validateInput(var, 32, w) )
		self.longTitle.trace( 'w', lambda nm, idx, mode, var=self.longTitle, w=longTitleCharCount: self.validateInput(var, 64, w) )
		self.longMaker.trace( 'w', lambda nm, idx, mode, var=self.longMaker, w=longMakerCharCount: self.validateInput(var, 64, w) )

	def validateInput( self, stringVar, maxCharacters, charLengthWidget=None ):

		""" Validates character length of user input for the Game ID, and all of the text input except Image Name and Comment. """

		enteredValue = stringVar.get()
		truncated = False

		# Truncate strings for all fields except Game Id text and the Image Name (which is validated upon saving)
		if len( enteredValue ) > maxCharacters:
			truncated = True
			stringVar.set( enteredValue[:maxCharacters] )

		# Update all of the game ID strings
		elif stringVar == self.gameIdText:
			self.consoleCodeText.set( '' )
			self.gameCodeText.set( '' )
			self.regionCodeText.set( '' )
			self.makerCodeText.set( '' )
			if len(enteredValue) > 0: self.consoleCodeText.set( enteredValue[0] )
			if len(enteredValue) > 1: self.gameCodeText.set( enteredValue[1:3] )
			if len(enteredValue) > 3: self.regionCodeText.set( enteredValue[3] )
			if len(enteredValue) > 4: self.makerCodeText.set( enteredValue[4:7] )

		# Update the character length display
		if charLengthWidget:
			if truncated:
				charLengthWidget['foreground'] = '#a34343' # red
				charLengthWidget['text'] = '{} / {}'.format(maxCharacters, maxCharacters)
			else:
				charLengthWidget['foreground'] = 'black'
				charLengthWidget['text'] = '{} / {}'.format(len(enteredValue), maxCharacters)

	def textModified( self, event, label ):

		""" Validates character length of user input for the Image Name and Comment fields. """

		textWidget = event.widget

		widgetText = textWidget.get( '1.0', 'end' )
		newTextLength = len( widgetText )
		maxTextLength = textWidget.maxByteLength

		# Update the character length label and truncate text in the text field if it's too long
		if newTextLength > maxTextLength:
			textWidget.delete( '1.0', 'end' )
			textWidget.insert( '1.0', widgetText[:maxTextLength])

			label['foreground'] = '#a34343' # red
			label['text'] = '{} / {}'.format(maxTextLength, maxTextLength)
		else:
			label['foreground'] = 'black'
			label['text'] = '{} / {}'.format(newTextLength, maxTextLength)

	def openIsoDestination( self, event ):

		""" This is only called by pressing Enter/Return on the top file path display/entry of
			the Disc Details tab. Verifies the given path and loads the file for viewing. """

		filepath = self.isoDestination.get().replace( '"', '' )
		self.mainGui.fileHandler( [filepath] )

	def resetWidgetBackgrounds( self ):

		""" Revert widget background colors to detault. """

		# Set Game ID background color
		self.gameIdTextEntry.configure( background=self.mainGui.defaultSystemBgColor )
		
		# Set all other text entry field background colors
		for widget in self.row3.winfo_children():
			updateName = getattr( widget, 'updateName', None )
			if updateName:
				widget.configure( background='white' )
	
	def loadDiscDetails( self ):

		""" This primarily updates the Disc Details tab using information from Boot.bin/ISO.hdr (so a disc should already be loaded); 
			it directly handles updating the fields for disc filepath, gameID (and its breakdown), region and version, image name,
			20XX version (if applicable), and disc file size.

			The disc's country code is also found, which is used to determine the encoding of the banner file.
			A call to update the banner image and other disc details is also made in this function.

			This function also updates the disc filepath on the Disc File Tree tab (and the hover/tooltip text for it). """

		disc = globalData.disc
		#discTab = self.mainGui.discTab

		self.resetWidgetBackgrounds()

		# Set the Game ID (and associated components)
		self.gameIdText.set( disc.gameId )

		# Set the filepath field in the GUI
		self.isoDestination.set( disc.filePath )

		# Set the disc revision
		self.isoRevisionText.set( '{} 1.{:02}'.format(disc.region, disc.version) )

		# Set the country code (sourced in disc from Bi2.bin or iso.hdr)
		if disc.countryCode == 1:
			self.encoding.set( 'latin_1' ) # Decode assuming English or other European countries
		else: self.encoding.set( 'shift_jis' ) # For Japanese

		# Update the project version label (e.g. 20XX version)
		if disc.is20XX:
			self.projectLabelText.set( '20XX Version:' )
			self.projectVerstionText.set( disc.is20XX )
		elif disc.isMex:
			self.projectLabelText.set( 'M-EX Version:' )
			self.projectVerstionText.set( disc.isMex )
		else:
			self.projectLabelText.set( '' )
			self.projectVerstionText.set( '' )

		# Get and display the disc's total files and total file size
		self.isoFileCountText.set( "{:,}".format(len(disc.files)) )
		isoByteSize = disc.getSize()
		self.isoFilesizeText.set( "{:,} bytes".format(isoByteSize) )
		self.isoFilesizeTextLine2.set( '(i.e.: ' + "{:,}".format(isoByteSize/1048576) + ' MB, or ' + humansize(isoByteSize) + ')' )

		# Set image name
		bootFile = disc.files.get( disc.gameId + '/Boot.bin', disc.gameId + '/ISO.hdr' )
		self.imageNameTextField.delete( '1.0', 'end' )
		self.imageNameTextField.insert( '1.0', bootFile.imageName )

		self.populateTexts()

		#discTab.updateBanner( self )

	def populateTexts( self ):

		""" Loads all texts which depend on a certain encoding. """

		# Load the banner and set its encoding
		bannerFile = globalData.disc.getBannerFile()
		bannerFile.encoding = self.encoding.get()

		# Load text strings from the banner
		self.shortTitle.set( bannerFile.shortTitle )
		self.shortMaker.set( bannerFile.shortMaker )
		self.longTitle.set( bannerFile.longTitle )
		self.longMaker.set( bannerFile.longMaker )
		self.gameDescField.delete( '1.0', 'end' )
		self.gameDescField.insert( '1.0', bannerFile.comment )

	def saveImageDetails( self, event ):

		""" Takes certain text input from the GUI on the Disc Details Tab and saves it 
			to the 'boot.bin' or 'opening.bnr' file within the currently loaded disc. """

		# Cancel if no disc appears to be loaded
		if not globalData.disc: return 'break'

		entryWidget = event.widget

		# Return if the Shift key was held while pressing Enter (going to assume the user wants a line break).
		modifierKeysState = event.state # An int. Check individual bits for mod key status'; http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/event-handlers.html
		shiftDetected = (modifierKeysState & 0x1) != 0 # Checks the first bit of the modifiers
		if shiftDetected: return # Not returning "break" on this one in order to allow event propagation

		# Get the currently entered text as hex
		encoding = self.encoding.get()
		if entryWidget.winfo_class() == 'TEntry' or entryWidget.winfo_class() == 'Entry': 
			inputBytes = entryWidget.get().encode( encoding )
		else: inputBytes = entryWidget.get( '1.0', 'end' )[:-1].encode( encoding ) # "[:-1]" ignores trailing line break
		newStringHex = hexlify( inputBytes )

		# Get the data for the file this text resides in
		gameId = globalData.disc.gameId
		targetFile = entryWidget.file
		if targetFile == 'boot.bin':
			fileObj = globalData.disc.files.get( gameId + '/Boot.bin', gameId + '/ISO.hdr' ) # Fall back to ISO.hdr if Boot.bin is not present (might no longer be necessary)
		else: # Get the banner file
			fileObj = globalData.disc.getBannerFile()
		targetFileData = fileObj.getData()
		if not targetFileData:
			msg( 'Unable to retrieve the {} file data!'.format( targetFile ) )
			return 'break'

		# Get the hex string of the current value/field in the file, including padding
		offset = entryWidget.offset # In this case, these ARE counting the file header
		maxLength = entryWidget.maxByteLength
		currentHex = hexlify( targetFileData[offset:offset+maxLength] )

		# Pad the end of the newly input string with empty space (up to the max string length), to ensure any other text in the file will be erased
		newPaddedStringHex = newStringHex + ( '0' * (maxLength * 2 - len(newStringHex)) )

		# Check if the value is different from what is already saved.
		if currentHex != newPaddedStringHex:
			updateName = entryWidget.updateName

			if updateName == 'Game ID' and len( newStringHex ) != maxLength * 2:
				msg( 'The new value must be ' + str(maxLength) + ' characters long.', warning=True )
			elif len( newStringHex ) > maxLength * 2:
				msg( 'The new text must be less than ' + str(maxLength) + ' characters long.', warning=True )
			else:
				# Change the background color of the widget, to show that changes have been made to it and are pending saving.
				entryWidget.configure( background="#faa" )

				# Update the file
				fileObj.updateData( offset, bytearray.fromhex(newPaddedStringHex), updateName + ' updated' )

				self.mainGui.updateProgramStatus( updateName + ' updated. Press CRTL-S to save changes to file' )

		return 'break' # Prevents the 'Return' keystroke that called this from propagating to the widget and creating a line break

	# def updateEncoding( self ):
	#	# Todo: maybe should update the encoding byte in the disc?
	# 	self.populateTexts()
	
	def setHelpText( self, updateName='' ):

		""" Sets or resets hover text when the user mouses over various GUI elements. """

		alignment = 'center'

		if updateName == 'Game ID':
			helpText = ( "The game's primary identification code; this is what most applications and databases "
						"use to determine what game the disc is. It's composed of the 4 parts shown to the right of the value. "
						"You can change the Game ID for your own purposes, but be warned that many applications might no longer "
						"recognize it as the original game. [Contained in boot.bin at 0x0]" )

		elif updateName == 'Console Code':
			alignment = 'left'
			helpText = ( 'An identifier for the type of console or system the game was released for. For example, "G" for GameCube games, '
						'"N" for Nintendo 64, and "R" or "S" for Wii games. See the "Code References" link above for a list of all console codes.' )

		elif updateName == 'Game Code':
			helpText = ( 'An ID/serial specific to just the game itself, this (as well as the other Game ID components) is determined by the NOA Lot Check Department.' )

		elif updateName == 'Region Code':
			alignment = 'left'
			helpText = ( '\tA letter designating the intended region for the game. For a few examples:'
					   '\nNTSC Regions:\tE: USA,\t\tJ: Japan,\t\tK: Korea,\t\tR: Russia,\tW: Taiwan'
					   '\nPAL Regions:\tD: Germany,\tF: France,\tH: Netherlands,\tP: Europe,\t(+ all other regions)'
					   '\n\t(Regions using SECAM recieved the PAL variation of the game.)'
					   '\n\n\tSee the "Code References" link above for a list of all region codes.' )

		elif updateName == 'Maker Code':
			alignment = 'left'
			helpText = ( 'i.e. The publisher.\t\t01: Nintendo, 08: Capcom, 41: Ubisoft, 4F: Eidos, '
					   '\n\t\t\t51: Acclaim, 52: Activision, 5D: Midway, 5G: Hudson, 64: Lucas Arts, '
					   '\n\t\t\t69: Electronic Arts, 6S: TDK Mediactive, 8P: Sega, A4: Mirage Studios, AF: Namco, '
					   '\n\t\t\tB2: Bandai, DA: Tomy, EM: Konami, WR: Warner Bros.'
					   '\n\n\t\t\tSee the "Code References" link above for a list of all maker codes.' )

		elif updateName == 'Disc Revision':
			helpText = ( 'Sometimes games have changes throughout the time of their release, such as bug '
						'fixes or other minor updates. This number is often used to keep track of those revisions.' )

		elif updateName == '20XX Version':
			helpText = ( 'This can also be determined in-game in the Debug Menu, '
						'or [beginning with v4.05] in the upper-right of the CSS.' )

		elif updateName == 'Total File Count':
			helpText = ( "The number of files in the disc's filesystem (excludes folders), including system files." )
		
		elif updateName == 'Disc Size':
			helpText = ( 'Full file size of the GCM/ISO disc image. This differs from clicking on the root item in the Disc File Tree tab\nbecause the latter '
						'does not include padding (extra space) between files.\n\nThe standard for GameCube discs is ~1.36 GB, or 1,459,978,240 bytes.' )

		elif updateName == 'Image Name':
			helpText = ( 'Disc/Image Name. This is what Nintendont uses to populate its game list.\n'
						'There is also a lot of free space here for a description or other notes. However, the Nkit format uses some '
						'\nof this space for its header data (between 0x200 and 0x21C).\n\n[Contained in boot.bin at 0x20.]' )

		elif updateName == 'Short Title':
			helpText = ( "The game's name. Displays in the IPL (GameCube BIOS).\n\n[Contained in opening.bnr at 0x1820.]" )

		elif updateName == 'Short Maker':
			helpText = ( 'The company/developer, game producer, and/or production date. Displays in the IPL (GameCube BIOS).\n\n[Contained in opening.bnr at 0x1840.]' )

		elif updateName == 'Long Title':
			helpText = ( "The game's full name. This is what Dolphin uses to display in its games list for the Title field. "
						"Remember to delete the cache file under '\\Dolphin Emulator\\Cache' to get this to update, or use "
						"the menu option in View -> Purge Game List Cache.\nAlso displays in the IPL (GameCube BIOS).\n\n[Contained in opening.bnr at 0x1860.]" )

		elif updateName == 'Long Maker':
			helpText = ( 'The company/developer, game producer, and/or production date. This is what Dolphin uses to display in '
						"its games list for the Maker field. Remember to delete the cache file under '\\Dolphin Emulator\\Cache' to get "
						"this to update, or use the menu option in View -> Purge Game List Cache. Also displays in the IPL (GameCube BIOS)."
						"\n\n[Contained in opening.bnr at 0x18A0.]" )

		elif updateName == 'Comment':
			helpText = ( 'Known as "Description" in GCR, and simply "comment" in official Nintendo documentation. Originally, '
						"this used to appear in the GameCube's BIOS (i.e. the IPL Main Menu; the menu you would see when booting the "
						"system while holding 'A'), as a short description before booting the game. Line breaks may be used here."
						"\n\n[Contained in opening.bnr at 0x18E0.]" )

		elif updateName == 'Encoding':
			helpText = ( 'This applies to the text strings from the "opening.bnr" file, which is everything after the Image Name. '
						'(The Image Name is assumed to be UTF-8.) Discs intended for the Japanese market may use Level 1 Shift-JIS '
						'characters as well as ASCII and single-byte ("hankaku") katakana characters. Discs intended for the non-Japanese '
						'market may use ANSI 8-bit (WinLatin1) characters.' )

		else:
			helpText = "Hover over an item to view information on it.\nPress 'Enter' to submit changes in a text input field before saving."

		self.helpTextLabel['justify'] = alignment
		self.helpText.set( helpText )

	def exportBanner( self ):
		exportSingleTexture( globalData.disc.gameId + ' Banner.png', self.bannerCanvas.pilImage, imageType=5 )

	def importBanner( self ):
		imagePath = importSingleTexture( "Choose a banner texture of 96x32 to import" )

		# The above will return an empty string if the user canceled
		if not imagePath: return ''

		# Get the disc file and save the banner image data to it
		bannerFile = globalData.disc.getBannerFile()
		try:
			returnCode = bannerFile.setTexture( 0x20, imagePath=imagePath )[0]
		except Exception as err:
			msg( 'An unexpected error occurred importing the texture: {}'.format(err), 'Import Error', error=True )
			return

		# Give a warning or success message
		if returnCode == 2:
			msg( 'The given image does not have the correct dimensions. The banner image should be 96x32 pixels.', 'Invalid Dimensions', warning=True )
		elif returnCode == 0:
			printStatus( 'Banner texture imported', success=True )
			

																			#===========================#
																			# ~ ~   Context Menus   ~ ~ #
																			#===========================#

class DiscMenu( Tk.Menu, object ):
	
	""" Context menu for the Disc File Tree. """

	def __init__( self, parent, tearoff=True, *args, **kwargs ):
		super( DiscMenu, self ).__init__( parent, tearoff=tearoff, *args, **kwargs )
		self.open = False

	def repopulate( self ):

		""" This method will be called every time the submenu is displayed. """

		# Clear all current population
		self.delete( 0, 'last' )

		# Determine the kind of file(s)/folder(s) we're working with, to determine menu options
		self.entity = ''
		self.fileObj = None
		self.entityName = ''
		#lastSeperatorAdded = False
		self.discTab = globalData.gui.discTab
		self.fileTree = self.discTab.isoFileTree
		self.iidSelectionsTuple = self.fileTree.selection()
		self.selectionCount = len( self.iidSelectionsTuple )
		if self.selectionCount == 1:
			# Check what kind of item is selected. May be "file", "nFolder" (native folder), or "cFolder" (convenience folder)
			itemType = self.fileTree.item( self.iidSelectionsTuple[0], 'values' )[1]
			if itemType == 'file':
				self.fileObj = globalData.disc.files.get( self.iidSelectionsTuple[0] )
				assert self.fileObj, 'IsoFileTree displays a missing file! ' + self.iidSelectionsTuple[0]
				self.entity = 'file'
				self.entityName = self.fileObj.filename
			else:
				self.entity = 'folder'
				self.entityName = os.path.basename( self.iidSelectionsTuple[0] )

		# Add main import/export options																					# Keyboard shortcuts:
		if self.iidSelectionsTuple:
			# Check if the root (Game ID) is selected
			rootIid = self.fileTree.get_children()[0]
			if self.selectionCount == 1 and self.entityName == rootIid:
				self.add_command( label='Extract Root for Dolphin', underline=0, command=self.extractRootWithNative )					# E
				self.add_command( label='Extract Root with Convenience Folders', underline=0, command=self.extractRootWithConvenience )	# E
			else:
				self.add_command( label='Export File(s)', underline=0, command=self.discTab.exportIsoFiles )							# E
		# 	self.add_command( label='Export Textures From Selected', underline=1, command=exportSelectedFileTextures )					# X

		# Add file-type-specific options if only a single file is selected
		if self.fileObj:
			self.add_command( label='Import File', underline=0, command=self.discTab.importSingleFile )									# I
			self.add_command( label='Auto Import', underline=0, command=self.discTab.importMultipleFiles )								# A
			self.add_command( label='Restore to Vanilla', underline=11, command=self.restore )											# V

			if self.fileObj.__class__ == MusicFile:
				self.add_command( label='Listen', underline=0, command=self.listenToMusic )												# L
			elif self.fileObj.__class__ == SisFile:
				self.add_command( label='Browse Strings', underline=7, command=self.openSisTextEditor )									# S
			elif self.fileObj.__class__ == CharAnimFile:
				self.add_command( label='List Animations', command=self.listAnimations )												# S
			elif self.fileObj.__class__ == CharDataFile:
				self.add_command( label='List Action Table Entries', command=self.listActionTableEntries )
			elif self.fileObj.__class__ == StageFile:
				self.add_command( label='Edit Stage', command=self.editStage )

		# self.add_command( label='Import Multiple Files', underline=7, command=importMultipleIsoFiles )								# M
			self.add_separator()

		elif self.selectionCount >= 1:
			self.add_command( label='Auto Import', underline=0, command=self.discTab.importMultipleFiles )								# A
			self.add_command( label='Restore to Vanilla', underline=11, command=self.restore )											# V
			self.add_separator()
		
		else:
			self.add_command( label='Auto Import', underline=0, command=self.discTab.importMultipleFiles )								# A

		# Add supplemental disc functions
		self.add_command( label='Add File(s) to Disc', underline=0, command=self.addFilesToIso )										# A
		# self.add_command( label='Add Directory of File(s) to Disc', underline=4, command=addDirectoryOfFilesToIso )					# D
		# self.add_command( label='Create Directory', underline=0, command=createDirectoryInIso )										# C
		if self.iidSelectionsTuple:
			if self.selectionCount == 1:
				self.add_command( label='Rename (in disc filesystem)', underline=2, command=self.renameFilesystemEntry )				# N

				if self.entity == 'file':
					is20XX = globalData.disc.is20XX
					fileType = self.fileObj.__class__.__name__

					if is20XX and fileType == 'StageFile' and self.fileObj.isRandomNeutral():
						self.add_command( label='Rename Stage Name (in CSS)', underline=2, command=self.renameDescription )				# N
					elif is20XX and fileType == 'MusicFile' and self.fileObj.isHexTrack:
						self.add_command( label='Rename Music Title (in CSS)', underline=2, command=self.renameDescription )			# N
					else:
						self.add_command( label='Edit Description (in yaml)', underline=5, command=self.renameDescription )				# D

			self.add_command( label='Delete Selected Item(s)', command=self.removeItemsFromIso )							# R
		# 	self.add_command( label='Move Selected to Directory', underline=1, command=moveSelectedToDirectory )						# O

		# Add general file operations
		if self.selectionCount == 1 and self.entity == 'file':
			self.add_separator()
			self.add_command( label='View Hex', underline=5, command=self.viewFileHex )													# H
			#self.add_command( label='Replace Hex', underline=8, command=self.replaceFileHex )											# H
			self.add_command( label='Copy Offset to Clipboard', underline=2, command=self.copyFileOffsetToClipboard )					# P
			# self.add_command( label='Browse Textures', underline=0, command=browseTexturesFromDisc )									# B
			# self.add_command( label='Analyze Structure', underline=5, command=analyzeFileFromDisc )									# Z

			if self.entityName.startswith( 'Pl' ):
				self.add_command( label='Set as CCC Source File', underline=11, command=lambda: self.cccSelectFromDisc( 'source' ) )		# S
				self.add_command( label='Set as CCC Destination File', underline=11, command=lambda: self.cccSelectFromDisc( 'dest' ) )		# D
		
		elif self.selectionCount > 1:
			# Check if all of the items are files
			for iid in self.iidSelectionsTuple:
				#if self.fileTree.item( self.iidSelectionsTuple[0], 'values' )[1] != 'file': break
				fileObj = globalData.disc.files.get( iid )
				if not fileObj: break
			else: # The loop above didn't break; only files here
				self.add_separator()
				self.add_command( label='Copy Offsets to Clipboard', underline=2, command=self.copyFileOffsetToClipboard )				# P
				
		# Check if this is a version of 20XX, and if so, get its main build number
		#orig20xxVersion = globalData.disc.is20XX # This is an empty string if the version is not detected or it's not 20XX

		# Add an option for CSP Trim Colors, if it's appropriate
		# if self.iidSelectionsTuple and orig20xxVersion:
		# 	if 'BETA' in orig20xxVersion:
		# 		majorBuildNumber = int( orig20xxVersion[-1] )
		# 	else: majorBuildNumber = int( orig20xxVersion[0] )

		# 	# Check if any of the selected files are an appropriate character alt costume file
		# 	for iid in self.iidSelectionsTuple:
		# 		entityName = os.path.basename( iid )
		# 		thisEntity = self.fileTree.item( iid, 'values' )[1] # Will be a string of 'file' or 'folder'

		# 		if thisEntity == 'file' and candidateForTrimColorUpdate( entityName, orig20xxVersion, majorBuildNumber ):
		# 			if not lastSeperatorAdded:
		# 				self.add_separator()
		# 				lastSeperatorAdded = True
		# 			self.add_command( label='Generate CSP Trim Colors', underline=0, command=self.prepareForTrimColorGeneration )		# G
		# 			break

	def extractRootWithNative( self ):

		""" Turn off convenience folders before export, if they're enabled. Restores setting afterwards. """

		useConvenienceFolders = globalData.checkSetting( 'useDiscConvenienceFolders' )

		if useConvenienceFolders:
			globalData.setSetting( 'useDiscConvenienceFolders', False )
			self.discTab.exportIsoFiles( addDolphinSubs=True )
			globalData.setSetting( 'useDiscConvenienceFolders', True )
		else: # No need to change the setting
			self.discTab.exportIsoFiles( addDolphinSubs=True )

	def extractRootWithConvenience( self ):

		""" Turn on convenience folders before export, if they're not enabled. Restores setting afterwards. """

		useConvenienceFolders = globalData.checkSetting( 'useDiscConvenienceFolders' )

		if useConvenienceFolders: # No need to change the setting
			self.discTab.exportIsoFiles()
		else:
			globalData.setSetting( 'useDiscConvenienceFolders', True )
			self.discTab.exportIsoFiles()
			globalData.setSetting( 'useDiscConvenienceFolders', False )

	def listenToMusic( self ):

		""" Add the Music Manager tab to the GUI and select it. """

		mainGui = globalData.gui
		
		# Load the audio tab
		if not mainGui.audioManagerTab:
			mainGui.audioManagerTab = AudioManager( mainGui.mainTabFrame, mainGui )
			mainGui.audioManagerTab.loadFileList()

		# Switch to the tab
		mainGui.mainTabFrame.select( mainGui.audioManagerTab )

		# Select the file
		mainGui.audioManagerTab.selectSong( self.fileObj.isoPath )

	def listAnimations( self ):

		self.fileObj.initialize()

		lines = []
		for anim in self.fileObj.animations:
			charName = anim.name[3:].split( '_' )[0]
			animName = anim.name.split( '_' )[3]
			
			lines.append( '{}  -  {}  -  0x{:X}'.format(charName, animName, 0x20+anim.offset) )

		cmsg( '\n'.join(lines), '{} Animation Names'.format(self.fileObj.filename) )

	def listActionTableEntries( self ):
		
		table = self.fileObj.getActionTable()
		title = self.fileObj.filename + ' Action Table Entries - ' + hex( table.offset + 0x20 )

		lines = []
		for i, values in table.iterateEntries():
			actionName = self.fileObj.getString( values[0] )
			offset = table.entryIndexToOffset( i )
			lines.append( '\t{} | {} - {}'.format(i, uHex(offset + 0x20), actionName) )
			
		cmsg( '\n'.join(lines), title )

	def editStage( self ):

		""" Adds the Stage Manager tab to the GUI if it's not already present, 
			then adds a new tab for the currently selected stage and selects it. """

		globalData.gui.loadStageEditor( targetStage=self.fileObj )

	def openSisTextEditor( self ):
		SisTextEditor( self.fileObj )

	def restore( self ):

		""" Restores the selected file(s) to their vanilla counterparts. """

		if self.selectionCount == 1:
			title = 'Restore Selected File?'
			message = ( 'Are you sure you want to restore this file to its vanilla '
					'(original/unmodified) self? This will of course overwrite any modifications it currently has.' )
		else:
			title = 'Restore Selected Files?'
			message = ( 'Are you sure you want to restore these files to their vanilla '
					'(original/unmodified) selves? This will of course overwrite any modifications they currently have.' )

		yes = askyesno( title, message )
		if not yes: return

		self.discTab.restoreFiles()

	def addFilesToIso( self ):

		""" Prompts the user for one or more files to add to the disc, and then 
			adds those files to both the internal disc object and the GUI. """

		# Prompt for one or more files to add.
		filepaths = tkFileDialog.askopenfilename(
			title='Choose one or more files (of any format) to add to the disc image.', 
			initialdir=globalData.getLastUsedDir(),
			multiple=True,
			filetypes=[ ('All files', '*.*'), ('Model/Texture data files', '*.dat *.usd *.lat *.rat'), ('Audio files', '*.hps *.ssm'),
						('System files', '*.bin *.ldr *.dol *.toc'), ('Video files', '*.mth *.thp') ]
			)

		if not filepaths: # User may have canceled; filepaths will be empty in that case
			globalData.gui.updateProgramStatus( 'Operation canceled' )
			return
		
		parent, iidToAddBefore = self.discTab.determineNewFileInsertionKey()

		if parent == 'sys':
			msg( 'Directories or files cannot be added to the system files folder.', warning=True )
			return

		# If only one file was selected, offer to modify its name (ignored on multiple files which would probably be tedious)
		if len( filepaths ) == 1:
			dirPath, fileName = os.path.split( filepaths[0] )
			newName = getNewNameFromUser( 30, message='Enter a disc file name:', defaultText=fileName )
			if not newName:
				globalData.gui.updateProgramStatus( 'Operation canceled' )
				return
			#filepaths = ( os.path.join(dirPath, newName), )
		else:
			newName = ''

		preexistingFiles = [] # Strings; absolute file paths
		filenamesTooLong = [] # Strings; absolute file paths
		filesToAdd = [] # These will be file objects

		# Add the files to the file tree, check for pre-existing files of the same name, and prep the files to import
		for filepath in filepaths: # Must be file paths; folders can't be selected by askopenfilename
			# Get the new file's name and size
			fileName = os.path.basename( filepath ).replace( ' ', '_' ).replace( '-', '/' ) # May denote folders in the file name!
			fileNameOnly = fileName.split('/')[-1] # Will be no change from the original string if '/' is not present

			# Construct a new isoPath for this file
			if not iidToAddBefore or iidToAddBefore == 'end':
				newFileIsoPath = parent + '/' + fileName
			else: # iidToAddBefore is an isoPath of an existing file
				isoFolderPath = '/'.join( iidToAddBefore.split('/')[:-1] ) # Remove last fragment
				newFileIsoPath = isoFolderPath + '/' + fileName

			# Exclude files with filenames that are too long
			if len( os.path.splitext(fileNameOnly)[0] ) >= 30:
				filenamesTooLong.append( filepath )
				continue

			# Create folders that may be suggested by the filename (if these folders don't exist, 
			# then the file won't either, so the file-existance check below this wont fail)
			# if '/' in fileName:
			# 	for folderName in fileName.split('/')[:-1]: # Ignore the last part, the file name
			# 		isoPath += '/' + folderName
			# 		iid = isoPath
			# 		if not self.isoFileTree.exists( iid ):
			# 			self.isoFileTree.insert( parent, index, iid=iid, text=' ' + folderName, image=globalData.gui.imageBank('folderIcon') )
			# 		parent = iid

			# Exclude files that already exist in the disc
			#isoPath += '/' + fileNameOnly
			#iid = isoPath
			#if self.fileTree.exists( newFileIsoPath ):
			if newFileIsoPath in globalData.disc.files:
				preexistingFiles.append( fileName )
				continue

			# Create a file object for this file
			try:
				fileSize = int( os.path.getsize(filepath) ) # int() required to convert the value from long to int
				fileObj = fileFactory( None, -1, fileSize, newFileIsoPath, extPath=filepath, source='file' )
				if newName:
					fileObj.isoPath = '/'.join( newFileIsoPath.split('/')[:-1] + [newName] )
					fileObj.filename = newName
			except Exception as err:
				print( 'Unable to initialize {}; {}'.format(filepath, err) )
				continue
			fileObj.insertionKey = iidToAddBefore
			filesToAdd.append( fileObj )

		# Actually add the new file objects to the disc object
		globalData.disc.addFiles( filesToAdd )

		# Show new files in the Disc File Tree
		if self.discTab:
			self.discTab.loadDisc( updateStatus=False, preserveTreeState=True )
			for fileObj in filesToAdd:
				self.fileTree.item( fileObj.isoPath, values=('Adding to disc...', 'file'), tags='changed' )

		# Update the Disc Details Tab
		detailsTab = globalData.gui.discDetailsTab
		if detailsTab:
			detailsTab.isoFileCountText.set( "{:,}".format(len(globalData.disc.files)) )
			#detailsTab # todo: disc size as well

		# Directly notify the user of any excluded files
		notifications = '' # For a pop-up message
		statusBarMsg = ''
		if preexistingFiles:
			notifications += 'These files were skipped, because they already exist in the disc:\n\n' + '\n'.join(preexistingFiles)
			statusBarMsg += '{} pre-existing disc files skipped. '.format( len(preexistingFiles) )
		if filenamesTooLong:
			if notifications: notifications += '\n\n'
			notifications += 'These files were skipped, because their file names are longer than 29 characters:\n\n' + '\n'.join(filenamesTooLong)
			statusBarMsg += '{} files skipped due to long filenames. '.format( len(filenamesTooLong) )
		if notifications:
			msg( notifications, warning=True )

		# If any files were added, scroll to the newly inserted item (so it's visible to the user), and update the pending changes and program status
		if not filesToAdd: # No files added
			globalData.gui.updateProgramStatus( 'No files added. ' + statusBarMsg )
			return
		
		# Scroll to the file(s) added so they're immediately visible to the user (unless a custom location was chosen, thus is probably already scrolled to)
		#if not iidToAddBefore or iidToAddBefore == 'end': # iidToAddBefore should be an empty string if the file was added alphanumerically
		self.fileTree.see( filesToAdd[0].isoPath ) # Should be the iid of the topmost item that was added

		# Update the program status message
		if len( filesToAdd ) == 1:
			if statusBarMsg:
				globalData.gui.updateProgramStatus( '{} added. '.format(filesToAdd[0].filename) + statusBarMsg )
			else:
				globalData.gui.updateProgramStatus( '{} added to the disc'.format(filesToAdd[0].filename) )
		else:
			globalData.gui.updateProgramStatus( '{} files added. '.format(len(filesToAdd)) + statusBarMsg )

	def removeItemsFromIso( self ):
		self.discTab.deleteIsoFiles( self.iidSelectionsTuple )

	# def prepareForTrimColorGeneration( self ):

	# 	""" One of the primary methods for generating CSP Trim Colors.

	# 		If only one file is being operated on, the user will be given a prompt to make the final color selection.
	# 		If multiple files are selected, the colors will be generated and selected autonomously, with no user prompts. """

	# 	# Make sure that the disc file can still be located
	# 	if not discDetected(): return

	# 	if self.selectionCount == 1:
	# 		generateTrimColors( self.iidSelectionsTuple[0] )

	# 	else: # Filter the selected files and operate on all alt costume files only, in autonomous mode
	# 		for iid in self.iidSelectionsTuple:
	# 			entityName = os.path.basename( iid )
	# 			thisEntity = self.fileTree.item( iid, 'values' )[1] # Will be a string of 'file' or 'folder'
	
				# Check if this is a version of 20XX, and if so, get its main build number
				#orig20xxVersion = globalData.disc.is20XX # This is an empty string if the version is not detected or it's not 20XX

	# 			if 'BETA' in orig20xxVersion: origMainBuildNumber = int( orig20xxVersion[-1] )
	# 			else: origMainBuildNumber = int( orig20xxVersion[0] )

	# 			if thisEntity == 'file' and candidateForTrimColorUpdate( entityName, orig20xxVersion, origMainBuildNumber ):
	# 				generateTrimColors( iid, True ) # autonomousMode=True means it will not prompt the user to confirm its main color choices

	def renameFilesystemEntry( self ):

		""" Renames the file name in the disc filesystem for the currently selected file. """

		# Prompt the user to enter a new name
		newName = getNewNameFromUser( 30, message='Enter a new filesystem name:', defaultText=self.entityName )
		if not newName:
			globalData.gui.updateProgramStatus( 'Name update canceled' )
			return

		# Reject illegal renames
		basename = os.path.basename( self.fileObj.filename )
		if self.fileObj.filename in globalData.disc.systemFiles:
			msg( 'System files cannot be renamed!', 'Invalid Rename' )
			globalData.gui.updateProgramStatus( 'Unable to rename system files' )
			return
		elif basename in ( 'MnSlChr', 'MnSlMap', 'opening' ):
			if not askyesno( ('These are important system files that are not '
				'expected to have any other name. Renaming them could lead to '
				'unexpected problems. \n\nAre you sure you want to do this?'), 'Warning!' ):
				return
		
		print( 'rename filesystem entry not yet implemented' )
		# Update the file name in the FST
		# oldName = 
		# for entry in globalData.disc.fstEntries: # Entries are of the form [ folderFlag, stringOffset, entryOffset, entrySize, entryName, isoPath ]
		# 	if entry[-2] == 

		# isoPath = self.iidSelectionsTuple[0]

		# self.fileTree.item( isoPath, 'text', newName )

	def renameDescription( self ):

		charLimit = 42 # Somewhat arbitrary limit

		if self.fileObj.__class__.__name__ == 'StageFile' and self.fileObj.isRandomNeutral():
			charLimit = 0x1F # Max space in CSS file
		elif self.fileObj.__class__.__name__ == 'MusicFile' and self.fileObj.isHexTrack:
			cssFile = globalData.disc.files.get( globalData.disc.gameId + '/MnSlChr.0sd' )
			if not cssFile:
				msg( "Unable to update CSS with song name; the CSS file (MnSlChr.0sd) could not be found in the disc." )
				globalData.gui.updateProgramStatus( "Unable to update CSS with song name; couldn't find the CSS file in the disc", error=True )
				return
			charLimit = cssFile.checkMaxHexTrackNameLen( self.fileObj.trackId )

		# Prompt the user to enter a new name
		newName = getNewNameFromUser( charLimit, message='Enter a new description:', defaultText=self.fileObj.longDescription )
		if not newName:
			globalData.gui.updateProgramStatus( 'Name update canceled' )
			return

		# Store the new name to file
		returnCode = self.fileObj.setDescription( newName )

		if returnCode == 0:
			# Update the new name in the treeview on this tab, as well as in the Stage Manager tab
			globalData.gui.discTab.updateDescription( self.fileObj.isoPath, self.fileObj.shortDescription, alt=self.fileObj.longDescription )
			if globalData.gui.stageManagerTab:
				globalData.gui.stageManagerTab.renameTreeviewItem( self.fileObj.isoPath, newName ) # No error if not currently displayed

			# Update the program status bar
			if self.fileObj.__class__.__name__ == 'StageFile' and self.fileObj.isRandomNeutral():
				globalData.gui.updateProgramStatus( 'Stage name updated in the CSS file', success=True )
			elif self.fileObj.__class__.__name__ == 'MusicFile' and self.fileObj.isHexTrack:
				globalData.gui.updateProgramStatus( 'Song name updated in the CSS file', success=True )
			else:
				globalData.gui.updateProgramStatus( 'File name updated in the {}.yaml config file'.format(globalData.disc.gameId), success=True )
		elif returnCode == 1:
			globalData.gui.updateProgramStatus( 'Unable to update name/description in the {}.yaml config file'.format(globalData.disc.gameId), error=True )
		elif returnCode == 2:
			globalData.gui.updateProgramStatus( "Unable to update CSS with the name; couldn't find the CSS file in the disc", error=True )
		elif returnCode == 3:
			globalData.gui.updateProgramStatus( "Unable to update CSS with the name; couldn't save the name to the CSS file", error=True )
		else:
			msg( 'An unrecognized return code was given by .setDescription(): ' + str(returnCode) )

	def viewFileHex( self ):

		""" Gets and displays hex data for a file within a disc in the user's hex editor of choice. """

		# Create a file name with folder names included, so that multiple files of the same name (but from different folders) can be opened.
		isoPath = self.iidSelectionsTuple[0]
		filename = '-'.join( isoPath.split('/')[1:] ) # Excludes the gameId

		# Get the file data, create a temp file with it, and show it in the user's hex editor
		datData = self.fileObj.getData()
		saveAndShowTempFileData( datData, filename )

	#def replaceFileHex( self ):

	def copyFileOffsetToClipboard( self ):
		# Ensure the user knows what's being operated on
		self.fileTree.selection_set( self.iidSelectionsTuple ) 	# Highlights the item(s)
		self.fileTree.focus( self.iidSelectionsTuple[0] ) 		# Sets keyboard focus to the first item

		# Get the offsets of all of the items selected
		offsets = []
		for iid in self.iidSelectionsTuple:
			fileObj = globalData.disc.files.get( iid )
			offsets.append( uHex(fileObj.offset) )

		copyToClipboard( ', '.join(offsets) )

	def cccSelectFromDisc( self, role ):

		""" Add character files from the disc to the CCC tool window. """

		# Check if an instance exists, and create one if it doesn't
		cccWindow = globalData.getUniqueWindow( 'Character Color Converter' )
		if not cccWindow:
			cccWindow = CharacterColorConverter()

		# Create a copy of the file (without making a disc copy) to send to the CCC, because it will be modified
		disc = self.fileObj.disc
		fileCopy = disc.copyFile( self.fileObj, disc )

		cccWindow.updateSlotRepresentation( fileCopy, role )