import os, re
from Section import Section as Section
# handleXML is imported in Series.update()

class Series:
    def __init__(self, *args, **kwargs):
        self.index = None
        self.viewport = None
        self.units = None
        self.autoSaveSeries = None
        self.autoSaveSection =  None
        self.warnSaveSection = None
        self.beepDeleting = None
        self.beepPaging = None
        self.hideTraces = None
        self.unhideTraces = None
        self.hideDomains = None
        self.unhideDomains = None
        self.useAbsolutePaths = None
        self.defaultThickness = None
        self.zMidSection = None
        self.thumbWidth = None
        self.thumbHeight = None
        self.fitThumbSections = None
        self.firstThumbSection = None
        self.lastThumbSection = None
        self.skipSections = None
        self.displayThumbContours = None
        self.useFlipbookStyle = None
        self.flipRate = None
        self.useProxies = None
        self.widthUseProxies = None
        self.heightUseProxies = None
        self.scaleProxies = None
        self.significantDigits = None
        self.defaultBorder = None
        self.defaultFill = None
        self.defaultMode = None
        self.defaultName = None
        self.defaultComment = None
        self.listSectionThickness = None
        self.listDomainSource = None
        self.listDomainPixelsize = None
        self.listDomainLength = None
        self.listDomainArea = None
        self.listDomainMidpoint = None
        self.listTraceComment = None
        self.listTraceLength = None
        self.listTraceArea = None
        self.listTraceCentroid = None
        self.listTraceExtent = None
        self.listTraceZ = None
        self.listTraceThickness = None
        self.listObjectRange = None
        self.listObjectCount = None
        self.listObjectSurfarea = None
        self.listObjectFlatarea = None
        self.listObjectVolume = None
        self.listZTraceNote = None
        self.listZTraceRange = None
        self.listZTraceLength = None
        self.borderColors = None
        self.fillColors = None
        self.offset3D = None
        self.type3Dobject = None
        self.first3Dsection = None
        self.last3Dsection = None
        self.max3Dconnection = None
        self.upper3Dfaces = None
        self.lower3Dfaces = None
        self.faceNormals = None
        self.vertexNormals = None
        self.facets3D = None
        self.dim3D = None
        self.gridType = None
        self.gridSize = None
        self.gridDistance = None
        self.gridNumber = None
        self.hueStopWhen = None
        self.hueStopValue = None
        self.satStopWhen = None
        self.satStopValue = None
        self.brightStopWhen = None
        self.brightStopValue = None
        self.tracesStopWhen = None
        self.areaStopPercent = None
        self.areaStopSize = None
        self.ContourMaskWidth = None
        self.smoothingLength = None
        self.mvmtIncrement = None
        self.ctrlIncrement = None
        self.shiftIncrement = None
        #Non-attributes
        self.name = None
        self.path = None
        self.contours = []
        self.zcontours = []
        self.sections = []
        self.processArguments(args, kwargs)
    def processArguments(self, args, kwargs):
        # 1) ARGS
        try:
            self.update(*args)
        except Exception, e:
            print('Could not process Series arg:%s\n\t'%str(args)+str(e))
        # 2) KWARGS
        try:
            self.update(**kwargs)
        except Exception, e:
            print('Could not process Series kwarg:%s\n\t'%str(kwargs)+str(e))
