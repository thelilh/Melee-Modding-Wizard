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

import json
import time
import struct
import bitstring
import globalData

from binascii import hexlify
from collections import OrderedDict

from .fileBases import FileBase
from .hsdFiles import DatFile
from FileSystem import hsdStructures
from .hsdStructures import StructBase, TableStruct, DataBlock
from basicFunctions import msg, printStatus, reverseDictLookup, uHex, roundTo32


class CharFileBase( object ):

	# Character file abbreviations; the key comes from the root node of the character file
	charAbbrs = { 	'Boy': 'Bo', 'Crazyhand': 'Ch', 'Gkoopa': 'Gk', 'Girl': 'Gl', 'Masterhand': 'Mh', 'Sandbag': 'Sb',
					'KirbyDk': 'KbDk', 'KirbyFc': 'KbFc', 'KirbyGw': 'KbGw', 'KirbyMt': 'KbMt', 'KirbyPr': 'KbPr', 

					'Captain': 'Ca', 'Clink': 'Cl', 'Donkey': 'Dk', 'Drmario': 'Dr', 'Falco': 'Fc', 'Emblem': 'Fe', 
					'Fox': 'Fx', 'Ganon': 'Gn', 'Gamewatch': 'Gw', 'Kirby': 'Kb', 'Koopa': 'Kp', 'Luigi': 'Lg', 
					'Link': 'Lk', 'Mario': 'Mr', 'Mars': 'Ms', 'Mewtwo': 'Mt', 'Nana': 'Nn', 'Ness': 'Ns', 
					'Pichu': 'Pc', 'Peach': 'Pe', 'Pikachu': 'Pk', 'Popo': 'Pp', 'Purin': 'Pr', 
					'Seak': 'Sk', 'Samus': 'Ss', 'Yoshi': 'Ys', 'Zelda': 'Zd' }

	# Character Abbreviation (key) to Internal Character ID (value)
	intCharIds = { 	'Mr': 0x00, 'Fx': 0x01, 'Ca': 0x02, 'Dk': 0x03, 'Kb': 0x04, 'Kp': 0x05, 'Lk': 0x06,
					'Sk': 0x07, 'Ns': 0x08, 'Pe': 0x09, 'Pp': 0x0A, 'Nn': 0x0B, 'Pk': 0x0C, 'Ss': 0x0D,
					'Ys': 0x0E, 'Pr': 0x0F, 'Mt': 0x10, 'Lg': 0x11, 'Ms': 0x12, 'Zd': 0x13, 'Cl': 0x14,
					'Dr': 0x15, 'Fc': 0x16, 'Pc': 0x17, 'Gw': 0x18, 'Gn': 0x19, 'Fe': 0x1A, 'Mh': 0x1B,
					'Ch': 0x1C, 'Bo': 0x1D, 'Gl': 0x1E, 'Gk': 0x1F, 'Sb': 0x20 }

	# Character Abbreviation (key) to External Character ID (value)
	extCharIds = { 	'Ca': 0x00, 'Dk': 0x01, 'Fx': 0x02, 'Gw': 0x03, 'Kb': 0x04, 'Kp': 0x05, 'Lk': 0x06,
					'Lg': 0x07, 'Mr': 0x08, 'Ms': 0x09, 'Mt': 0x0A, 'Ns': 0x0B, 'Pe': 0x0C, 'Pk': 0x0D,
					'Pp': 0x0E, 'Pr': 0x0F, 'Ss': 0x10, 'Ys': 0x11, 'Zd': 0x12, 'Sk': 0x13, 'Fc': 0x14,
					'Cl': 0x15, 'Dr': 0x16, 'Fe': 0x17, 'Pc': 0x18, 'Gn': 0x19, 'Mh': 0x1A, 'Bo': 0x1B,
					'Gl': 0x1C, 'Gk': 0x1D, 'Ch': 0x1E, 'Sb': 0x1F, 'Nn': 0x0E } # Excludes 0x20 (Solo Popo)

	specialAttrNames = {}
	subActionTranslations = {}
	eventNotes = {}
	translationsChecked = False

	@property
	def intCharId( self ):
		if self._intCharId == -2:
			self._intCharId = self.intCharIds.get( self.charAbbr, -1 )
		return self._intCharId

	@property
	def extCharId( self ):
		if self._extCharId == -2:
			self._extCharId = self.extCharIds.get( self.charAbbr, -1 )
		return self._extCharId
		
	@property
	def charAbbr( self ): # e.g. 'Ca'
		if not self._charAbbr:
			self._charAbbr = self.getCharAbbr()
		return self._charAbbr

	@property
	def charName( self ): # e.g. 'Captain Falcon'
		if not self._charName and self.extCharId >= 0:
			self._charName = self.getCharName( self.extCharId )
		return self._charName

	@property
	def nickname( self ): # e.g. 'Captain'
		if not self._nickname:
			self.getCharAbbr()
		return self._nickname

	def getCharName( self, extCharId ):
		if extCharId < 0 or extCharId >= len( globalData.charList ):
			return 'Unidentified'
		elif extCharId == 0xE: # "Ice Climbers" in the character list
			if self.charAbbr == 'Nn':
				return 'Nana'
			elif self.charAbbr == 'Pp':
				return 'Popo'
			else: # Failsafe; not expected
				return 'ICies'
		else:
			return globalData.charList[extCharId]

	def getCharDataTranslations( self ):

		""" Retrieves various human-readable names and notes for character data files from a JSON file. """

		if not self.translationsChecked:
			# Open the Properties.json file and get its file contents
			try:
				jsonPath = globalData.paths['charDataTranslations']
				with open( jsonPath, 'r' ) as jsonFile:
					jsonContents = json.load( jsonFile )
					self.specialAttrNames = jsonContents['specialAttributes']
					self.subActionTranslations = jsonContents['subActionTranslation']
					self.eventNotes = jsonContents['eventNotes']
			except Exception as err:
				errMsg = 'Encountered an error when attempting to open "{}" (likely due to incorrect formatting); {}'.format( jsonPath, err )
				msg( errMsg )
			self.translationsChecked = True

	def getEventNotes( self, eventCode ):

		""" Returns the notes (a string) for a given subAction event code/ID. 
			Returns an empty string if no notes are available. """

		key = '0x{:02X}'.format( eventCode )
		value = self.eventNotes.get( key, '' )

		# Very long strings will be stored as lists for better readability in the json file
		if isinstance( value, list ):
			value = ''.join( value )

		return value

	def getFriendlyActionName( self, symbol=None, symbolPointer=-1, actionTableIndex=-1 ):

		""" Translates an action state or animation subaction symbol name, such as 
			"PlyCaptain5K_Share_ACTION_AttackS3S_figatree", to a more human-friendly and 
			recognizable name, such as "Forward Tilt". Returns the game name (AttackS3S) as well as 
			the translated name (Forward Tilt). The translated name may be an empty string if not defined. """

		self.getCharDataTranslations()

		# Get and parse the full symbol name
		if not symbol:
			assert symbolPointer != -1, 'Invalid input to .getFriendlyActionName(); no symbol pointer provided.'
			symbol = self.getString( symbolPointer ) # e.g. 'PlyCaptain5K_Share_ACTION_AttackS3S_figatree'
		gameName = symbol.split( '_' )[3] # e.g. 'AttackS3S'

		# Try to look up the friendly name
		friendlyName = self.subActionTranslations.get( gameName, '' )

		# Modify the friendly name for certain actions
		if friendlyName:
			if isinstance( self, CharDataFile ):
				assert actionTableIndex != -1, 'No action table index provided for action name translation.'
				
				if actionTableIndex >= 0x6C and actionTableIndex <= 0x83: # Item swing actions
					if actionTableIndex <=0x6F:
						friendlyName = 'Beam Sword ' + friendlyName
					elif actionTableIndex <=0x73:
						friendlyName = 'Bat ' + friendlyName
					elif actionTableIndex <=0x77:
						friendlyName = 'Parasol ' + friendlyName
					elif actionTableIndex <=0x7B:
						friendlyName = 'Fan ' + friendlyName
					elif actionTableIndex <=0x7F:
						friendlyName = 'Star Rod ' + friendlyName
					else:
						friendlyName = "Lip's Stick " + friendlyName

		elif self.charAbbr == 'Gk' or self.charAbbr == 'Kp': # Bowser/Giga Bowser
			if gameName.startswith( 'TKoopaSpecial' ):
				friendlyName = 'Koopa Klaw'

		elif self.charAbbr == 'Dk':
			if gameName.startswith( 'TDonkeyThrowF' ):
				friendlyName = 'Kong Karry'

		elif gameName[0] == 'T' and gameName[1] != 'h' and 'Throw' in gameName: # Taro animations
			friendlyName = 'Victim Thrown'

			if gameName.endswith( 'F' ):
				friendlyName += ' Forward'
			elif gameName.endswith( 'B' ):
				friendlyName += ' Backward'
			elif gameName.endswith( 'Hi' ):
				friendlyName += ' Up'
			elif gameName.endswith( 'Lw' ):
				friendlyName += ' Down'
			elif gameName.endswith( 'LwPeach' ):
				friendlyName = 'Peach Thrown Down'
		
		return gameName, friendlyName


