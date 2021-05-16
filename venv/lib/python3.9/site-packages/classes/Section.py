# handleXML is imported in .update()
import os
class Section:
	def __init__(self, *args, **kwargs):
		self.name = None # Series name + index
		self.index = None
		self.thickness = None
		self.alignLocked = None
		#Non-attributes
		self.images = [] #=== d1fixed
		self.contours = []
		self._path = None
		self.processArguments(args, kwargs)
	def processArguments(self, args, kwargs):
		'''Populates data from the *args and **kwargs arguments via self.update.'''
		# 1) ARGS
		for arg in args:
			try:
				self.update(arg)
			except Exception, e:
				print('Could not process Section arg: %s\n\t'%str(arg)+str(e))
		# 2) KWARGS #===
		for kwarg in kwargs:
			try:
				self.update(kwarg)
			except Exception, e:
				print('Could not process Section kwarg:%s\n\t'%str(kwarg)+str(e))
# MUTATORS
	def update(self, *args): #=== **kwargs eventually, need a way to choose overwrite or append to contours
		'''Changes Section data from arguments. Assesses type of argument then determines where to place it.'''
		for arg in args: # Assess type
			# Dictionary argument
			if type(arg) == type({}):
				for key in arg:
					# Dict:Attribute
					if key in self.__dict__:
						self.__dict__[key] = arg[key]
					# Dict:List
					elif type(arg[key]) == type([]):
						for item in arg[key]:
							if item.__class__.__name__ == 'Image':
								self.images.append(item)
							elif item.__class__.__name__ == 'Contour':
								self.contours.append(item)
					# Dict:Image
					elif arg[key].__class__.__name__ == 'Image':
						self.images.append(arg[key]) #=== d1fixed
					# Dict:Contour
					elif arg[key].__class__.__name__ == 'Contour':
						self.contours.append(arg[key])
			# String argument
			elif type(arg) == type(''): # Possible path to XML?
				import pyrecon.tools.handleXML as xml
				self.update(*xml.process(arg))
				self.name = arg.split('/')[-1]
				self._path = os.path.dirname(arg)
				if self._path[-1] != '/':
					self._path += '/'
			# Contour argument
			elif arg.__class__.__name__ == 'Contour':
				self.contours.append(arg)
			# Image argument
			elif arg.__class__.__name__ == 'Image':
				self.images.append(arg) #=== d1fixed
			# List argument
			elif type(arg) == type([]):
				for item in arg:
					if item.__class__.__name__ == 'Contour':
						self.contours.append(item)
					elif item.__class__.__name__ == 'Image':
						self.images.append(item)
		for img in self.images:
			img._path = self._path
	def popShapes(self):
		for contour in self.contours:
			contour.popShape()
# ACCESSORS
	def __len__(self):
		'''Return number of contours in Section object'''
		return len(self.contours)
	def __eq__(self, other): #=== images eval correctly?
		'''Allows use of == between multiple objects'''
		return (self.thickness == other.thickness and
				self.index == other.thickness and
				self.alignLocked == other.alignLocked and
				self.images == other.images and #=== d1fixed
				self.contours == other.contours)
	def __ne__(self, other):
		'''Allows use of != between multiple objects'''
		return not self.__eq__(other)
	def eq(self, other, eqType=None): #===
		'''Check equivalency with the option for type of attributes to compare. Default: __eq__'''
		if not eqType:
			return self.__eq__(other)
		elif eqType.lower() == 'attributes':
			return (self.thickness == other.thickness and
					self.index == other.index and
					self.alignLocked == other.alignLocked)
		elif eqType.lower() in ['images', 'image', 'img']:
			return (self.images == other.images) #=== d1fixed
		elif eqType.lower() in ['contours', 'contour']:
			return (self.contours == other.contours)
	def attributes(self):
		'''Returns a dict of this Section's attributes'''
		return {'name':self.name,
				'index':self.index,
				'thickness':self.thickness,
				'alignLocked':self.alignLocked
			}