# MUTATORS
    def update(self, *args, **kwargs):
        for arg in args:
            # String argument
            if type(arg) == type(''): # Possible path to XML?
                import pyrecon.tools.handleXML as xml
                try: # given full path to .ser file
                    self.update(*xml.process(arg))
                    self.path = arg
                    self.name = arg.split('/')[len(arg.split('/'))-1].replace('.ser','')
                except: # given directory path instead of path to .ser file
                    path = arg
                    if path[-1] != '/':
                        path += '/'
                    path = path+str([f for f in os.listdir(path) if '.ser' in f].pop())
                    self.update(*xml.process(path))
                    self.path = path
                    self.name = path.split('/')[len(path.split('/'))-1].replace('.ser','')
            # Dictionary
            elif type(arg) == type({}):
                for key in arg:
                    if key in self.__dict__:
                        self.__dict__[key] = arg[key]
            # List
            elif type(arg) == type([]):
                for item in arg:
                    # Contour
                    if item.__class__.__name__ == 'Contour':
                        self.contours.append(item)
                    # ZSection
                    elif item.__class__.__name__ == 'ZContour':
                        self.zcontours.append(item)
                    # Section
                    elif item.__class__.__name__ == 'Section':
                        self.sections.append(item)
            # Contour
            elif arg.__class__.__name__ == 'Contour':
                self.contours.append(arg)
            # ZSection
            elif arg.__class__.__name__ == 'ZContour':
                self.zcontours.append(item)         
            # Section
            elif arg.__class__.__name__ == 'Section':
                self.sections.append(arg)
        for kwarg in kwargs:
            # Load sections
            if 'sections' in kwargs:
                if kwargs['sections'] == True:
                    print('Attempting to load sections...'),
                    ser = os.path.basename(self.path)
                    serfixer = re.compile(re.escape('.ser'), re.IGNORECASE)
                    sername = serfixer.sub('', ser)
                    # look for files with 'seriesname'+'.'+'number'
                    p = re.compile('^'+sername+'[.][0-9]*$')
                    sectionlist = [f for f in os.listdir(self.path.replace(ser,'')) if p.match(f)]
                    # create and append Sections for each section file
                    path = self.path.replace(os.path.basename(self.path),'')
                    for sec in sectionlist:
                        section = Section(path+sec)
                        if section.index is not None: #===
                            self.update(section)
                    # sort sections by index
                    self.sections = sorted(self.sections, key=lambda Section: Section.index)
                    print(' SUCCESS!')
# ACCESSORS
    def attributes(self):
        '''Returns a dict of this Serie's attributes'''
        not_attributes = ['name','path','contours','zcontours','sections']
        attributes = {}
        for att in self.__dict__:
            if att not in not_attributes: # if att is considered a desired attribute
                attributes[att] = self.__dict__[att]
        return attributes
    def deleteTraces(self, exceptions=[]):
        '''Deletes all traces except the regex found in exceptions list'''
        for section in self.sections:
            for contour in section.contours:
                for regex in exceptions:
                    if re.compile(regex).match(contour.name):
                        pass
                    else:
                        print 'Removing:', contour.name
                        section.contours.remove(contour)
# calibrationTool functions
    def zeroIdentity(self):
        '''Converts points for all sections in a series to identity transform'''
        for sec in self.sections:
            for c in sec.contours:
                if c.image is None: # Don't alter image contours i.e. domain1     
                    c.points = c.transform.worldpts(c.points)
                    c.transform.dim = 0
                    c.transform.ycoef = [0,0,1,0,0,0]
                    c.transform.xcoef = [0,1,0,0,0,0]
                    c._tform = c.transform.tform()
