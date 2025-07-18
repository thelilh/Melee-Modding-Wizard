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

# DTW's Structural Analysis tab or the following thread/post are useful for more details on structures:
# 		https://smashboards.com/threads/melee-dat-format.292603/post-21913374

import struct
import time, math
from itertools import zip_longest as zip

from collections import OrderedDict

import globalData

from basicFunctions import uHex
from renderEngine import Vertex, VertexList

showLogs = True


GXCompType_VAL = [ # Describes vertex attribute formatting
	'B', # uint8
	'b', # sint8
	'H', # uint16
	'h', # sint16
	'f', # float
]

GXCompType_CLR = [ # Describes vertex attribute formatting for colors
	'H', 		# GX_RGB565
	'BBB', 		# GX_RGB8
	'BBBB', 	# GX_RGBX8
	'H',  		# GX_RGBA4 (i.e. RGBA4444)
	'BBB',  	# GX_RGBA6
	'BBBB' 		# GX_RGBA8
]

					# = ---------------------------------------------- = #
					#  [   HSD Internal File Structure Base Classes   ]  #
					# = ---------------------------------------------- = #

class StructBase( object ):

	""" Base class to represent an abstract structure within a HAL DAT file. 

		Each structure keeps a reference to its host dat file, 
		referring to it for information on itself and other structs. """

	# __slots__ = ( 'dat', 'offset', 'data', 'name', 'label', 'fields', 'length', 'entryCount', 'formatting',
	# 			  'parents', 'siblings', 'children', 'values', 'branchSize', 'childClassIdentities',
	# 			  '_parentsChecked', '_siblingsChecked', '_childrenChecked' )

	def __init__( self, datSource, dataSectionOffset, parentOffset=-1, structDepth=None, entryCount=-1 ):

		self.dat 			= datSource				# Host DAT File object
		self.offset 		= dataSectionOffset
		self.data			= ()					# Will become a bytearray
		self.padding		= 0
		self.name 			= 'Struct ' + uHex( 0x20 + dataSectionOffset )
		self.label 			= datSource.getStructLabel( dataSectionOffset ) # From the DAT's string table
		self.fields			= ()
		self.length			= -1
		self.entryCount 	= entryCount			# Used with array & table structures; -1 means it's not an array/table
		self.formatting		= ''
		self.parents 		= set()					# Set of integers (offsets of other structs)
		self.siblings 		= [] 					# List of integers (offsets of other structs)
		self.children 		= [] 					# List of integers (offsets of other structs)
		self.values 		= () 					# Actual decoded values (ints/floats/etc) of the struct's data
		self.branchSize 	= -1					# The size of this structure plus all of its children
		self.structDepth 	= None
		self.childClassIdentities = {}
		self.classParents	= {}

		self._parentsChecked = False
		self._siblingsChecked = False
		self._childrenChecked = False

		# Determine the structure's file depth (x, y) tuple, if possible.
		#		x = how "deep" into the file (the file header is first, at 0. Root Nodes Table is next, at 1)
		# 		y = sibling index
		self.structDepthQuickCheck( parentOffset, structDepth ) # Also sets parents

	def validated( self, provideChildHints=True, deducedStructLength=-1 ):

		""" This method attempts to test sequential data against the format of a known 
			structure, validating whether or not it is actually the expected struct. 
			Primarily, it checks that the struct sizes are not too mismatched (there may be 
			padding thrown in, making a struct appear larger than it is), and validates pointers. 

			This function will also read and save the data (unpacking it to 'values') to the 
			struct object and set the following struct attributes: data, values, padding """

		if not self.fields: return False
		skipValuesValidation = False

		if deducedStructLength == -1:
			deducedStructLength = self.dat.getStructLength( self.offset ) # This length will include any padding too

		# Make sure this proposed struct has enough data (is long enough that it could match)
		if deducedStructLength < self.length or deducedStructLength > self.length + 0x20: # Expecting that there is never more that 0x20 bytes of padding
			return False

		# Separate the actual struct data from any padding, and perform some basic validation
		structData = self.dat.getData( self.offset, deducedStructLength )
		paddingData = structData[self.length:]
		structData = structData[:self.length] # Trim off any padding
		if not any( structData ):
			# Check if there's a class hint for this struct
			existingEntity = self.dat.structs.get( self.offset, None )

			if existingEntity == self: # Presumably, this has already been validated; continue with the rest of this method just in case anything needs updating
				skipValuesValidation = True
			elif isinstance( existingEntity, str ) and existingEntity == self.__class__.__name__:
				# If there's a class hint that matches this struct class, assume this is correct (since we can't use the values to determine it).
				skipValuesValidation = True
			else:
				return False # Assume it's an unknown structure
		if any( paddingData ):
			return False # If values are found in the padding, it's probably not padding (and thus it's an unknown structure)

		# Invalidate based on the expectation of children
		if not self.childClassIdentities and self.hasChildren():
			print( 'Invalidating {} as {} since it has children'.format(self.name, self.__class__.__name__) )
			return False

		try:
			isValid = True
			fieldOffset = self.offset
			self.nullPointers = []
			fieldValues = struct.unpack( self.formatting, structData )

			# See if a sibling can be initialized with the same class. Check for a 'Next_' field marker, indicating a sibling struct pointer
			# for siblingFieldIndex, field in enumerate( self.fields ):
			# 	if field.startswith( 'Next_' ):
			# 		if self.valueIndexToOffset( siblingFieldIndex ) in self.dat.pointerOffsets: # Valid pointer
			# 			if not self.dat.initSpecificStruct( self.__class__, fieldValues[siblingFieldIndex], printWarnings=True ):
			# 				return False
			# 		break
			# else: # Loop didn't break; 'Next_' field not found
			# 	self._siblingsChecked = True

			if not skipValuesValidation:
				# Name pointers are always null (except with some custom structs :/)
				# if self.fields[0] == 'Name_Pointer' and fieldValues[0] != 0: 
				# 	#print 'disqualifying', self.name, 'as', self.__class__.__name__, 'due to populated Name_Pointer'
				# 	return False

				# Validate specific fields based on the expected type of data
				for i, fieldFormat in enumerate( self.formatting[1:] ): # Skips the endianess indicator

					if self.fields[i] == 'Padding' and fieldValues[i] != 0:
						print( 'Invalidating {} as {} due to non-empty padding at 0x{:X}: 0x{:X}'.format(self.name, self.__class__.__name__, self.valueIndexToOffset(i), fieldValues[i]) )
						isValid = False
						break

					elif fieldFormat == '?': # Bool (one byte)
						if fieldValues[i] not in ( 0, 1 ): # Should only be a 1 or 0
							isValid = False
							break

						fieldOffset += 1

					elif fieldFormat == 'b': # Signed Character (1 byte)
						fieldOffset += 1

					elif fieldFormat == 'B': # Unsigned Character (1 byte)
						fieldOffset += 1

					elif fieldFormat == 'h': # Signed Short (halfword)
						fieldOffset += 2

					elif fieldFormat == 'H': # Unsigned Short (halfword)
						fieldOffset += 2

					elif fieldFormat == 'i': # Signed Int
						fieldOffset += 4

					elif fieldFormat == 'I': # Unsigned Int
						# If the class for this struct identifies this value as a pointer, 
						# then it should be 0 or a valid starting offset of another struct.
						fileSaysItsAPointer = ( fieldOffset in self.dat.pointerOffsets ) # RT may include pointers of value 0
						classSaysItsAPointer = self.fields[i].endswith( '_Pointer' )

						if fileSaysItsAPointer:
							if not classSaysItsAPointer:
								isValid = False
								break
						elif classSaysItsAPointer:
							if fieldValues[i] == 0:
								self.nullPointers.append( i ) # Don't want to add a class hint for these!
							elif self.fields[i] != 'Name_Pointer': # Some custom structures may have improperly modified the name pointer. :/ Ignore those.
								isValid = False
								break

						fieldOffset += 4

					elif fieldFormat == 'f': # Signed Float
						fieldOffset += 4

					else:
						raise ValueError( 'Unrecognized field formatting: ' + fieldFormat )

		except Exception as err:
			print( err )
			return False

		if isValid:
			self.data = structData
			self.values = fieldValues
			self.padding = deducedStructLength - self.length

			if provideChildHints: # This should be false by all 'super().validation' calls, so we don't add hints prematurely
				self.provideChildHints()

		return isValid

	def provideChildHints( self ):
		# Add hints for what this structure's child structs are
		for valueIndex, classIdentity in self.childClassIdentities.items():
			if valueIndex in self.nullPointers: continue
			childStructOffset = self.values[valueIndex]

			if childStructOffset not in self.dat.structs:
				self.dat.structs[childStructOffset] = classIdentity

	def getLength( self ):

		""" This uses principles of the relocation table to determine structure starts, 
			thus padding may be included in the returned value. """

		if self.length == -1:
			self.length = self.dat.getStructLength( self.offset )
		return self.length

	def getValues( self, specificValue='' ):

		""" Unpacks the data for this structure, according to the struct's formatting.
			Only unpacks on the first call (returns the same data after that). Returns a tuple. """

		if not self.values:
			self.values = struct.unpack( self.formatting, self.data[:self.length] )

		if not specificValue:
			return self.values

		# Perform some validation on the input
		elif not self.fields:
			print( 'Unable to get a specific value; struct lacks known fields.' )
			return None
		elif specificValue not in self.fields:
			print( 'Unable to get a specific value; field name not found.' )
			return None

		# Get a specific value by field name
		else:
			fieldIndex = self.fields.index( specificValue )
			return self.values[fieldIndex]

	def revert( self ):

		""" Resets this structure data and its values back to the data residing in the file. """

		self.data = self.dat.getData( self.offset, self.length )
		self.values = ()
		self.getValues()

	def getAnyDataSectionParent( self ):

		""" Only looks for one arbitrary parent (non-sibling) offset, 
			so this can be faster than getParent() or getParents(). """

		if self.parents:
			# Remove references of the root or reference node tables, and get an arbitrary item from the set
			dataSectionSectionParents = self.parents.difference( [self.dat.headerInfo['rtEnd'], self.dat.headerInfo['rootNodesEnd']] ) # Won't modify .parents

			if dataSectionSectionParents:
				return next( iter(dataSectionSectionParents) )

		# Couldn't find a suitable existing parent above, so perform a new check on the data section pointers directly
		parents = set()
		for pointerOffset, pointerValue in self.dat.pointers:
			# Look for any pointers that point to this structure
			if pointerValue == self.offset:
				assert pointerOffset < self.dat.headerInfo['rtStart'], 'Unable to find any data section parent for ' + self.name

				# Pointer found; get the structure that owns this pointer
				parentOffset = self.dat.getPointerOwner( pointerOffset, offsetOnly=True )

				if self.isSibling( parentOffset ):
					parentStruct = self.dat.getStruct( parentOffset )
					grandparentStructOffsets = parentStruct.getParents()

					while True:
						# May have multiple parents; check if any of them are a sibling (want to follow that path)
						for grandparentOffset in grandparentStructOffsets:
							if parentStruct.isSibling( grandparentOffset ):
								parentStruct = self.dat.structs[grandparentOffset]
								grandparentStructOffsets = parentStruct.getParents()
								break
						else: # Above loop didn't break; no more siblings found
							break # Out of the while loop

					parents.add( next(iter( grandparentStructOffsets )) )

				else:
					parents.add( parentOffset )

				break

		# Remove references of the root or reference node tables, and get an arbitrary item from the set
		dataSectionSectionParents = parents.difference( [self.dat.headerInfo['rtEnd'], self.dat.headerInfo['rootNodesEnd']] )
		assert dataSectionSectionParents, 'The only parent(s) found for {} were root/ref nodes: {}'.format( self.name, [hex(0x20+o) for o in parents] )

		return next( iter(dataSectionSectionParents) )

	def getParent( self, targetClass, printWarnings=False ):

		""" Checks among all parents this structure is attached to and returns one of a target class. 
			Returns None if a parent of the given class couldn't be initialized. """

		# See if it's cached
		parent = self.classParents.get( targetClass )
		if parent:
			return parent

		# Not already collected; try to find it
		for parentOffset in self.getParents():
			# Test if we can initialize this structure offset with the target class
			parent = self.dat.initSpecificStruct( targetClass, parentOffset, self.offset, printWarnings=printWarnings )
			if parent: break

		# Cache so we don't have to search next time for this parent
		if parent:
			self.classParents[targetClass] = parent
		elif printWarnings:
			print( 'Unable to find a {} parent to {}'.format(targetClass.__name__, self.name) )

		return parent

	def getParents( self, includeNodeTables=False ):

		""" Finds the offsets of all [non-sibling] structures that point to this structure.
			May include root and reference node table offsets. Returns a set. """

		if not self._parentsChecked:
			self.parents = set()

			for pointerOffset, pointerValue in self.dat.pointers:

				# Look for any pointers that point to this structure
				if pointerValue == self.offset:
					# Pointer found; get the structure that owns this pointer
					parentOffset = self.dat.getPointerOwner( pointerOffset, offsetOnly=True )

					if self.isSibling( parentOffset ):
						parentStruct = self.dat.getStruct( parentOffset )
						grandparentStructOffsets = parentStruct.getParents()

						# Make sure this isn't a sibling; seek through references until the actual parent is found
						foundAnotherSibling = True
						while foundAnotherSibling:
							# May have multiple parents; check if any of them are a sibling
							for grandparentOffset in grandparentStructOffsets:
								if parentStruct.isSibling( grandparentOffset ):
									parentStruct = self.dat.structs[grandparentOffset]
									grandparentStructOffsets = parentStruct.getParents()
									break
							else: # Above loop didn't break; no more siblings found
								foundAnotherSibling = False

						self.parents.update( grandparentStructOffsets )

					else:
						self.parents.add( parentOffset )

			self._parentsChecked = True

		if includeNodeTables:
			return self.parents

		else: # Remove references to the Root/Ref Node tables (returns new set; will not update original parents set)
			return self.parents.difference( [self.dat.headerInfo['rtEnd'], self.dat.headerInfo['rootNodesEnd']] )

	def isSibling( self, structOffset ):

		""" Checks if the given structure is a parent/sibling to this structure. This is only designed 
			to work with an immediate parent/sibling relationship; if you need to check a 
			relationship that is separated by other siblings, call getSiblings() first. """

		# Sibling determination not possible without knowing the structure.
		if self.__class__ == StructBase:
			return False

		# Check if siblings have already been determined
		elif self._siblingsChecked:
			return ( structOffset in self.siblings )

		# Preliminary check; no siblings for these potential structs: file header, node tables, string table
		elif structOffset in ( -32, self.dat.headerInfo['rtStart'], self.dat.headerInfo['rtEnd'], 
								self.dat.headerInfo['rootNodesEnd'], self.dat.headerInfo['stringTableStart'] ):
			return False

		# Attempt to initialize the struct relative (could be a parent or sibling)
		potentialParentStruct = self.dat.initSpecificStruct( self.__class__, structOffset, printWarnings=False )
		if not potentialParentStruct or not potentialParentStruct.fields:
			return False # Sibling determination not possible without knowing the structure.

		# Look for a 'Next_' field, and check if it's a pointer to this struct
		for i, field in enumerate( potentialParentStruct.fields ):
			if field.startswith( 'Next_' ):
				siblingPointerValue = potentialParentStruct.getValues()[i]
				return ( siblingPointerValue == self.offset )
		else: # Loop above didn't break or return; no 'Next_' field
			return False

	def getFirstSibling( self ):

		""" Returns the first sibling structure in this structure's group (not the 'Next' struct to this one). 
			Returns None if there are no siblings. """

		if not self._siblingsChecked:
			self.getSiblings()

		if not self.siblings:
			return None
		
		return self.dat.initSpecificStruct( self.__class__, self.siblings[0] )

	def getSiblings( self, nextOnly=False, asStructs=False ):

		""" Returns a list of all sibling structure offsets in this struct's group (from each "Next_" field).
			If the struct has no Next fields, this returns an empty list. If it can have siblings but doesn't, 
			a list with just one entry (this struct's offset) will be returned. If nextOnly is True, only the first 
			sibling (pointed to by the current structure) is returned, and self.siblings will not be populated. 
			This also initializes all sibling structs uncovered this way. """

		if self._siblingsChecked:
			if self.siblings and asStructs:
				# Get and return a list of struct objects instead of just offsets
				structs = []
				for offset in self.siblings:
					structs.append( self.dat.structs[offset] ) # These are expected to have been initialized already
				return structs
			else:
				return self.siblings

		self.siblings = []
		sibs = []

		# Sibling determination not possible without knowing the structure.
		if not self.fields:
			self._siblingsChecked = True
			return self.siblings

		# Check for the 'Next_' field marker, indicating a sibling struct pointer
		for siblingFieldIndex, field in enumerate( self.fields ):
			if field.startswith( 'Next_' ): break
		else: # Loop didn't break; 'Next_' field not found
			self._siblingsChecked = True
			return self.siblings

		allSiblingStructs = [] # List of actual structure objects, used to share the final siblings list to all structs

		if not nextOnly:
			# Recursively search for prior sibling structs until none are found
			currentStruct = self
			while currentStruct:
				for pointerOffset, pointerValue in self.dat.pointers:
					# Look for any pointers that point to this structure
					if pointerValue == currentStruct.offset:
						# Pointer found; get the structure that owns this pointer
						parentOffset = self.dat.getPointerOwner( pointerOffset, offsetOnly=True )
						if currentStruct.isSibling( parentOffset ):
							currentStruct = self.dat.initSpecificStruct( self.__class__, parentOffset, printWarnings=False )
							if currentStruct:
								sibs.insert( 0, parentOffset )
								allSiblingStructs.insert( 0, currentStruct )
							break
				else: # The loop above didn't break; no more prior structs found
					currentStruct = None

			sibs.append( self.offset )
			allSiblingStructs.append( self )

		# Look for next sibling that this struct points to
		nextStruct = self
		while nextStruct:
			# Calculate the absolute file offset for the pointer to the sibling (+1 to index due to endianness marker)
			siblingPointerOffset = nextStruct.offset + struct.calcsize( nextStruct.formatting[1:siblingFieldIndex+1] )

			if siblingPointerOffset in self.dat.pointerOffsets: # Found a valid sibling pointer
				siblingOffset = nextStruct.getValues()[siblingFieldIndex]
				
				sibs.append( siblingOffset )

				if nextOnly:
					# No need to continue and update other structures
					if asStructs:
						return self.dat.initSpecificStruct( self.__class__, siblingOffset )
					else:
						return siblingOffset
					
				# Check for the next sibling's sibling (init a structure that's the same kind as the current struct)
				nextStruct = self.dat.initSpecificStruct( self.__class__, siblingOffset, printWarnings=False )

				if nextStruct:
					allSiblingStructs.append( nextStruct )
				else:
					nextStruct = None
					print( 'Unable to init sibling of {}; failed at sibling offset 0x{:X}'.format(self.name, 0x20+siblingOffset) )

					# Structure series invalidated. Re-initialize all structures encountered for this sibling set
					for structure in allSiblingStructs:
						self.dat.structs[structure.offset] = self.dat.initGenericStruct( structure.offset )
					return []
			else:
				nextStruct = None

		# Check for the rest of the siblings if not returning just the first
		if not nextOnly and allSiblingStructs:
			if len( allSiblingStructs ) == 1: # Only dealing with this (self) struct
				if self.structDepth:
					self.structDepth = ( self.structDepth[0], 0 )
				self.siblings = sibs
				self._siblingsChecked = True

			else: # Multiple structs need updating with the siblings list gathered above
				if self.structDepth:
					fileDepth = self.structDepth[0] # Avoiding multiple look-ups from the loop below
				else:
					fileDepth = None

				# Now that the full set is known, share it to all of the sibling structs (so they don't need to make the same determination)
				for siblingId, structure in enumerate( allSiblingStructs ):
					structure.siblings = sibs
					structure._siblingsChecked = True

					if fileDepth:
						structure.structDepth = ( fileDepth, siblingId )
					else:
						structure.structDepth = ( -1, siblingId )

		if asStructs:
			return allSiblingStructs
		else:
			return self.siblings

	def hasChildren( self ):

		""" Checks only whether the structure has ANY children at all. A bit more 
			efficient than calling getChildren and checking how many were returned. """

		# Might already know the answer
		if self._childrenChecked:
			return bool( self.children )

		# Need to determine this based on the pointers in the data section
		structEndingOffset = self.offset + self.length
		for pointerOffset in self.dat.pointerOffsets:
			if pointerOffset >= self.offset and pointerOffset < structEndingOffset: # Pointer found in data block
				return True

		# No children. We can set the children list and children-checked flag
		self._childrenChecked = True
		self.children = []

		return False

	def initChild( self, structClass, valueIndex=-1, valueName='' ):

		""" Initializes a child structure of the given class and returns it. 
			The given class may be the actual class object, or a string of it. 
			The value to use as the child pointer may be given by valueIndex, 
			OR by the valueName (the value's field name). """
		
		assert valueIndex != -1 or valueName != '', 'Invalid call to Struct.initChild(); no valueIndex or valueName provided.'

		if isinstance( structClass, str ):
			structClass = globalData.fileStructureClasses.get( structClass )

		# Ensure we have a value index
		if valueIndex == -1:
			if valueName not in self.fields:
				print( 'Unable to initialize child struct; field name "{}" not found.'.format(valueName) )
				return None
			
			valueIndex = self.fields.index( valueName )

		# Get the pointer offset and ensure there's a valid pointer there
		pointerOffset = self.valueIndexToOffset( valueIndex )
		if pointerOffset not in self.dat.pointerOffsets:
			return None
		
		pointer = self.getValues()[valueIndex]

		return self.dat.initSpecificStruct( structClass, pointer, self.offset, printWarnings=False )

	def getChildren( self, includeSiblings=False ):

		""" Searches for pointers to other structures within this structure. Returns a list of struct offsets.
			If siblings are requested as well, do not use the saved list from previous look-ups. """

		if self._childrenChecked and not includeSiblings:
			return self.children

		self.children = []

		# Look for pointers to other structures within this structure
		if self.fields and includeSiblings:
			# Iterate over all pointers in the data section, looking for those that are within the offset range of this structure
			for pointerOffset, pointerValue in self.dat.pointers:
				# Ensure we're only looking in range of this struct
				if pointerOffset < self.offset: continue
				elif pointerOffset >= self.offset + self.length: break

				self.children.append( pointerValue )
			
			self._childrenChecked = False

		else:
			# Check for sibling offsets that should be ignored
			siblingPointerOffsets = []
			for i, fieldName in enumerate( self.fields ):
				if fieldName.startswith( 'Next_' ):
					relativeOffset = struct.calcsize( self.formatting[1:i+1] ) # +1 due to endianness marker
					siblingPointerOffsets.append( self.offset + relativeOffset )
					break # Not expecting multiple of these atm

			# Iterate over all pointers in the data section, looking for those that are within the offset range of this structure
			for pointerOffset, pointerValue in self.dat.pointers:
				# Ensure we're only looking in range of this struct
				if pointerOffset < self.offset: continue
				elif pointerOffset >= self.offset + self.length: break

				if pointerOffset in siblingPointerOffsets: continue

				self.children.append( pointerValue )

			# If siblings were not included, remember this list for future queries
			if includeSiblings:
				self._childrenChecked = False
			else:
				self._childrenChecked = True

		return self.children

	def getDescendants( self, override=False, classLimit=None, structs=None, classLimitInclusive=True ):

		""" Recursively initializes structures for an entire branch within the data section and returns them. """

		if not structs:
			structs = []

		# Initialize children
		for childStructOffset in self.getChildren( includeSiblings=True ):
			if childStructOffset == self.offset: continue # Prevents infinite recursion, in cases where a struct points to itself

			# Check if the target child struct has already been initialized
			childStruct = self.dat.structs.get( childStructOffset, None )

			# Check if we got a struct, None, or a class hint
			if childStruct and not childStruct.__class__ == str:
				# This struct/branch has already been initialized. So just update the child's parent structs set with this item.
				childStruct.parents.add( self.offset )

				# Ignore structs already collected (it may have multiple parents)
				if childStruct in structs:
					continue

			else: # Create the new struct
				childStruct = self.dat.getStruct( childStructOffset, self.offset )

			# Prevent initialization of lower structures if using a class limit
			if childStruct.__class__ in classLimit:
				if classLimitInclusive:
					siblings = childStruct.getSiblings( asStructs=True )
					if siblings:
						# This child will be included in its list of siblings
						structs.extend( siblings )
					else:
						structs.append( childStruct )
				continue

			# Collect this struct and its descendants
			structs.append( childStruct )
			childStruct.getDescendants( classLimit=classLimit, structs=structs, classLimitInclusive=classLimitInclusive )

		return structs

	def getBranchSize( self ):

		""" Checks this structure and recursively all children to determine the entire branch of structs. """

		if self.branchSize != -1:
			return self.branchSize

		# tic = time.time()

		structsCounted = [ self.offset ]
		totalSize = self.length + self.padding

		def checkChildren( structure, totalSize ):
			for childStructOffset in structure.getChildren( includeSiblings=True ):
				if childStructOffset in structsCounted: # Prevents redundancy as well as infinite recursion, in cases where a struct points to itself
					continue # Already added the size for this one

				# Get the target struct if it has already been initialized
				childStruct = self.dat.getStruct( childStructOffset )

				totalSize += childStruct.length + childStruct.padding
				structsCounted.append( childStructOffset )
				
				totalSize = checkChildren( childStruct, totalSize )

			return totalSize

		self.branchSize = checkChildren( self, totalSize )

		# toc = time.time()
		# print 'getBranchSize time:', toc-tic

		return self.branchSize

	def structDepthQuickCheck( self, parentOffset, structDepth ):

		""" This is just a quick check for the struct depth, getting it if it was
			provided by default or by checking a parent structure, if one was provided. """

		if structDepth:
			self.structDepth = structDepth

			if parentOffset != -1:
				self.parents = set( [parentOffset] )

		# Struct depth not provided, but if a parent was, try to determine it from that
		elif parentOffset != -1:
			self.parents = set( [parentOffset] )	# Set of integers (offsets of other structs)

			self.structDepth = None

		# No struct depth or parent
		else:
			self.structDepth = None

	def getStructDepth( self ):

		""" More intensive check for structure depth than the above method. 
			Will recursively check parent structures (and parents of parents)
			until a depth is found or until reaching the root/ref nodes. """

		if self.structDepth and self.structDepth[0] != -1: # -1 is a file depth placeholder, in case siblings/siblingID have been checked
			return self.structDepth

		parents = self.getParents( includeNodeTables=True )

		# Remove self-references, if present
		parents.difference_update( (self.offset,) )

		# Check if this is a root structure (first-level struct out of the root or reference node tables)
		if len( parents ) == 1 and ( self.dat.headerInfo['rtEnd'] in parents or self.dat.headerInfo['rootNodesEnd'] in parents ):
			self.structDepth = ( 2, 0 )
			return self.structDepth

		# Remove root/ref node labels
		parents.difference_update( (self.dat.headerInfo['rtEnd'], self.dat.headerInfo['rootNodesEnd']) )

		# Iterate over mid-file level parents. Do this recursively until a parent has been found with a struct depth
		for parentOffset in parents:
			parentStruct = self.dat.getStruct( parentOffset )

			if parentStruct.getStructDepth():
				if self.structDepth: # Sibling ID must already be set
					siblingId = self.structDepth[1]

					# The only reason we're still in this method is to get the file depth
					self.structDepth = ( parentStruct.structDepth[0] + 1, siblingId )
				else:
					self.structDepth = ( parentStruct.structDepth[0] + 1, 0 )

					# Update the sibling ID portion of the struct depth
					self.getSiblings()

				break

		if not self.structDepth:
			print( 'Unable to get a struct depth for ' + self.name )

		return self.structDepth

	def setData( self, offset, data ):

		""" Updates data in this structure with the given data. This also 
			clears the .values property so they will be re-fetched, if needed. """

		self.data[offset:offset+len(data)]
		self.values = ()

	def setValue( self, index, value ):

		""" Updates the value of a specific field of data, using the field name or an index. """

		if not self.values:
			self.getValues()

		if type( index ) == str: # The index is a field name
			if index not in self.fields:
				raise Exception( 'Invalid field name, "{}", for {}'.format(index, self.name) )
			index = self.fields.index( index )

		valuesList = list( self.values )
		valuesList[index] = value
		self.values = tuple( valuesList )

	def setFlag( self, valueIndex, bitNumber ):

		""" Sets a flag/bit in a sequence of structure flags.
				- valueIndex is the index of the flags field/value
				- bitNumber is the bit to be set """

		# Get the full flags value
		structValues = self.getValues()
		flagsValue = structValues[valueIndex]

		# Check the current value; if the flag is already set, we're done
		if flagsValue & (1 << bitNumber): return

		# Set the flag
		flagsValue = flagsValue | (1 << bitNumber) # OR the current bits with the new bit to be set

		# Put the flags value back in with the rest of the struct values
		valuesList = list( structValues )
		valuesList[valueIndex] = flagsValue
		self.values = tuple( valuesList )

	def clearFlag( self, valueIndex, bitNumber ):

		""" Clears a flag/bit in a sequence of structure flags.
				- valueIndex is the index of the flags field/value
				- bitNumber is the bit to be cleared """

		# Get the full flags value
		structValues = self.getValues()
		flagsValue = structValues[valueIndex]

		# Check the current value; if the flag is already cleared, we're done
		if not flagsValue & (1 << bitNumber): return

		# Set the flag
		flagsValue = flagsValue & ~(1 << bitNumber) # '~' operation inverts bits

		# Put the flags value back in with the rest of the struct values
		valuesList = list( structValues )
		valuesList[valueIndex] = flagsValue
		self.values = tuple( valuesList )

	def valueIndexToOffset( self, valueIndex ):

		""" Converts an index into the field/value arrays into a file data section offset for that item. 
			For example, for the third value (index 2) in a structure with the formatting "HHII", the offset
			returned should be the structure's offset + 4. """

		return self.offset + struct.calcsize( self.formatting[1:valueIndex+1] ) # +1 due to endianness marker

	# def updateToFile( self, description='' ):

	# 	""" Packs this structure's values to binary data, and replaces that data in the file. 
	# 		Also records to the file's unsavedChanges property to remember the change. """

	# 	self.data = bytearray( struct.pack() )
	# 	self.dat.setData( self.offset, self.data )

	# 	if not description:
	# 		description = ''

	# 	self.dat.recordChange( description )