class CharDataFile( CharFileBase, DatFile ):

	""" Pl__.dat (ftData_) """
	
	def __init__( self, *args, **kwargs ):
		super( CharDataFile, self ).__init__( *args, **kwargs )

		self._intCharId = -2
		self._extCharId = -2
		self._charAbbr = ''
		self._charName = ''
		self._nickname = ''

	def getCharAbbr( self ):

		""" Returns the two-letter abbreviation for this character (e.g. 'Ca' for Captain Falcon). 
			Also sets the character nickname (e.g. 'Captain' for Captain Falcon) often used in strings. """

		# Ensure root nodes and the string table have been parsed
		self.initialize()

		rootNodeName = self.rootNodes[0][1]
		self._nickname = rootNodeName[6:] # Removes 'ftData' from the string

		if self._nickname.startswith( 'KirbyCopy' ):
			self._nickname = 'Kirby'

		return self.charAbbrs.get( self._nickname, '' )

	def validate( self ):

		""" Verifies whether this is actually a character data file by checking the string table. 
			This will also initialize the file and retrieve its file data. """

		self.initialize()
		rootNodeName = self.rootNodes[0][1]

		if not rootNodeName.startswith( 'ftData' ):
			raise Exception( "Invalid character data file; no 'ftData...' symbol node found." )

	def hintRootClasses( self ):
		dataTableOffset = self.rootNodes[0][0]
		self.structs[dataTableOffset] = 'FighterDataTable'

	def getDescription( self ):
		
		# Attempt to get the character name this file is for
		charName = globalData.charNameLookup.get( self.charAbbr, '' )
		if not charName:
			self._longDescription = 'Unknown ({}) data file'.format( self.charAbbr )
		elif charName.endswith( 's' ):
			self._longDescription = charName + "' data file"
		else:
			self._longDescription = charName + "'s data file"

		# First two are for 20XX files
		if self.ext[1] == 'p':
			self._shortDescription = 'PAL Data file'
			self._longDescription.replace( 'data', 'PAL data' )
		elif self.ext[1] == 's':
			self._shortDescription = 'SDR Data file'
			self._longDescription.replace( 'data', 'SDR data' )
		else:
			self._shortDescription = 'Data file'

		# Give additional details for Kirby copy powers
		if len( self.filename ) == 12 and self.filename.startswith( 'PlKbCp' ):
			copyTargetExternalId = self.extCharIds.get( self.filename[6:8], -1 )
			copyTarget = self.getCharName( copyTargetExternalId )
			self._shortDescription += ' for {} copy power'.format( copyTarget )
			self._longDescription += ' for {} copy power'.format( copyTarget )

	def getAttributesInfo( self ):

		""" Read the JSON file containing attribute names, if it has not already been read, 
			and return the attribute names and formatting for this character. """
		
		self.getCharDataTranslations()

		# Get and return the attribute names/formats for this character
		return self.specialAttrNames.get( self.charAbbr )

	def getGeneralProperties( self ):

		self.initialize()

		# Get the root fighter data table
		fighterTableOffset = self.rootNodes[0][0] # Root nodes is a list of tuples, each of the form ( structOffset, string )
		ftDataTable = self.initSpecificStruct( FighterDataTable, fighterTableOffset )

		# Get and return the general properties struct
		propertiesPointer = ftDataTable.getValues()[0]
		return self.initDataBlock( GeneralFighterProperties, propertiesPointer, fighterTableOffset, dataLength=0x184 )

	def getSpecialAttributes( self ):

		self.initialize()

		# Get the root fighter data table
		fighterTableOffset = self.rootNodes[0][0] # Root nodes is a list of tuples, each of the form ( structOffset, string )
		ftDataTable = self.initSpecificStruct( FighterDataTable, fighterTableOffset )

		# Get and return the special attributes struct
		attributesPointer = ftDataTable.getValues()[1]
		propStruct = self.initDataBlock( SpecialCharacterAttributes, attributesPointer, fighterTableOffset )

		# Cast what we're going to edit into lists, so we can use item assignment
		propFieldNames = list( propStruct.fields )
		propFormatting = list( propStruct.formatting[1:] ) # Excludes '>' character
		propStruct.notes = [ '' for i in range(len( propStruct.fields )) ]

		# Update field names and formatting for this struct if info on it is available
		attrInfo = self.getAttributesInfo()
		if attrInfo:
			offsetsFound = set()

			for offset, attrType, name, note in attrInfo[1:]: # Excludes first entry (character name)
				# Validate the offset
				try:
					offset = int( offset, 16 )
				except:
					msg( 'An invalid offset was found in the Properties.json file for "{}": {}. This should be a hexadecimal number.'.format(name, offset), 'Invalid Attribute Offset', warning=True )
					continue
				if offset % 4 != 0:
					msg( 'An invalid offset was found in the Properties.json file for "{}": {}. These values should be a multiple of 4.'.format(name, offset), 'Invalid Attribute Offset', warning=True )
					continue
				elif offset in offsetsFound:
					msg( 'A duplicate offset was found in the Properties.json file for "{}": {}'.format(name, offset), 'Duplicate Attribute Offset', warning=True )
					continue
				else:
					offsetsFound.add( offset )
					valueIndex = offset / 4
					if valueIndex >= len( propStruct.fields ):
						msg( 'An invalid offset was found in the Properties.json file for "{}": {}. The offset is beyond the range of the special attributes structure.'.format(name, offset), 'Invalid Attribute Offset', warning=True )
						continue

				# Validate the attribute type
				if attrType not in ( 'I', 'f' ):
					msg( 'An invalid attribute type was found in the Properties.json file for "{}": {}. These should either be "I" or "f" for integers and floats, respectively.'.format(name, offset), 'Invalid Attribute Type', warning=True )
					continue

				# Update the field name and format identifier for this entry
				if name: # Might be empty
					propFieldNames[valueIndex] = name
				propFormatting[valueIndex] = attrType
				propStruct.notes[valueIndex] = note

			# Re-cast and replace the original struct fields and formatting
			propStruct.fields = tuple( propFieldNames )
			propStruct.formatting = '>' + ''.join( propFormatting )

			# Re-unpack values since we've modified the attribute types
			propStruct.values = ()
			propStruct.getValues()
		
		return propStruct

	def getModelLookupTable( self ):

		self.initialize()

		# Get the root fighter data table
		fighterTableOffset = self.rootNodes[0][0] # Root nodes is a list of tuples, each of the form ( structOffset, string )
		ftDataTable = self.initSpecificStruct( FighterDataTable, fighterTableOffset )

		# Get and return the lookup table
		tablePointer = ftDataTable.getValues()[2]
		return self.initSpecificStruct( ModelLookupTables, tablePointer, ftDataTable.offset )

	def getActionTable( self ):

		self.initialize()

		# Get the root fighter data table
		fighterTableOffset = self.rootNodes[0][0] # Root nodes is a list of tuples, each of the form ( structOffset, string )
		ftDataTable = self.initSpecificStruct( FighterDataTable, fighterTableOffset )

		# Get and return the action table
		actionTablePointer = ftDataTable.getValues()[3]
		return self.initSpecificStruct( ActionTable, actionTablePointer, ftDataTable.offset )