# curationTool functions
    def locateInvalidTraces(self, delete=False):
        invalidDict = {}
        for section in self.sections:
            invalids = []
            for contour in section.contours:
                if contour.isInvalid():
                    invalids.append(contour.name)
                    if delete:
                        print 'deleted: ',contour.name,'at section',section.index
                        section.contours.remove(contour)
            if len(invalids) != 0:
                invalidDict[section.index] = invalids
        return invalidDict
    def locateReverseTraces(self):
        reverseDict = {}
        for section in self.sections:
            revTraces = []
            for contour in section.contours:
                try:
                    if contour.isReverse():
                        revTraces.append(contour)
                except:
                        print('Invalid contour (%s on section %d) was ignored')%(contour.name, section.index)
                        print('\t check coordinates in XML file')
            if len(revTraces) != 0:
                reverseDict[section.index] = revTraces
        return reverseDict
    def locateDistantTraces(self, threshold=7):
        '''Returns a dictionary of indexes containing traces that exist after <threshold (def: 7)> sections of non-existence'''
        # Build a list of lists for all the contours in each section
        allSectionContours = []
        for section in self.sections:
            contours = list(set([cont.name for cont in section.contours]))
            allSectionContours.append(contours)
        # Go through list of contours and check for distances
        index = int(self.sections[0].index) # correct starting index (can be 0 or 1)
        distantTraces = {}
        for sec in range(len(allSectionContours)):
            traces = []
            for contour in allSectionContours[sec]:
                # Check above
                if sec+threshold+1 <= len(self.sections):
                    # Check and ignore if in section:section+threshold
                    sectionToThresholdContours = [] 
                    for contList in allSectionContours[sec+1:sec+threshold+1]:
                        sectionToThresholdContours.extend(contList)
                    if contour not in sectionToThresholdContours:
                        # Check if contour is in section+threshold and up
                        thresholdToEndContours = []
                        for contList in allSectionContours[sec+threshold+1:]:
                            thresholdToEndContours.extend(contList)
                        if contour in thresholdToEndContours:
                            traces.append(contour)
                # Check below
                if sec-threshold-1 >= 0:
                    # Check and ignore if in section-threshold:section
                    minusThresholdToSectionContours = []
                    for contList in allSectionContours[sec-threshold:sec]:
                        minusThresholdToSectionContours.extend(contList)
                    if contour not in minusThresholdToSectionContours:
                        # Check if contour is in section-threshold and down
                        beginToMinusThresholdContours = []
                        for contList in allSectionContours[:sec-threshold]:
                            beginToMinusThresholdContours.extend(contList)
                        if contour in beginToMinusThresholdContours:
                            traces.append(contour)
                # Add traces to distantTraces dictionary
                if len(traces) != 0:
                    distantTraces[index] = traces
            index += 1
        return distantTraces
    def locateDuplicates(self):
        '''Locates overlapping traces of the same name in a section. Returns a dictionary of section numbers with duplicates'''
        # Build dictionary of sections w/ contours whose name appear more than once in that section
        duplicateNames = {}
        for section in self.sections:
            duplicates = []
            contourNames = [cont.name for cont in section.contours] # List of contour names
            # Go through each contour, see if name appears in contourName > 1 time
            for contour in section.contours:
                if contourNames.count(contour.name) > 1:
                    duplicates.append(contour)
            if len(duplicates) != 0:
                duplicateNames[section.index] = duplicates
        
        # Go through each list of >1 contour names and check if actually overlaps
        duplicateDict = {}
        for key in duplicateNames:
            duplicates = []
            for contour in duplicateNames[key]:
                # Filter contours of same memory address so that overlap isn't tested on itself
                copyContours = [cont for cont in duplicateNames[key] if id(cont) != id(contour) and cont.name == contour.name]
                for cont in copyContours:
                    try:
                        if contour.overlaps(cont) == 1: # Perfect overlap (within threshold)
                            duplicates.append(cont)
                    except:
                        print('Invalid contour (%s on section %d) was ignored')%(cont.name, key)
                        print('\t check coordinates in XML file')
            if len(duplicates) != 0:
                duplicateDict[key] = duplicates
        return duplicateDict
