'''Functions for reading from/writing to RECONSTRUCT XML files.'''
from pyrecon.classes import Contour, Image, Section, Series, Transform, ZContour
from lxml import etree as ET # lxml parsing library Element Tree module
import os, re
# Process Files
def process(path, obj=False):
	'''Process XML file defined by path'''
	tree = ET.parse(path)
	root = tree.getroot()
	if root.tag == 'Section': # Process Section
		if obj:
			return Section(*processSectionFile(tree))
		return processSectionFile(tree)
	elif root.tag == 'Series': # Process Series
		if obj:
			return Series(*processSeriesFile(tree))
		return processSeriesFile(tree)
def processSeriesFile(tree):
	root = tree.getroot()
	attributes = seriesAttributes(root)
	contours = None
	zcontours = None
	for elem in root:
		if elem.tag == 'Contour':
			contour = Contour(contourAttributes(elem), None)
			if contours == None:
				contours = []
			contours.append(contour)
		elif elem.tag == 'ZContour':
			zcontour = ZContour(zContourAttributes(elem)) #===
			if zcontours == None:
				zcontours = []
			zcontours.append(zcontour)
	return attributes, contours, zcontours
def processSectionFile(tree):
	'''Returns attribute dictionary, image object, and contour list associated with a Section's XML <tree>'''
	# Process attributes
	root = tree.getroot()
	attributes = sectionAttributes(root)

	# Process images and contours
	images = []
	contours = None
	for transform in root:
		# make Transform object
		tForm = Transform( transformAttributes(transform) )
		children = [child for child in transform]
		
		# Image transform node
		img = [child for child in children if child.tag == 'Image']
		if len(img) > 0:
			img = img.pop()
			img = Image( imageAttributes(img) )
			imgContour = [child for child in children if child.tag == 'Contour']
			if len(imgContour) > 0:
				imgContour = imgContour.pop()
				contour = Contour( contourAttributes(imgContour), tForm )
				contour.image = img # set contour's image to the image
				img.contour = contour # set image's contour to the contour
				images.append(img)
		# Non-Image Transform Node
		else:
			for child in children:
				if child.tag == 'Contour':
					cont = Contour( contourAttributes(child), tForm )
					if contours == None:
						contours = []
					contours.append( cont )
	return attributes, images, contours

# Process attributes from tree nodes
def contourAttributes(node):
	try: # Contours in Sections
		attributes = {}
		attributes['name'] = str(node.get('name'))
		attributes['comment'] = str(node.get('comment'))
		attributes['hidden'] = node.get('hidden').capitalize() == 'True'
		attributes['closed'] = node.get('closed').capitalize() == 'True'
		attributes['simplified'] = node.get('simplified').capitalize() == 'True'
		attributes['mode'] = int(node.get('mode'))
		attributes['border'] = tuple(float(x) for x in node.get('border').strip().split(' '))
		attributes['fill'] = tuple(float(x) for x in node.get('fill').strip().split(' '))
		attributes['points'] = zip([float(x.replace(',','')) for x in node.get('points').split()][0::2], [float(x.replace(',','')) for x in node.get('points').split()][1::2])
		attributes['coordSys'] = 'bio'
	except: # Contours in Series
		try:
			attributes = {}
			attributes['name'] = str(node.get('name'))
			attributes['closed'] = node.get('closed').capitalize() == 'True'
			attributes['mode'] = int(node.get('mode'))
			attributes['border'] = tuple(float(x) for x in node.get('border').strip().split(' '))
			attributes['fill'] = tuple(float(x) for x in node.get('fill').strip().split(' '))
			attributes['points'] = zip([int(x.replace(',','')) for x in node.get('points').split()][0::2], [int(x.replace(',','')) for x in node.get('points').split()][1::2])
			attributes['coordSys'] = 'bio'
		except:
			print('Problem retrieving contourAttributes')
	return attributes
def imageAttributes(node):
	attributes = {}
	attributes['src'] = str(node.get('src'))
	attributes['mag'] = float(node.get('mag'))
	attributes['contrast'] = float(node.get('contrast'))
	attributes['brightness'] = float(node.get('brightness'))
	attributes['red'] = node.get('red').capitalize() == 'True'
	attributes['green'] = node.get('green').capitalize() == 'True'
	attributes['blue'] = node.get('blue').capitalize() == 'True'
	return attributes