class FighterDataTable( StructBase ):

	""" Primary/root table for character data files (Pl__.dat). """

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Fighter Data Table ' + uHex( 0x20 + args[1] )
		self.formatting = '>IIIIIIIIIIIIIIIIIIIIIIII'
		self.fields = ( 'Common_Attributes_Pointer',
						'Special_Attributes_Pointer',
						'Model_Lookup_Tables_Pointer',
						'Fighter_Action_Table_Pointer',
						'Dynamic_Action_Behaviors_Pointer',		# 0x10
						'Demo_Fighter_Action_Table_Pointer',
						'Demo_Dynamic_Action_Behaviors_Pointer',
						'Model_Part_Animations_Pointer',
						'Shield_Pose_Container_Pointer',		# 0x20
						'Idle_Action_Chances_Pointer',
						'Wait_Idle_Action_Chances_Pointer',
						'Physics_Pointer',
						'Hurtboxes_Pointer',					# 0x30
						'Center_Bubble_Pointer',
						'Coin_Collision_Spheres_Pointer',
						'Camera_Box_Pointer',
						'Item_Pickup_Params_Pointer',			# 0x40
						'Environment_Collision_Pointer',
						'Articles_Pointer',
						'Common_Sound_Effect_Table_Pointer',
						'JostleBox_Pointer',					# 0x50
						'Fighter_Bone_Table_Pointer',
						'Fighter_IK_Pointer',
						'Metal_Model_Pointer'
					)
		self.length = 0x60
		self.structDepth = ( 2, 0 )
		self._siblingsChecked = True
		self.childClassIdentities = { 
			0: 'GeneralFighterProperties', 
			1: 'SpecialCharacterAttributes', 
			2: 'ModelLookupTables', 
			3: 'ActionTable' 
		}


class ModelLookupTables( StructBase ):

	""" Character model-part lookup table, used to determine which parts of 
		a model should be visible (such as for high-poly or low-poly), along 
		with information on some specific materials and bones. """

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Model Lookup Table ' + uHex( 0x20 + self.offset )
		self.formatting = '>IIIIBBBBBBH'
		self.fields = ( 'Visibility_Group_Lookup_Lengths',
						'Part_Visibility_Table_Pointer',
						'Material_Group_Lookup_Lengths',
						'Material_Lookup_Table_Pointer',
						'Item_Hold_Bone',
						'Shield_Bone',
						'TopOfHead_Bone',
						'LeftFoot_Bone',
						'RightFoot_Bone',
						'Padding',
						'Padding'
					)
		self.length = 0x18
		self.structDepth = ( 3, 0 )
		self._siblingsChecked = True
		self.childClassIdentities = { 
			1: 'CostumeVisibilityTable', 
			#3: 'MaterialLookupTable'
		}


class CostumeVisibilityTable( TableStruct ):

	""" Character model-part lookup table, used to determine which parts of 
		a model should be visible (such as for high-poly or low-poly). This 
		table contains 4 values per entry, where each entry is for each one 
		of the costume slots available for this character. """

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Part Visibility Table ' + uHex( 0x20 + self.offset )
		self.formatting = '>IIII'
		self.fields = ( 'High_Poly_Group_Pointer',
						'Low_Poly_Group_Pointer',
						'Metal_Group_Pointer',
						'Metal_Main_Group_Pointer'
					)
		self.length = 0x10
		self.structDepth = ( 4, 0 )
		self._siblingsChecked = True

		# Attempt to get the length and array count of this struct
		deducedStructLength = self.dat.getStructLength( self.offset )
		self.entryCount = deducedStructLength / 0x10

		TableStruct.__init__( self )

		for i in range( 0, len(self.fields) ):
			self.childClassIdentities[i] = 'GroupLookupArray'

	def _getGroupArray( self, costumeIndex, arrayGroupIndex ):

		""" This attempts to get a group of pointers (one entry in this struct) 
			for a particular costume index. However, entries for some costumes 
			may be null, in which case we fall back to the default (first) entry. """

		# Try to get a lookup group for this costume
		arrayGroup = self.initChild( GroupLookupArray, costumeIndex, arrayGroupIndex )

		# If the above failed (invalid pointer in that group), default to the first table entry (neutral costume slot)
		if not arrayGroup and costumeIndex != 0:
			arrayGroup = self.initChild( GroupLookupArray, 0, arrayGroupIndex )

		return arrayGroup

	def getHighPolyPartIds( self, costumeIndex ):

		""" Recursively parses the array group structs and gets all high-poly IDs. """
		
		highPolyGroupArray = self._getGroupArray( costumeIndex, 0 )
		return highPolyGroupArray.getLookupIds()

	def getLowPolyPartIds( self, costumeIndex ):

		""" Recursively parses the array group structs and gets all low-poly IDs. """
		
		lowPolyGroupArray = self._getGroupArray( costumeIndex, 1 )
		return lowPolyGroupArray.getLookupIds()