class TableStruct( StructBase ):

	""" Used for table and array structures to manage "entries" within them 
		(essentially structs within structs). Classes inheriting this should first 
		call StructBase's init, then set its own name/formmatting/entryCount 
		properties for a single entry, and then call this classes' init method. """

	def __init__( self ):
		assert self.entryCount != -1, 'Error initializing a TableStruct; entryCount was not set.'

		# Remember elements of a single entry
		self.entryFormatting = self.formatting
		self.entryValueCount = len( self.fields )
		self.entryLength = self.length

		# Update properties to cover the entire struct
		self.formatting = '>' + ( self.formatting[1:] * self.entryCount )
		self.fields = self.fields * self.entryCount
		self.length = self.length * self.entryCount
		
		self._siblingsChecked = True

	def getEntryValues( self, entryIndex ):

		""" Gets values only for one specific table/array entry. If you'd like to 
			iterate over all entries/values, .iterateEntries() will be more efficient. """

		assert entryIndex < self.entryCount, 'Invalid entryIndex; {} >= self.entryCount ({})'.format( entryIndex, self.entryCount )

		valuesIndex = self.entryValueCount * entryIndex
		return self.getValues()[valuesIndex:valuesIndex+self.entryValueCount]

	def setEntryValue( self, entryIndex, valueIndex, value ):

		""" Sets one value for one specific table/array entry. 
			Both index arguments are 0-indexed; valueIndex is relative to the start of the entry. """

		# Get the absolute value index (from the start of this structure) and send that to the standard .setValue method
		absIndex = ( self.entryValueCount * entryIndex ) + valueIndex
		self.setValue( absIndex, value )

	def iterateEntries( self ):

		""" Generator method to loop over entries in this table. Each iteration 
			yields the entry index (iteration number) and values for that entry. """
		
		values = self.getValues()

		for i in range( self.entryCount ):
			valuesIndex = i * self.entryValueCount
			yield i, values[valuesIndex:valuesIndex+self.entryValueCount]

	def entryIndexToOffset( self, index ):

		return self.offset + ( struct.calcsize(self.entryFormatting) * index )

	def initChild( self, structClass, entryIndex=-1, valueIndex=-1, valueName='' ):

		""" Initializes a child structure of the given class and returns it. 
			The given class may be the actual class object, or a string of it. 
			The value to use as the child pointer may be given by valueIndex, 
			OR by the valueName (the value's field name). """
		
		assert valueIndex != -1 or valueName != '', 'Invalid call to TableStruct.initChild(); no valueIndex or valueName provided.'

		# Ensure we have a value index
		if valueIndex == -1:
			if valueName not in self.fields:
				print( 'Unable to initialize child struct; field name "{}" not found.'.format(valueName) )
				return None
			
			valueIndex = self.fields.index( valueName )
		
		# Calculate a new index if targeting a table entry beyond the first
		if entryIndex > 0:
			valueIndex += entryIndex * self.entryValueCount

		# Call the parent method with the updated value index
		return super( TableStruct, self ).initChild( structClass, valueIndex )


class DataBlock( StructBase ):

	""" A specialized class for raw blocks of data, to mimic and behave as other structures. """
	
	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Data Block ' + uHex( 0x20 + args[1] )
		self._siblingsChecked = True
		self._childrenChecked = True

	def validated( self, *args, **kwargs ): return True
	def getSiblings( self, *args, **kwargs ): return []
	def isSibling( self, *args, **kwargs ): return False
	def getChildren( self, *args, **kwargs ): return []
	def getDescendants( self, *args, **kwargs ): return []
	def getAttributes( self ): # Gets the properties of this block from a parent image/palette/other data header
		aParentOffset = self.getAnyDataSectionParent()
		return self.dat.getStruct( aParentOffset ).getValues()


class ImageDataBlock( DataBlock ):

	def __init__( self, *args, **kwargs ):
		DataBlock.__init__( self, *args, **kwargs )

		self.name = 'Image ' + self.name

	@staticmethod
	def getDataLength( width, height, imageType ):

		""" This method differs from that of datObj.getStructLength in that it guarantees no padding is included, since 
			image data always comes in 0x20 byte chunks. Arguments should each be ints. The result is an int, in bytes. """

		byteMultiplier = { # Defines the bytes required per pixel for each image type.
			0: .5, 1: 1, 2: 1, 3: 2, 4: 2, 5: 2, 6: 4, 8: .5, 9: 1, 10: 2, 14: .5 }
		blockDimensions = { # Defines the block width and height for each image type.
			0: (8,8), 1: (8,4), 2: (8,4), 3: (4,4), 4: (4,4), 5: (4,4), 6: (4,4), 8: (8,8), 9: (8,4), 10: (4,4), 14: (8,8) }

		# Calculate based on all encoded pixels (including those in unused block areas), not just the visible ones of the given dimensions.
		blockWidth, blockHeight = blockDimensions[imageType]
		trueWidth = math.ceil( float(width) / blockWidth ) * blockWidth
		trueHeight = math.ceil( float(height) / blockHeight ) * blockHeight

		return int( trueWidth * trueHeight * byteMultiplier[imageType] )

	@staticmethod
	def getMipmapLength( baseLevelSize, maxLOD ):

		""" Calculates the total size of an image and all of its mipmap levels. """

		totalSize = baseLevelSize

		for mipmapDepth in range( 1, int(maxLOD) ):
			textureSize = baseLevelSize >> ( mipmapDepth * 2 )
			
			if textureSize < 0x20:
				totalSize += 0x20 # A texture can't be smaller than this
			else:
				totalSize += textureSize

		return totalSize

	def getAttributes( self ):

		""" Overidden to be more specific with struct initialization (avoiding structure factory for efficiency). 
			The returned values should be: (imageDataOffset, width, height, imageType, mipMapFlag, minLOD, maxLOD) """

		aHeaderOffset = self.getAnyDataSectionParent()
		return self.dat.initSpecificStruct( ImageObjDesc, aHeaderOffset ).getValues()


class PaletteDataBlock( DataBlock ):

	def __init__( self, *args, **kwargs ):
		DataBlock.__init__( self, *args, **kwargs )

		self.name = 'Palette ' + self.name

	def getAttributes( self ):

		""" Overidden to be more specific with struct initialization (avoiding structure factory for efficiency). """

		aHeaderOffset = self.getAnyDataSectionParent()
		return self.dat.initSpecificStruct( PaletteObjDesc, aHeaderOffset ).getValues()


