import re
from collections import OrderedDict
from pyrecon.main import openSeries

class MultiSectionContour:
    '''Object with data representing a Contour that spans multiple sections. Example data includes: start, end, count, surface area, flat area, volume, etc. and depends on the type of object loaded into MultiSectionContour.'''
    def __init__(self, name=None, series=None):
        self.name = None # Name of object
        self.series = None # Series to which this object belongs
        
        self.start = None
        self.end = None
        self.count = None

        self.load(name,series)
        self.makeSpecific()
    
    def load(self, name, series):
        self.name = name
        if type(series) == type(''):
            series = openSeries(series)
        self.series = series
        self.protrusion = self.getProtNumber() # Protrusion number (stored as 'p##')
        self.dendrite = self.getDendNumber() # Parent dendrite number (stored as 'd##')
        self.rType = self.getrType()
        self.data = {} # updated in makeSpecific
        SEC = self.series.getStartEndCount(self.name)
        self.start = SEC[0]
        self.end = SEC[1]
        self.count = SEC[2]

    def getDendNumber(self):
        dend = re.compile('d[0-9]{1,}')
        try:
            return self.name[:dend.match(self.name).end()]
        except:
            return None
    
    def getProtNumber(self): 
        dend = re.compile('d[0-9]{1,}')
        tmpName = self.name[dend.match(self.name).end():] # remove dendrite portion of name
        try:
            prot = re.compile('[0-9]{1,}')
            protNum = tmpName[prot.search(tmpName).start():prot.search(tmpName).end()]
            return 'p'+str(protNum)
        except:
            return None
            
    def makeSpecific(self):
        '''Creates unique data for this rObject (depends on type)'''
        if self.rType != None:
            rType = self.rType.lower()
            if rType == 'p': # Protrusion
                importantData = ['start', 'end', 'count']
                self.children = self.findChildren()
            elif rType == 'c': # C
                importantData = ['start', 'end', 'count']
            elif 'cfa' in rType: # CFA
                importantData = ['start', 'end', 'count', 'surface area', 'flat area']
            elif 'endo' in rType: # Endosome
                importantData = ['start', 'end', 'count']
            elif rType[0:3] == 'ser': # SER #===
                importantData = ['start', 'end', 'count']
            elif rType[0:2] == 'sp': # Spine #===
                importantData = ['start', 'end', 'count', 'surface area', 'flat area', 'volume']
            elif rType[0:2] == 'ax': # Axon #===
                importantData = ['start', 'end', 'count']
            else:
                importantData = ['start', 'end', 'count']
        else:
            importantData = ['start', 'end', 'count']
        self.getData( importantData )
    
    def getData(self, list_of_desired_data=None):
        data = OrderedDict()
        for item in list_of_desired_data:
            data[item] = self.series.getData(self.name, item)
        self.data = data
        self.numColumns = len(list_of_desired_data)
             
    def getrType(self):
        '''Returns type of character'''
        if self.protrusion != None:
            prot = re.compile(self.protrusion[1:]) # dont include the 'p' in self.protrusion
            dend = re.compile(self.dendrite)
            tmpName = self.name[dend.match(self.name).end():] # remove dendrite from name
            return tmpName[:prot.search(tmpName).start()]
        return None
        
    def findChildren(self):
        '''Finds children of this protrusion and puts in self.children dict under trace type'''
        children = {}
        child_exp = re.compile(self.dendrite+'.{0,}'+self.protrusion[1:]) # dont include 'p' in self.protrusion
        dend_exp = re.compile(self.dendrite)
        for child in self.series.getObjectLists()[2]:
            if child_exp.match(child) != None:
                # Extract from name what is in between dend and prot
                endOfDendrite = dend_exp.match(child).end()
                beginOfProtrusion = child.rfind(self.protrusion[1:])
                try: # Try to add to existing entry in dictionary
                    children[str(child[endOfDendrite:beginOfProtrusion])].append(child)
                except: # Make entry and then add to it
                    children[str(child[endOfDendrite:beginOfProtrusion])] = []
                    children[str(child[endOfDendrite:beginOfProtrusion])].append(child)            
        return children
    
    def getSpacing(self):
        '''Returns number of spaces to add after excel sheet'''
        try:
            return max([len(self.children[child]) for child in self.children])-1
        except:
            return 0

class Dendrite(MultiSectionContour):
    def __init__(self, name=None, series=None):
        MultiSectionContour.__init__(self, name, series)
        data = {}
    def loadData(self):
        return
        
class Axon(MultiSectionContour):
    def __init__(self, name=None, series=None):
        MultiSectionContour.__init__(self, name, series)
        data = {}
    def loadData(self):
        return

class Spine(MultiSectionContour):
    def __init__(self, name=None, series=None):
        MultiSectionContour.__init__(self, name, series)
        data = {}
    def loadData(self):
        return

class SER(MultiSectionContour):
    def __init__(self, name=None, series=None):
        MultiSectionContour.__init__(self, name, series)
        data = {}
    def loadData(self):
        return

class CFA(MultiSectionContour):
    def __init__(self, name=None, series=None):
        MultiSectionContour.__init__(self, name, series)
        data = {}
    def loadData(self):
        return

class C(MultiSectionContour):
    def __init__(self, name=None, series=None):
        MultiSectionContour.__init__(self, name, series)
        data = {}
    def loadData(self):
        return