class GroupLookupArray( TableStruct ):

	""" An array of Count and Pointer entries. """

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Group Lookup Array ' + uHex( 0x20 + self.offset )
		self.formatting = '>II'
		self.fields = ( 'SubArray_Count', 'SubGroup_Pointer' )
		self.length = 8
		self.structDepth = ( 5, 0 )
		self._siblingsChecked = True

		# Get the array count for this struct
		lookupTable = self.dat.getModelLookupTable()
		self.entryCount = lookupTable.getValues()[0]

		TableStruct.__init__( self )

		for i in range( 0, len(self.fields), self.entryValueCount ):
			self.childClassIdentities[i+1] = 'SubGroupLookupArray'

	def initChildren( self ):

		""" Initializes all child structs with the entryCount values present in this struct. """

		children = []

		for _, ( count, subGroupPointer ) in self.iterateEntries():
			if count == 0:
				continue

			subGroupArray = self.dat.initSpecificStruct( SubGroupLookupArray, subGroupPointer, self.offset, (6, 0), count )
			if subGroupArray:
				children.append( subGroupArray )

		return children
	
	def getLookupIds( self ):

		""" Initializes all child SubGroup Arrays, gets all of their children (LookupEntry structs), 
			and processes them to get their ID values. """

		entries = []

		for subGroupArray in self.initChildren():
			lookupEntries = subGroupArray.initChildren()
			for entry in lookupEntries:
				entries.extend( entry.getValues() )

		return entries


class SubGroupLookupArray( TableStruct ):

	""" An array of Count and Pointer entries. """

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'SubGroup Lookup Array ' + uHex( 0x20 + self.offset )
		self.formatting = '>II'
		self.fields = ( 'Lookup_Entry_Count', 'Lookup_Pointer' )
		self.length = 8
		self.structDepth = ( 6, 0 )
		self._siblingsChecked = True

		# Get the array count for this struct (unused if parent's "initChildren" is used)
		if self.entryCount == -1:
			# Check the parent's SubArray_Count to see how many elements should be in this array
			parentOffset = self.getAnyDataSectionParent()
			parentStruct = self.dat.initSpecificStruct( GroupLookupArray, parentOffset )
			for _, ( count, pointer ) in parentStruct.iterateEntries():
				if pointer == self.offset:
					self.entryCount = count
					break

		TableStruct.__init__( self )

		for i in range( 0, len(self.fields), self.entryValueCount ):
			self.childClassIdentities[i+1] = 'LookupEntry'

	def initChildren( self ):

		""" Initializes all child structs with the idCount (data length) values present in this struct. """

		children = []

		for _, ( idCount, entryPointer ) in self.iterateEntries():
			if idCount == 0:
				continue

			lookupEntry = self.dat.initDataBlock( LookupEntry, entryPointer, self.offset, (7, 0), idCount )
			if lookupEntry:
				children.append( lookupEntry )

		return children


class LookupEntry( DataBlock ):

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Lookup Entry ' + uHex( 0x20 + self.offset )


class GeneralFighterProperties( DataBlock ):

	""" Describes common/basic properties which all characters have 
		(first struct referenced in Pl__.dat files' fighter data tables). """
		
	flags = { 'Weight_Dependent_Throw_Flags': OrderedDict([
				( '1<<0', 'FThrow' ),	# 1
				( '1<<1', 'BThrow' ),	# 2
				( '1<<2', 'UThrow' ),	# 4
				( '1<<3', 'DThrow' ),	# 8
		]) }

	def __init__( self, *args, **kwargs ):
		DataBlock.__init__( self, *args, **kwargs )

		self.name = 'General Fighter Properties ' + uHex( 0x20 + args[1] )
		self.formatting = '>ffffffffffffffffffffffIfffffffffffffffIffIfffffffffffffffffffffffffffffffffffffffffffffffffIffffBBH'
		self.fields = ( 'Walk_Starting_Speed',
						'Walk_Acceleration',
						'Max_Walking_Speed',
						'Walk_Animation_Speed',
						'Mid_Walk_Point',					# 0x10
						'Fast_Walk_Speed',

						'Friction',

						'Dash_Starting_Speed',
						'StopTurn_Initial_Speed_A',			# 0x20
						'StopTurn_Initial_Speed_B',
						'Max_Run_Speed',
						'Run_Animation_Scaling',
						'Dash_Lockout_Direction',			# 0x30
						'Dash_Duration_Before_Run',

						'Jump_Startup_Lag_(Frames)',
						'Initial_Horizontal_Jump_Velocity',
						'Initial_Vertical_Jump_Velocity',	# 0x40
						'Ground-to-Air_Jump_Momentum_Multiplier',
						'Max_Shorthop_Horizontal_Velocity',
						'Max_Shorthop_Vertical_Velocity',
						'Double_Jump_Horizontal_Multiplier', # 0x50
						'Double_Jump_Vertical_Multiplier',

						'Number_of_Jumps', # Int
						'Gravity',
						'Terminal_Velocity',				# 0x60
						'Aerial_Mobility_A',
						'Aerial_Mobility_B',
						'Max_Aerial_Horizontal_Speed',
						'Air_Friction',						# 0x70
						'FastFall_Terminal_Velocity',
						'TiltTurn_Forced_Velocity',

						'Jab2_Window',
						'Jab3_Window',						# 0x80
						'Frames_to_Change_Direction_on_Standing_Turn',
						'Weight',
						'Model_Scaling',
						'Shield_Size',						# 0x90
						'Shield_Break_Initial_Velocity',
						'Rapid_Jab_Window', # Int
						'Clank_Speed_Multiplier',
						'Hit-by-Item_Flag',					# 0xA0
						'Unknown_0xA4', # Int
						'Ledge_Jump_Horizontal_Velocity',
						'Ledge_Jump_Vertical_Velocity',
						'Item_Throw_Velocity',				# 0xB0
						'Item_Throw_Damage_Scaling',
						'Run_Side_Special_Momentum',
						
						'Egg_Size',
						'Egg_Hurtbox',						# 0xC0
						'Egg_Hurtbox_X',
						'Egg_Hurtbox_Y',
						'Egg_Hurtbox_Z',

						'Unknown_0xD0',						# 0xD0
						'Unknown_0xD4',
						'Egg_Hurtbox_Radius',
						'Kirby_Neutral_Special_Star_Swallow_Damage',
						'Kirby_Neutral_Special_Star_Damage',	# 0xE0

						'Normal_Landing_Lag',
						'Nair_Landing_Lag',
						'Fair_Landing_Lag',
						'Bair_Landing_Lag',					# 0xF0
						'Uair_Landing_Lag',
						'Dair_Landing_Lag',

						'Victory_Screen_Model_Scale',
						'Wall_Tech_X',						# 0x100
						'Wall_Jump_Horizontal_Velocity',
						'Wall_Jump_Vertical_Velocity',
						'Ceiling_Tech_X_Direction',
						'Unknown_0x110',					# 0x110

						'Left_Bunny_Hood_X',
						'Left_Bunny_Hood_Y',
						'Left_Bunny_Hood_Z',
						'Right_Bunny_Hood_X',				# 0x120
						'Right_Bunny_Hood_Y',
						'Right_Bunny_Hood_Z',
						'Bunny_Hood_Size',

						'Flower_X',							# 0x130
						'Flower_Y',
						'Flower_Z',
						'Flower_Size',
						'Screw_Attack_Upward_Knockback',	# 0x140
						'Screw_Attack_Effect_Size',
						'Unknown_0x148',
						'Bubble_Ratio',

						'Freeze_Offset_1',					# 0x150
						'Freeze_Offset_2',
						'Freeze_Escape_Height',
						'Freeze_Escape_X_Momentum',
						'Frozen_Size',						# 0x160

						'WarpStar_Hitbox_Scaling',
						'Unknown_0x168',
						'Camera_Zoom_Target_Bone', # Int
						'Magnified_X_Sway',					# 0x170
						'Magnified_Y_Sway',
						'Magnified_Z_Sway',
						'Footstool_Y_Offset',
						'Weight_Dependent_Throw_Flags',		# 0x180
						'Padding',
						'Padding'
					)
		self.length = 0x184
		self.structDepth = ( 3, 0 )