# excelTool functions
    def getObject(self, regex):
        '''Returns a list of 1 list per section containing all the contour that match the regex'''
        objects = []
        for section in self.sections:
            section.append(section.getObject(regex))
        return objects  
    def getObjectLists(self):
        '''Returns sorted lists of dendrite names, protrusion names, trace names, and a list of other objects in series'''
        dendrite_expression = 'd[0-9]{2,}' # represents base dendrite name (d##)
        protrusion_expression = 'd[0-9]{2,}p[0-9]{2,}$' # represents base protrusion name (d##p##)
        trace_expression = 'd[0-9]{2,}.{1,}[0-9]{2,}' # represents trace name (d##<tracetype>##)
        
        # Convert expressions to usable regular expressions
        dendrite_expression = re.compile(dendrite_expression)
        protrusion_expression = re.compile(protrusion_expression, re.I)
        trace_expression = re.compile(trace_expression, re.I)

        # Create lists for names of dendrites, protrusions, traces, and other objects
        dendrites = []
        protrusions = []
        traces = []
        others = []
        for section in self.sections:
            for contour in section.contours:
                # Dendrite
                if dendrite_expression.match(contour.name) != None:
                    dendrites.append(contour.name[0:dendrite_expression.match(contour.name).end()])
                # Protrusion
                if protrusion_expression.match(contour.name) != None:
                    protrusions.append(contour.name)
                # Trace === expand to > 2 digits!
                if (trace_expression.match(contour.name) != None and
                    protrusion_expression.match(contour.name) == None):
                    traces.append(contour.name)
                    # Make sure a d##p## exists for this trace
                    thisProt = contour.name[0:3]+'p'+contour.name[4:6]
                    if (protrusion_expression.match(thisProt) and
                        thisProt not in protrusions):
                        protrusions.append(thisProt)
                # Everything else (other)
                if (dendrite_expression.match(contour.name) == None and
                    protrusion_expression.match(contour.name) == None and
                    trace_expression.match(contour.name) == None):
                    others.append(contour.name)
        return sorted(list(set(dendrites))), sorted(list(set(protrusions))), sorted(list(set(traces))), sorted(list(set(others)))
    def getData(self, object_name, data_string):
        string = str(data_string).lower()
        if string == 'volume':
            return self.getVolume(object_name)
        elif string == 'total volume':
            return self.getTotalVolume(object_name)
        elif string == 'surface area':
            return self.getSurfaceArea(object_name)
        elif string == 'flat area':
            return self.getFlatArea(object_name)
        elif string == 'start':
            return self.getStartEndCount(object_name)[0]
        elif string == 'end':
            return self.getStartEndCount(object_name)[1]
        elif string == 'count':    
            return self.getStartEndCount(object_name)[2]
    def getVolume(self, object_name):
        '''Returns volume of the object throughout the series. Volume calculated by summing the value obtained by
        multiplying the area by section thickness over all sections.'''
        vol = 0
        for section in self.sections:
            for contour in section.contours:
                if contour.name == object_name:
                    try:
                        contour.popShape()
                        vol += (contour.shape.area * section.thickness)
                    except:
                        print 'getVolume(): Invalid contour:', contour.name, 'in section index:', section.index, '\nCheck XML file and fix before trusting data.\n'
        return vol
    def getTotalVolume(self, object_name):
        related_objects = []
        if object_name[-1].isalpha():
            object_name = object_name[:-1]
            # Get all related objects by base object name
            for section in self.sections:
                for contour in section.contours:
                    if object_name in contour.name:
                        related_objects.append(contour.name)
        # Find total volume by summing volume for all related objects
        totVol = 0
        for obj in list(set(related_objects)):
            totVol+=self.getVolume(obj)
        return totVol
    def getSurfaceArea(self, object_name):
        '''Returns surface area of the object throughout the series. Surface area calculated by summing
        the length multiplied by section thickness across sections.'''
        sArea = 0
        for section in self.sections:
            for contour in section.contours:
                if contour.name == object_name:
                    try:
                        sArea += (contour.getLength() * section.thickness)
                    except:
                        print 'getSurfaceArea(): Invalid contour:', contour.name, 'in section index:', section.index, '\nCheck XML file and fix before trusting data.\n'
        return sArea
    def getFlatArea(self, object_name):
        '''Returns the flat area of the object throughout the series. Flat area calculated by summing the area of
        the object across all sections.'''
        fArea = 0
        for section in self.sections:
            for contour in section.contours:
                if contour.name == object_name:
                    try:
                        contour.popShape()
                        if contour.closed:
                            fArea += contour.shape.area
                        else:
                            fArea += (contour.getLength() * section.thickness)
                    except:
                        print 'getFlatArea(): Invalid contour:', contour.name, 'in section index:', section.index, '\nCheck XML file and fix before trusting data.\n'
        return fArea
    def getStartEndCount(self, object_name):
        '''Returns a tuple containing the start index, end index, and count of the item in series.'''
        start = 0
        end = 0
        count = 0
        # Count
        for section in self.sections:
            for contour in section.contours:
                if contour.name == object_name:
                    count += 1
            # Start/End
            if object_name in [cont.name for cont in section.contours]:
                # Start index
                if start == 0:
                    start = section.index
                # End index
                end = section.index
        return start, end, count