def sectionAttributes(node):
	attributes = {}
	attributes['index']=int(node.get('index'))
	attributes['thickness']=float(node.get('thickness'))
	attributes['alignLocked']=node.get('alignLocked').capitalize() == 'True'
	return attributes
def seriesAttributes(node):
	attributes = {}
	attributes['index'] = int(node.get('index'))
	attributes['viewport'] = tuple(float(x) for x in node.get('viewport').split(' '))
	attributes['units'] = str(node.get('units'))
	attributes['autoSaveSeries'] = node.get('autoSaveSeries').capitalize() == 'True'
	attributes['autoSaveSection'] = node.get('autoSaveSection').capitalize() == 'True'
	attributes['warnSaveSection'] = node.get('warnSaveSection').capitalize() == 'True'
	attributes['beepDeleting'] = node.get('beepDeleting').capitalize() == 'True'
	attributes['beepPaging'] = node.get('beepPaging').capitalize() == 'True'
	attributes['hideTraces'] = node.get('hideTraces').capitalize() == 'True'
	attributes['unhideTraces'] = node.get('unhideTraces').capitalize() == 'True'
	attributes['hideDomains'] = node.get('hideDomains').capitalize() == 'True'
	attributes['unhideDomains'] = node.get('hideDomains').capitalize() == 'True'
	attributes['useAbsolutePaths'] = node.get('useAbsolutePaths').capitalize() == 'True'
	attributes['defaultThickness'] = float(node.get('defaultThickness'))
	attributes['zMidSection'] = node.get('zMidSection').capitalize() == 'True'
	attributes['thumbWidth'] = int(node.get('thumbWidth'))
	attributes['thumbHeight'] = int(node.get('thumbHeight'))
	attributes['fitThumbSections'] = node.get('fitThumbSections').capitalize() == 'True'
	attributes['firstThumbSection'] = int(node.get('firstThumbSection'))
	attributes['lastThumbSection'] = int(node.get('lastThumbSection'))
	attributes['skipSections'] = int(node.get('skipSections'))
	attributes['displayThumbContours'] = node.get('displayThumbContours').capitalize() == 'True'
	attributes['useFlipbookStyle'] = node.get('useFlipbookStyle').capitalize()  == 'True'
	attributes['flipRate'] = int(node.get('flipRate'))
	attributes['useProxies'] = node.get('useProxies').capitalize() == 'True'
	attributes['widthUseProxies'] = int(node.get('widthUseProxies'))
	attributes['heightUseProxies'] = int(node.get('heightUseProxies'))
	attributes['scaleProxies'] = float(node.get('scaleProxies'))
	attributes['significantDigits'] = int(node.get('significantDigits'))
	attributes['defaultBorder'] = tuple(float(x) for x in node.get('defaultBorder').split(' '))
	attributes['defaultFill'] = tuple(float(x) for x in node.get('defaultFill').split(' '))
	attributes['defaultMode'] = int(node.get('defaultMode'))
	attributes['defaultName'] = str(node.get('defaultName'))
	attributes['defaultComment'] = str(node.get('defaultComment'))
	attributes['listSectionThickness'] = node.get('listSectionThickness').capitalize() == 'True'
	attributes['listDomainSource'] = node.get('listDomainSource').capitalize() == 'True'
	attributes['listDomainPixelsize'] = node.get('listDomainPixelsize').capitalize() == 'True'
	attributes['listDomainLength'] = node.get('listDomainLength').capitalize() == 'True'
	attributes['listDomainArea'] = node.get('listDomainArea').capitalize() == 'True'
	attributes['listDomainMidpoint'] = node.get('listDomainMidpoint').capitalize() == 'True'
	attributes['listTraceComment'] = node.get('listTraceComment').capitalize() == 'True'
	attributes['listTraceLength'] = node.get('listTraceLength').capitalize()  == 'True'
	attributes['listTraceArea'] = node.get('listTraceArea').capitalize() == 'True'
	attributes['listTraceCentroid'] = node.get('listTraceCentroid').capitalize() == 'True'
	attributes['listTraceExtent'] = node.get('listTraceExtent').capitalize() == 'True'
	attributes['listTraceZ'] = node.get('listTraceZ').capitalize() == 'True'
	attributes['listTraceThickness'] = node.get('listTraceThickness').capitalize() == 'True'
	attributes['listObjectRange'] = node.get('listObjectRange').capitalize() == 'True'
	attributes['listObjectCount'] = node.get('listObjectCount').capitalize() == 'True'
	attributes['listObjectSurfarea'] = node.get('listObjectSurfarea').capitalize() == 'True'
	attributes['listObjectFlatarea'] = node.get('listObjectFlatarea').capitalize() == 'True'
	attributes['listObjectVolume'] = node.get('listObjectVolume').capitalize() == 'True'
	attributes['listZTraceNote'] = node.get('listZTraceNote').capitalize() == 'True'
	attributes['listZTraceRange'] = node.get('listZTraceRange').capitalize() == 'True'
	attributes['listZTraceLength'] = node.get('listZTraceLength').capitalize() == 'True'
	attributes['borderColors'] = [tuple(float(x) for x in x.split(' ') if x != '') for x in [x.strip() for x in node.get('borderColors').split(',')] if len(tuple(float(x) for x in x.split(' ') if x != '')) == 3]
	attributes['fillColors'] = [tuple(float(x) for x in x.split(' ') if x != '') for x in [x.strip() for x in node.get('fillColors').split(',')] if len(tuple(float(x) for x in x.split(' ') if x != '')) == 3]
	attributes['offset3D'] = tuple(float(x) for x in node.get('offset3D').split(' '))
	attributes['type3Dobject'] = int(node.get('type3Dobject'))
	attributes['first3Dsection'] = int(node.get('first3Dsection'))
	attributes['last3Dsection'] = int(node.get('last3Dsection'))
	attributes['max3Dconnection'] = int(node.get('max3Dconnection'))
	attributes['upper3Dfaces'] = node.get('upper3Dfaces').capitalize() == 'True'
	attributes['lower3Dfaces'] = node.get('lower3Dfaces').capitalize() == 'True'
	attributes['faceNormals'] = node.get('faceNormals').capitalize() == 'True'
	attributes['vertexNormals'] = node.get('vertexNormals').capitalize() == 'True'
	attributes['facets3D'] = int(node.get('facets3D'))
	attributes['dim3D'] = tuple(float(x) for x in node.get('dim3D').split())
	attributes['gridType'] = int(node.get('gridType'))
	attributes['gridSize'] = tuple(float(x) for x in node.get('gridSize').split(' '))
	attributes['gridDistance'] = tuple(float(x) for x in node.get('gridDistance').split(' '))
	attributes['gridNumber'] = tuple(float(x) for x in node.get('gridNumber').split(' '))
	attributes['hueStopWhen'] = int(node.get('hueStopWhen'))
	attributes['hueStopValue'] = int(node.get('hueStopValue'))
	attributes['satStopWhen'] = int(node.get('satStopWhen'))
	attributes['satStopValue'] = int(node.get('satStopValue'))
	attributes['brightStopWhen'] = int(node.get('brightStopWhen'))
	attributes['brightStopValue'] = int(node.get('brightStopValue'))
	attributes['tracesStopWhen'] = node.get('tracesStopWhen').capitalize()
	attributes['areaStopPercent'] = int(node.get('areaStopPercent'))
	attributes['areaStopSize'] = int(node.get('areaStopSize'))
	attributes['ContourMaskWidth'] = int(node.get('ContourMaskWidth'))
	attributes['smoothingLength'] = int(node.get('smoothingLength'))
	attributes['mvmtIncrement'] = tuple(float(x) for x in node.get('mvmtIncrement').split(' '))
	attributes['ctrlIncrement'] = tuple(float(x) for x in node.get('ctrlIncrement').split(' '))
	attributes['shiftIncrement'] = tuple(float(x) for x in node.get('shiftIncrement').split(' '))
	return attributes