class SpecialCharacterAttributes( DataBlock ):

	""" Describes special properties specific to only one character 
		(second struct referenced in Pl__.dat files' fighter data tables). 
		
		Field names and correct formatting is defined in bin/Properties.json
		and should be updated when this struct is requested by charDat.getSpecialAttributes(). """

	def __init__( self, *args, **kwargs ):
		DataBlock.__init__( self, *args, **kwargs )

		self.name = 'Special Character Attributes ' + uHex( 0x20 + self.offset )

		# Build the formatting string and fields tuple based on the length of the struct
		self.length = self.dat.getStructLength( self.offset )
		self.formatting = '>' + 'f' * ( self.length / 4 )
		fieldOffsets = [ (i * 4) for i in range(len(self.formatting)-1) ]
		self.fields = tuple( 'Unknown 0x' + hex( o )[2:].upper().rstrip( 'L' ) for o in fieldOffsets )

		self.structDepth = ( 3, 0 )


class ActionTable( TableStruct ):
		
	flags = { 'State_Flags': OrderedDict([
				( '1<<0', 'Unknown 1' ),				# 1
				( '1<<1', 'Affects Model Scale' ),		# 2
				( '1<<2', 'Update TransN' ),			# 4
				( '1<<3', 'Disable Dynamics' ),			# 8
				( '1<<4', 'Unknown 2' ),				# 16
				( '1<<5', 'Unknown 3' ),				# 32
				( '1<<6', 'Loop Animation' ),			# 64
				( '1<<7', 'Anim. Induced Physics' ),	# 128
		]) }

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Action Table ' + uHex( 0x20 + args[1] )
		self.formatting = '>IIIIBHBI'
		self.fields = ( 'Action_Name_Pointer',
						'Animation_Offset',			# Offset into the AJ files
						'Animation_Size',
						'SubAction_Events_Pointer',
						'State_Flags',				# 0x10 (1 byte)
						'AdditionalBone_DisableBlendBoneIndex ',	# 0x11 (halfword)
						'Internal_Character_ID',	# 0x13 (1 byte)
						'Padding'					# ARAM animation pointer placeholder (used when loaded into memory)
					)
		self.length = 0x18
		self.structDepth = ( 3, 0 )
		tableLength = self.dat.getStructLength( self.offset )
		self.entryCount = tableLength // self.length

		# Reinitialize this as a Table Struct to duplicate this entry struct for all enties in this table
		TableStruct.__init__( self )
		#super( ActionTable, self ).__init__( self ) # probably should use this instead

		for i in range( 3, len(self.fields), self.entryValueCount ):
			self.childClassIdentities[i] = 'SubAction'


class SubActionEvent( object ):

	""" Doesn't represent a full structure, but a logical part of one; 
		a SubAction structure is composed of these events. """

	def __init__( self, eventCode, name, length, valueNames, bitFormats, data ):

		self.id = eventCode
		self.name = name			# From the SubAction class' event descriptions
		self.length = length		# Length of this event's data in bytes
		self.fields = valueNames	# A tuple of names for this event's values
		self.formats = ( 'uint:6', )
		self.formats += bitFormats	# A tuple of formats from the SubAction class event descriptions (plus the ID format)
		self.modified = False

		# Convert the event's data from a bytearray to a stream of bits (a BitStream)
		self._data = data			# Still a bytearray here
		dataBits = bitstring.ConstBitStream( bytes=data )

		# Unpack the data stream (creates a list of values, excluding the event ID)
		self.values = dataBits.readlist( self.formats )[1:]

		# Try to catch any parsing errors or abnomalities
		if not self.fields and self.values[0] != 0:
			print( 'Unexpectedly found a non-zero value for a {} subAction event with no fields.'.format(name) )
		elif self.id == 0 and self.values[0] != 0:
			raise Exception( 'SubActions parsing error: invalid End of Script event.' )

	@property
	def data( self ):

		""" Repacks all bits from current values if this event has been modified. """

		# Repack the bit stream into a new bytearray if the values have been updated
		if self.modified:
			dataBits = bitstring.pack( self.formats, self.id, *self.values )

			# Pad to length
			padding = self.length * 8 - dataBits.length # Padding in number of bits
			assert padding > -1, 'Invalid length of packed bits; {} should be {} bytes long.'.format( self.formats, self.length )
			if padding > 0:
				dataBits.append( bitstring.Bits(length=padding) )

			# Convert to bytes
			self._data = dataBits.tobytes()
			self._data = bytearray( self._data )
			self.modified = False

		return self._data

	def updateValue( self, valueIndex, value ):
		# Validate the value (this will raise an exception upon invalid encoding)
		valueFormat = self.formats[valueIndex+1] # +1 to skip ID
		formatting = '{}={}'.format( valueFormat, value )
		bitstring.Bits( formatting )

		self.values[valueIndex] = value
		self.modified = True


