import math
class ZContour:
    def __init__(self, *args, **kwargs):
        self.name = None
        self.closed = None
        self.border = None
        self.fill = None
        self.mode = None 
        self.points = None
        self.processArguments(args, kwargs)
    def processArguments(self, args, kwargs):
        # 1) ARGS
        for arg in args:
            try:
                self.update(arg)
            except:
                print('Could not process ZContour arg:%s\n\t'%str(arg)+str(e))
        # 2) KWARGS
        for kwarg in kwargs:
            try:
                self.update(kwarg)
            except:
                print('Could not process ZContour kwarg:%s\n\t'%str(kwarg)+str(e))
    def update(self, *args): #=== KWARGS eventually
        for arg in args:
            # Dictionary
            if type(arg) == type({}):
                for key in arg:
                    # Dict:attributes
                    if key in self.__dict__:
                        self.__dict__[key] = arg[key]
    def __eq__(self,other):
        return (self.name == other.name and
                self.points == other.points and
                self.closed == other.closed)
    def __ne__(self,other):
        return not self.__eq__(other)
    # mergeTool Functions
    def overlaps(self, other, threshold=(1+2**(-17))):
        def distance(pt0, pt1):
            '''Distance formula: return distance between two points.'''
            return math.sqrt( (pt0[0] - pt1[0])**2 + (pt0[1] - pt1[1])**2 )
        # Check equal # pts
        if len(self.points) != len(other.points):
            return 0
        # Build list of min distance between pts
        distlist = []
        for pt in self.points:
            ptdistances = []
            for pt2 in other.points:
                if pt[2] == pt2[2]: # if in same section
                    dist = distance(pt[0:2],pt[0:2])
                    ptdistances.append( dist )
            if len(ptdistances) != 0:
                distlist.append( min(ptdistances) )
        # check for any distances above threshold
        for dist in distlist:
            if dist > threshold: # no matching point
                return 0
        return 1  