def transformAttributes(node):
	def intorfloat(input):
		'''Returns number data type from string.'''
		if '.' in input:
			return float(input)
		else:
			try: #=== 
				return int(input)
			except:
				print '\n\thandleXML.intorfloat():',input,'converted to float',float(input),'\n'
				return float(input)
	attributes = {}
	attributes['dim'] = int(node.get('dim'))
	attributes['xcoef'] = [intorfloat(x) for x in node.get('xcoef').strip().split(' ')]
	attributes['ycoef'] = [intorfloat(x) for x in node.get('ycoef').strip().split(' ')]
	return attributes
def zContourAttributes(node):
	attributes = {}
	attributes['name'] = str(node.get('name'))
	attributes['closed'] = node.get('closed').capitalize() == 'True'
	attributes['border'] = tuple(float(x) for x in node.get('border').split(' '))
	attributes['fill'] = tuple(float(x) for x in node.get('fill').split(' '))
	attributes['mode'] = int(node.get('mode'))
	attributes['points'] = [(float(x.split(' ')[0]), float(x.split(' ')[1]), int(x.split(' ')[2])) for x in [x.strip() for x in node.get('points').split(',')] if len(tuple(float(x) for x in x.split(' ') if x != '')) == 3]
	return attributes
# Write objects to XML
def objectToElement(object):
	'''Returns an ElementTree Element for <object> that is appropriate for writing to an XML file.'''
	def contourToElement(contour):
		try: # Contour in Section
			element = ET.Element("Contour",
				name=str(contour.name),
				hidden=str(contour.hidden).lower(),
				closed=str(contour.closed).lower(),
				simplified=str(contour.simplified).lower(),
				border=str(contour.border[0])+' '+str(contour.border[1])+' '+str(contour.border[2]),
				fill=str(contour.fill[0])+' '+str(contour.fill[1])+' '+str(contour.fill[2]),
				mode=str(contour.mode),
				points= ', '.join([str(pt[0])+' '+str(pt[1]) for pt in contour.points])+','
				)
		except:
			try: # Contour in Series
				element = ET.Element("Contour",
				name=str(contour.name),
				closed=str(contour.closed).lower(),
				border=str(contour.border[0])+' '+str(contour.border[1])+' '+str(contour.border[2]),
				fill=str(contour.fill[0])+' '+str(contour.fill[1])+' '+str(contour.fill[2]),
				mode=str(contour.mode),
				points= ', '.join([str(pt[0])+' '+str(pt[1]) for pt in contour.points])+','
				)
			except:
				print('Problem creating Contour element', contour.name)
		return element
	def imageToElement(image):
		element = ET.Element("Image",
			mag=str(image.mag),
			contrast=str(image.contrast),
			brightness=str(image.brightness),
			red=str(image.red).lower(),
			green=str(image.red).lower(),
			blue=str(image.blue).lower(),
			src=str(image.src)
			)
		return element
	def sectionToElement(section):
		element = ET.Element("Section",
			index=str(section.index),
			thickness=str(section.thickness),
			alignLocked=str(section.alignLocked).lower()
			)
		return element
	def seriesToElement(series):
		element = ET.Element('Series',
			index=str(series.index),
			viewport=' '.join([str(val) for val in series.viewport]),
			units=str(series.units),
			autoSaveSeries=str(series.autoSaveSeries).lower(),
			autoSaveSection=str(series.autoSaveSection).lower(),
			warnSaveSection=str(series.warnSaveSection).lower(),
			beepDeleting=str(series.beepDeleting).lower(),
			beepPaging=str(series.beepPaging).lower(),
			hideTraces=str(series.hideTraces).lower(),
			unhideTraces=str(series.unhideTraces).lower(),
			hideDomains=str(series.hideDomains).lower(),
			unhideDomains=str(series.unhideDomains).lower(),
			useAbsolutePaths=str(series.useAbsolutePaths).lower(),
			defaultThickness=str(series.defaultThickness),
			zMidSection=str(series.zMidSection).lower(),
			thumbWidth=str(series.thumbWidth),
			thumbHeight=str(series.thumbHeight),
			fitThumbSections=str(series.fitThumbSections).lower(),
			firstThumbSection=str(series.firstThumbSection),
			lastThumbSection=str(series.lastThumbSection),
			skipSections=str(series.skipSections),
			displayThumbContours=str(series.displayThumbContours).lower(),
			useFlipbookStyle=str(series.useFlipbookStyle).lower(),
			flipRate=str(series.flipRate),
			useProxies=str(series.useProxies).lower(),
			widthUseProxies=str(series.widthUseProxies),
			heightUseProxies=str(series.heightUseProxies),
			scaleProxies=str(series.scaleProxies),
			significantDigits=str(series.significantDigits),
			defaultBorder=' '.join([str(val) for val in series.defaultBorder]),
			defaultFill=' '.join([str(val) for val in series.defaultFill]),
			defaultMode=str(series.defaultMode),
			defaultName=str(series.defaultName),
			defaultComment=str(series.defaultComment),
			listSectionThickness=str(series.listSectionThickness).lower(),
			listDomainSource=str(series.listDomainSource).lower(),
			listDomainPixelsize=str(series.listDomainPixelsize).lower(),
			listDomainLength=str(series.listDomainLength).lower(),
			listDomainArea=str(series.listDomainArea).lower(),
			listDomainMidpoint=str(series.listDomainMidpoint).lower(),
			listTraceComment=str(series.listTraceComment).lower(),
			listTraceLength=str(series.listTraceLength).lower(),
			listTraceArea=str(series.listTraceArea).lower(),
			listTraceCentroid=str(series.listTraceCentroid).lower(),
			listTraceExtent=str(series.listTraceExtent).lower(),
			listTraceZ=str(series.listTraceZ).lower(),
			listTraceThickness=str(series.listTraceThickness).lower(),
			listObjectRange=str(series.listObjectRange).lower(),
			listObjectCount=str(series.listObjectCount).lower(),
			listObjectSurfarea=str(series.listObjectSurfarea).lower(),
			listObjectFlatarea=str(series.listObjectFlatarea).lower(),
			listObjectVolume=str(series.listObjectVolume).lower(),
			listZTraceNote=str(series.listZTraceNote).lower(),
			listZTraceRange=str(series.listZTraceRange).lower(),
			listZTraceLength=str(series.listZTraceLength).lower(),
			borderColors=','.join([str(val[0])+' '+str(val[1])+' '+str(val[2]) for val in series.borderColors])+',',
			fillColors=','.join([str(val[0])+' '+str(val[1])+' '+str(val[2]) for val in series.fillColors])+',',
			offset3D=' '.join([str(val) for val in series.offset3D]),
			type3Dobject=str(series.type3Dobject),
			first3Dsection=str(series.first3Dsection),
			last3Dsection=str(series.last3Dsection),
			max3Dconnection=str(series.max3Dconnection),
			upper3Dfaces=str(series.upper3Dfaces).lower(),
			lower3Dfaces=str(series.lower3Dfaces).lower(),
			faceNormals=str(series.faceNormals).lower(),
			vertexNormals=str(series.vertexNormals).lower(),
			facets3D=str(series.facets3D),
			dim3D=' '.join([str(val) for val in series.dim3D]),
			gridType=str(series.gridType),
			gridSize=' '.join([str(val) for val in series.gridSize]),
			gridDistance=' '.join([str(val) for val in series.gridDistance]),
			gridNumber=' '.join([str(val) for val in series.gridNumber]),
			hueStopWhen=str(series.hueStopWhen),
			hueStopValue=str(series.hueStopValue),
			satStopWhen=str(series.satStopWhen),
			satStopValue=str(series.satStopValue),
			brightStopWhen=str(series.brightStopWhen),
			brightStopValue=str(series.brightStopValue),
			tracesStopWhen=str(series.tracesStopWhen).lower(),
			areaStopPercent=str(series.areaStopPercent),
			areaStopSize=str(series.areaStopSize),
			ContourMaskWidth=str(series.ContourMaskWidth),
			smoothingLength=str(series.smoothingLength),
			mvmtIncrement=' '.join([str(val) for val in series.mvmtIncrement]),
			ctrlIncrement=' '.join([str(val) for val in series.ctrlIncrement]),
			shiftIncrement=' '.join([str(val) for val in series.shiftIncrement])
			)
		return element
	def transformToElement(transform):
		element = ET.Element("Transform",
			dim=str(transform.dim),
			xcoef=' '+' '.join([str(item) for item in transform.xcoef]),
			ycoef=' '+' '.join([str(item) for item in transform.ycoef])
			)
		return element
	def zcontourToElement(zcontour):
		element = ET.Element('ZContour',
			name=str(zcontour.name),
			closed=str(zcontour.closed).lower(),
			border=' '.join([str(val) for val in zcontour.border]),
			fill=' '.join([str(val) for val in zcontour.fill]),
			mode=str(zcontour.mode),
			points=', '.join([str(pt[0])+' '+str(pt[1])+' '+str(pt[2]) for pt in zcontour.points])+','
			)
		return element
	if object.__class__.__name__ == 'Contour':
		return contourToElement(object)
	elif object.__class__.__name__ == 'Image':
		return imageToElement(object)
	elif object.__class__.__name__ == 'Section':
		return sectionToElement(object)
	elif object.__class__.__name__ == 'Series':
		return seriesToElement(object)
	elif object.__class__.__name__ == 'Transform':
		return transformToElement(object)
	elif object.__class__.__name__ == 'ZContour':
		return zcontourToElement(object)