class SubAction( DataBlock ):

	eventDesc = { # Defines [EventID]: ( name, length, valueNames, bitFormats )
		0x00: ( 'End of Script', 4, (), ('int:26',) ),
		0x01: ( "Synchronous Timer", 4, ('Frame',), ('uint:26',) ),
		0x02: ( "Asynchronous Timer", 4, ('Frame',), ('uint:26',) ),
		0x03: ( "Set Loop", 4, ('Loop Count',), ('uint:26',) ),
		0x04: ( "Execute Loop", 4, (), ('int:26',) ),
		0x05: ( "Subroutine", 8, ('Padding', 'Pointer'), ('uint:26', 'uint:32')), # First param is "Target"?
		0x06: ( "Return", 4, (), ('int:26',) ),
		0x07: ( "GoTo", 8, ('Padding', 'Pointer'), ('uint:26', 'uint:32')), # First param is "Target"?
		0x08: ( "Set Loop Animation Timer", 4, (), ('int:26',) ),
		0x09: ( "Unknown 0x09", 4, ('Unknown',), ('int:26',) ),
		0x0A: ( "Graphic Effect", 0x14, ('Bone ID', 'Use Common Bone ID', 'Destroy On State Change', 
										'Use Unknown Bone ID?', 'Unknown', 'Graphic ID', 'Unknown Bone ID?', 
										'Z Offset', 'Y Offset', 'X Offset', 
										'Z Range', 'Y Range', 'X Range'), 
										('uint:8', 'bool', 'bool', 
										'bool', 'uint:15', 'uint:16', 'uint:16', 
										'int:16', 'int:16', 'int:16', 
										'uint:16', 'uint:16', 'uint:16') ),

		# https://smashboards.com/threads/melee-hacks-and-you-new-hackers-start-here-in-the-op.247119/page-48#post-10769744
		# Details on Rebound (Hitbox Interaction): https://smashboards.com/threads/official-ask-anyone-frame-things-thread.313889/post-17742200
		0x0B: ( "Create Hitbox", 0x14, ('Hitbox ID', 'Padding', 'Bone Attachment', 'Padding', 'Damage', 
										'Size', 'Z Offset', 'Y Offset', 'X Offset', 
										'Knockback Angle', 'Knockback Growth', 'Weight Dependent Set Knockback', 
										'Padding', 'Hitbox Interaction', 'Base Knockback',
										'Element', 'Unknown', 'Shield Damage', 'Sound Effect', 'Hit Grounded Opponents', 'Hit Airborne Opponents'), 
										('uint:3', 'uint:5', 'uint:7', 'int:2', 'uint:9', 
										'uint:16', 'int:16', 'int:16', 'int:16', # 12 bytes so far
										'uint:9', 'uint:9', 'uint:9', 
										'int:3', 'uint:2', 'uint:9', 
										'uint:5', 'bool', 'uint:7', 'uint:8', 'bool', 'bool') ),

		0x0C: ( "Adjust Hitbox Damage", 4, ('Hitbox ID', 'Damage'), ('uint:3', 'uint:23') ),
		0x0D: ( "Adjust Hitbox Size", 4, ('Hitbox ID', 'New Size'), ('uint:3', 'uint:23') ),
		0x0E: ( "Set Hitbox Interaction", 4, ('Hitbox ID', 'Type', 'Can Interact'), ('uint:24', 'bool', 'bool'), ),
		0x0F: ( "Remove Hitbox", 4, (), ('int',) ), # Should include hitbox ID?
		0x10: ( "Clear Hitboxes", 4, (), ('int',) ), # Sound effect?
		0x11: ( "Sound Effect", 0xC, ('Unknown 1', 'Unknown 2', 'Sound Effect ID', 'Offset'), 
										('uint:32', 'uint:6', 'uint:20', 'uint:32') ),
		0x12: ( "Random Smash SFX", 4, ('Unknown',), ('int:26',) ),
		0x13: ( "Auto-cancel", 4, ('Flags', 'Padding'), ('uint:2', 'int:24') ),
		0x14: ( "Reverse Direction", 4, (), ('int:26',) ),
		0x15: ( "Unknown 0x15", 4, ('Unknown',), ('int:26',) ), # set flag
		0x16: ( "Unknown 0x16", 4, ('Unknown',), ('int:26',) ), # set flag
		0x17: ( "Allow Interrupt", 4, ('Unknown',), ('int:26',) ),
		0x18: ( "Projectile Flag", 4, ('Unknown',), ('int:26',) ),
		0x19: ( "Set Jump State", 4, ('Value',), ('uint:26',) ), # related to ground air state
		0x1A: ( "Set Body Collision State", 4, ('Padding', 'Body State'), ('int:24', 'uint:2') ),
		0x1B: ( "Body Collision Status", 4, ('Padding',), ('int:26',) ), # Has value (used)?
		0x1C: ( "Set Bone Collision State", 4, ('Bone ID', 'Collision State'), ('uint:8', 'uint:18') ),
		0x1D: ( "Enable Jab Follow-up", 4, ('Unknown',), ('int:26',) ),
		0x1E: ( "Toggle Jab Follow-up", 4, (), ('int:26',) ),
		0x1F: ( "Changle Model State", 4, ('Struct ID', 'Padding', 'Object ID'), ('uint:6', 'uint:12', 'uint:8') ),
		0x20: ( "Revert Models", 4, (), ('int:26',) ),
		0x21: ( "Remove Models", 4, (), ('int:26',) ),

		# https://smashboards.com/threads/melee-hacks-and-you-new-hackers-start-here-in-the-op.247119/page-49#post-10804377
		0x22: ( "Throw", 0xC, ('Throw Type', 'Padding', 
								'Damage', 'Angle', 'Knockback Growth', 
								'Weight Dependent Set Knockback', 'Padding', 'Base Knockback', 
								'Element', 'SFX Severity', 'SFX Kind', 'Padding'), 
								('uint:3', 'uint:14', 
								'uint:9', 'uint:9', 'uint:9', 
								'uint:9', 'uint:5', 'uint:9', 
								'uint:4', 'uint:3', 'uint:4', 'uint:12') ),

		0x23: ( "Held Item Invisibility", 4, ('Padding', 'Flag'), ('uint:25', 'bool') ),
		0x24: ( "Body Article Invisibility", 4, ('Padding', 'Flag'), ('uint:25', 'bool') ),
		0x25: ( "Character Invisibility", 4, ('Padding', 'Flag'), ('uint:25', 'bool') ),
		0x26: ( "Pseudo-Random Sound Effect", 0x1C, ('Unknown',), ('int:218',) ),
		0x27: ( "Unknown 0x27", 0x10, ('Unknown',), ('int:122',) ),
		0x28: ( "Animate Texture", 4, ('Material Flag', 'Material Index', 'Frame Flags', 'Frame'), 
										('bool', 'int:7', 'int:7', 'int:11') ),
		0x29: ( "Animate Model", 4, ('Body Part', 'State', 'Unknown'), ('uint:10', 'uint:4', 'uint:12') ),
		0x2A: ( "Unknown 0x2A", 4, ('Unknown',), ('int:26',) ),
		0x2B: ( "Rumble", 4, ('Unknown Flag', 'Unknown Value', 'Unknown Value'), ('bool', 'int:12', 'int:13',) ),
		0x2C: ( "Unknown 0x2C", 4, ('Padding', 'Flag'), ('uint:25', 'bool') ), # set flag
		0x2D: ( "Unknown 0x2D", 0xC, ('Unknown',), ('int:90',) ),

		# https://smashboards.com/threads/changing-color-effects-in-melee.313177/page-2#post-14490878
		0x2E: ( "Body Aura", 4, ('Aura ID', 'Duration'), ('uint:8', 'uint:18') ),
		0x2F: ( "Remove Color Overlay", 4, ('Unknown',), ('int:26',) ),
		0x30: ( "Unknown 0x30", 4, ('Unknown',), ('int:26',) ),
		0x31: ( "Sword Trail", 4, ('Use Beam Sword Trail', 'Padding', 'Render Status'), ('bool', 'int:17', 'uint:8') ),
		0x32: ( "Enable Ragdoll Physics", 4, ('Bone ID',), ('uint:26',) ),
		0x33: ( "Self Damage", 4, ('Padding', 'Damage'), ('uint:10', 'uint:16') ),
		0x34: ( "Continuation Control", 4, ('Unknown',), ('int:26',) ),
		0x35: ( "Footsnap Behavior", 4, ('Flags?',), ('int:26',) ), # set flag
		0x36: ( "Footstep Effect (SFX+VFX)", 0xC, ('Unknown',), ('int:90',) ),
		0x37: ( "Landing Effect (SFX+VFX)", 0xC, ('Unknown',), ('int:90',) ),

		# https://smashboards.com/threads/changing-color-effects-in-melee.313177/#post-13616960
		0x38: ( "Start Smash Charge", 8, ('Padding', 'Charge Frames', 'Charge Rate', 'Visual Effect', 'Padding'), 
											('uint:2', 'uint:8', 'uint:16', 'uint:8', 'uint:24') ),
		0x39: ( "Unknown 0x39", 4, ('Unknown',), ('int:26',) ),
		0x3A: ( "Aesthetic Wind Effect", 0x10, ('Unknown',), ('int:122',) ),
		0x3B: ( "Unknown 0x3B", 4, ('Unknown',), ('int:26',) )
	}

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'SubAction Events ' + uHex( 0x20 + self.offset )
		self.events = [] # List of SubActionEvent objects

	def parse( self ):

		""" Parses this subAction's data into a list of subAction events (self.data -> self.events). """

		if self.events:
			return

		position = 0
		byte = self.data[0]

		while True:
			# Check the op code of this event and look up its info
			eventCode = ( byte & 0xFC ) >> 2 # Filtering to just top 6 bits
			eventDesc = self.eventDesc.get( eventCode )
			if not eventDesc:
				print( 'Unrecognized event opCode: 0x{:X} (0x{:X})'.format( eventCode, byte & 0xFC ) )
				position += 1
				byte = self.data[position]
				continue
			name, length, valueNames, bitFormats = eventDesc

			# Create an event object and store it
			eventData = self.data[position:position+length]
			event = SubActionEvent( eventCode, name, length, valueNames, bitFormats, eventData )
			self.events.append( event )

			# End parsing once an End of Script event is reached or no more data
			position += length
			if eventCode == 0 or position >= len( self.data ):
				break

			# Jump to the next event
			byte = self.data[position]

		print( 'orig data for {}:'.format(self.name) )
		print( hexlify(self.data) )

	def rebuild( self ):

		""" Reassembles data for this subAction, based on current values in the events. """

		# Add a single End of Script event if there is nothing else
		if len( self.events ) == 0:
			name, length, valueNames, bitFormats = self.eventDesc.get( 0 )
			self.events.append( SubActionEvent(0, name, length, valueNames, bitFormats, bytearray(4)) )

		self.data = bytearray()
		for event in self.events:
			self.data.extend( event.data )

		self.length = len( self.data )
			
		print( 'rebuilt data for {}:'.format(self.name) )
		print( hexlify(self.data) )

	def deleteEvent( self, eventIndex ):

		if isinstance( eventIndex, SubActionEvent ):
			for i, event in enumerate( self.events ):
				if event == eventIndex:
					eventIndex = i
					break
			else: # Above loop didn't break; event object not found
				raise Exception( 'Unable to find the given {} event!'.format(eventIndex.name) )

		del self.events[eventIndex]