class FrameDataBlock( DataBlock ):

	interpolationTypes = { 0: 'None', 1: 'Constant', 2: 'Linear', 3: 'Hermite Value', 4: 'Hermite Value and Curve', 5: 'Hermite Curve', 6: 'Key Data' }

	def __init__( self, *args, **kwargs ):
		DataBlock.__init__( self, *args, **kwargs )

		self.name = 'Frame ' + self.name

	def identifyTrack( self ):

		""" Determine what kind of object this track is for, e.g. for a joint, material, etc. 
			Returns a tuple of two strings: ( trackCategory, specificTrackName ) """

		# Get a parent FObjDesc
		parentFrameObjOffset = self.getAnyDataSectionParent()
		parentFrameObj = self.dat.initSpecificStruct( FrameObjDesc, parentFrameObjOffset )

		# Get the next parent (grandparent struct), which should be an animation object (AObjDesc). Sibling FObjDesc ignored.
		aObjDescOffset = parentFrameObj.getAnyDataSectionParent()
		aObjDesc = self.dat.initSpecificStruct( AnimationObjectDesc, aObjDescOffset )

		# Get the next parent, which should be a [Joint/Texture/Material/etc] Animation Struct
		animationStructOffset = aObjDesc.getAnyDataSectionParent()
		animationStruct = self.dat.getStruct( animationStructOffset )

		animationTracks = getattr( animationStruct, 'animationTracks', None )
		if not animationTracks: 
			return ( 'Unknown', 'Unknown' )

		trackType = animationStruct.name.split()[0] # Returns 'Texture', 'Material', etc.
		trackId = parentFrameObj.getValues()[3]
		trackName = animationTracks.get( trackId, 'Unknown' )
		
		return ( trackType, trackName )

	def decodeUleb128( self, readPosition ):

		""" Parser for the Unsigned Little-Endian Base 128 data format. These are capped at 3 bytes in this case.
			Documentation: https://en.wikipedia.org/wiki/LEB128 
			Examples: https://smashboards.com/threads/melee-dat-format.292603/post-23487048 """

		value = 0
		shift = 0

		while shift <= 14: # Failsafe; make sure we don't go beyond 3 bytes
			# Add the first 7 bits of the current byte to the value
			byteValue = self.data[readPosition]
			value |= ( byteValue & 0b1111111 ) << shift
			readPosition += 1

			# Check bit 8 to see if we should continue to the next byte
			if byteValue & 0b10000000:
				shift += 7
			else: # bit 8 is 0; done reading this value
				break

		if shift > 14: # Error
			print( 'Warning; uleb128 value found to be invalid (more than 3 bytes)' )
			value = -1

		return readPosition, value

	def parse( self ):
		debugging = False

		# Get an arbitrary parent offset; shouldn't matter which
		dataHeaders = self.getParents()
		aParentOffset = next( iter(dataHeaders) )
		parentStruct = self.dat.initSpecificStruct( FrameObjDesc, aParentOffset, printWarnings=False ) # Just gets it if it's already initialized

		# Make sure there's a parent struct, and it's the correct class
		if not parentStruct or parentStruct.__class__ != FrameObjDesc: 
			print( 'Unable to parse {}; unable to initialize parent as a FrameObjDesc.'.format(self.name) )
			return -1, -1, []

		_, stringLength, _, _, dataTypeAndScale, slopeDataTypeAndScale, _, _ = parentStruct.getValues()

		# Display the data type and scale
		dataType = dataTypeAndScale >> 5 		# Use the last (left-most) 3 bits
		dataScale = 1 << ( dataTypeAndScale & 0b11111 ) 	# Use the first 5 bits
		dataTypeFormatting, dataTypeByteLength = parentStruct.dataTypes[dataType][1:]
		if debugging:
			print( 'dataTypeAndScale: ' + format( dataTypeAndScale, 'b' ).zfill( 8 ) )
			print( 'dataType / scale: {} / {}'.format(dataType, dataScale) )
			print( 'dataType len: ' + str(dataTypeByteLength) )

		# Display the slope dataType and slope scale
		slopeDataType = slopeDataTypeAndScale >> 5 			# Use the last (left-most) 3 bits
		slopeDataScale = 1 << ( slopeDataTypeAndScale & 0b11111 ) 	# Use the first 5 bits
		slopeDataTypeFormatting, slopeDataTypeByteLength = parentStruct.dataTypes[slopeDataType][1:]
		if debugging:
			print( 'slopeDataTypeAndScale: ' + format( slopeDataTypeAndScale, 'b' ).zfill( 8 ) )
			print( 'slope dataType / scale: {} / {}'.format(slopeDataType, slopeDataScale) )
			print( 'slope dataType len: ' + str(slopeDataTypeByteLength) )

		# The first value in the string is a uleb128, which defines two variables: interpolationID, and an array size
		readPosition, opCodeValue = self.decodeUleb128( 0 ) # Starts with read position 0

		#  -- maybe not a uleb? always two bytes??
		# readPosition = 2
		# opCodeValue = struct.unpack( '>H', self.data[:2] )[0]
		# -- 

		interpolationID = opCodeValue & 0b1111 # First 4 bits
		arrayCount = ( opCodeValue >> 4 ) + 1 # Everything else. Seems to be 0-indexed
		if debugging:
			print( 'interpolation: {} ({})    arrayCount: {}'.format(interpolationID, self.interpolationTypes[interpolationID], arrayCount) )
			print( '\n' )

		parsedValues = []

		while readPosition < stringLength:
			try:
				if debugging:
					print( 'starting loop at read position ' + str(readPosition) )

				# Read Value
				if interpolationID == 0 or interpolationID == 5: # For 'None' and 'Hermite Curve'
					value = 0
				else:
					if debugging:
						print( '\treading', dataTypeByteLength, 'bytes for value' )
					dataBytes = self.data[readPosition:readPosition+dataTypeByteLength]
					value = struct.unpack( dataTypeFormatting, dataBytes )[0] / float( dataScale )
					readPosition += dataTypeByteLength

				# Read Tangent
				if interpolationID == 4 or interpolationID == 5: # For 'Hermite Value and Curve' and 'Hurmite Curve'
					if debugging:
						print( '\treading', dataTypeByteLength, 'bytes for tangent value' )
					dataBytes = self.data[readPosition:readPosition+slopeDataTypeByteLength]
					tangentValue = struct.unpack( slopeDataTypeFormatting, dataBytes )[0] / float( slopeDataScale )
					readPosition += slopeDataTypeByteLength
				else:
					tangentValue = 0

				# Read the next uleb
				if debugging:
					print( 'reading uleb at read position', readPosition )
				readPosition, ulebValue = self.decodeUleb128( readPosition )

				parsedValues.append( (value, tangentValue, ulebValue) )

			except:
				parsedValues.append( (-1, -1, -1) )
				print( 'Error encountered during FObjDesc parsing,', self.name )
				break

		return interpolationID, arrayCount, parsedValues


class DisplayListBlock( DataBlock ):

	enums = { 'Primitive_Type':
		OrderedDict([
			( 0xB8, 'GL_POINTS' ),
			( 0xA8, 'GL_LINES' ),
			( 0xB0, 'GL_LINE_STRIP' ),
			( 0x90, 'GL_TRIANGLES' ),
			( 0x98, 'GL_TRIANGLE_STRIP' ),
			( 0xA0, 'GL_TRIANGLE_FAN' ),
			( 0x80, 'GL_QUADS' )
		])
	}

	def __init__( self, *args, **kwargs ):
		DataBlock.__init__( self, *args, **kwargs )

		self.name = 'Display List ' + self.name

	def parse( self, length, attributesInfo ):

		""" Parses all entries in this display list, combines it with the vertex attributes data 
			(provided in attributesInfo), and initializes a list of primitives with the 
			decoded vertex data. The attributesInfo argument is expected to be a list of tuples 
			of the form ( name, attrType, compType, vertexDescriptor, indexStride, vertexStream ). """

		debugging = False

		# Determine the data length and formatting for one vertex of one entry in the display list
		baseLength = 0
		baseFormat = ''
		for name, attrType, compType, vertexDescriptor, _, vertexStream in attributesInfo:
			if attrType == 0: # GX_NONE
				continue

			elif attrType == 1: # DIRECT
				if name == 11 or name == 12: # Color values
					if vertexDescriptor == 'H': # 16-bit
						baseLength += 2
					elif vertexDescriptor == 'BBB': # 24-bit
						baseLength += 3
					elif vertexDescriptor == 'BBBB': # 32-bit
						baseLength += 4
					else: # Failsafe
						enumName = VertexAttributesArray.enums['Attribute_Name'][name]
						print( 'Warning! Invalid vertexDescriptor constructed for {}: {}'.format(enumName, vertexDescriptor) )
						return []
					baseFormat += vertexDescriptor
				else: # Everything else (primarily matrix indices)
					baseLength += 1
					baseFormat += 'B'

			elif attrType == 2: # GX_INDEX8
				baseLength += 1
				baseFormat += 'B'
				if not vertexStream:
					enumName = VertexAttributesArray.enums['Attribute_Name'][name]
					print( 'Unable to get indexed vertex attribute; missing {} vertex stream for {}'.format(enumName, self.name) )

			elif attrType == 3: # GX_INDEX16
				baseLength += 2
				baseFormat += 'H'
				if not vertexStream:
					enumName = VertexAttributesArray.enums['Attribute_Name'][name]
					print( 'Unable to get indexed vertex attribute; missing {} vertex stream for {}'.format(enumName, self.name) )

			else: # Failsafe
				print( 'Invalid attribute type "{}"!'.format(attrType) )
				return []

		dataBlockLength = ( length << 5 ) - 3 # Data chunk count * 0x20 (-3 for next header)
		vertexLists = []
		offset = 0

		# Iterate over all entries in this display list
		try:
			while offset < dataBlockLength:
				# Parse the header for this entry
				headerData = self.data[offset:offset+3]
				offset += 3
				if not any( headerData ): # NOP FIFO command
					continue
				primitiveFlags, vertexCount = struct.unpack( '>BH', headerData )
				primitiveType = primitiveFlags & 0xF8
				vertexStreamIndex = primitiveFlags & 7
				if vertexStreamIndex != 0:
					print( 'Found a non-0 vertex stream index: ' + str(vertexStreamIndex) )

				# End the list if encountering an unrecognized type
				if primitiveType not in self.enums['Primitive_Type'].keys():
					if primitiveType != 0 and debugging:
						print( 'Found an unrecognized primitive type: 0x{:X}'.format(primitiveType) )
					continue

				# Collect data for this primitive group and unpack it
				dataLength = baseLength * vertexCount
				dataFormat = '>' + ( baseFormat * vertexCount )
				data = self.data[offset:offset+dataLength]
				displayListValues = struct.unpack( dataFormat, data )

				# Parse the display list for vertices and create a VertexList from them
				vl = self.createVertexList( primitiveType, displayListValues, vertexCount, attributesInfo )
				vertexLists.append( vl )

				offset += dataLength

		except Exception as err:
			if debugging:
				print( 'Unable to fully parse {}; {}'.format(self.name, err) )

		return vertexLists

	def createVertexList( self, primitiveType, displayListValues, vertexCount, attributesInfo ):

		""" Creates a VertexList (one entry in the display list; i.e. one set of primitives), 
			and gives it properties parsed out from the vertex attributes and display list data. """

		displayListIndex = 0
		vl = VertexList( primitiveType )

		# Iterate over each attribute value/index for each entry in this display set
		for i in range( vertexCount ):
			# Create the vertex and apply attributes (position/colors, etc.) for the current vertex
			for name, attrType, compType, _, indexStride, vertexStream in attributesInfo:
				if attrType == 0:
					continue
				elif attrType == 1: # DIRECT
					if name == 11 or name == 12: # Color values
						valueIndex = displayListIndex * indexStride
						values = displayListValues[valueIndex:valueIndex+indexStride]
						displayListIndex += indexStride
					else: # Everything else (primarily matrix indices)
						values = ( displayListValues[displayListIndex], )
						displayListIndex += 1
				else: # GX_INDEX8 / GX_INDEX16
					if vertexStream:
						valueIndex = displayListValues[displayListIndex] * indexStride
						values = vertexStream[valueIndex:valueIndex+indexStride]
					displayListIndex += 1

				# Create the vertex and update it with the values collected above
				if name == 0: # GX_VA_PNMTXIDX
					vl.weights.append( values[0] / 3 )
				elif name == 9: # Positional data (x, y, z coordinates)
					vl.vertices[1].extend( values )
				elif name == 11: # GX_VA_CLR0
					color = self.decodeColor( compType, values )
					vl.vertexColors[1].extend( color )
				# elif name == 12: # GX_VA_CLR1
				# 	print( 'Encountered secondary color (GX_VA_CLR1)' )
				elif name == 13: # GX_VA_TEX0
					vl.texCoords[1].extend( values )
					#print( self.name, values )

		vl.finalize()

		return vl

	def decodeColor( self, compType, pixelValues ):

		""" Decodes 2 to 4 bytes of data into an ( R, G, B, A ) color tuple (0-255 range). """

		if compType == 0: # GX_RGB565 (2 bytes)
			# 16 bit color without transparency
			# RRRRRGGGGGGBBBBB
			pixelValue = pixelValues[0]
			r = ( pixelValue >> 11 ) * 8
			g = ( pixelValue >> 5 & 0b111111 ) * 4
			b = ( pixelValue & 0b11111 ) * 8
			a = 255
		elif compType == 1: # GX_RGB8 (3 bytes)
			# 24 bit color without transparency
			# RRRRRRRRGGGGGGGGBBBBBBBB
			r = pixelValues[0]
			g = pixelValues[1]
			b = pixelValues[2]
			a = 255
		elif compType == 2 or compType == 5: # GX_RGBX8 or GX_RGBA8 (4 bytes)
			# 32 bit color with transparency
			# RRRRRRRRGGGGGGGGBBBBBBBBAAAAAAAA
			r = pixelValues[0]
			g = pixelValues[1]
			b = pixelValues[2]
			a = pixelValues[3]
		elif compType == 3: # GX_RGBA4 (i.e. RGBA4444; 2 bytes)
			# 16 bit color with transparency
			# RRRRGGGGBBBBAAAA
			pixelValue = pixelValues[0]
			r = pixelValue >> 12
			g = pixelValue >> 8 & 0b1111
			b = pixelValue >> 4 & 0b1111
			a = pixelValue & 0b1111

			# Normalize into the 0-255 range
			r = r * 16 + r
			g = g * 16 + g
			b = b * 16 + b
			a = a * 16 + a
		elif compType == 4: # GX_RGBA6 (3 bytes)
			# 24 bit color with transparency
			# RRRRRRGGGGGGBBBBBBAAAAAA
			r = pixelValues[0] >> 2
			g = ( (pixelValues[0] & 0b11) << 4 ) + pixelValues[1] >> 4
			b = ( pixelValues[1] & 0b1111 ) + pixelValues[2] >> 6
			a = pixelValues[2] & 0b111111

			# Normalize into the 0-255 range
			r = r * 4 + r
			g = g * 4 + g
			b = b * 4 + b
			a = a * 4 + a

		return ( r, g, b, a )


class VertexDataBlock( DataBlock ):

	""" Contains vertex data for a specific vertex attribute. """

	def __init__( self, *args, **kwargs ):
		DataBlock.__init__( self, *args, **kwargs )

		self.name = 'Vertex Data Block' + self.name


					# = --------------------------------------------------- = #
					#  [   HSD Internal File Structure Classes  (Common)   ]  #
					# = --------------------------------------------------- = #

class JointObjDesc( StructBase ): # A.k.a Bone Structure

	flags = { 'Joint_Flags': OrderedDict([
				( '1<<0', 'SKELETON' ),
				( '1<<1', 'SKELETON_ROOT' ),
				( '1<<2', 'ENVELOPE_MODEL' ),
				( '1<<3', 'CLASSICAL_SCALING' ),
				( '1<<4', 'HIDDEN' ),
				( '1<<5', 'PTCL' ),
				( '1<<6', 'MTX_DIRTY' ),
				( '1<<7', 'LIGHTING' ),
				( '1<<8', 'TEXGEN' ),
				( '1<<9', 'BILLBOARD' ),
				( '2<<9', 'VBILLBOARD' ),
				( '3<<9', 'HBILLBOARD' ),
				( '4<<9', 'RBILLBOARD' ),
				( '1<<12', 'INSTANCE' ),
				( '1<<13', 'PBILLBOARD' ),
				( '1<<14', 'SPLINE' ),
				( '1<<15', 'FLIP_IK' ),
				( '1<<16', 'SPECULAR' ),
				( '1<<17', 'USE_QUATERNION' ),
				( '1<<18', 'OPA' ),		# Opaque
				( '1<<19', 'XLU' ),		# Transparent
				( '1<<20', 'TEXEDGE' ),
				( '0<<21', 'NULL' ),
				( '1<<21', 'JOINT1' ),
				( '2<<21', 'JOINT2' ),
				( '3<<21', 'EFFECTOR' ),
				( '1<<23', 'USER_DEFINED_MTX' ),
				( '1<<24', 'MTX_INDEPEND_PARENT' ),
				( '1<<25', 'MTS_INDEPEND_SRT' ),
				( '1<<28', 'ROOT_OPA' ),
				( '1<<29', 'ROOT_XLU' ),
				( '1<<30', 'ROOT_TEXEDGE' )
		]) }

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )
		
		self.name = 'Joint Struct ' + uHex( 0x20 + args[1] )
		self.formatting = '>IIIIIfffffffffII'
		self.fields = ( 'Name_Pointer',
						'Joint_Flags',
						'Child_Pointer',
						'Next_Sibling_Pointer',
						'Display_Object_Pointer',
						'Rotation_X',		# Euler rotaion angles
						'Rotation_Y',
						'Rotation_Z',
						'Scale_X',
						'Scale_Y',
						'Scale_Z',
						'Translation_X',
						'Translation_Y',
						'Translation_Z',
						'Inverse_Matrix_Pointer',	# Object refers to parent if this is null
						'Reference_Object_Pointer'
					)
		self.length = 0x40
		self.childClassIdentities = { 2: 'JointObjDesc', 3: 'JointObjDesc', 4: 'DisplayObjDesc', 14: 'InverseMatrixObjDesc' }
		self._dobj = None

	@property
	def flags( self ):
		if self.values:
			return self.values[1]
		else:
			return self.getValues( 'Joint_Flags' )

	@property
	def DObj( self ):
		if not self._dobj:
			pointer = self.getValues( 'Display_Object_Pointer' )
			if pointer == 0: return None
			self._dobj = self.dat.initSpecificStruct( DisplayObjDesc, pointer, self.offset )
		return self._dobj

	@property
	def isBone( self ):
		flags = self.flags

		# Check for the SKELETON and SKELETON_ROOT flags
		if flags & 1 or flags & 2:
			return True
		else:
			return False

	def buildLocalMatrix( self ):

		""" Constructs a flattened 4x4 transformation matrix from this 
			bone's rotation, scale, and translation x/y/z values. This 
			matrix is therefore relative to the parent joint's vector. """

		# Collect local rotation, scale, and translation values
		rx, ry, rz, sx, sy, sz, tx, ty, tz = self.getValues()[5:14]

		# Create the initial matrix, with translation included
		matrix = [
			0, 0, 0, 0,
			0, 0, 0, 0,
			0, 0, 0, 0,
			tx, ty, tz, 1.0,
		]

		# Compute sin and cos values to build a rotation matrix
		cos_x, sin_x = math.cos( rx ), math.sin( rx )
		cos_y, sin_y = math.cos( ry ), math.sin( ry )
		cos_z, sin_z = math.cos( rz ), math.sin( rz )

		# Rotation and scale
		matrix[0] = sx * cos_y * cos_z 	# M11
		matrix[1] = sx * cos_y * sin_z 	# M12
		matrix[2] = sx * -sin_y 		# M13
		matrix[4] = sy * ( cos_z * sin_x * sin_y - cos_x * sin_z )	# M21
		matrix[5] = sy * ( sin_z * sin_x * sin_y + cos_x * cos_z )	# M22
		matrix[6] = sy * sin_x * cos_y 		# M23
		matrix[8] = sz * ( cos_z * cos_x * sin_y + sin_x * sin_z )	# M31
		matrix[9] = sz * ( sin_z * cos_x * sin_y - sin_x * cos_z )	# M32
		matrix[10] = sz * cos_x * cos_y 	# M33

		return matrix