def writeSection(section, directory, outpath=None, overwrite=False):
	'''Writes <section> to an XML file in directory'''
	print 'Writing section:',section.name
	if not outpath: # Will write to file with sections name
		if str(directory[-1]) != '/':
			directory += '/'
		outpath = str(directory)+str(section.name)
	
	# Make root (Section attributes: index, thickness, alignLocked)
	root = objectToElement(section)
	
	# Add Transform nodes for images (assumes they can all have different tform)
	for image in section.images:
		trnsfrm = objectToElement( image.contour.transform )
		img = objectToElement( image ) # image as XML output node
		cntr = objectToElement( image.contour )
		trnsfrm.append(img)
		trnsfrm.append(cntr)
		root.append(trnsfrm) # append images transform node to XML file

	# Non-Image Contours
	# - Build list of unique Transform objects
	uniqueTransforms = []
	for contour in section.contours:
		unique = True
		for tform in uniqueTransforms:
			if tform == contour.transform:
				unique = False
				break
		if unique:
			uniqueTransforms.append(contour.transform)

	# - Add contours to their equivalent Transform objects
	for transform in uniqueTransforms:
		transformElement = objectToElement(transform)
		for contour in section.contours:
			if contour.transform == transform:
				cont = objectToElement(contour)
				transformElement.append(cont)
		root.append(transformElement)

	# Make tree and write
	elemtree = ET.ElementTree(root)
	if os.path.exists(outpath) and not overwrite:
		print('Section write aborted (%s) due to overwrite conflict.'%(section.name)) 
		return
	elemtree.write(outpath, pretty_print=True, xml_declaration=True, encoding="UTF-8")