class CharAnimFile( CharFileBase, FileBase ):

	""" Character animation files (Pl__AJ.dat files); i.e. Ply[charAbbr]5K_Share_ACTION_Wait1_figatree 
		This file format is just a container/list of DAT files, where each DAT is an animation. 
		These sub-files are stored end-to-end (with no header to define said list), but aligned to 0x20 bytes. """

	def __init__( self, *args, **kwargs ):
		super( CharAnimFile, self ).__init__( *args, **kwargs )

		self.animations = [] # A list of DAT file objects for the contents of this file
		self.animNames = [] # Animation names (symbols) matching the above files
		
		self._intCharId = -2
		self._extCharId = -2
		self._charAbbr = ''
		self._charName = ''
		self._nickname = ''

	def validate( self ):

		""" Verifies whether this is actually a character animation file by 
			checking the first animation file symbol. """
			
		# Make sure file data has been loaded
		self.getData()

		# Get the size of this animation
		headerData = self.getData( 0, 0x14 )
		animSize, rtStart, rtEntryCount, rootNodeCount, referenceNodeCount = struct.unpack( '>5I', headerData )

		if rootNodeCount != 1:
			raise Exception( 'Invalid character animation file; root node count is not 1.' )
		elif referenceNodeCount != 0:
			raise Exception( 'Invalid character animation file; reference node count is not 0.' )

		# Get the name of this animation (the symbol). Simpler method than initializing the file
		nameOffset = 0x20 + rtStart + ( rtEntryCount * 4 ) + 8
		stringLength = 0x20 + animSize - nameOffset
		symbol = self.getString( nameOffset, stringLength )

		if not symbol.startswith( 'Ply' ) or '_ACTION_' not in symbol:
			raise Exception( 'Invalid character animation file; invalid symbol name: {}'.format(symbol) )

	def initialize( self ):

		""" Parse out the file's individual DAT files within, and collect information on them. """

		if self.animations:
			return # This file has already been initialized!
			
		# Make sure file data has been loaded
		self.getData()

		readOffset = 0

		# Create a DAT file for each animation
		while 1:
			# Get the size of this animation
			headerData = self.getData( readOffset, 0xC, hideWarnings=True )
			if len( headerData ) != 0xC:
				break # Reached the end of the file
			animSize, rtStart, rtEntryCount = struct.unpack( '>3I', headerData )

			# Create a DAT file for this animation and attach its data
			anim = DatFile( None, readOffset, animSize, self.filename, source='self' )
			anim.data = self.getData( readOffset, animSize )

			# Get the name of this animation (the symbol). Simpler method than initializing the file
			nameOffset = readOffset + 0x20 + rtStart + ( rtEntryCount * 4 ) + 8
			stringLength = readOffset + animSize - nameOffset
			anim.name = self.getString( nameOffset, stringLength )
			self.animNames.append( anim.name )

			self.animations.append( anim )

			# Calculate offset of next animation (round up to nearest 0x20 bytes)
			readOffset += roundTo32( animSize )

	def getCharAbbr( self ):

		""" Returns the two-letter abbreviation for this character (e.g. 'Ca' for Captain Falcon). 
			Also sets the character nickname (e.g. 'Captain' for Captain Falcon) often used in strings. 
			This may confuse Wireframe characters for Falcon/Zelda, since they share the same character nicknames. """

		# Ensure root nodes and the string table have been parsed
		self.initialize()

		symbol = self.animations[0].name # e.g. "PlyCaptain5K_Share_ACTION_Wait1_figatree"
		symbolBase = symbol[3:].split( '_' )[0] # Remove 'Ply' and everything after first underscore
		self._nickname = symbolBase.replace( '5K', '' )

		# Attempt a fallback method to not confuse wireframe characters
		if self._nickname == 'Captain' and 'Bo' in self.filename:
			charAbbr = 'Bo'
		elif self._nickname == 'Zelda' and 'Gl' in self.filename:
			charAbbr = 'Gl'
		else:
			charAbbr = self.charAbbrs.get( self._nickname, '' )

		return charAbbr

	def getDescription( self ):
		
		# Attempt to get the character name this file is for
		charName = globalData.charNameLookup.get( self.charAbbr, '' )
		if not charName:
			self._shortDescription = 'Unknown ({})'.format( self.charAbbr )
			self._longDescription = self._shortDescription
			return

		self._shortDescription = 'Animation data'
		if charName.endswith( 's' ):
			self._longDescription = charName + "' animation data"
		else:
			self._longDescription = charName + "'s animation data"


class CharIdleAnimFile( CharFileBase, FileBase ):

	""" Character idle animation files (Pl__DViWaitAJ.dat files); i.e. ftDemoViWaitMotionFile[charAbbr]
		This file format is basically a DAT file contained within another DAT file. Both have a header 
		and string table, but the outer archive/DAT file has no relocation table. """

	def __init__( self, *args, **kwargs ):
		super( CharIdleAnimFile, self ).__init__( *args, **kwargs )

		self.animations = []
		self.animNames = []
		
		self._intCharId = -2
		self._extCharId = -2
		self._charAbbr = ''
		self._charName = ''
		self._nickname = ''


