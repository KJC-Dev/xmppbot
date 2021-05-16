from shapely.geometry import Polygon, LineString, box, LinearRing
import math

class Contour:
    def __init__(self, *args, **kwargs):
        self.name = None
        self.comment = None
        self.hidden = None
        self.closed = None
        self.simplified = None
        self.mode = None
        self.border = None
        self.fill = None
        self.points = None
        #Non-attributes
        self.coordSys = None
        self.image = None # Only used if image contour 
        self.transform = None 
        self.shape = None
        self.processArguments(args, kwargs)
    def processArguments(self, args, kwargs):
        # 1) ARGS
        for arg in args:
            try:
                self.update(arg)
            except Exception, e:
                print('Could not process Contour arg:%s\n\t'%str(arg)+str(e))
        # 2) KWARGS
        for kwarg in kwargs:
            try:
                self.update(kwarg)
            except Exception, e:
                print('Could not process Contour kwarg:%s\n\t'%str(kwarg)+str(e))
# MUTATORS
    def update(self, *args): #=== Kwargs eventually
        for arg in args:
            # Dictionary
            if type(arg) == type({}):
                for key in arg:
                    # Dict:attributes
                    if key in self.__dict__:
                        self.__dict__[key] = arg[key]
            # Transform
            elif arg.__class__.__name__ == 'Transform':
                self.transform = arg
            # Image
            elif arg.__class__.__name__ == 'Image':
                self.image = arg
# ACCESSORS
    def __eq__(self, other):
        '''Allows use of == between multiple contours.'''
        comparisonDict1 = {}
        for key in self.__dict__:
            if key not in ['shape','comment','hidden','image']:
                comparisonDict1[key] = self.__dict__[key]
        comparisonDict2 = {}
        for key in other.__dict__:
            if key not in ['shape','comment','hidden','image']:
                comparisonDict2[key] = other.__dict__[key]
        return (comparisonDict1 == comparisonDict2)
    def __ne__(self, other):
        '''Allows use of != between multiple contours.'''
        return not self.__eq__(other)
# transform/shape operations
    def convertToBioCoords(self, mag):
        '''converts points to biological coordinate system and performs appropraite updates to shape.'''
        if self.coordSys == 'bio':
            return 'Already in biological coordinate system -- abort.'
        self.points = self.transform.worldpts(self.points, mag)
        self.coordSys = 'bio'
        self.popShape() # repopulate shape
    def convertToPixCoords(self, mag):
        '''Converts points to pixel coordinate system and performs appropraite updates to shape.'''
        if self.coordSys == 'pix':
            return 'Already in pixel coordinate system -- abort.'
        self.points = self.transform.imagepts(self.points, mag)
        self.coordSys = 'pix'
        self.popShape() # repopulate shape
    def popShape(self):
        '''Adds polygon object (shapely) to self._shape'''
        # Closed trace
        if self.closed == True:
            # If image contour, multiply pts by mag before inverting transform
            if self.image.__class__.__name__ == 'Image':
                mag = self.image.mag
                xvals = [pt[0]*mag for pt in self.points]
                yvals = [pt[1]*mag for pt in self.points]
                pts = zip(xvals,yvals)
            else:
                if len(self.points) < 3:
                    return None
                pts = self.points
            self.shape = Polygon( self.transform.worldpts(pts) ) #===
        # Open trace
        elif self.closed == False and len(self.points)>1:
            self.shape = LineString( self.transform.worldpts(self.points) ) #===
        else:
            print('\nInvalid shape characteristics: '+self.name)
            print('Quit for debug')
            quit() # for dbugging
    def box(self):
        '''Returns bounding box of shape (shapely) library'''
        if self.shape != None:
            minx, miny, maxx, maxy = self.shape.bounds
            return box(minx, miny, maxx, maxy)
        else:
            print('NoneType for shape: '+self.name)
# mergeTool functions
    def overlaps(self, other, threshold=(1+2**(-17))):
        '''Return 0 if no overlap.
        For closed traces: return 1 if AoU/AoI < threshold, return AoU/AoI if not < threshold
        For open traces: return 0 if # pts differs or distance between parallel pts > threshold
                         return 1 otherwise'''
        if self.shape == None:self.popShape()
        if other.shape == None:other.popShape()
        # Check bounding box (reduces comp. time for non-overlapping contours)
        if (not self.box().intersects(other.box()) and
            not self.box().touches(other.box()) ):
            return 0
        # Check if both same type of contour
        if self.closed != other.closed:
            return 0
        # Closed contours
        if self.closed:
            # check if both are consistent directions (cw/ccw) to prevent reverse contours from conflicting with normal ones
            if self.isReverse() != other.isReverse():
                return 0
            AoU = self.shape.union( other.shape ).area
            AoI = self.shape.intersection( other.shape ).area
            if AoI == 0:
                return 0
            elif AoU/AoI >= threshold: #===
                return AoU/AoI # Returns actual value, not 0 or 1
            elif AoU/AoI < threshold:
                return 1
        # Open contours
        if not self.closed:
            if len( self.points ) != len( other.points ):
                return 0
            def distance(pt0, pt1):
                return math.sqrt( (pt0[0] - pt1[0])**2 + (pt0[1] - pt1[1])**2 )
            # Lists of world coords to compare
            a = self.transform.worldpts(self.points)
            b = other.transform.worldpts(other.points)
            distlist = [distance(a[i],b[i]) for i in range(len(self.points))] 
            for elem in distlist:
                if elem > threshold:
                    return 0
        return 1
# curationTool functions
    def getLength(self):
        '''Returns the sum of all line segments in the contour object'''
        length = 0
        for index in range( len(self.points) ):
            if index+1 >= len(self.points): # stop when outside index range
                break
            pt = self.points[index]
            nextPt = self.points[index+1]
            length += (((nextPt[0]-pt[0])**2)+((nextPt[1]-pt[1])**2))**(0.5)
        if self.closed: # If closed object, add distance between 1st and last pt too
            length += (((self.points[0][0]-self.points[-1][0])**2)+((self.points[0][1]-self.points[-1][1])**2))**(0.5)
        return length #=== sqrt is taxing computation; reimplement with 1 sqrt at end?
    def getStartEndCount(self, series):
        '''Returns the start, end, and count values for this contour in given series. Determined by self.name only'''
        return series.getStartEndCount(self.name)
    def getVolume(self, series):
        return series.getVolume(self.name)
    def getSurfaceArea(self, series):
        return series.getSurfaceArea(self.name)
    def getFlatArea(self, series):
        return series.getFlatArea(self.name)
    def isReverse(self):
        '''Returns true if contour is a reverse trace (negative area)'''
        if self.shape is None:
            self.popShape()
        if self.closed:
            ring = LinearRing(self.shape.exterior.coords) # convert polygon to ring
            return not ring.is_ccw # For some reason, the opposite is true (image vs biological coordinate system?)
        else:
            return False
    def isInvalid(self):
        '''Returns true if this is an invalid contour.'''
        if self.closed and len(self.points) < 3:
            return True