def writeSeries(series, directory, outpath=None, sections=False, overwrite=False):
	'''Writes <series> to an XML file in directory'''
	print 'Writing series:',series.name
	# Pre-writing checks
	# - Make sure directory is correctly input
	if directory[-1] != '/':
		directory += '/'
    # - Check if directory exists, make if does not exist
	if not os.path.exists(directory):
		os.makedirs(directory)
	if not outpath:
		outpath = directory+series.name+'.ser'
    # - Raise error if this file already exists to prevent overwrite
	if not overwrite and os.path.exists(outpath):
		msg = 'CAUTION: Files already exist in ths directory: Do you want to overwrite them?'
		try: # Graphical
			from PySide.QtGui import QApplication, QMessageBox
			app = QApplication.instance()
			if app == None:
				app = QApplication([])
			msgBox = QMessageBox()
			msgBox.setText(msg)
			msgBox.setStandardButtons( QMessageBox.Ok | QMessageBox.Cancel)
			response = msgBox.exec_()
			if response == QMessageBox.Ok:
				a = 'yes'
			else:
				a = 'no'
		except: # StdOut
			a = raw_input(msg+' (y/n)')
		overwrite = str(a).lower() in ['y','yes']
		if not overwrite:
			raise IOError('\nFilename %s already exists.\nQuiting write command to avoid overwrite'%outpath)
		print ('!!! OVERWRITE ENABLED !!!')
    # Build series root element
	root = objectToElement( series ) 
	# Add Contours/ZContours to root
	if series.contours is not None:
		for contour in series.contours:
			root.append( objectToElement(contour) )
	else:
		print 'No contours in', series.name
	if series.zcontours is not None:
		for zcontour in series.zcontours:
			root.append( objectToElement(zcontour) )
	else:
		print 'No zcontours in', series.name
	# Make tree and write
	elemtree = ET.ElementTree(root)
	elemtree.write(outpath, pretty_print=True, xml_declaration=True, encoding="UTF-8")
	# Write all sections if <sections> == True
	if sections == True:
		for section in series.sections:
			writeSection(section, directory, overwrite=overwrite)