class CharCostumeFile( CharFileBase, DatFile ):

	""" Character model & texture files (costumes); i.e. Ply[charAbbr]5KBu_Share_joint """
	
	def __init__( self, *args, **kwargs ):
		super( CharCostumeFile, self ).__init__( *args, **kwargs )

		self._intCharId = -2
		self._extCharId = -2
		self._charAbbr = ''
		self._charName = ''
		self._nickname = ''
		self._colorAbbr = ''

	@property
	def colorAbbr( self ):
		if not self._colorAbbr:
			self._colorAbbr = self.getColorAbbr()
		return self._colorAbbr

	def validate( self ):

		""" Verifies whether this is actually a character costume file by checking the string table. 
			This will also initialize the file and retrieve its file data. """

		self.initialize()
		rootNodeName = self.rootNodes[0][1]

		if not rootNodeName.endswith( '_Share_joint' ):
			raise Exception( "Invalid character costume file; no '..._Share_joint' symbol node found." )

	def getCharAbbr( self ):

		""" Analyzes the file's root nodes / string table to determine the character, rather than trusting the file name. """

		# Ensure root nodes and the string table have been parsed
		self.initialize()
		
		rootNodeName = self.rootNodes[0][1]
		nameParts = rootNodeName.split( '5K' )

		if not rootNodeName.startswith( 'Ply' ):
			print( 'Unrecognized root node name, "{}" from {}'.format(rootNodeName, self.filename) )
			return ''

		if len( nameParts ) == 1: # Must be a character like Master Hand or a Wireframe (no 5K string portion), or a Kirby copy costume
			charShorthand = rootNodeName.split( '_' )[0][3:]

			# If this is Kirby, strip off the color abbreviation or copy strings
			if charShorthand.startswith( 'Kirby' ):
				charShorthand = 'Kirby'

		else:
			charShorthand = nameParts[0][3:] # Excludes beginning 'Ply'

		self._nickname = charShorthand

		return self.charAbbrs.get( self._nickname, '' )

	def getColorAbbr( self ):

		""" Analyzes the file's root nodes / string table to determine the costume color, rather than trusting the file name. """

		# Ensure root nodes and the string table have been parsed
		self.initialize()
		
		rootNodeName = self.rootNodes[0][1]
		nameParts = rootNodeName.split( '5K' )

		if not rootNodeName.startswith( 'Ply' ):
			print( 'Unrecognized root node name, "{}" from {}'.format(rootNodeName, self.filename) )
			return ''

		if len( nameParts ) == 1: # Must be a character like Master Hand or a Wireframe (no 5K string portion), or a Kirby copy costume
			charShorthand = rootNodeName.split( '_' )[0]

			if charShorthand.startswith( 'PlyKirby' ):
				colorAbbr = charShorthand[-2:] # Gets last two characters of this section
				if colorAbbr not in ( 'Bu', 'Gr', 'Re', 'Wh', 'Ye' ):
					colorAbbr = 'Nr'
			else:
				colorAbbr = 'Nr'
		else:
			colorAbbr = nameParts[1].split( '_' )[0]

			if not colorAbbr:
				colorAbbr = 'Nr'

		return colorAbbr

	def getCostumeId( self ):

		""" Converts this file's costume color to an index or costume ID, 
			which the game uses to choose a costume file. This will default 
			to 0 (the neutral/Nr slot) if the character is not found, which 
			is fine for "extra" characters such as Master Hand or Wireframes. """

		char = self.charAbbr
		color = self.colorAbbr

		colorSlots = globalData.costumeSlots.get( char, ('Nr',) )
		return colorSlots.index( color )

	def getDescription( self ):
		
		# Attempt to get the character name this file is for
		charName = globalData.charNameLookup.get( self.charAbbr, '' )
		if not charName:
			self._shortDescription = 'Unknown ({})'.format( self.charAbbr )
			self._longDescription = self._shortDescription
			return

		if charName.endswith( 's' ):
			self._longDescription = charName + "' "
		else:
			self._longDescription = charName + "'s "

		# Check the costume color
		colorKey = self.colorAbbr
		color = globalData.charColorLookup.get( colorKey, '' )
		if not color:
			print( 'Unable to get a character color look-up from {} (from {})'.format(colorKey, self.filename) )
			self._shortDescription = 'Unknown costume color'
			self._longDescription += ' (unknown costume color)'
			return
		else:
			self._shortDescription = color + ' costume'

		# Give additional details for Kirby copy powers
		if len( self.filename ) == 14 and self.filename.startswith( 'PlKb' ) and self.filename[6:8] == 'Cp':
			copyTargetExternalId = self.extCharIds.get( self.filename[8:10], -1 )
			copyTarget = self.getCharName( copyTargetExternalId )
			self._shortDescription += ' for {} copy power'.format( copyTarget )
			self._longDescription += ' for {} copy power'.format( copyTarget )

		# Add parenthesis for 20XX costume alts
		if self.ext == '.lat' or colorKey == 'Rl': self._shortDescription += " ('L' alt)" # For 20XX
		elif self.ext == '.rat' or colorKey == 'Rr': self._shortDescription += " ('R' alt)"

		self._longDescription += self._shortDescription

		# Ensure the first word is capitalized
		self._shortDescription = self._shortDescription[0].upper() + self._shortDescription[1:]

	def buildDiscFileName( self, defaultToUsd=True ):	# todo: depricate in favor of disc.constructCharFileName( self, charId, colorId, ext='dat', defaultToUsd=True )

		""" Determines the disc file name for this file, using the root nodes / string table. """

		char = self.charAbbr
		color = self.colorAbbr

		if len( char ) == 4: # Kirby copy power costumes
			filename = 'PlKb{}Cp{}.dat'.format( color, char[2:] )
		elif char == 'Ca' and color == 'Re': # Falcon's Red Costume
			if defaultToUsd or ( self.disc and self.disc.countryCode == 1 ):
				filename = 'PlCaRe.usd'
			else:
				filename = 'PlCaRe.dat'
		else:
			filename = 'Pl{}{}.dat'.format( char, color )

		return filename

	def getSkeletonRoot( self ):

		""" Returns the root bone in the model's skeleton 
			(first bone of the first root node structure). """
		
		# Ensure root nodes and the string table have been parsed
		self.initialize()

		firstNodeOffset, firstNodeString = self.rootNodes[0]
		assert firstNodeString.endswith( 'Share_joint' ), 'Unable to get skeleton; incorrect root node string encountered: ' + firstNodeString

		# Get the skeleton struct (should be the joint/bone of the first root node)
		jointClass = globalData.fileStructureClasses['JointObjDesc']
		return self.initSpecificStruct( jointClass, firstNodeOffset )

	def getSkeleton( self ):

		""" Returns all bones (joint structures) making up this character's skeleton. """

		rootJoint = self.getSkeletonRoot()
		return self.getBranch( rootJoint.offset, classLimit=['DisplayObjDesc'], classLimitInclusive=False )

	def getDObjs( self ):

		""" An optimization to the generic DAT method (searches just the first/main root node). 
			Finds and returns all Display Objects in the file. """

		self.initialize()

		try:
			# tic = time.time()

			# Process structs from the main model joint
			rootStruct = self.getSkeletonRoot()
			descendants = rootStruct.getDescendants( classLimit=hsdStructures.DisplayObjDesc )

			# toc = time.time()
			# print( 'time to get {} structs: {}'.format(len(descendants), toc-tic) )

			# Filter the Display Objects and return them
			return [ obj for obj in descendants if isinstance(obj, hsdStructures.DisplayObjDesc) ]
		
		except Exception as errorMessage:
			printStatus( 'Unable to parse DObjs from {}; {}'.format(self.printPath(), errorMessage), error=True )
			return []