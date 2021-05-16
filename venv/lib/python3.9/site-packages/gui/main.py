'''Contains graphical components of PyRECONSTRUCT that are used accross multple tools.'''
from PySide.QtCore import *
from PySide.QtGui import *

from pyrecon.main import openSeries
# Pyrecon tool modules imported when called by their functions below

class PyreconMainWindow(QMainWindow):
    '''Main PyRECONSTRUCT window.'''
    def __init__(self, *args, **kwargs):
        QMainWindow.__init__(self)
        self.setWindowTitle('PyRECONSTRUCT')
        self.loadMenus()
        self.show()
        newSize = QDesktopWidget().availableGeometry().size() / 4
        self.resize( newSize )
        self.statusBar().showMessage('Ready! Welcome to PyRECONSTRUCT')
    def loadMenus(self):
        self.toolsMenu = self.menuBar().addMenu("&Tools")
        self.loadToolsMenu()
        self.helpMenu = self.menuBar().addMenu("&Help")
    def loadToolsMenu(self):
        # 1) Create Actions
        # - gitTool
        gitAction = QAction( QIcon(), 'gitTool', self)
        gitAction.triggered.connect( self.loadGitTool )
        gitAction.setStatusTip( 'Open git widget' )
        # - mergeTool
        mergeAction = QAction( QIcon(), 'mergeTool', self ) #QIcon() is null, but necessary for Action creation
        mergeAction.triggered.connect( self.loadMergeTool )
        mergeAction.setStatusTip( 'Open merge widget' )
        # - calibrationTool
        calibAction = QAction( QIcon(), 'calibrationTool', self )
        calibAction.triggered.connect( self.loadCalibrationTool )
        calibAction.setStatusTip( 'Open calibration widget' )
        # - excelTool
        excelAction = QAction( QIcon(), 'excelTool', self )
        excelAction.triggered.connect( self.loadExcelTool )
        excelAction.setStatusTip( 'Open excel widget' )
        # - curationTool
        curateAction = QAction( QIcon(), 'curationTool', self )
        curateAction.triggered.connect( self.loadCurationTool )
        curateAction.setStatusTip( 'Open curation widget' )
        # 2) Add actions to toolbars
        self.toolsMenu.addAction( gitAction )
        self.toolsMenu.addAction( mergeAction )
        self.toolsMenu.addAction( calibAction )
        self.toolsMenu.addAction( excelAction )
        self.toolsMenu.addAction( curateAction )
    def loadMergeTool(self):
        from pyrecon.tools.mergeTool.main import createMergeSet
        from pyrecon.gui.mergeTool.main import MergeSetWrapper
        loadDialog = DoubleSeriesLoad() # User locates 2 series
        s1 = openSeries(loadDialog.output[0])
        s2 = openSeries(loadDialog.output[1])
        mSet = createMergeSet( s1, s2 )
        self.setCentralWidget( MergeSetWrapper(mSet) )
    def loadCurationTool(self):
        from pyrecon.gui.curationTool.curationGUI import curationToolStuff
        # Left dockWidget: load series/options
        self.curateSelector = QDockWidget()
        self.curationTool = curationToolStuff(self)
        self.curateSelector.setWidget( self.curationTool )
        self.addDockWidget( Qt.LeftDockWidgetArea, self.curateSelector )
        self.setCentralWidget(self.curationTool.outputWidget)
    def loadCalibrationTool(self):
        from pyrecon.gui.calibrationTool.calibrationGUI import calibrationToolStuff
        # Left dockWidget: load series/options
        self.calibSelector = QDockWidget()
        self.calibrationTool = calibrationToolStuff(self)
        self.calibSelector.setWidget( self.calibrationTool )
        self.addDockWidget( Qt.LeftDockWidgetArea, self.calibSelector )
    def loadExcelTool(self):
        from pyrecon.gui.excelTool.excelGUI import excelToolWindow
        # Left dockWidget
        self.excelSelector = QDockWidget()
        self.excelTool = excelToolWindow(self)
        self.excelSelector.setWidget( self.excelTool )
        self.addDockWidget( Qt.LeftDockWidgetArea, self.excelSelector)
    def loadGitTool(self):
        # importing mergeTool stuff here was the only way to get it to work
        from pyrecon.tools.mergeTool.main import createMergeSet
        from pyrecon.gui.mergeTool.main import MergeSetWrapper
        from pyrecon.gui.gitTool.main import main as gitMain
        self.setCentralWidget( gitMain() ) 