class DisplayObjDesc( StructBase ):

	""" Represents an object to be displayed (rendered), including a material 
	 	with color and/or textures with other rendering properties, and a mesh. """

	count = 0

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Display Object ' + uHex( 0x20 + args[1] )
		self.formatting = '>IIII'
		self.fields = ( 'Name_Pointer',					# 0x0
						'Next_Sibling_Pointer',			# 0x4
						'Material_Object_Pointer',		# 0x8
						'Polygon_Object_Pointer',		# 0xC
					)
		self.length = 0x10
		self.childClassIdentities = { 1: 'DisplayObjDesc', 2: 'MaterialObjDesc', 3: 'PolygonObjDesc' }
		self._mobj = None
		self._pobj = None
		self.id = -1
		self.skeleton = {} # The same skeleton in to self.dat.skeletons[]

	def validated( self, deducedStructLength=-1 ):
		if not super( DisplayObjDesc, self ).validated( False, deducedStructLength ): 
			return False

		# At this point, we know the struct's pointers are good. Check if the Material pointer leads to a valid material struct.
		matObjOffset = self.getValues()[2]

		if matObjOffset != 0 or self.offset + 8 in self.dat.pointerOffsets:
			materialStruct = self.dat.initSpecificStruct( MaterialObjDesc, matObjOffset, self.offset, printWarnings=False )
			if not materialStruct:
				#print self.name, 'invalidated as', self.__class__.__name__, 'due to child at', hex(0x20+matObjOffset)
				return False

		self.provideChildHints()

		return True

	@property
	def MObj( self ):
		if not self._mobj:
			pointer = self.getValues( 'Material_Object_Pointer' )
			self._mobj = self.dat.initSpecificStruct( MaterialObjDesc, pointer, self.offset )
		return self._mobj

	@property
	def PObj( self ):
		if not self._pobj:
			pointer = self.getValues( 'Polygon_Object_Pointer' )
			self._pobj = self.dat.initSpecificStruct( PolygonObjDesc, pointer, self.offset )
		return self._pobj
	
	def getBoneAttachments( self ):

		""" Returns a list of bones (joint offsets) that this mesh is attached to or influenced by. """

		bones = []
		polygonObj = self.initChild( PolygonObjDesc, 3 )

		if polygonObj.isEnvelope:
			# Get a list of envelope objects from the envelope array
			envelopeArray = polygonObj.initChild( EnvelopeArray, 6 )
			envelopes = envelopeArray.getEnvelopes()

			# Collect joints (bones) from the envelopes
			for envelope in envelopes:
				for _, ( jointPointer, weight ) in envelope.iterateEntries():
					if weight == 0:
						continue
					joint = self.dat.initSpecificStruct( JointObjDesc, jointPointer, envelope.offset )
					bones.append( joint.offset )
		
		elif polygonObj.hasJObjRef:
			# Return just the single joint referenced
			bone = polygonObj.initChild( JointObjDesc, 6 )
			bones.append( bone.offset )
		
		else:
			# Get the parent joint this DObj is attached to
			for parentOffset in self.getParents():
				joint = self.dat.initSpecificStruct( JointObjDesc, parentOffset )
				if joint:
					bones.append( joint.offset )

		return bones