# Helper widgets
class BrowseWidget(QWidget):
    '''Provides a QLineEdit and button for browsing through a file system. browseType can be directory, file or series but defaults to directory.'''
    def __init__(self, browseType='directory'):
        QWidget.__init__(self)
        self.loadObjects(browseType)
        self.loadFunctions(browseType)
        self.loadLayout()
    def loadObjects(self, browseType):
        # Path entry area
        self.path = QLineEdit()
        if browseType == 'directory':
            title = 'Enter or browse path to directory'
        elif browseType == 'series':
            title = 'Enter or browse path'
        else:
            title = 'Enter or browse path to file'
        self.path.setText(title)
        # Browse button
        self.browseButton = QPushButton()
        self.browseButton.setText('Browse')
    def loadFunctions(self, browseType):
        if browseType == 'directory':
            self.browseButton.clicked.connect( self.browseDir )
        elif browseType == 'series':
            self.browseButton.clicked.connect( self.browseSeries )
        else:
            self.browseButton.clicked.connect( self.browseFile )
    def loadLayout(self):
        hbox = QHBoxLayout()
        hbox.addWidget(self.path)
        hbox.addWidget(self.browseButton)
        self.setLayout(hbox)
    def browseDir(self):
        dirName = QFileDialog.getExistingDirectory(self)
        self.path.setText( str(dirName) )
    def browseFile(self):
        fileName = QFileDialog.getOpenFileName(self, "Open File", "/home/")
        self.path.setText( str(fileName[0]) )
    def browseSeries(self):
        fileName = QFileDialog.getOpenFileName(self, "Open Series", "/home/", "Series File (*.ser)")
        self.path.setText( str(fileName[0]) )

class BrowseOutputDirectory(QDialog):
    '''Starts a popup dialog for choosing a directory in which to save a series'''
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.loadObjects()
        self.loadFunctions()
        self.loadLayout()
        self.exec_()
    def loadObjects(self):
        self.path = BrowseWidget()
        self.doneBut = QPushButton() 
    def loadFunctions(self):
        self.doneBut.setText('Write Series')
        self.doneBut.clicked.connect( self.finish )
    def loadLayout(self):
        main = QVBoxLayout()
        main.addWidget(self.path)
        main.addWidget(self.doneBut)
        self.setLayout(main)
    def finish(self):
        self.output = str(self.path.path.text())
        if 'Enter or browse' not in self.output or self.output == '':
            self.done(1)
        else:
            msg=QMessageBox()
            msg.setText('Invalid output directory: '+str(self.output))
            msg.exec_()
            return

class SingleSeriesLoad(QDialog):
    '''Dialog for loading series files into memory as pyrecon.classes.Series objects'''
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.loadObjects()
        self.loadFunctions()
        self.loadLayout()
        self.exec_()
    def loadObjects(self):
        self.series = BrowseWidget(browseType='series')
        self.closeButton = QPushButton()
        self.closeButton.setText('Load Series')
    def loadFunctions(self):
        self.closeButton.clicked.connect( self.loadClose )
    def loadLayout(self):
        vbox = QVBoxLayout()
        vbox.addWidget(self.series)
        vbox.addWidget(self.closeButton)
        self.setLayout(vbox)
    def loadClose(self):
        # Add paths to self.output
        self.output = str(self.series.path.text())
        self.close()

class DoubleSeriesLoad(QDialog):
    '''Dialog for loading series files into memory as pyrecon.classes.Series objects'''
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.loadObjects()
        self.loadFunctions()
        self.loadLayout()
        self.exec_()
    def loadObjects(self):
        self.series1 = BrowseWidget(browseType='series')
        self.series2 = BrowseWidget(browseType='series')
        self.closeButton = QPushButton()
        self.closeButton.setText('Load Series')
    def loadFunctions(self):
        self.closeButton.clicked.connect( self.loadClose )
    def loadLayout(self):
        vbox = QVBoxLayout()
        vbox.addWidget(self.series1)
        vbox.addWidget(self.series2)
        vbox.addWidget(self.closeButton)
        self.setLayout(vbox)
    def loadClose(self):
        # Add paths to self.output
        self.output = ( str(self.series1.path.text()),
                        str(self.series2.path.text()) )
        self.close()

if __name__ == '__main__':
    app = QApplication.instance()
    if app == None:
        app = QApplication([])
    a = PyreconMainWindow()
    app.exec_()