class InverseMatrixObjDesc( DataBlock ):

	def __init__( self, *args, **kwargs ):
		DataBlock.__init__( self, *args, **kwargs )

		self.name = 'Inverse Bind Matrix ' + uHex( 0x20 + args[1] )
		self.formatting = '>ffffffffffff'
		self.fields = ( 'M00', 'M01', 'M02', 'M03',
						'M10', 'M11', 'M12', 'M13',
						'M20', 'M21', 'M22', 'M23',
					)
		self.length = 0x30

	def build4x4( self ):

		""" Builds out the matrix from a 4x3 column-major format into a flattened 4x4 matrix. """

		v = self.getValues()

		matrix = ( 
			v[0], v[4], v[8],  0.0, 
			v[1], v[5], v[9],  0.0, 
			v[2], v[6], v[10], 0.0, 
			v[3], v[7], v[11], 1.0, 
		)

		return matrix

	# def invertMatrix( self, matrix ):
	# 	# Get the number of rows and columns of the matrix
	# 	rows = len(matrix)
	# 	cols = len(matrix[0])

	# 	# Create an identity matrix of the same size
	# 	identity = [[1 if i == j else 0 for j in range(cols)] for i in range(rows)]

	# 	# Augment the original matrix with the identity matrix
	# 	augmented = [row + identity_row for row, identity_row in zip(matrix, identity)]

	# 	# Perform row operations to convert the original matrix to the identity matrix
	# 	for i in range(rows):
	# 		# Scale the current row to make the leading entry 1
	# 		scale = augmented[i][i]
	# 		for j in range(cols * 2):
	# 			augmented[i][j] /= scale

	# 		# Perform row operations to eliminate other entries in the current column
	# 		for k in range(rows):
	# 			if k != i:
	# 				factor = augmented[k][i]
	# 				for j in range(cols * 2):
	# 					augmented[k][j] -= factor * augmented[i][j]

	# 	# Extract the inverted matrix from the augmented matrix
	# 	inverted_matrix = [row[cols:] for row in augmented]

	# 	return inverted_matrix

	def getMatrixMinor( self, m,i,j ):
		return [row[:j] + row[j+1:] for row in (m[:i]+m[i+1:])]
	
	def getMatrixDeternminant( self, m ):
		#base case for 2x2 matrix
		# if len(m) == 2:
		# 	return m[0][0]*m[1][1]-m[0][1]*m[1][0]

		determinant = 0
		for c in range(len(m)):
			determinant += ((-1)**c)*m[0][c]*self.getMatrixDeternminant(self.getMatrixMinor(m,0,c))
		return determinant

	def getMatrixInverse( self, unflattenedMatrix ):
		# Convert the flattened matrix to a 2D array (4x4)
		m = [unflattenedMatrix[i:i+4] for i in range(0, 16, 4)]

		determinant = self.getMatrixDeternminant(m)
		if determinant == 0:
			return unflattenedMatrix

		#special case for 2x2 matrix:
		# if len(m) == 2:
		# 	return [[m[1][1]/determinant, -1*m[0][1]/determinant],
		# 		[-1*m[1][0]/determinant, m[0][0]/determinant]]

		#find matrix of cofactors
		cofactors = []
		for r in range(len(m)):
			cofactorRow = []
			for c in range(len(m)):
				minor = self.getMatrixMinor(m,r,c)
				cofactorRow.append(((-1)**(r+c)) * self.getMatrixDeternminant(minor))
			cofactors.append(cofactorRow)
		cofactors = map(list,zip(*cofactors)) # Use "list(map(list,zip(*cofactors)))" for Python 3
		for r in range(len(cofactors)):
			for c in range(len(cofactors)):
				cofactors[r][c] = cofactors[r][c]/determinant
				
		# Convert the inverted matrix back to a flattened array
		inverted_matrix_flattened = [element for row in cofactors for element in row]

		return inverted_matrix_flattened
	
	def eliminate( self, r1, r2, col, target=0 ):
		fac = (r2[col]-target) / r1[col]
		for i in range(len(r2)):
			r2[i] -= fac * r1[i]

	def gauss( self, a ):
		for i in range(len(a)):
			if a[i][i] == 0:
				for j in range(i+1, len(a)):
					if a[i][j] != 0:
						a[i], a[j] = a[j], a[i]
						break
				else:
					raise ValueError("Matrix is not invertible")
			for j in range(i+1, len(a)):
				self.eliminate(a[i], a[j], i)
		for i in range(len(a)-1, -1, -1):
			for j in range(i-1, -1, -1):
				self.eliminate(a[i], a[j], i)
		for i in range(len(a)):
			self.eliminate(a[i], a[i], i, target=1)
		return a

	def inverse( self, unflattenedMatrix ):
		# Convert the flattened matrix to a 2D array (4x4)
		a = [ list(unflattenedMatrix[i:i+4]) for i in range(0, 16, 4) ]

		tmp = [[] for _ in a]
		for i,row in enumerate(a):
			assert len(row) == len(a)
			tmp[i].extend(row + [0]*i + [1] + [0]*(len(a)-i-1))
		self.gauss(tmp)
		ret = []
		for i in range(len(tmp)):
			ret.append(tmp[i][len(tmp[i])//2:])
		#return ret

		# Convert the inverted matrix back to a flattened array
		inverted_matrix_flattened = [element for row in ret for element in row]

		return inverted_matrix_flattened


# class ReferenceObjDesc( StructBase ):

# 	def __init__( self, *args, **kwargs ):
# 		StructBase.__init__( self, *args, **kwargs )


# 		self.name = 'Inverse Bind Matrix ' + uHex( 0x20 + args[1] )
	# 	formatting = '>'
	# 	fields = (  '',
	# 				''
	# 			)
	# 	length = 
	#	childClassIdentities = { 
#		self._siblingsChecked = 


class MaterialObjDesc( StructBase ):

	flags = { 'Rendering_Flags': OrderedDict([
				( '1<<0',  'USE_CONSTANT_SHADING' ),
				( '2<<0',  'USE_VERTEX_COLORS' ),
				( '3<<0',  'USE_CONSTANT_AND_VERTEX' ),	# Ever used?
				( '1<<2',  'RENDER_DIFFUSE' ),
				( '1<<3',  'RENDER_SPECULAR' ),
				( '1<<4',  'RENDER_TEX0' ),
				( '1<<5',  'RENDER_TEX1' ),
				( '1<<6',  'RENDER_TEX2' ),
				( '1<<7',  'RENDER_TEX3' ),
				( '1<<8',  'RENDER_TEX4' ),
				( '1<<9',  'RENDER_TEX5' ),
				( '1<<10', 'RENDER_TEX6' ),
				( '1<<11', 'RENDER_TEX7' ),
				( '1<<12', 'RENDER_TOON' ),				# Not used in Melee
				( '0<<13', 'RENDER_ALPHA_COMPAT' ),		# Required for alpha pixel-processing
				( '1<<13', 'RENDER_ALPHA_MAT' ),
				( '2<<13', 'RENDER_ALPHA_VTX' ),
				( '3<<13', 'RENDER_ALPHA_BOTH' ),
				( '1<<26', 'RENDER_SHADOW' ),			# Allows shadows to be cast on the object
				( '1<<27', 'RENDER_ZMODE_ALWAYS' ),
				( '1<<28', 'RENDER_DF_NONE' ),
				( '1<<29', 'RENDER_NO_ZUPDATE' ),		# Sends object to the back (no Z order calculation)
				( '1<<30', 'RENDER_XLU' ),				# Enables transparency application via color struct (eXtreme Level of Detail?)
				( '1<<31', 'RENDER_USER' )
			]) }

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Material Object ' + uHex( 0x20 + args[1] )
		self.formatting = '>IIIIII'
		self.fields = ( 'Name_Pointer',					# 0x0
						'Rendering_Flags',				# 0x4
						'Texture_Object_Pointer',		# 0x8
						'Material_Colors_Pointer',		# 0xC
						'Render_Struct_Pointer',		# 0x10 (Not used?)
						'Pixel_Proc._Pointer' 			# 0x14
					)
		self.length = 0x18
		self.childClassIdentities = { 2: 'TextureObjDesc', 3: 'MaterialColorObjDesc', 5: 'PixelProcObjDesc' }
		self._siblingsChecked = True

	@property
	def flags( self ):
		if self.values:
			return self.values[1]
		else:
			return self.getValues( 'Rendering_Flags' )

	def validated( self, deducedStructLength=-1 ):
		prelimCheck = super( MaterialObjDesc, self ).validated( False, deducedStructLength )
		if not prelimCheck: return False

		# At this point, we know the struct's pointers are good. Check if the Texture Object pointer leads to a valid texture struct.
		texObjOffset = self.getValues()[2]
		if texObjOffset != 0 or self.offset + 8 in self.dat.pointerOffsets:
			texStruct = self.dat.initSpecificStruct( TextureObjDesc, texObjOffset, self.offset, printWarnings=False )
			if not texStruct: return False

		self.provideChildHints()
		return True


class PolygonObjDesc( StructBase ): # A.k.a. Meshes

	flags = { 'Polygon_Flags': OrderedDict([
				( '1<<0', 'SHAPESET_AVERAGE' ), # NOTINVERTED?
				( '1<<1', 'SHAPESET_ADDITIVE' ),
				( '1<<2', 'UNKNOWN' ),
				( '1<<3', 'ANIMATED' ),
				( '1<<12', 'SHAPEANIM' ),
				( '1<<13', 'ENVELOPE' ),
				( '1<<14', 'CULLFRONT' ),
				( '1<<15', 'CULLBACK' )
			]) }

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Polygons Object ' + uHex( 0x20 + args[1] )
		self.formatting = '>IIIHHII'
		mostFields = (  'Name_Pointer',							# 0x0
						'Next_Sibling_Pointer',					# 0x4
						'Vertex_Attributes_Array_Pointer',		# 0x8
						'Polygon_Flags',						# 0xC
						'Display_List_Length',					# 0xE
						'Display_List_Pointer'					# 0x10
						# Last field is dynamic (set below)		# 0x14
					)
		self.length = 0x18
		self.childClassIdentities = { 1: 'PolygonObjDesc', 2: 'VertexAttributesArray', 5: 'DisplayListBlock' }

		self.isShapeSet = False
		self.isEnvelope = False
		self.hasJObjRef = False

		# Check flags to determine last field name and child structure
		try: # Exercising caution here because this structure hasn't been validated yet (which also means no self.data or unpacked values)
			flagsOffset = args[1] + 0xC
			flagsValue = struct.unpack( '>H', self.dat.data[flagsOffset:flagsOffset+2] )[0]

			if flagsValue & 0x1000: # Uses ShapeAnims (SHAPEANIM flag set), for vertex/mesh animations
				self.fields = mostFields + ( 'Shape_Set_Pointer', )
				print( self.name + ' found a Shape_Set!' )
				self.childClassIdentities[6] = 'ShapeSetDesc'
				self.isShapeSet = True

			elif flagsValue & 0x2000: # Uses Envelopes (ENVELOPE flag set), for skin weights
				self.fields = mostFields + ( 'Envelope_Array_Pointer', )
				self.childClassIdentities[6] = 'EnvelopeArray'
				self.isEnvelope = True

			elif args[1] + 0x14 in self.dat.structureOffsets: # Not expected, but just in case....
				self.fields = mostFields + ( 'JObjDesc_Pointer', )
				print( self.name + ' found a JObjDesc pointer!' )
				self.hasJObjRef = True

			else:
				self.fields = mostFields + ( 'Null Terminator',)

		except Exception as err:
			self.fields = mostFields + ( 'Unknown Pointer', ) # No underscore, so validation method ignores this as an actual pointer
			print( 'PolygonObjDesc initialization failure; {}'.format(err) )

	def decodeGeometry( self ):

		""" Initialize child structs and parse their data to decode model geometry. 
			Returns a list of VertexList objects, which are each a set of primitives. """

		# Initialize the child structs, Vertex Attributes Array and Display List
		vertexAttributes = self.initChild( VertexAttributesArray, 2 )
		displayList = self.initChild( DisplayListBlock, 5 )

		# Parse the attributes info and combine it with the display list data to build primitive lists
		vertexAttributeInfo = vertexAttributes.decodeEntries()
		displayListLength = self.getValues( 'Display_List_Length' )
		vertexLists = displayList.parse( displayListLength, vertexAttributeInfo )

		return vertexLists

	def moveToModelSpace( self, vertexLists, skeleton ):

		""" Applies transformations to the vertices of this object's mesh to convert 
			them from bind-pose or local-bone space to model space. """

		if self.isEnvelope:
			# Get a list of envelope objects from the envelope array
			envelopeArray = self.initChild( EnvelopeArray, 6 )
			envelopes = envelopeArray.getEnvelopes()

			for vl in vertexLists:
				# Prepare for iterating over individual vertex coordinates
				newCoords = []
				coordsIter = iter( vl.vertices[1] )
				coordsList = [ coordsIter ] * 3

				for envelopeIndex, x, y, z in zip( vl.weights, *coordsList ):
					envelope = envelopes[envelopeIndex]
					if not envelope: # Failsafe
						continue

					# Apply the matrices
					weightedVertex = envelope.applyMatrices( x, y, z, skeleton )
					newCoords.extend( weightedVertex )

				vl.vertices = ( vl.vertices[0], newCoords )

			return

		elif self.isShapeSet:
			print( '{} isShapeSet'.format(self.name) )
			return

		# Use a reference or parent JObj to determine model space
		elif self.hasJObjRef:
			print( '{} hasJObjRef'.format(self.name) )

			# Get the governing JObj
			joint = self.initChild( JointObjDesc, 6 )

		else:
			# Get the parent DObj this mesh is attached to
			dobj = self.getParent( DisplayObjDesc )

			# Unable to continue without a parent DObj!
			if not dobj:
				print( 'Unable to initialize a parent DObj for ' + self.name )
				return

			# Get the parent JObj this DObj is attached to
			joint = dobj.getParent( JointObjDesc )

		# Unable to continue without a JObj!
		if not joint:
			print( 'Unable to initialize a governing joint for ' + self.name )
			return

		# Get the model matrix
		bone = skeleton[joint.offset]
		m = bone.modelMatrix

		# Apply the final matrix to get the vertices into model space
		for vl in vertexLists:
			# Prepare for iterating over individual vertex coordinates
			newCoords = []
			coordsIter = iter( vl.vertices[1] )
			coordsList = [ coordsIter ] * 3

			for x, y, z in zip( *coordsList ):
				newCoords.append( m[0]*x + m[4]*y + m[8]*z + m[12] )
				newCoords.append( m[1]*x + m[5]*y + m[9]*z + m[13] )
				newCoords.append( m[2]*x + m[6]*y + m[10]*z + m[14] )

			vl.vertices = ( vl.vertices[0], newCoords )


class VertexAttributesArray( TableStruct ):

	""" Data defining aspects/properties of vertices, including their positions, 
		normals, colors, texture coordinates, etc. (See Attribute_Name for all.) """

	enums = { 'Attribute_Name': OrderedDict([
				( 0, 'GX_VA_PNMTXIDX' ),	# Position/Normal matrix index (index into envelope array)
				( 1, 'GX_VA_TEX0MTXIDX' ),	# Texture matrix indices
				( 2, 'GX_VA_TEX1MTXIDX' ),
				( 3, 'GX_VA_TEX2MTXIDX' ),
				( 4, 'GX_VA_TEX3MTXIDX' ),
				( 5, 'GX_VA_TEX4MTXIDX' ),
				( 6, 'GX_VA_TEX5MTXIDX' ),
				( 7, 'GX_VA_TEX6MTXIDX' ),
				( 8, 'GX_VA_TEX7MTXIDX' ),
				( 9, 'GX_VA_POS' ),			# Position
				( 10, 'GX_VA_NRM' ), 		# Or GX_VA_NBT (Normal or Normal/Binormal/Tangent)
				( 11, 'GX_VA_CLR0' ),		# Vertex colors (primary and secondary)
				( 12, 'GX_VA_CLR1' ),
				( 13, 'GX_VA_TEX0' ),		# Texture coordinates
				( 14, 'GX_VA_TEX1' ),
				( 15, 'GX_VA_TEX2' ),
				( 16, 'GX_VA_TEX3' ),
				( 17, 'GX_VA_TEX4' ),
				( 18, 'GX_VA_TEX5' ),
				( 19, 'GX_VA_TEX6' ),
				( 20, 'GX_VA_TEX7' ),

				( 21, 'GX_VA_POS_MTX_ARRAY' ),	# Position matrix array pointer
				( 22, 'GX_VA_NRM_MTX_ARRAY' ),	# Normal matrix array pointer
				( 23, 'GX_VA_TEX_MTX_ARRAY' ),	# Texture matrix array pointer
				( 24, 'GX_VA_LIGHT_ARRAY' ),	# Light parameter array pointer
				( 25, 'GX_VA_NBT' ),			# Normal/Bi-normal/tangent ID/Value
				( 26, 'GX_VA_MAX_ATTR' ),		# Maximum number of vertex attributes

				( 0xFF, 'GX_VA_NULL' )
			]),
			'Attribute_Type': OrderedDict([
				( 0, 'GX_NONE' ),
				( 1, 'GX_DIRECT' ),
				( 2, 'GX_INDEX8' ),
				( 3, 'GX_INDEX16' ),
			]),
			# Component_Count may be one of several 
			# different enumerations, based on Attribute_Name:
			# GXCompCnt:
			# 	GX_DEFAULT   = 0
			# 
			# Position Counts (GXPosCompCnt):
			# 	GX_POS_XY    = 0
			# 	GX_POS_XYZ   = 1
			# 
			# Normal Counts (GXNrmCompCnt):
			# 	GX_NRM_XYZ   = 0
			# 	GX_NRM_NBT   = 1  (one index per NBT)
			# 	GX_NRM_NBT3  = 2  (one index per each of N/B/T)
			# 
			# Color Counts (GXClrCompCnt):
			# 	GX_CLR_RGB   = 0
			# 	GX_CLR_RGBA  = 1
			# 
			# Texture Coordinate Counts (GXTexCompCnt):
			# 	GX_TEX_S     = 0
			# 	GX_TEX_ST    = 1
			# 
			'Component_Type': OrderedDict([ # GXCompType
				( 0, 'GX_U8' ),		# 0 - 255
				( 1, 'GX_S8' ),		# -127 - +127
				( 2, 'GX_U16' ),	# 0 - 65535
				( 3, 'GX_S16' ),	# -32767 - +32767
				( 4, 'GX_F32' ),	# Float
			])
	}

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Vertex Attributes Array ' + uHex( 0x20 + args[1] )
		self.fields = (	'Attribute_Name',			# 0x0  -{ GXAttr; determines the kind of attribute and how to interpret its data
						'Attribute_Type',			# 0x4  -{ GXAttrType (i.e. index type)
						'Component_Count',			# 0x8  -{ GXCompCnt (may be one of several enumerations: PosComp/NrmComp/ClrComp/TexComp)
						'Component_Type',			# 0xC  -{ GXCompType/GXClrCompType (i.e. value formatting; int8, uint16, etc.)
						'Scale',					# 0x10 -{ "frac"; number of fractional bits to use when scaling ints into floats
						'Padding',					# 0x11
						'Stride',					# 0x12 -{ Multiplyer used when indexing bytes in the vertex data
						'Vertex_Data_Pointer' )		# 0x14 -{ Pointer to raw data for a specific attribute
		self.formatting = '>IIIIBBHI'
		self.length = 0x18

		# Attempt to get the length and array count of this struct
		deducedStructLength = self.dat.getStructLength( self.offset ) # This length will include any padding too
		if deducedStructLength / 0x18 == 1: # Using division rather than just '==0x18' in case there's trailing padding
			self.entryCount = 1
		else:
			# Scan ahead for a null attribute name (GX_VA_NULL; value of 0xFF)
			try:
				self.entryCount = -1

				for fieldOffset in range( self.offset, self.offset + deducedStructLength, 0x18 ):
					attributeName = self.dat.data[fieldOffset+3]

					if attributeName == 0xFF: # End of this array
						self.entryCount = ( fieldOffset - self.offset ) / 0x18 + 1
						break
			except:
				self.entryCount = -1

		TableStruct.__init__( self )

		for i in range( 7, len(self.fields), self.entryValueCount ):
			self.childClassIdentities[i] = 'VertexDataBlock'
		self._siblingsChecked = True
		self._attributeInfo = []

	def determineDimensions( self, name, count ):

		""" Determines the number of dimensions or channels for an attribute, based on 
			enumerations for the kind of attribute (Attribute_Name) and component count.
			For example, 2 for a 2D point, or 4 for an RGBA color. """

		# GX_VA_PNMTXIDX - GX_VA_TEX7MTXIDX
		if name < 9 :
			# GX_VA_PNMTXIDX or another matrix index (component count = GXCompCnt; only 1 enumeration)
			dimensions = 1 # GX_DEFAULT

		# GX_VA_POS
		elif name == 9:
			# Position coordinates (enumeration is among GXPosCompCnt)
			if count == 0: # GX_POS_XY
				dimensions = 2
				print( 'Found a 2D point in {}!'.format(self.name) )
			elif count == 1: # GX_POS_XYZ
				dimensions = 3
			else:
				dimensions = -1
				enumName = self.enums['Attribute_Name'][name]
				print( 'Warning! Vertex attribute name {} has an unexpected dimensions enumeration: {}'.format(enumName, count) )

		# GX_VA_NRM
		elif name == 10:
			dimensions = 3

		# GX_VA_CLR0, GX_VA_CLR1
		elif name < 13:
			# Color attribute component (GXClrCompCnt)
			if count == 0: # GX_CLR_RGB
				dimensions = 3
			elif count == 1: # GX_CLR_RGBA
				dimensions = 4
			else:
				dimensions = -1
				enumName = self.enums['Attribute_Name'][name]
				print( 'Warning! Vertex attribute name {} has an unexpected dimensions enumeration: {}'.format(enumName, count) )

		# GX_VA_TEX0 - GX_VA_TEX7
		elif name < 21:
			# Texture mapping coordinates (GXTexCompCnt)
			if count == 0: # GX_TEX_S
				dimensions = 1
			elif count == 1: # GX_TEX_ST
				dimensions = 2
			else:
				dimensions = -1
				enumName = self.enums['Attribute_Name'][name]
				print( 'Warning! Vertex attribute name {} has an unexpected dimensions enumeration: {}'.format(enumName, count) )

		# GX_VA_NBT
		elif name == 25:
			# Normal/Bitangent/tangent vectors (1 to 3 sets of 3 values each)
			if count == 0:
				dimensions = 3
			else: # GX_NRM_NBT3 (for HW2)
				dimensions = 9

		else:
			dimensions = 1
			enumName = self.enums['Attribute_Name'][name]
			print( 'Encountered the vertex attribute {} in {}'.format(enumName, self.name) )

		return dimensions

	def decodeEntries( self ):

		""" Iterate over the attributes array, collect information on each attribute, 
			and unpack the vertex attributes data. """

		if self._attributeInfo:
			return self._attributeInfo

		self._attributeInfo = []
		warnings = set() # Collect warnings, preventing duplicates

		for i, (name, attrType, count, compType, scale, _, stride, dataPointer) in self.iterateEntries():

			# Check for the end of the array
			if name == 0xFF: # GX_VA_NULL
				break

			# Determine the formatting and number of values will be unpacked per vertex for this attribute
			elif name == 11 or name == 12:
				vertexDescriptor = GXCompType_CLR[compType]
				indexStride = len( vertexDescriptor ) # Number of values after unpacking, not byte count!
			else:
				# Determine formatting for this attribute's values
				dimensions = self.determineDimensions( name, count )
				valueFormat = GXCompType_VAL[compType]

				# Assemble the formatting
				vertexDescriptor = '{}{}'.format( dimensions, valueFormat )
				indexStride = dimensions * len( valueFormat ) # Number of values after unpacking, not byte count!

			# Check if this is direct (GX_DIRECT) display list data; no data indexing
			if attrType == 1 or stride == 0:
				self._attributeInfo.append( (name, attrType, compType, vertexDescriptor, indexStride, []) )
				continue

			# Ensure that the vertex data pointer is pointing to a valid struct
			pointerOffset = self.offset + ( self.entryLength * i ) + 0x14
			if pointerOffset not in self.dat.pointerOffsets:
				self._attributeInfo.append( (name, attrType, compType, '', 0, []) )
				warnings.add( 'Warning! A vertex attribute, index {} in {}, references a data struct but does not have one!'.format(i, self.name) )
				continue

			# More validation
			elif struct.calcsize( vertexDescriptor ) != stride:
				self._attributeInfo.append( (name, attrType, compType, '', 0, []) )
				warnings.add( 'Warning! Vertix attribute descriptor does not match expected stride! {} != {}'.format(struct.calcsize(vertexDescriptor), stride) )
				continue

			# Get the vertex attribute data struct, and get its data without padding
			vertexDataStruct = self.dat.initSpecificStruct( VertexDataBlock, dataPointer, self.offset )
			vertexCount = vertexDataStruct.length / stride
			dataFormat = '>' + ( vertexDescriptor * vertexCount )
			trimmedData = vertexDataStruct.data[:stride * vertexCount] # Strips off any padding to get exact data size

			# Unpack the vertex data struct's values and apply scaling
			vertexData = struct.unpack( dataFormat, trimmedData )
			if compType != 4 and scale != 0: # If not a float and scale is non-zero (not used with color types)
				vertexData = [ value / float(1 << scale) for value in vertexData ]

			# Store the info and data for this attribute
			self._attributeInfo.append( (name, attrType, compType, vertexDescriptor, indexStride, vertexData) )

			# Mention instances of unhandled attributes (#todo!)
			if name not in ( 0, 9, 11, 12, 13 ):
				enumName = self.enums['Attribute_Name'][name]
				warnings.add( 'Encountered {} in {}'.format(enumName, self.name) )

		if warnings:
			print( '\n'.join(list(warnings)) )

		return self._attributeInfo


class EnvelopeArray( StructBase ):

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Envelope Array ' + uHex( 0x20 + args[1] )
		self._siblingsChecked = True

		# Check the parent's array count to see how many elements should be in this structure
		self.length = self.dat.getStructLength( self.offset )
		self.entryCount = self.length / 4 - 1

		# Use the above info to dynamically build this struct's basic properties
		self.formatting = '>' + ( 'I' * self.entryCount ) + 'I'
		self.fields = ( 'Envelope_Pointer', ) * self.entryCount + ( 'Null Terminator', )
		for i in range( 0, self.entryCount ):
			self.childClassIdentities[i] = 'EnvelopeObjDesc'

	def getEnvelopes( self ):

		""" Returns a list of the envelope objects described by this array. """

		envelopePointers = self.getValues()[:-1] # Exclude last entry (the null terminator)
		return [ self.dat.initSpecificStruct(EnvelopeObjDesc, offset, self.offset) for offset in envelopePointers ]


class EnvelopeObjDesc( TableStruct ):

	""" Describes a series of inverse bind matrices and weights for their application to 
		vertices. The inverse bind matrices are attached to JObjs described by this struct. """

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Envelope Object ' + uHex( 0x20 + args[1] )

		# Use the above info to dynamically build this struct's basic properties
		self.formatting = '>If'
		self.fields = ( 'Joint_Pointer', 'Weight' )
		self.length = 8

		# Define an entrycount for the struct before initializing as a table
		deducedStructLength = self.dat.getStructLength( self.offset )
		self.entryCount = deducedStructLength / self.length

		TableStruct.__init__( self )

		for i in range( 0, self.entryCount*2, self.entryValueCount ):
			self.childClassIdentities[i] = 'JointObjDesc'

	def applyMatrices( self, x, y, z, skeleton ):

		""" Applies the weighted transformations for all joints/bones applicable 
			(from this envelope object) to the given vertex coordinates. If more 
			than one joint's transforms are needed, the vertices are expected to 
			be in bind-pose space. If not, they are already in local-bone space. """

		structValues = self.getValues()

		# See if we can avoid some loops
		if self.entryCount == 2 and structValues[-1] == 0:
			# Only applying transformations from one bone
			jointPointer = structValues[0]

			# Get the inverse bind matrix for this joint
			# joint = self.dat.initSpecificStruct( JointObjDesc, jointPointer )
			# matrixStruct = joint.initChild( InverseMatrixObjDesc, 14 )
			# inverseBindMatrix = matrixStruct.build4x4()

			# Combine the matrices of the bone with the inverse bind matrix
			bone = skeleton[jointPointer]
			# m = bone.matrixMultiply_4x4( inverseBindMatrix, bone.modelMatrix )
			m = bone.modelMatrix
			
			new_x = m[0]*x + m[4]*y + m[8]*z + m[12]
			new_y = m[1]*x + m[5]*y + m[9]*z + m[13]
			new_z = m[2]*x + m[6]*y + m[10]*z + m[14]

			return ( new_x, new_y, new_z )
		
		else:
			# Applying transformations from multiple bones
			weightedVertex = [ 0, 0, 0 ]

			for _, ( jointPointer, weight ) in self.iterateEntries():
				if weight == 0:
					continue

				# Get the inverse bind matrix for this bone/joint
				bone = skeleton[jointPointer]
				#joint = self.dat.initSpecificStruct( JointObjDesc, jointPointer )
				matrixStruct = bone.joint.initChild( InverseMatrixObjDesc, 14 )
				inverseBindMatrix = matrixStruct.build4x4()

				# Combine the matrices of the bone with the inverse bind matrix
				m = bone.matrixMultiply_4x4( inverseBindMatrix, bone.modelMatrix )
				
				# Apply the final matrix to get the vertex into model space
				weightedVertex[0] += ( m[0]*x + m[4]*y + m[8]*z + m[12] ) * weight
				weightedVertex[1] += ( m[1]*x + m[5]*y + m[9]*z + m[13] ) * weight
				weightedVertex[2] += ( m[2]*x + m[6]*y + m[10]*z + m[14] ) * weight

			return weightedVertex


class ShapeSetDesc( StructBase ):

	flags = { 'Shape_Flags': OrderedDict([
				( '1<<0', 'SHAPESET_AVERAGE' ),
				( '1<<1', 'SHAPESET_ADDITIVE' )
			]) }

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Shape Set Object ' + uHex( 0x20 + args[1] )
		self.formatting = '>HHIIIIIIII'
		self.fields = ( 'Shape_Flags',
						'Number_of_Shapes',
						'Number_of_Vertex_Indices',
						'Vertex_Desc_Array_Pointer',
						'Vertex_Index_Array_Pointer',
						'Number_of_Normal_Indices',
						'Normal_Desc_Array_Pointer',
						'Normal_Index_Array_Pointer',
						'Blend_Floats_Array_Pointer', # Array of floats of size (nb_shape * sizeof(float))
						'Blend_Value' )
		self.length = 0x24
		self._siblingsChecked = True
		self.childClassIdentities = { 3: 'VertexAttributesArray', 6: 'VertexAttributesArray' }


class TextureObjDesc( StructBase ):

	flags = { 'Texture_Flags': OrderedDict([
				( '0<<0', 'COORD_UV' ),
				( '1<<0', 'COORD_REFLECTION' ),
				( '2<<0', 'COORD_HILIGHT' ),
				( '3<<0', 'COORD_SHADOW' ),
				( '4<<0', 'COORD_TOON' ),
				( '5<<0', 'COORD_GRADATION' ),
				( '6<<0', 'COORD_BACKLIGHT' ),
				( '1<<4', 'LIGHTMAP_DIFFUSE' ),
				( '2<<4', 'LIGHTMAP_SPECULAR' ),
				( '4<<4', 'LIGHTMAP_AMBIENT' ),
				( '8<<4', 'LIGHTMAP_EXT' ),
				( '16<<4', 'LIGHTMAP_SHADOW' ),
				( '0<<16', 'COLORMAP_NONE' ),
				( '1<<16', 'COLORMAP_ALPHA_MASK' ),
				( '2<<16', 'COLORMAP_RGB_MASK' ),
				( '3<<16', 'COLORMAP_BLEND' ),
				( '4<<16', 'COLORMAP_MODULATE' ),
				( '5<<16', 'COLORMAP_REPLACE' ),
				( '6<<16', 'COLORMAP_PASS' ),
				( '7<<16', 'COLORMAP_ADD' ),
				( '8<<16', 'COLORMAP_SUB' ),
				( '1<<20', 'ALPHAMAP_ALPHA_MASK' ),
				( '2<<20', 'ALPHAMAP_BLEND' ),
				( '3<<20', 'ALPHAMAP_MODULATE' ),
				( '4<<20', 'ALPHAMAP_REPLACE' ),
				( '5<<20', 'ALPHAMAP_PASS' ),
				( '6<<20', 'ALPHAMAP_ADD' ),
				( '7<<20', 'ALPHAMAP_SUB' ),
				( '1<<24', 'BUMP' ),
				( '1<<31', 'MTX_DIRTY' )
			]) }

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Texture Struct ' + uHex( 0x20 + args[1] )
		self.formatting = '>IIIIfffffffffIIBBHIfIIIII'
		self.fields = ( 'Name_Pointer',
						'Next_Sibling_Pointer',
						'GXTexMapID',		# i.e. Animation ID
						'GXTexGenSrc', 		# Coord Gen Source Args
						'Rotation_X',
						'Rotation_Y',
						'Rotation_Z',
						'Scale_X',
						'Scale_Y',
						'Scale_Z',
						'Translation_X',
						'Translation_Y',
						'Translation_Z',
						'GXTexWrapMode_S',
						'GXTexWrapMode_T',
						'Repeat_S',
						'Repeat_T',
						'Padding',
						'Texture_Flags',
						'Blending',
						'Mag_Filter',	# GXTexFilter
						'Image_Header_Pointer',
						'Palette_Header_Pointer',
						'LOD_Struct_Pointer',
						'TEV_Struct_Pointer'
					)
		self.length = 0x5C
		self.childClassIdentities = { 1: 'TextureObjDesc', 21: 'ImageObjDesc', 22: 'PaletteObjDesc', 23: 'LodObjDes', 24: 'TevObjDesc' }

	@property
	def flags( self ):
		if self.values:
			return self.values[18]
		else:
			return self.getValues()[18]

	def validated( self, deducedStructLength=-1 ):
		prelimCheck = super( TextureObjDesc, self ).validated( False, deducedStructLength )
		if not prelimCheck: return False

		# Check for and initialize a TEV Struct, if present
		tevStructOffset = self.getValues()[-1]
		if tevStructOffset == 0:
			self.provideChildHints()
			return True
		else:
			if not tevStructOffset in self.dat.structs:
				self.dat.structs[tevStructOffset] = 'TevObjDesc' # Adding a hint to permit this struct to be created even if it's all null data
			tevStruct = self.dat.initSpecificStruct( TevObjDesc, tevStructOffset, self.offset, printWarnings=False )
			if not tevStruct: return False

			# Validation passed
			self.provideChildHints()
			return True

	def buildLocalMatrix( self ):

		""" Constructs a flattened 4x4 transformation matrix from this 
			TObj's rotation, scale, and translation x/y/z values. This 
			matrix will be column-major order and assumes Euler angles. """

		# Collect local rotation, scale, and translation values
		rx, ry, rz, sx, sy, sz, tx, ty, tz = self.getValues()[4:13]

		# Create the initial matrix, with translation included
		matrix = [
			0, 0, 0, 0,
			0, 0, 0, 0,
			0, 0, 0, 0,
			tx, ty, tz, 1.0,
		]

		# Compute sin and cos values to build a rotation matrix
		cos_x, sin_x = math.cos( rx ), math.sin( rx )
		cos_y, sin_y = math.cos( ry ), math.sin( ry )
		cos_z, sin_z = math.cos( rz ), math.sin( rz )

		# Rotation and scale
		matrix[0] = sx * cos_y * cos_z 	# M11
		matrix[1] = sx * cos_y * sin_z 	# M12
		matrix[2] = sx * -sin_y 		# M13
		matrix[4] = sy * ( cos_z * sin_x * sin_y - cos_x * sin_z )	# M21
		matrix[5] = sy * ( sin_z * sin_x * sin_y + cos_x * cos_z )	# M22
		matrix[6] = sy * sin_x * cos_y 		# M23
		matrix[8] = sz * ( cos_z * cos_x * sin_y + sin_x * sin_z )	# M31
		matrix[9] = sz * ( sin_z * cos_x * sin_y - sin_x * cos_z )	# M32
		matrix[10] = sz * cos_x * cos_y 	# M33

		return matrix

	def buildLocalInverseMatrix( self ):

		""" Constructs a flattened 4x4 transformation matrix from this 
			TObj's rotation, scale, and translation x/y/z values. This 
			matrix will be column-major order and assumes Euler angles. 
			However, this builds the inverted form. """

		# Collect local rotation, scale, and translation values
		rx, ry, rz, sx, sy, sz, tx, ty, tz = self.getValues()[4:13]

		# Create the initial matrix, with translation included
		matrix = [
			0, 0, 0, 0,
			0, 0, 0, 0,
			0, 0, 0, 0,
			-tx, -ty, -tz, 1.0,
		]

		# Compute sin and cos values to build a rotation matrix
		cos_x, sin_x = math.cos( rx ), -math.sin( rx )
		cos_y, sin_y = math.cos( ry ), -math.sin( ry )
		cos_z, sin_z = math.cos( rz ), -math.sin( rz )

		# Rotation and scale
		sx = 1 / sx
		sy = 1 / sy
		sz = 1 / sz
		matrix[0] = sx * cos_y * cos_z 	# M11
		matrix[1] = sx * cos_y * sin_z 	# M12
		matrix[2] = sx * -sin_y 		# M13
		matrix[4] = sy * ( cos_z * sin_x * sin_y - cos_x * sin_z )	# M21
		matrix[5] = sy * ( sin_z * sin_x * sin_y + cos_x * cos_z )	# M22
		matrix[6] = sy * sin_x * cos_y 		# M23
		matrix[8] = sz * ( cos_z * cos_x * sin_y + sin_x * sin_z )	# M31
		matrix[9] = sz * ( sin_z * cos_x * sin_y - sin_x * cos_z )	# M32
		matrix[10] = sz * cos_x * cos_y 	# M33

		return matrix


class MaterialColorObjDesc( StructBase ):

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Material Colors ' + uHex( 0x20 + args[1] )
		self.formatting = '>IIIff'
		self.fields = (	'RGBA_Ambience',
						'RGBA_Diffusion',
						'RGBA_Specular_Highlights',
						'Transparency',
						'Shininess'
					)
		self.length = 0x14
		self._siblingsChecked = True
		self._childrenChecked = True

	@property
	def ambience( self ): # Normalize to 0-1.0 range
		return [ channel / 255.0 for channel in self.data[:4] ]
	@property
	def diffusion( self ): # Normalize to 0-1.0 range
		return [ channel / 255.0 for channel in self.data[4:8] ]
	@property
	def specular( self ): # Normalize to 0-1.0 range
		return [ channel / 255.0 for channel in self.data[8:0xC] ]
	@property
	def transparency( self ):
		return self.getValues()[-2]
	@property
	def shininess( self ):
		return self.getValues()[-1]


class PixelProcObjDesc( StructBase ): # Pixel Processor Struct (PEDesc)
														# [ Internal GX Notes ]
	flags = { 'Pixel Proc. Flags': OrderedDict([
				( '1<<0', 'Enable Color Updates' ),			# update_enable [GXSetColorUpdate]
				( '1<<1', 'Enable Alpha Updates' ),			# update_enable [GXSetAlphaUpdate]
				( '1<<2', 'Enable Destination Alpha' ),		# enable [GXSetDstAlpha] (constant alpha)
				( '1<<3', 'Z-Buff Before Texturing' ),		# before_tex [GXSetZCompLoc]
				( '1<<4', 'Enable Z Comparisons' ),			# compare_enable [GXSetZMode]
				( '1<<5', 'Enable Z Updates' ),				# update_enable [GXSetZMode]
				( '1<<6', 'Enable Dithering' )				# dither [GXSetDither]
			]) }

	enums = { 'Blend Mode Type': OrderedDict([			# GXBlendMode:
				( 0, 'None' ),					# GX_BM_NONE (writes directly to EFB)
				( 1, 'Additive' ),				# GX_BM_BLEND
				( 2, 'Logical Bitwise' ),		# GX_BM_LOGIC
				( 3, 'Subtract' ),				# GX_BM_SUBTRACT
				( 4, 'Max Blend' )				# GX_MAX_BLENDMODE
			]),
			'Source Factor': OrderedDict([				# GXBlendFactor:
				( 0, 'Zero' ),					# GX_BL_ZERO			0.0
				( 1, 'One' ),					# GX_BL_ONE				1.0
				( 2, 'Destination Color' ),		# GX_BL_DSTCLR			frame buffer color
				( 3, 'Inverse Dest. Color' ),	# GX_BL_INVDSTCLR		1.0 - (frame buffer color)
				( 4, 'Source Alpha' ),			# GX_BL_SRCALPHA		source alpha
				( 5, 'Inverse Src. Alpha' ),	# GX_BL_INVSRCALPHA		1.0 - (source alpha)
				( 6, 'Destination Alpha' ),		# GX_BL_DSTALPHA		frame buffer alpha
				( 7, 'Inverse Dest. Alpha' )	# GX_BL_INVDSTALPHA		1.0 - (frame buffer alpha)
			]),
			'Destination Factor': OrderedDict([			# GXBlendFactor:
				( 0, 'Zero' ),					# GX_BL_ZERO			0.0
				( 1, 'One' ),					# GX_BL_ONE				1.0
				( 2, 'Source Color' ),			# GX_BL_SRCCLR			source color
				( 3, 'Inverse Src. Color' ),	# GX_BL_INVSRCCLR		1.0 - (source color)
				( 4, 'Source Alpha' ),			# GX_BL_SRCALPHA		source alpha
				( 5, 'Inverse Src. Alpha' ),	# GX_BL_INVSRCALPHA		1.0 - (source alpha)
				( 6, 'Destination Alpha' ),		# GX_BL_DSTALPHA		frame buffer alpha
				( 7, 'Inverse Dest. Alpha' )	# GX_BL_INVDSTALPHA		1.0 - (frame buffer alpha)
			 ]) }

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Pixel Proc. Struct ' + uHex( 0x20 + args[1] )
		self.formatting = '>BBBBBBBBBBBB'							# [Original GX function name from SDK]
		self.fields = (	'Pixel Proc. Flags',		#			bitflags 
						'Reference Value 0',		#			ref0 [GXSetAlphaCompare]
						'Reference Value 1',		#			ref1 [GXSetAlphaCompare]
						'Destination Alpha',		#			alpha [GXSetDstAlpha]
						'Blend Mode Type',			# 0x4		type [GXSetBlendMode]
						'Source Factor',			#			src_factor [GXSetBlendMode]
						'Destination Factor',		#			dst_factor [GXSetBlendMode]
						'Pixel Logic Operation',	#			op [GXSetBlendMode]
						'Z Compare Function',		# 0x8		func [GXSetZMode]
						'Alpha Compare 0',			#			comp0 [GXSetAlphaCompare]
						'Alpha Operation',			#			op [GXSetAlphaCompare]
						'Alpha Compare 1'			#			comp1 [GXSetAlphaCompare]
					)
		self.length = 0xC
		self._siblingsChecked = True
		self._childrenChecked = True

	@property
	def flags( self ):
		if self.values:
			return self.values[0]
		else:
			return self.getValues()[0]


class ImageObjDesc( StructBase ):

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Image Data Header ' + uHex( 0x20 + args[1] )
		self.formatting = '>IHHIIff'
		self.fields = (	'Image_Data_Pointer',
						'Width',
						'Height',
						'Image_Type',
						'Mipmap_Flag',
						'MinLOD',
						'MaxLOD'
					)
		self.length = 0x18
		self.childClassIdentities = { 0: 'ImageDataBlock' }
		self._siblingsChecked = True

	def validated( self, deducedStructLength=-1 ):
		# Perform basic struct validation
		prelimCheck = super( ImageObjDesc, self ).validated( False, deducedStructLength )
		if not prelimCheck: return False

		# Check specific data values for known restrictions
		dataBlockOffset, width, height, imageType, mipmapFlag, minLOD, maxLOD = self.getValues()

		if width < 1 or height < 1: return False
		elif width > 1024 or height > 1024: return False
		elif imageType not in ( 0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 14 ): return False
		elif mipmapFlag > 1: return False
		elif minLOD > 10 or maxLOD > 10: return False
		elif minLOD > maxLOD: return False

		# Check for a minimum size on the image data block. Most image types require at least 0x20 bytes for even just a 1x1 pixel image
		childStructLength = self.dat.getStructLength( dataBlockOffset )
		if childStructLength == -1: pass # Can't trust this; unable to calculate the length (data must be after the string table)
		elif imageType == 6 and childStructLength < 0x40: return False
		elif childStructLength < 0x20: return False

		# Check if the child (image data) has any children (which it shouldn't)
		for pointerOffset in self.dat.pointerOffsets:
			if pointerOffset >= dataBlockOffset:
				if pointerOffset < dataBlockOffset + childStructLength: # Pointer found in data block
					return False
				break

		# Validation passed
		self.provideChildHints()
		return True


class PaletteObjDesc( StructBase ):

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Palette Data Header ' + uHex( 0x20 + args[1] )
		self.formatting = '>IIIH'
		self.fields = (	'Palette_Data_Pointer',
						'Palette_Type', 		# GXTlutFmt
						'Name',
						'Color_Count'
					)
		self.length = 0xE
		self.childClassIdentities = { 0: 'PaletteDataBlock' }
		self._siblingsChecked = True

	def validated( self, deducedStructLength=-1 ):
		# Perform basic struct validation
		prelimCheck = super( PaletteObjDesc, self ).validated( False, deducedStructLength )
		if not prelimCheck: return False

		# Check specific data values for known restrictions
		dataBlockOffset, paletteType, name, colorCount = self.getValues()

		if dataBlockOffset == 0: return False
		elif paletteType > 2: return False # Should only be 0-2
		elif name != 0: return False # Always seen as 0
		elif colorCount > 16384: return False # Max is 16/256/16384 for image types 8/9/10, respectively

		# Check for a minimum size on the palette data block
		childStructLength = self.dat.getStructLength( dataBlockOffset )
		if childStructLength < 0x20: return False # Even _8 type paletted textures (CI4), the smallest type, reserve at least 0x20 bytes

		# Check if the child (palette data) has any children (which it shouldn't)
		for pointerOffset in self.dat.pointerOffsets:
			if pointerOffset >= dataBlockOffset:
				if pointerOffset < dataBlockOffset + childStructLength: # Pointer found in data block
					return False
				break
		
		# Validation passed
		self.provideChildHints()
		return True


class LodObjDes( StructBase ): # Level Of Detail

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Level of Detail Struct ' + uHex( 0x20 + args[1] )
		self.formatting = '>If??HI'
		self.fields = ( 'Min_Filter',		# GXTexFilter
						'LOD_Bias',			# Float
						'Bias_Clamp', 		# Bool
						'Edge_LOD_Enable',	# Bool
						'Padding',			# 2 bytes
						'Max_Anisotrophy'	# GXAnisotropy
					)
		self.length = 0x10
		self._siblingsChecked = True
		self._childrenChecked = True

	""" A few restrictions on the values of this structure:
			LOD Bias - should be between -4.0 to 3.99
			Edge LOD must be enabled for Max Anisotrophy
			Max Anisotrophy can be 0, 1, 2, or 4 
			(latter two values require trilinear filtering) """


class TevObjDesc( StructBase ): # Texture Environment struct

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Texture Environment Struct ' + uHex( 0x20 + args[1] )
		self.formatting = '>????????BBBBBBBBIIII'
		self.fields = ( 'Color_Op',
						'Alpha_Op',
						'Color_Bias',
						'Alpha_Bias',
						'Color_Scale',
						'Alpha_Scale',
						'Color_Clamp',
						'Alpha_Clamp',
						'Color_A',			# 0x8
						'Color_B',
						'Color_C',
						'Color_D',
						'Alpha_A',
						'Alpha_B',
						'Alpha_C',
						'Alpha_D',
						'RGBA_Color_1_(konst)',	# 0x10
						'RGBA_Color_2_(tev0)',
						'RGBA_Color_3_(tev1)',
						'Active'
					)
		self.length = 0x20
		self._siblingsChecked = True
		self._childrenChecked = True


class CameraObjDesc( StructBase ): # CObjDesc

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Camera Struct ' + uHex( 0x20 + args[1] )
		self.formatting = '>IHHHHHHHHHHIIfIffffff'
		self.fields = ( 'Name_Pointer',
						'Camera_Flags',		# 0x4
						'Projection_Type',
						'Viewport_Left',	# 0x8
						'Viewport_Right',
						'Viewport_Top',		# 0xC
						'Viewport_Bottom',
						'Scissor_Left',		# 0x10
						'Scissor_Right',
						'Scissor_Top',		# 0x14
						'Scissor_Bottom',
						'Eye_Position_WorldObj_Pointer', # 0x18
						'Interest_WorldObj_Pointer',	 # 0x1C
						'Roll',
						'UpVector_Pointer',	# 0x24
						'Near',
						'Far',
						'FieldOfView',		# 0x30
						'Aspect_Ratio',
						'Projection_Left',
						'Projection_Right'	# 0x3C
					)
		self.length = 0x40
		self._siblingsChecked = True


					# = ---------------------------------------------------- = #
					#  [   HSD Internal File Structure Classes (Specific)   ]  #
					# = ---------------------------------------------------- = #

class MapHeadObjDesc( StructBase ):

	""" Class for a stage file's "map_head" structure. """

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Map Head Struct ' + uHex( 0x20 + args[1] )
		self.formatting = '>IIIIIIIIIIII'		# In the context below, 'array' means multiple objects in one file structure.
		self.fields = ( 'General_Points_Array_Pointer',		# 0x0 - Points to an array of 0xC long objects
						'General_Points_Array_Count',		# 0x4 - These are all 1-indexed
						'Game_Objects_Array_Pointer',		# 0x8 - Points to an array of 0x34 long objects
						'Game_Objects_Array_Count',
						'Splines_Array_Pointer',			# 0x10 - Points to an array of 0x4 long objects (just pointers)
						'Splines_Array_Count',
						'Map_Lights_Array_Pointer',			# 0x18 - Points to an array of 0x8 long objects
						'Map_Lights_Array_Count',
						'Array_5_Pointer',					# 0x20 - SplineDesc?
						'Array_5_Count',
						'Material_Shadows_Array_Pointer',	# 0x28
						'Material_Shadows_Array_Count',
					)
		self.length = 0x30
		self.childClassIdentities = { 0: 'MapGeneralPointsArray', 2: 'MapGameObjectsArray' }
		self._siblingsChecked = True

	def getGeneralPoint( self, targetPointType ):

		""" Returns the given 'general point' (e.g. spawn points, stage borders, etc.), 
			if it exists within the General Points Arrays. Returns None if it doesn't. """

		pointsArrayOffset, pointsArrayCount = self.getValues()[:2]
		pointsArray = self.dat.initSpecificStruct( MapGeneralPointsArray, pointsArrayOffset, self.offset, entryCount=pointsArrayCount )
		joints = []

		for _, (jointGroupPtr, typesArrayPtr, arrayCount) in pointsArray.iterateEntries():
			typesArray = self.dat.initSpecificStruct( MapPointTypesArray, typesArrayPtr, pointsArrayOffset, entryCount=arrayCount )

		# jointGroupPtr, typesArrayPtr, arrayCount = pointsArray.getValues()[:3]
		# typesArray = self.dat.initSpecificStruct( MapPointTypesArray, typesArrayPtr, pointsArrayOffset, entryCount=arrayCount )

			for _, (jointIndex, pointType) in typesArray.iterateEntries():
				if pointType == targetPointType:
					# Target point found; initialize the joint group and get the offsets of the joints within it
					jointGroup = self.dat.initSpecificStruct( JointObjDesc, jointGroupPtr, pointsArrayOffset, entryCount=arrayCount )
					childOffset = jointGroup.getChildren()[0]
					childStruct = self.dat.initSpecificStruct( JointObjDesc, childOffset, jointGroupPtr )
					# points = childStruct.getSiblings()[:]
					# points.insert( 0, childStruct.offset )
					points = childStruct.getSiblings()

					# Ensure the index is valid and collect the appropriate joint struct
					if jointIndex < 1 or jointIndex > len( points ): # The joint index is 1-indexed
						print( 'Joint index for general point type {} out of range in type array 0x{:X} in {}'.format(pointType, 0x20+typesArrayPtr, self.dat.filename) )
						continue
					joints.append( self.dat.initSpecificStruct(JointObjDesc, points[jointIndex-1]) )

		return joints

	def getGeneralPoints( self ):

		""" Returns 'general points' (e.g. spawn points, stage borders, etc.), as a 
			multidimentional array. """

		pointsArrayOffset, pointsArrayCount = self.getValues()[:2]
		pointsArray = self.dat.initSpecificStruct( MapGeneralPointsArray, pointsArrayOffset, self.offset, entryCount=pointsArrayCount )
		pointTypeNames = MapPointTypesArray.enums['Point_Type']

		arrays = []

		for _, (jointGroupPtr, typesArrayPtr, arrayCount) in pointsArray.iterateEntries():
			jointGroup = self.dat.initSpecificStruct( JointObjDesc, jointGroupPtr, pointsArrayOffset, entryCount=arrayCount )
			typesArray = self.dat.initSpecificStruct( MapPointTypesArray, typesArrayPtr, pointsArrayOffset, entryCount=arrayCount )

			# Initialize the joint group and get the offsets of the points/joints
			childOffset = jointGroup.getChildren()[0]
			childStruct = self.dat.initSpecificStruct( JointObjDesc, childOffset, jointGroupPtr )
			# points = childStruct.getSiblings()[:]
			# points.insert( 0, childStruct.offset )
			points = childStruct.getSiblings()

			pointsInfo = []

			for arrayTypeIndex, (jointIndex, pointType) in typesArray.iterateEntries():
				if jointIndex < 1 or jointIndex > len( points ): # The joint index is 1-indexed
					print( 'Joint index for general point type {} out of range in type array 0x{:X} in {}'.format(pointType, 0x20+typesArrayPtr, self.dat.filename) )
					continue
				
				if jointIndex != arrayTypeIndex+1:
					# Interesting! (though it doesn't affect the outcome of this method)
					print( 'Found a general point index out of order; within type array 0x{:X} in {}'.format(0x20+typesArrayPtr, self.dat.filename) )

				jointStruct = self.dat.initSpecificStruct( JointObjDesc, points[jointIndex-1] )
				values = jointStruct.getValues()
				scale = values[8:11]
				scale = [ round(v) for v in scale ]

				# if scale != ( 1.0, 1.0, 1.0 ):
				# 	print( 'Found non-1.0 scale for a general point at 0x{:X} in {}: {}'.format(points[jointIndex-1], self.dat.filename, scale) )

				# Collect the X and Y coords of this joint
				pointName = pointTypeNames.get( pointType, 'Unknown Type ({})'.format(pointType) )
				pointsInfo.append( (jointIndex, pointType, pointName, (values[11], values[12]), scale) )

			arrays.append( pointsInfo )

		return arrays


class MapGeneralPointsArray( TableStruct ):

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'General Points Array ' + uHex( 0x20 + args[1] )

		if self.entryCount == -1:
			# Check the parent's General_Points_Array_Count to see how many elements should be in this array structure
			parentOffset = self.getAnyDataSectionParent()
			parentStruct = self.dat.initSpecificStruct( MapHeadObjDesc, parentOffset )
			self.entryCount = parentStruct.getValues()[1]

		self.fields = ( 'Map_Joint_Group_Parent_Pointer',	# Has a child with 'n' siblings
						'Map_Point_Types_Array_Pointer',
						'Map_Point_Types_Array_Count'		# 1-indexed
					  )

		# Use the above info to dynamically rebuild this struct's properties
		self.formatting = '>III'
		self.length = 0xC

		TableStruct.__init__( self )

		for i in range( 0, len(self.fields), self.entryValueCount ):
			self.childClassIdentities[i] = 'JointObjDesc'
			self.childClassIdentities[i+1] = 'MapPointTypesArray'


class MapPointTypesArray( TableStruct ):

	enums = { 'Point_Type': OrderedDict([
				( 0, 'Player 1 Spawn' ), ( 1, 'Player 2 Spawn' ), ( 2, 'Player 3 Spawn' ), ( 3, 'Player 4 Spawn' ), 
				( 4, 'Player 1 Respawn' ), ( 5, 'Player 2 Respawn' ), ( 6, 'Player 3 Respawn' ), ( 7, 'Player 4 Respawn' ), 

				( 127, 'Item Spawn 1' ), ( 128, 'Item Spawn 2' ), ( 129, 'Item Spawn 3' ), ( 130, 'Item Spawn 4' ), 
				( 131, 'Item Spawn 5' ), ( 132, 'Item Spawn 6' ), ( 133, 'Item Spawn 7' ), ( 134, 'Item Spawn 8' ), 
				( 135, 'Item Spawn 9' ), ( 136, 'Item Spawn 10' ), ( 137, 'Item Spawn 11' ), ( 138, 'Item Spawn 12' ), 
				( 139, 'Item Spawn 13' ), ( 140, 'Item Spawn 14' ), ( 141, 'Item Spawn 15' ), ( 142, 'Item Spawn 16' ), 
				( 143, 'Item Spawn 17' ), ( 144, 'Item Spawn 18' ), ( 145, 'Item Spawn 19' ), ( 146, 'Item Spawn 20' ), 

				( 148, 'Delta Camera Angle' ), 
				( 149, 'Top-Left Camera Limit' ), ( 150, 'Bottom-Right Camera Limit' ), ( 151, 'Top-Left Blast-Zone' ), ( 152, 'Bottom-Right Blast-Zone' ), 
				( 153, 'Stage Exit' ), # Seen as exit points for stages such as All-Star Heal and F-Zero Grand Prix

				( 199, 'Target 1' ), ( 200, 'Target 2' ), ( 201, 'Target 3' ), ( 202, 'Target 4' ), ( 203, 'Target 5' ), 
				( 204, 'Target 6' ), ( 205, 'Target 7' ), ( 206, 'Target 8' ), ( 207, 'Target 9' ), ( 208, 'Target 10' )
			]) }

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Point Types Array ' + uHex( 0x20 + args[1] )

		# Check how many elements should be in this array structure
		parentOffset = self.getAnyDataSectionParent()
		parentStruct = self.dat.initSpecificStruct( MapGeneralPointsArray, parentOffset )
		# parentValues = parentStruct.getValues()
		# for i, value in enumerate( parentValues ):
		# 	if value == self.offset:
		# 		self.entryCount = parentValues[i+1]
		# 		break
		for _, (_, typesArrayPtr, arrayCount) in parentStruct.iterateEntries():
			if typesArrayPtr == self.offset:
				self.entryCount = arrayCount
				break

		# Use the above info to dynamically rebuild this struct's properties
		self.formatting = '>HH'
		self.fields = ( 'Joint_Object_Index', 'Point_Type' )
		self.length = 4

		TableStruct.__init__( self )
		self._childrenChecked = True


class MapGameObjectsArray( TableStruct ):	# Makes up an array of GOBJs (a.k.a. GroupObj/GenericObj)

	# Some details on this structure can be found here: https://smashboards.com/threads/melee-dat-format.292603/post-23774149

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Game Objects Array ' + uHex( 0x20 + args[1] )
		self.fields = (	'Root_Joint_Pointer',				# 0x0
						'Joint_Anim_Array_Pointer',			# 0x4
						'Material_Anim_Array_Pointer',		# 0x8
						'Shape_Anim_Array_Pointer',			# 0xC
						'Camera_Pointer',					# 0x10
						'Unknown_0x14_Pointer',				# 0x14
						'Lights_Array_Pointer',				# 0x18
						'Fog_Struct_Pointer',				# 0x1C
						'Coll_Anim_Enable_Array_Pointer',	# 0x20		Points to a null-terminated array of 6-byte elements. Relates to moving collision links
						'Coll_Anim_Enable_Array_Count',		# 0x24
						'Anim_Loop_Enable_Array_Pointer',	# 0x28		Points to an array of 1-byte booleans, for enabling animation loops
						'Shadow_Enable_Array_Pointer',		# 0x2C		Points to a null-terminated halfword array
						'Shadow_Enable_Array_Count',		# 0x30
					)
		self.formatting = '>IIIIIIIIIIIII'
		self.length = 0x34

		# Check the parent's Game_Objects_Array_Count to see how many elements should be in this array structure
		parentOffset = self.getAnyDataSectionParent()
		parentStruct = self.dat.initSpecificStruct( MapHeadObjDesc, parentOffset )
		self.entryCount = parentStruct.getValues()[3]

		TableStruct.__init__( self )

		for i in range( 0, len(self.fields), self.entryValueCount ):
			self.childClassIdentities[i] = 'JointObjDesc'
			self.childClassIdentities[i+1] = 'JointAnimStructArray'
			#self.childClassIdentities[i+2] = 'MatAnimJointDesc'
			#self.childClassIdentities[i+4] = 'CameraObjDesc'
			self.childClassIdentities[i+8] = 'MapCollAnimEnableArray'
			self.childClassIdentities[i+10] = 'MapAnimLoopEnableArray'
			self.childClassIdentities[i+11] = 'MapShadowEnableArray'


class MapCollAnimEnableArray( StructBase ):

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Collision Animation Enable Array ' + uHex( 0x20 + args[1] )
		self._siblingsChecked = True
		self._childrenChecked = True

		# Check how many elements should be in this array structure
		parentOffset = self.getAnyDataSectionParent()
		parentStruct = self.dat.initSpecificStruct( MapGameObjectsArray, parentOffset )
		getNextValue = False
		for parentValue in parentStruct.getValues():
			if getNextValue:
				self.entryCount = parentValue
				break
			elif parentValue == self.offset: getNextValue = True

		# Use the above info to dynamically rebuild this struct's properties
		self.formatting = '>' + ( 'HHH' * self.entryCount ) + 'H' # +1 null terminator at the end
		fields = [ 'Joint_Object_Index', '', 'Collision_Object_Index' ]
		self.fields = tuple( fields * self.entryCount + ['Null terminator'] )
		self.length = 6 * self.entryCount + 2


class MapAnimLoopEnableArray( StructBase ):

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Animation Loop Enable Array ' + uHex( 0x20 + self.offset )
		self._siblingsChecked = True
		self._childrenChecked = True

		# Check how many elements should be in this array structure
		self.entryCount = self.dat.getStructLength( self.offset )

		# Use the above info to dynamically rebuild this struct's properties
		self.formatting = '>' + '?' * self.entryCount # +1 null terminator at the end?
		self.fields = ( 'JObj_Index_Anim._Enable', ) * self.entryCount	# Simply an array of bools
		self.length = self.entryCount


class MapShadowEnableArray( StructBase ): # Only found in Ness' BTT stage?

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Shadow Enable Array ' + uHex( 0x20 + self.offset )
		self._siblingsChecked = True
		self._childrenChecked = True

		# Check how many elements should be in this array structure
		parentOffset = self.getAnyDataSectionParent()
		parentStruct = self.dat.initSpecificStruct( MapGameObjectsArray, parentOffset )
		getNextValue = False
		for parentValue in parentStruct.getValues():
			if getNextValue:
				self.entryCount = parentValue
				break
			elif parentValue == self.offset: getNextValue = True

		# Use the above info to dynamically rebuild this struct's properties
		self.formatting = '>' + ( 'H' * self.entryCount ) + 'H' # +1 null terminator at the end
		self.fields = tuple( ['Joint_Object_Index'] * self.entryCount + ['Null terminator'] )
		self.length = 2 * self.entryCount + 2


class MapCollisionData( StructBase ):

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Collision Data Struct ' + uHex( 0x20 + args[1] )
		self.formatting = '>IIIIHHHHHHHHHHII'
		self.fields = ( 'Spot_Table_Pointer',				# 0x0  - Each entry is 8 bytes
						'Spot_Table_Entry_Count',			# 0x4
						'Link_Table_Pointer',				# 0x8  - Each entry is 0x10 bytes
						'Link_Table_Entry_Count',			# 0xC
						'First_Top_Link_Index',				# 0x10
						'Top_Links_Count',					# 0x12
						'First_Bottom_Link_Index',			# 0x14
						'Bottom_Links_Count',				# 0x16
						'First_Right_Link_Index',			# 0x18
						'Right_Links_Count',				# 0x1A
						'First_Left_Link_Index',			# 0x1C
						'Left_Links_Count',					# 0x1E
						'Dynamic_Links_Index',				# 0x20
						'Dynamic_Link_Count',				# 0x22
						'Area_Table_Pointer',				# 0x24 - Each entry is 0x28 bytes
						'Area_Table_Entry_Count'			# 0x28
				)
		self.length = 0x2C
		self.childClassIdentities = { 0: 'MapSpotTable', 2: 'MapLinkTable', 14: 'MapAreaTable' }
		self._siblingsChecked = True


class MapSpotTable( StructBase ):

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Spot Table ' + uHex( 0x20 + args[1] )
		self._siblingsChecked = True
		self._childrenChecked = True

		# Check the parent's General_Points_Array_Count to see how many elements should be in this array structure
		parentOffset = self.getAnyDataSectionParent()
		parentStruct = self.dat.initSpecificStruct( MapCollisionData, parentOffset )
		self.entryCount = parentStruct.getValues()[1]

		# Use the above info to dynamically rebuild this struct's properties
		self.formatting = '>' + ( 'ff' * self.entryCount )
		self.fields = ( 'Spot_X_Coord', 'Spot_Y_Coord' ) * self.entryCount
		self.length = 8 * self.entryCount

	def getVertices( self ):

		""" Returns a list of vertex objects. """

		valueIterator = iter( self.getValues() )
		return [ Vertex((xCoord, yCoord, 0)) for xCoord, yCoord in zip(valueIterator, valueIterator) ]


class MapLinkTable( StructBase ):

	flags = { 'Physics_Interaction_Flags': OrderedDict([
				( '1<<0', 'Top' ),		# 1
				( '1<<1', 'Bottom' ), 	# 2
				( '1<<2', 'Right' ),	# 4
				( '1<<3', 'Left' ),		# 8
				( '1<<4', 'Disabled' )	# 16
			]),
			  'Ground_Property_Flags': OrderedDict([
			  	( '1<<0', 'Drop-through' ),
			  	( '1<<1', 'Ledge-grabbable' ),
			  	( '1<<2', 'Dynamic' )
			]) }
	
	enums = { 'Material_Enum': OrderedDict([
				( 0, 'Basic' ), ( 1, 'Rock' ), ( 2, 'Grass' ),
				( 3, 'Dirt' ), ( 4, 'Wood' ), ( 5, 'LightMetal' ),
				( 6, 'HeavyMetal' ), ( 7, 'UnkFlatZone' ), ( 8, 'AlienGoop' ),
				( 9, 'Unknown9' ), ( 10, 'Water' ), ( 11, 'Unknown11' ),
				( 12, 'Glass' ), ( 13, 'GreatBay' ), ( 14, 'Unknown14' ),
				( 15, 'Unknown15' ), ( 16, 'FlatZone' ), ( 17, 'Unknown17' ),
				( 18, 'Checkered' )
			]) }

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Link Table ' + uHex( 0x20 + args[1] )
		self._siblingsChecked = True
		self._childrenChecked = True

		# Check the parent's General_Points_Array_Count to see how many elements should be in this array structure
		parentOffset = self.getAnyDataSectionParent()
		parentStruct = self.dat.initSpecificStruct( MapCollisionData, parentOffset )
		self.entryCount = parentStruct.getValues()[3]

		fields = (
			'Starting_Spot_Index', 
			'Ending_Spot_Index',
			'Previous_Link_Index',		# -1 if unused
			'Next_Link_Index',			# -1 if unused
			'First_Virtual_Link_Index',
			'Second_Virtual_Link_Index',
			'Padding',
			'Physics_Interaction_Flags',
			'Ground_Property_Flags',
			'Material_Enum'
		)

		# Use the above info to dynamically rebuild this struct's properties
		self.formatting = '>' + ( 'hhhhhhBBBB' * self.entryCount )
		self.fields = fields * self.entryCount
		self.length = 0x10 * self.entryCount

	def getFaces( self ):

		""" Groups the structure's values into groups of 10, then iterates over them to 
			build collision link objects. Returns a list of CollissionSurface objects. """

		self.getValues()
		surfaces = []
		index = 0

		iterReference = iter( self.values )
		iterRefs = [ iterReference ] * 10 # Making multiple references to the same iterator

		for i1, i2, i3, i4, i5, i6, _, physicsFlags, propertyFlags, materialFlags in zip( *iterRefs ):
			link = ( i1, i2 )
			allSpotIndices = ( i1, i2, i3, i4, i5, i6 )
			surfaces.append( CollissionSurface( link, allSpotIndices, physicsFlags, propertyFlags, materialFlags, index ) )
			index += 1

		return surfaces


class CollissionSurface:

	def __init__( self, vertexIndices, allSpotIndices, physicsFlags, propertyFlags, materialFlags, index, color='' ):
		self.points = vertexIndices # The main start and stop spot indices
		self.allSpotIndices = allSpotIndices
		self.physics = physicsFlags
		self.property = propertyFlags
		self.material = MapLinkTable.enums['Material_Enum'].get( materialFlags, 'Unknown' )
		self.index = index
		self.renderObj = None 

		if not color:
			self.colorByPhysics()
		else:
			self.fill = self.outline = color

	def colorByPhysics( self ):

		""" These are the colors used by vanilla Melee, in Debug Mode (excluding the color for "disabled"). """

		if self.physics & 1: # Top
			self.fill = self.outline = '#c0c0c0' # Gray
		elif self.physics & 2: # Bottom (Ceiling)
			self.fill = self.outline = '#c08080' # Light red
		elif self.physics & 4: # Right
			self.fill = self.outline = '#80c080' # Light green
		elif self.physics & 8: # Left
			self.fill = self.outline = '#8080c0' # Light blue
		else: # Disabled (bit 4 should be set)
			self.fill = self.outline = '#909090' # Darker Gray (arbitrary color, not from in vMelee)


class ColCalcArea:
	
	""" Collision Calculation Area. Used to reduce the amount of 
		processing needed for collision calculations. """

	def __init__( self, vertexIndices ):
		self.points = vertexIndices 	# (bottomLeftX, bottomLeftY, topRightX, topRightY)
		self.fill = ''
		self.outline = 'red'


class MapAreaTable( StructBase ): # A.k.a. Line Groups

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Area Table ' + uHex( 0x20 + args[1] )
		self._siblingsChecked = True
		self._childrenChecked = True

		# Check the parent's array count to see how many elements should be in this structure
		parentOffset = self.getAnyDataSectionParent()
		parentStruct = self.dat.initSpecificStruct( MapCollisionData, parentOffset )
		self.entryCount = parentStruct.getValues()[15]
		#print 'entry count for Area Table:', hex( self.entryCount ), 'length:', hex(0x28*self.entryCount), 'apparent length:', hex(self.dat.getStructLength( self.offset ))

		fields = (  'Top_Link_Index', 
					'Top_Links_Count',
					'Bottom_Link_Index', 
					'Bottom_Links_Count',
					'Right_Link_Index', 
					'Right_Links_Count',
					'Left_Link_Index', 
					'Left_Links_Count',
					'Dynamic_Link_Index?',		# <- why not -1 for non-entries?
					'Dynamic_Links_Count?',		# <- why not -1 for non-entries?
					'Bottom-left_X_Coord',
					'Bottom-left_Y_Coord',
					'Top-right_X_Coord',
					'Top-right_Y_Coord',
					'Vertex_Start',
					'Vertex_Count'
				)

		# Use the above info to dynamically rebuild this struct's properties
		self.formatting = '>' + ( 'HHHHHHHHHHffffHH' * self.entryCount )
		self.fields = fields * self.entryCount
		self.length = 0x28 * self.entryCount

	def getAreas( self ):

		""" Groups the structure's values into groups of 15, then iterates over them to build area objects. """

		self.getValues()
		areas = []

		iterRefs = [ iter(self.values) ] * 16 # Making multiple references to the same iterator

		for tLi, tLc, bLi, bLc, rLi, rLc, lLi, lLc, dLi, dLc, botLeftX, botLeftY, topRightX, topRightY, vS, vC in zip( *iterRefs ):
			areas.append( ColCalcArea(( botLeftX, -botLeftY, topRightX, -topRightY )) )

		return areas


class MapGroundParameters( StructBase ): # grGroundParam

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Stage Parameters ' + uHex( 0x20 + args[1] )
		self.formatting = '>fIIIIIfffffIIIIffffIffffffHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHIIIIIIIIIII'
		self.fields = ( 'Stage_Scaling',
						'Shadow_Intensity',
						'Camera_FieldOfView',
						'Min._Camera_Distance',
						'Max_Camera_Distance',			# 0x10
						'Pitch_Scaling_(Vertical_Rotation)',
						'Pitch_Bias_(Vertical_Rotation)',
						'Yaw_Bias_(Horizontal_Rotation)',
						'Camera_Fixation',				# 0x20
						'Bubble_Multiplier',
						'Camera_Speed_Smoothness',					# Higher value results in tighter control
						'',
						'Pause_Min_Zoom',			# 0x30
						'Pause_Initial_Zoom',
						'Pause_Max_Zoom',
						'Pause_Max_Angle_Up',
						'Pause_Max_Angle_Left',		# 0x40
						'Pause_Max_Angle_Right',
						'Pause_Max_Angle_Down',
						'Fixed_Camera_Mode_Bool',		# 0x4C (1=Enable, 0=Normal Camera)
						'Fixed_Camera_X-Axis',	
						'Fixed_Camera_Y-Axis',
						'Fixed_Camera_Z-Axis',
						'Fixed_Camera_FoV',
						'Fixed_Camera_Vertical_Angle',	# 0x60
						'Fixed_Camera_Horizontal_Angle',
						'',		'',		'',		'',		# 0x68 - First halfword
						'',		'',		'',		'',
						'',		'',		'',		'',
						'',		'',		'',		'',
						'',		'',		'',		'',
						'',		'',		'',		'',
						'',		'',		'',		'',
						'',		'',		'',		'',
						'',		'',		'',		'',		# Last halfword
						'Music_Table_Pointer',			# 0xB0
						'Music_Table_Entry_Count',
						'RGBA_Bubble_Top-left',			# 0xB8
						'RGBA_Bubble_Top-middle',
						'RGBA_Bubble_Top-right',
						'RGBA_Bubble_Sides-top',
						'RGBA_Bubble_Sides-middle',
						'RGBA_Bubble_Sides-bottom',
						'RGBA_Bubble_Bottom-left',
						'RGBA_Bubble_Bottom-middle',
						'RGBA_Bubble_Bottom-right'
					)
		self.length = 0xDC
		self.childClassIdentities = { 62: 'MapMusicTable' }
		self._siblingsChecked = True


class MapMusicTable( TableStruct ):

	enums = { 'Song_Behavior': OrderedDict([
				( 0, 'Play Main Music, Unless Holding L' ),
				( 1, 'Main Music, or 1/12 Chance of Alt-Music' ),
				( 2, 'Main Music, or Custom Chance of Alt-Music' ),
				( 3, 'Marth Conditional' ),
				( 4, 'Y. Link Conditional' ),
				( 5, 'Mach Rider Conditional' ),
				( 6, 'All Chars Unlocked Conditional' ),
				( 7, 'All Stages Unlocked Conditional' ),
				( 8, 'Only Use Main Music' )
			]) }
	
	songBehaviorDescriptions = {
		0: 'Play main music, or if a player holds L during stage load, the alt-music plays.',
		1: ( 'Main music plays by default, with 1/12 (~8.33%) chance for alt music. '
			 'Or if a player holds L during stage load, the alt-music plays.' ),
		2: ( "Main music plays by default, with 'Alt. Music % Chance' given to play the alt-music. "
			 "Or if a player holds L during stage load, the alt-music plays." ),
		3: ( "Main Music plays by default. However, if Marth is unlocked, the 'Alt. Music % Chance' " 
			 "is given to play the alt-music. Or if a player holds L during stage load, the alt-music plays." ),
		4: ( "Main Music plays by default. However, if Y. Link is unlocked, the 'Alt. Music % Chance' " 
			 "is given to play the alt-music. Or if a player holds L during stage load, the alt-music plays." ),
		5: ( "Main Music plays by default. However, if the Mach Rider trophy is unlocked, the 'Alt. Music % Chance' " 
			 "is given to play the alt-music. Or if a player holds L during stage load, the alt-music plays." ),
		6: ( "Main Music plays by default. However, if all characters are unlocked, the 'Alt. Music % Chance' " 
			 "is given to play the alt-music. Or if a player holds L during stage load, the alt-music plays." ),
		7: ( "Main Music plays by default. However, if all stages are unlocked, the 'Alt. Music % Chance' " 
			 "is given to play the alt-music. Or if a player holds L during stage load, the alt-music plays." ),
		8: 'Only the main music will ever play.'
	}

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Music Table ' + uHex( 0x20 + args[1] )
		self.formatting = '>IiiiiHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHI'
		self.fields = ( 'External_Stage_ID', 
						'Background_Music_ID',			# 0x4 - Main Song (for this, and each song below, -1 (FFFFFFFF) means unused)
						'Alt_Background_Music_ID',
						'SSD_Background_Music_ID',		# 0xC - Super Sudden Death Main Song
						'SSD_Alt_Background_Music_ID',
						'Song_Behavior',				# 0x14
						'Alt_Music_Percent_Chance', 
						'',		'',						# 0x18 - halfwords from here on (besides padding)
						'',		'',
						'',		'',
						'',		'',
						'',		'',
						'',		'',
						'',		'',
						'',		'',
						'',		'',
						'',		'',
						'',		'',
						'',		'',
						'',		'',
						'',		'',
						'',		'',
						'',		'',
						'',		'',
						'',		'',
						'Padding'
					)
		self.length = 0x64
		self._childrenChecked = True

		# Check the parent's Music_Table_Entry_Count to see how many entries should be in this table structure
		parentOffset = self.getAnyDataSectionParent()
		parentStruct = self.dat.initSpecificStruct( MapGroundParameters, parentOffset )
		self.entryCount = parentStruct.getValues()[63]
		#print 'entry count for Area Table:', hex( self.entryCount ), 'length:', hex(0x64*self.entryCount), 'apparent length:', hex(self.dat.getStructLength( self.offset ))

		# Reinitialize this as a Table Struct to duplicate this entry struct for all enties in this table
		TableStruct.__init__( self )
		#super( MapMusicTable, self ).__init__( self ) # probably should use this instead


class CharSelectScreenDataTable( StructBase ):

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Character Select Menu Data Table ' + uHex( 0x20 + args[1] )
		self.formatting = '>IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII'
		self.fields = ( 'Unknown_Pointer',
						'Unknown_Pointer',
						'Unknown_Pointer',
						'Unknown_Pointer',
						'Background_Model_Joint_Pointer',	# 0x10
						'Background_Animation_Pointer',
						'',
						'',
						'Hand_Model_Joint_Pointer',			# 0x20
						'',
						'Hand_Material_Anim._Pointer',
						'',
						'Token_Model_Joint_Pointer',		# 0x30
						'',
						'Token_Material_Anim._Pointer',
						'',
						'Menu_Model_Joint_Pointer',			# 0x40
						'Menu_Model_Animation_Pointer',
						'Menu_Material_Anim._Pointer',
						'',
						'Press_Start_Model_Joint_Pointer',	# 0x50
						'Press_Start_Animation_Pointer',
						'Press_Start_Mat._Anim._Pointer',
						'',
						'Debug_Camera_Model_Joint_Pointer',	# 0x60
						'',
						'Debug_Camera_Mat._Anim._Pointer',
						'',
						'1P_Mode_Menu_Model_Joint_Pointer',	# 0x70
						'1P_Mode_Menu_Animation_Pointer',
						'1P_Mode_Menu_Mat._Anim._Pointer',
						'',
						'1P_Mode_Options_Model_Pointer',	# 0x80
						'',
						'',
						'',
						'CSP_Model_Joint_Pointer',			# 0x90
						'',
						'CSP_Material_Anim._Pointer',
						''
					)
		self.length = 0xA0
		self.childClassIdentities = { 4: 'JointObjDesc', 5: 'JointAnimationDesc', # Background
								8: 'JointObjDesc', 10: 'MatAnimJointDesc',  # Hand
								12: 'JointObjDesc', 14: 'MatAnimJointDesc',  # Token
								16: 'JointObjDesc', 17: 'JointAnimationDesc', 18: 'MatAnimJointDesc', # Menu Model
								20: 'JointObjDesc', 21: 'JointAnimationDesc', 22: 'MatAnimJointDesc', # 'Press Start' overlay
								24: 'JointObjDesc', 26: 'MatAnimJointDesc',  # Debug Camera
								28: 'JointObjDesc', 29: 'JointAnimationDesc', 30: 'MatAnimJointDesc', # 1P Mode Menu Model
								32: 'JointObjDesc', 		# 1P Mode Menu Options
								36: 'JointObjDesc', 38: 'MatAnimJointDesc' } # CSPs
		self._siblingsChecked = True


class JointAnimStructArray( StructBase ):

	""" Null-terminated array of pointers to JointAnimationDesc structures. """

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Joint Animation Struct Array ' + uHex( 0x20 + args[1] )
		self._siblingsChecked = True

		# Check the length of the struct to see how many elements should be in this structure
		structLength = self.dat.getStructLength( self.offset )
		self.entryCount = structLength / 4

		# Use the above info to dynamically build this struct's basic properties
		self.formatting = '>' + ( 'I' * self.entryCount )
		self.fields = ( 'Joint_Anim._Struct_Pointer', ) * ( self.entryCount - 1 ) + ( 'Null Terminator', )
		self.length = structLength

		for i in range( 0, self.entryCount - 1 ):
			self.childClassIdentities[i] = 'JointAnimationDesc'


class JointAnimationDesc( StructBase ): # A.k.a. Joint Animation Joint

	animationTracks = {
		1: 'HSD_A_J_ROTX', 2: 'HSD_A_J_ROTY', 3: 'HSD_A_J_ROTZ', 4: 'HSD_A_J_PATH', # Rotation, Path
		5: 'HSD_A_J_TRAX', 6: 'HSD_A_J_TRAY', 7: 'HSD_A_J_TRAZ', # Translation
		8: 'HSD_A_J_SCAX', 9: 'HSD_A_J_SCAY', 0xA: 'HSD_A_J_SCAZ', 0xB: 'HSD_A_J_NODE', 0xC: 'HSD_A_J_BRANCH',  # Scale, Node, Branch
		0x14: 'HSD_A_J_SETBYTE0', 0x15: 'HSD_A_J_SETBYTE1', 0x16: 'HSD_A_J_SETBYTE2', 0x17: 'HSD_A_J_SETBYTE3', 0x18: 'HSD_A_J_SETBYTE4', 
		0x19: 'HSD_A_J_SETBYTE5', 0x1A: 'HSD_A_J_SETBYTE6', 0x1B: 'HSD_A_J_SETBYTE7', 0x1C: 'HSD_A_J_SETBYTE8', 0x1D: 'HSD_A_J_SETBYTE9', 
		0x1E: 'HSD_A_J_SETFLOAT0', 0x1F: 'HSD_A_J_SETFLOAT1', 0x20: 'HSD_A_J_SETFLOAT2', 0x21: 'HSD_A_J_SETFLOAT3', 0x22: 'HSD_A_J_SETFLOAT4', 
		0x23: 'HSD_A_J_SETFLOAT5', 0x24: 'HSD_A_J_SETFLOAT6', 0x25: 'HSD_A_J_SETFLOAT7', 0x26: 'HSD_A_J_SETFLOAT8', 0x27: 'HSD_A_J_SETFLOAT9', 
	}

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Joint Animation Struct ' + uHex( 0x20 + args[1] )
		self.formatting = '>IIIII'
		self.fields = ( 'Child_Pointer',
						'Next_Sibling_Pointer',
						'Anim._Object_Pointer',
						'',
						''
					)
		self.length = 0x14
		self.childClassIdentities = { 0: 'JointAnimationDesc', 1: 'JointAnimationDesc', 2: 'AnimationObjectDesc' }

	def validated( self, deducedStructLength=-1 ):
		prelimCheck = super( JointAnimationDesc, self ).validated( False, deducedStructLength )
		if not prelimCheck: return False

		# Check for and initialize a child Animation Obj, if present
		animObjOffset = self.getValues()[2]

		if animObjOffset == 0: # Can't glean any more here (valid so far)
			self.provideChildHints()
			return True
		else:
			if not animObjOffset in self.dat.structs:
				self.dat.structs[animObjOffset] = 'AnimationObjectDesc' # Adding a hint to permit this struct to be created even if it's all null data
			animObj = self.dat.initSpecificStruct( AnimationObjectDesc, animObjOffset, self.offset, printWarnings=False )
			if not animObj: return False

			self.provideChildHints()
			return True


class MatAnimJointDesc( StructBase ):

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Material Animation Joint ' + uHex( 0x20 + args[1] )
		self.formatting = '>III'
		self.fields = ( 'Child_Pointer', 'Next_Sibling_Pointer', 'Mat._Anim._Struct_Pointer' )
		self.length = 0xC
		self.childClassIdentities = { 0: 'MatAnimJointDesc', 1: 'MatAnimJointDesc', 2: 'MatAnimDesc' }

	def validated( self, deducedStructLength=-1 ):
		prelimCheck = super( MatAnimJointDesc, self ).validated( False, deducedStructLength )
		if not prelimCheck: return False

		# Check for and initialize a child Animation Obj, if present
		childMatAnimOffset, _, matAnimObjOffset = self.getValues()

		if childMatAnimOffset != 0 or self.offset in self.dat.pointerOffsets:
			# Try to initialize the child for further validation
			if not childMatAnimOffset in self.dat.structs:
				self.dat.structs[childMatAnimOffset] = 'MatAnimJointDesc' # Adding a hint to permit this struct to be created even if it's all null data
			matAnimObj = self.dat.initSpecificStruct( MatAnimJointDesc, childMatAnimOffset, self.offset, printWarnings=False )
			if not matAnimObj:
				#print 'Struct', hex(0x20+self.offset) , 'invalidated as', self.__class__.__name__, 'due to child at', hex(0x20+childMatAnimOffset)
				return False

		if matAnimObjOffset != 0 or self.offset + 8 in self.dat.pointerOffsets:
			# Try to initialize the child for further validation
			if not matAnimObjOffset in self.dat.structs:
				self.dat.structs[matAnimObjOffset] = 'MatAnimDesc' # Adding a hint to permit this struct to be created even if it's all null data
			matAnimObj = self.dat.initSpecificStruct( MatAnimDesc, matAnimObjOffset, self.offset, printWarnings=False )
			if not matAnimObj:
				#print 'Struct', hex(0x20+self.offset) , 'invalidated as', self.__class__.__name__, 'due to child at', hex(0x20+matAnimObjOffset)
				return False
		
		self.provideChildHints()
		return True


class MatAnimDesc( StructBase ):

	animationTracks = {
		1: 'HSD_A_M_AMBIENT_R', 2: 'HSD_A_M_AMBIENT_G', 3: 'HSD_A_M_AMBIENT_B', # Ambience RGB
		4: 'HSD_A_M_DIFFUSE_R', 5: 'HSD_A_M_DIFFUSE_G', 6: 'HSD_A_M_DIFFUSE_B', # Diffusion RGB
		7: 'HSD_A_M_SPECULAR_R', 8: 'HSD_A_M_SPECULAR_G', 9: 'HSD_A_M_SPECULAR_B', 0xA: 'HSD_A_M_ALPHA', # Specular RGB, Transparency
	}

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Material Animation Struct ' + uHex( 0x20 + args[1] )
		self.formatting = '>IIII'
		self.fields = ( 'Next_Sibling_Pointer', 'Anim._Object_Pointer', 'Texture_Anim._Pointer', 'Render_Anim._Pointer' )
		self.length = 0x10
		self.childClassIdentities = { 0: 'MatAnimDesc', 1: 'AnimationObjectDesc', 2: 'TexAnimDesc' }

	def validated( self, deducedStructLength=-1 ):
		prelimCheck = super( MatAnimDesc, self ).validated( False, deducedStructLength )
		if not prelimCheck: return False

		# Check for and initialize a child Animation Obj, if present
		animObjOffset = self.getValues()[1]

		if animObjOffset == 0: # Can't glean any more here (valid so far)
			self.provideChildHints()
			return True
		else:
			if not animObjOffset in self.dat.structs:
				self.dat.structs[animObjOffset] = 'AnimationObjectDesc' # Adding a hint to permit this struct to be created even if it's all null data
			animObj = self.dat.initSpecificStruct( AnimationObjectDesc, animObjOffset, self.offset, printWarnings=False )
			if not animObj:
				#print self.name, 'invalidated as', self.__class__.__name__, 'due to child at', hex(0x20+animObjOffset)
				return False

			self.provideChildHints()
			return True


class AnimationObjectDesc( StructBase ):

	flags = { 'Animation_Flags': OrderedDict([
				( '1<<26', 'ANIM_REWINDED' ),
				( '1<<27', 'FIRST_PLAY' ),
				( '1<<28', 'NO_UPDATE' ),
				( '1<<29', 'ANIM_LOOP' ),
				( '1<<30', 'NO_ANIM' )
			]) }

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Animation Object ' + uHex( 0x20 + args[1] )
		self.formatting = '>IfII'
		self.fields = ( 'Animation_Flags', 'End_Frame', 'Frame_Object_Pointer', 'Object_ID' )
		self.length = 0x10
		self.childClassIdentities = { 2: 'FrameObjDesc' }
		self._siblingsChecked = True


class TexAnimDesc( StructBase ):

	animationTracks = {
		1: 'HSD_A_T_TIMG', 2: 'HSD_A_T_TRAU', 3: 'HSD_A_T_TRAV', 4: 'HSD_A_T_SCAU', 5: 'HSD_A_T_SCAV', 
		6: 'HSD_A_T_ROTX', 7: 'HSD_A_T_ROTY', 8: 'HSD_A_T_ROTZ', 9: 'HSD_A_T_BLEND', 0xA: 'HSD_A_T_TCLT', 
	}

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Texture Animation Struct ' + uHex( 0x20 + args[1] )
		self.formatting = '>IIIIIHH'
		self.fields = ( 'Next_Sibling_Pointer', 
						'GXTexMapID', 
						'Anim._Object_Pointer',
						'Image_Header_Array_Pointer',
						'Palette_Header_Array_Pointer',
						'Image_Header_Array_Count',
						'Palette_Header_Array_Count'
					)
		self.length = 0x18
		self.childClassIdentities = { 0: 'TexAnimDesc', 2: 'AnimationObjectDesc', 3: 'ImageHeaderArray', 4: 'PaletteHeaderArray' }


class FrameObjDesc( StructBase ):

	# Great detail on this structure can be found here: https://smashboards.com/threads/melee-dat-format.292603/post-23487048

	dataTypes = {   0: ( 'Float', '>f', 4 ),
					1: ( 'Signed Halfword', '<h', 2 ), # Bytes reversed (little-endian)
					2: ( 'Unsigned Halfword', '<H', 2 ), # Bytes reversed (little-endian)
					3: ( 'Signed Byte', 'b', 1 ),
					4: ( 'Unsigned Byte', 'B', 1 ) }

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Frame Object ' + uHex( 0x20 + args[1] )
		self.formatting = '>IIfBBBBI'
		self.fields = ( 'Next_Sibling_Pointer',
						'Data_String_Length',
						'Start_Frame',
						'Track_Type',
						'Data_Type_and_Scale',
						'Slope_Data_Type_and_Scale',
						'Padding',
						'Data_String_Pointer'
					)
		self.length = 0x14
		self.childClassIdentities = { 0: 'FrameObjDesc', -1: 'FrameDataBlock' }


class ImageHeaderArray( StructBase ):

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Image Data Header Array ' + uHex( 0x20 + args[1] )
		self._siblingsChecked = True

		# Check the parent's array count to see how many elements should be in this structure
		parentOffset = self.getAnyDataSectionParent()
		parentStruct = self.dat.initSpecificStruct( TexAnimDesc, parentOffset )
		#assert parentOffset, 'Unable to initialize the parent struct of ' + self.name + ' (' + hex(0x20+parentOffset) + ')'
		#print 'initialized a', parentStruct.__class__.__name__, ' parent for', self.name
		self.entryCount = parentStruct.getValues()[-2]

		# Use the above info to dynamically build this struct's basic properties
		self.formatting = '>' + ( 'I' * self.entryCount )
		self.fields = ( 'Image_Header_Pointer', ) * self.entryCount
		self.length = 4 * self.entryCount

		for i in range( 0, self.entryCount ):
			self.childClassIdentities[i] = 'ImageObjDesc'


class PaletteHeaderArray( StructBase ):

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Palette Data Header Array ' + uHex( 0x20 + args[1] )
		self._siblingsChecked = True

		# Check the parent's array count to see how many elements should be in this structure
		parentOffset = self.getAnyDataSectionParent()
		parentStruct = self.dat.initSpecificStruct( TexAnimDesc, parentOffset )
		self.entryCount = parentStruct.getValues()[-1]

		# Use the above info to dynamically build this struct's basic properties
		self.formatting = '>' + ( 'I' * self.entryCount )
		self.fields = ( 'Palette_Header_Pointer', ) * self.entryCount
		self.length = 4 * self.entryCount

		for i in range( 0, self.entryCount ):
			self.childClassIdentities[i] = 'PaletteObjDesc'



CommonStructureClasses = ( JointObjDesc, MaterialObjDesc, DisplayObjDesc, TextureObjDesc ) # re-add ImageObjDesc?
AnimationStructureClasses = ( JointAnimationDesc, MatAnimJointDesc )
# SpecificStructureClasses = { 'map_head': MapHeadObjDesc, 'coll_data': MapCollisionData, 'grGroundParam': MapGroundParameters,
# 							 'MnSelectChrDataTable': CharSelectScreenDataTable }


# Ensure that structure classes are set up properly; the number of 
# fields should be the same as the number of format identifiers
# if __name__ == '__main__':

#	import sys
#	import inspect

# 	for module in sys.modules[__name__]:
# 		print module

# 	for structClass in CommonStructureClasses:
# 		if len( structClass.fields ) != len( structClass.formatting ) - 1: # -1 accounts for byte order indicator
# 			raise ValueError( "Struct format length does not match number of field names for {}.".format(structClass.__class__.__name__) )
# 	else:
# 		print 'Struct format lengths match.'
# 		raw_input( 'Press Enter to exit.' )

# for name, obj in inspect.getmembers( sys.modules[__name__] ):
# 	if inspect.isclass( obj ) and issubclass( obj, (StructBase,) ):
# 		#print name, ':'
# 		print( obj )