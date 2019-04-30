import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import json
import sys
import urllib, urllib2

class SharedGDriveUtils():

  def __init__(self, SharedGDriveFolderId):
    self.gdriveRoot = SharedGDriveFolderId    
  
  def canAccess(self):
    try:
      self._listFolderFromGoogleDrive(self.gdriveRoot,0)
      return True
    except:
      return False
        
  def listDirectory(self, dirname='',depth=0):
    try:
      if dirname=='' or dirname=='.': return self._listFolderFromGoogleDrive(self.gdriveRoot,depth)
      directoryId = self._getResourceId(self.gdriveRoot, dirname)
      if directoryId==None: return []
      return self._listFolderFromGoogleDrive(directoryId, depth)
    except:
      return []
  
  def downloadFile(self, src, dst):
    srcId = self._getResourceId(self.gdriveRoot, src)
    if srcId==None: return None
    if not os.path.exists(os.path.dirname(dst)): os.makedirs(os.path.dirname(dst))
    self._downloadFileFromGoogleDrive(srcId, dst)

  def _downloadFileFromGoogleDrive(self,file_id, destination):  
    queryParameters = {"export":"download", "id":file_id}
    queryParameters =  dict((k, v) for k, v in queryParameters.iteritems() if v)
    queryString = "?%s" % urllib.urlencode(queryParameters)
    URL = "https://drive.google.com/uc?export=download"  
    requestUrl = URL + queryString
    request = urllib2.Request(requestUrl)
    response = urllib2.urlopen(request)
    self._downloadURLStreaming(response, destination)
    cookie = response.headers.get('Set-Cookie')
    if os.stat(destination).st_size<10000:
      confirmationURL = self._getConfirmationURL(destination)
      if confirmationURL:
        confirmationURL = 'https://drive.google.com'+confirmationURL.replace('&amp;','&')
        req2 = urllib2.Request(confirmationURL)
        req2.add_header('cookie', cookie)
        response = urllib2.urlopen(req2)
        self._downloadURLStreaming(response, destination)
  
  def _downloadURLStreaming(self,response,destination):
    slicer.app.processEvents()
    import time
    t0 = time.time()
    if response.getcode() == 200:
      destinationFile = open(destination, "wb")
      bufferSize = 1024*1024
      print 'Downloading ',
      while 1:
        buffer = response.read(bufferSize)
        slicer.app.processEvents()
        if not buffer: break
        destinationFile.write(buffer)
      destinationFile.close()
      print '... [DONE]'
    t1 = time.time()
    print 'time for downloading '+str(t1-t0)+' seconds'
    
  def _getConfirmationURL(self,destination):
    with open(destination) as f:
      for line in f:        
        starttoken='/uc?export=download&amp;'
        start = line.find(starttoken)
        if start!=-1:
          line = line[start:]
          end = line.find('">')
          value = line[0:end]
          return value.decode('string_escape')
    return None
                   
  def _listFolderFromGoogleDrive(self,folder_id,depth=0):
    URL = "https://drive.google.com/drive/folders/"+folder_id+"?usp=sharing"
    request = urllib2.Request(URL)
    response = urllib2.urlopen(request)
    if response.getcode()!=200:
      print ('Error accessing resource')
      return
    jsondata = self._GetDriveIvd(response)
    jsondata = json.loads(jsondata)
    dirlist = jsondata[0]
    dircontent = []
    if dirlist is not None:
      for item in dirlist:
        identifier = item[0]
        name = item[2]
        ftype = item[3]
        fsize = item[13]
        isFolder = ftype=='application/vnd.google-apps.folder'
        dircontent.append({'name':name, 'id':identifier, 'type': ftype, 'isFolder':isFolder, 'size':fsize})
        if isFolder and depth>0:
          subdir = self._listFolderFromGoogleDrive(identifier,depth-1)
          if subdir is not None:
            for sub in subdir:
              subname = os.path.join(name, sub['name'])
              dircontent.append({'name':subname, 'id':sub['id'], 'type': sub['type'], 'isFolder':sub['isFolder'], 'size':sub['size']})
    return dircontent
    
  def _splitPath(self, p):
    a,b = os.path.split(p)
    return (self._splitPath(a) if len(a) and len(b) else []) + [b]  
    
  def _getResourceId(self, folder_id, relativePath):
    pathParts = self._splitPath(relativePath)
    finalNode = len(pathParts)==1
    currentName = pathParts[0]
    dircontent = self._listFolderFromGoogleDrive(folder_id)
    for d in dircontent:
      if d['name']==currentName:
        if finalNode: return d['id']
        else:
          remainingPath = pathParts[1]
          for p in pathParts[2:]: remainingPath = os.path.join(remainingPath, p)      
          return self._getResourceId(d['id'], remainingPath)
    return None

  def _GetDriveIvd(self,response):
    for line in response:
      starttoken='window[\'_DRIVE_ivd\'] = \''
      start = line.find(starttoken)
      if start!=-1:
        line = line[start+len(starttoken):]
        end = line.find('\'')
        value = line[0:end]
        return value.decode('string_escape')
    return None

class lapdMouseBrowserWindow(qt.QMainWindow):

  def __init__(self, parent=None):
    super(lapdMouseBrowserWindow, self).__init__(parent)
    self.table = None
    self.workingDirectory = None
    self.isEditing = False
    self.datasets = []
    self.remoteFolderId = '1-_CeHHmk94y_08KRzexUhTdtdFMxMs_8'
    self.localCashFolder = os.path.join(os.path.expanduser("~"),'data','R01_lapdmousetest')
    self.projectURL='https://lapdmouse.iibi.uiowa.edu'
    self.setupWindow()

  def setupWindow(self):
    self.setWindowTitle("lapdMouse Data Archive Browser")
    self.resize(1000,600)
    
    if 'lapdMouseDBBrowser' in slicer.util.moduleNames():
      self.modulePath = slicer.modules.lapdmousedbbrowser.path.replace("lapdMouseDBBrowser.py","")
    else:
      self.modulePath = '.'
    self.downloadIcon = qt.QIcon(os.path.join(self.modulePath,'Resources','Icons','download.png'))
    self.storedIcon = qt.QIcon(os.path.join(self.modulePath,'Resources','Icons','stored.png'))
    self.logo =  qt.QPixmap(os.path.join(self.modulePath,'Resources','Icons','lapdMouseDBBrowser.png'))
    
    self.banner = qt.QFrame()
    self.banner.setLayout(qt.QGridLayout())
    logo = qt.QLabel()
    logo.setPixmap(self.logo)
    self.banner.layout().addWidget(logo,0,0)    
    self.bannerTextBrowser = qt.QTextBrowser()
    self.bannerTextBrowser.setOpenExternalLinks(True)
    self.bannerTextBrowser.setMaximumHeight(120)
    text = "<h1>lapdMouse Data Archive Browser</h1>"
    text += "The lapdMouse data archive contains anatomically derived lung models and aerosol deposition measurements of mice for modeling and computational toxicology in mice."
    text += " For more details about available datasets, data representation, other software, and support, please visit the <a href=\""+self.projectURL+"\">lapdMouse project</a>"
    text += "<br />This work was supported in part by NIH project R01ES023863."    
    self.bannerTextBrowser.html=text
    self.banner.layout().addWidget(self.bannerTextBrowser,0,1)

    self.table = qt.QTableWidget(self)
    self.table.setRowCount(0)
    self.table.setColumnCount(1)
    self.table.setSizePolicy(qt.QSizePolicy.Expanding,qt.QSizePolicy.Expanding)
    self.table.setHorizontalHeaderLabels(["Dataset name"])#,"Status","Comment"])
    self.table.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
    self.table.setSelectionMode(qt.QAbstractItemView.SingleSelection)
    self.table.horizontalHeader().setStretchLastSection(True)
    self.table.connect("itemSelectionChanged()",self.onDatasetChanged)

    self.customForm = qt.QFrame()
    self.customForm.setLayout(qt.QFormLayout())
    self.customFormName = qt.QLineEdit("",self.customForm)
    self.customFormName.readOnly = True
    self.customForm.layout().addRow("Name",self.customFormName)
    self.customFormDatasetInfo = qt.QLabel('<a href=\"'+self.projectURL+'\">info</a>')
    self.customFormDatasetInfo.setTextFormat(1)
    self.customFormDatasetInfo.setOpenExternalLinks(True)
    self.customForm.layout().addRow("Info",self.customFormDatasetInfo)    
    self.customFormAction = qt.QFrame(self.customForm)
    self.customFormAction.setLayout(qt.QHBoxLayout())
    self.customFormAction.layout().setSpacing(0)
    self.customFormAction.layout().setMargin(0)
    self.customFormDownloadButton = qt.QPushButton("download standard file selection", self.customFormAction)
    self.customFormAction.layout().addWidget(self.customFormDownloadButton)
    self.customFormDownloadButton.connect("clicked()", self.onDownloadDataset)
    self.customFormLoadButton = qt.QPushButton("load standard file selection in Slicer", self.customFormAction)
    self.customFormAction.layout().addWidget(self.customFormLoadButton)
    self.customFormLoadButton.connect("clicked()", self.onLoadDataset)
    self.customForm.layout().addRow("Quick actions",self.customFormAction)
    self.customFormFiles = qt.QTableWidget(self.customForm)
    self.customFormFiles.setRowCount(0)
    self.customFormFiles.setColumnCount(3)
    self.customFormFiles.setHorizontalHeaderLabels(["Status","Filename", "Size"])
    self.customFormFiles.horizontalHeader().setSectionResizeMode(1, qt.QHeaderView.Stretch)
    self.customFormFiles.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
    self.customFormFiles.setMinimumHeight(400)
    self.customForm.layout().addRow("Files",self.customFormFiles)
    
    self.customFormAction2 = qt.QFrame(self.customForm)
    self.customFormAction2.setLayout(qt.QHBoxLayout())
    self.customFormAction2.layout().setSpacing(0)
    self.customFormAction2.layout().setMargin(0)
    self.customFormDownloadButton2 = qt.QPushButton("download selected files", self.customFormAction2)
    self.customFormAction2.layout().addWidget(self.customFormDownloadButton2)
    self.customFormDownloadButton2.connect("clicked()", self.onDownloadSelectedDataset)
    self.customFormDeleteButton2 = qt.QPushButton("delete selected files", self.customFormAction2)
    self.customFormAction2.layout().addWidget(self.customFormDeleteButton2)
    self.customFormDeleteButton2.connect("clicked()", self.onDeleteSelectedDataset)
    self.customFormLoadButton2 = qt.QPushButton("load selected files in Slicer", self.customFormAction2)
    self.customFormAction2.layout().addWidget(self.customFormLoadButton2)
    self.customFormLoadButton2.connect("clicked()", self.onLoadSelectedDataset)
    self.customForm.layout().addRow("",self.customFormAction2)
    
    splitView = qt.QSplitter(self)
    splitView.addWidget(self.table)
    splitView.addWidget(self.customForm)
    splitView.setSizes([200,800])

    self.updateTable()
    self.onDatasetChanged()
    self.setMenuWidget(self.banner)
    self.setCentralWidget(splitView)
    
  def load(self):
    self.datasets = [d['name'] for d in SharedGDriveUtils(self.remoteFolderId).listDirectory() if d["isFolder"]==True]
    if os.path.exists(self.localCashFolder):
      localFolders = [d for d in os.listdir(self.localCashFolder) if \
        os.path.isdir(os.path.join(self.localCashFolder,d))]
      self.datasets = list(set(self.datasets).union(set(localFolders)))
    self.datasets.sort()
    self.updateTable()
  
  def updateTable(self):
    self.table.setRowCount(len(self.datasets))
    for i in range(len(self.datasets)):
      self.updateTableElement(i)

  def updateTableElement(self, identifier):
    datasetname = self.datasets[identifier]
    self.table.setItem(identifier,0,qt.QTableWidgetItem(datasetname))
    
  def getSelectedId(self):
    datasetId = -1
    if len(self.table.selectedRanges()):
      datasetId = self.table.selectedRanges()[0].bottomRow()
    return datasetId
  
  def onDatasetChanged(self):
    datasetId = self.getSelectedId()
    if datasetId==-1: # clear data set into
      pass
      return
    datasetname = self.datasets[datasetId]
    self.updateForm()

  def updateForm(self):
    datasetId = self.getSelectedId()
    if datasetId==-1: # clear form
      pass
    datasetname = self.datasets[datasetId]
    self.customFormName.text = datasetname
    url = self.projectURL+'/ViewMD/index.html?src=../resources/db_info/'+datasetname+'_Info.md'
    self.customFormDatasetInfo.text='<a href=\"'+url+'\">info</a>'
    datasetFiles = self.listFilesForDataset(datasetname)    
    self.customFormFiles.setRowCount(len(datasetFiles))
    for i in range(len(datasetFiles)):
      fname = datasetFiles[i]["name"]
      fsize = datasetFiles[i]["size"]
      remoteName = os.path.join(datasetname,fname.replace('/',os.sep))
      localName = os.path.join(self.localCashFolder,remoteName)
      downloaded = os.path.exists(localName)
      self.customFormFiles.setItem(i,0,qt.QTableWidgetItem())
      self.customFormFiles.item(i,0).setIcon(self.storedIcon if downloaded else self.downloadIcon)
      self.customFormFiles.item(i,0).setToolTip('downloaded' if downloaded else 'available for download')
      self.customFormFiles.setItem(i,1,qt.QTableWidgetItem(fname))
      self.customFormFiles.setItem(i,2,qt.QTableWidgetItem(self.hrSize(fsize)))
  
  def listFilesForDataset(self,datasetname):
    remoteFolderContent = SharedGDriveUtils(self.remoteFolderId).listDirectory(datasetname, 0)
    files = [f for f in remoteFolderContent if not f['isFolder']]
    filenames = [f['name'] for f in files]
    localDatasetDirectory = os.path.join(self.localCashFolder,datasetname)
    if os.path.exists(localDatasetDirectory):
      localFiles = [f for f in os.listdir(localDatasetDirectory) if \
        (os.path.isfile(os.path.join(localDatasetDirectory,f)) and \
        not f.startswith('.'))]
      for f in localFiles:
        if not f in filenames:
          files.append({'name':f, 'size':\
            os.path.getsize(os.path.join(localDatasetDirectory,f))})
    return files    
  
  def onDownloadDataset(self):
    datasetId = self.getSelectedId()
    if datasetId==-1: return
    datasetname = self.datasets[datasetId]
    selectedFiles = []
    defaultFiles = ['AutofluorescentSub4.mha','AerosolNormalizedSub4.mha', \
      'Lobes.nrrd','AirwayOutlets.vtk', 'AirwayWallDeposition.vtk']
    for df in defaultFiles:
      for f in self.listFilesForDataset(datasetname):
        if f['name'].find(df)!=-1:
          selectedFiles.append(f['name'])
    self.downloadFiles(datasetname, selectedFiles)
    self.updateForm()
    
  def getSelectedFiles(self):
    files = [self.customFormFiles.item(index.row(),1).text() for index in self.customFormFiles.selectionModel().selectedRows()]
    return files    
    
  def onDownloadSelectedDataset(self):
    datasetId = self.getSelectedId()
    if datasetId==-1: return
    datasetname = self.datasets[datasetId]
    files = self.getSelectedFiles()
    self.downloadFiles(datasetname, files)
    self.updateForm()
    
  def onDeleteSelectedDataset(self):
    datasetId = self.getSelectedId()
    if datasetId==-1: return
    datasetname = self.datasets[datasetId]
    files = self.getSelectedFiles()
    self.deleteFiles(datasetname, files)
    self.updateForm()
    
  def downloadFiles(self, datasetname, files, askForConfirmation=True):
    if askForConfirmation:
      filestats = self.listFilesForDataset(datasetname)
      filesToDownload = [f for f in filestats if f['name'] in files and \
        not os.path.exists(os.path.join(self.localCashFolder,datasetname,f['name']))]
      if len(filesToDownload)==0: return True
      s = 'Downloading '+str(len(filesToDownload))+' file(s) with '+\
        self.hrSize(sum(f['size'] for f in filesToDownload))+'.'+\
        ' This could take some time. Do you want to continue?'
      confirmDownload = qt.QMessageBox.question(self,'Download?', s, qt.QMessageBox.Yes, qt.QMessageBox.No)
      if confirmDownload!=qt.QMessageBox.Yes:
        return False
    
    pd = qt.QProgressDialog('Downloading file(s)...', 'Cancel', 0, len(files)+2, slicer.util.mainWindow())
    pd.setModal(True)
    pd.setMinimumDuration(0)
    pd.show()
    slicer.app.processEvents()
    for f in files:   
      if pd.wasCanceled: break
      pd.setValue(files.index(f)+1)
      slicer.app.processEvents()   
      remoteName = os.path.join(datasetname,f.replace('/',os.sep))
      localName = os.path.join(self.localCashFolder,remoteName)
      if not os.path.exists(localName):
        print 'downloading '+remoteName
        try:
          SharedGDriveUtils(self.remoteFolderId).downloadFile(remoteName, localName)
        except:
          print 'error downloading file: '
          print sys.exc_info()[0]
    pd.setValue(len(files)+2)
    return True
    
  def deleteFiles(self, datasetname, files):
    for f in files:
      remoteName = os.path.join(datasetname,f.replace('/',os.sep))
      localName = os.path.join(self.localCashFolder,remoteName)
      if os.path.exists(localName):
        print "deleting file "+localName
        os.remove(localName)
      
  def onLoadDataset(self):
    datasetId = self.getSelectedId()
    if datasetId==-1: return
    datasetname = self.datasets[datasetId]
    selectedFiles = []
    defaultFiles = ['AutofluorescentSub4.mha','AerosolNormalizedSub4.mha', \
      'Lobes.nrrd','AirwayOutlets.vtk', 'AirwayWallDeposition.vtk']
    for df in defaultFiles:
      for f in self.listFilesForDataset(datasetname):
        if f['name'].find(df)!=-1:
          selectedFiles.append(f['name'])
    if self.downloadFiles(datasetname, selectedFiles):
      self.updateForm()
      self.loadFiles(datasetname, selectedFiles)
  
  def onLoadSelectedDataset(self):
    datasetId = self.getSelectedId()
    if datasetId==-1: return
    datasetname = self.datasets[datasetId]
    files = self.getSelectedFiles()
    if self.downloadFiles(datasetname, files):
      self.updateForm()
      self.loadFiles(datasetname, files)
  
  def loadFiles(self, datasetname, files):
    pd = qt.QProgressDialog('Loading file(s) in Slicer...', 'Cancel', 0, len(files)+2, slicer.util.mainWindow())
    pd.setModal(True)
    #pd.setMinimumDuration(0)
    pd.show()
    slicer.app.processEvents()
    for f in files:
      if pd.wasCanceled: break
      pd.setValue(files.index(f)+1)
      slicer.app.processEvents()
      remoteName = os.path.join(datasetname,f.replace('/',os.sep))
      localName = os.path.join(self.localCashFolder,remoteName)
      if not os.path.exists(localName): continue
      try:
        print 'loading '+localName 
        self.loadFile(localName)
      except:
        print 'error loading file: '
        print sys.exc_info()[0]
    pd.setValue(len(files)+2)
    pd.hide()
  
  def loadFile(self, filename):
    lapdMouseDBBrowser.loadColorTables()
    name, extension = os.path.splitext(filename)
    if extension=='.mha': self.loadVolume(filename)
    elif extension=='.nrrd': self.loadLabelmap(filename)
    elif extension=='.vtk': self.loadMesh(filename)
    elif extension=='.meta': self.loadTree(filename)
    elif extension=='.csv': self.loadMeasurements(filename)
    else:
      print 'Warning: can\'t load: '+filename
    
  def loadVolume(self, filename):
    slicer.util.loadVolume(filename)
    
    name = os.path.splitext(os.path.basename(filename))[0]
    nodes = slicer.util.getNodes(name+'*')
    node = nodes.values()[len(nodes.values())-1]
    
    node.CreateDefaultDisplayNodes()
    nd = node.GetDisplayNode()
    
    if (str(os.path.basename(filename)).find('Aerosol')!=-1):
      colorLUT = slicer.util.getFirstNodeByClassByName('vtkMRMLColorTableNode','Red')
      if colorLUT: nd.SetAndObserveColorNodeID(colorLUT.GetID())
      nd.SetAutoWindowLevel(False)
      if (str(os.path.basename(filename)).find('Normalized')!=-1): nd.SetWindowLevel(10,5)
      else: nd.SetWindowLevel(1000,500)
      
    if (str(os.path.basename(filename)).find('Autofluorescent')!=-1):
      colorLUT = slicer.util.getFirstNodeByClassByName('vtkMRMLColorTableNode','Green')
      if colorLUT: nd.SetAndObserveColorNodeID(colorLUT.GetID())
      nd.SetAutoWindowLevel(False)
      nd.SetWindowLevel(3000,1500)
  
  def loadLabelmap(self, filename):
    self.turnLabelmapsToOutline()
    slicer.util.loadLabelVolume(filename)
    
    name = os.path.splitext(os.path.basename(filename))[0]
    nodes = slicer.util.getNodes(name+'*')
    node = nodes.values()[len(nodes.values())-1]
    
    colorLUT = None
    if (str(os.path.basename(filename)).find('Lobes.nrrd')!=-1):
      colorLUT = slicer.util.getFirstNodeByClassByName('vtkMRMLColorTableNode','lapdMouseLobes')
    else:
      colorLUT = slicer.util.getFirstNodeByClassByName('vtkMRMLColorTableNode','lapdMouseSegments')
    if colorLUT:
      nd=node.GetDisplayNode()
      nd.SetAndObserveColorNodeID(colorLUT.GetID())
  
  def getTransformNode(self):
    if len(slicer.util.getNodes('ras2lps*'))>0:
      transformNode = slicer.util.getNode('ras2lps*')
    else:
      transformNode = slicer.vtkMRMLLinearTransformNode()
      transformNode.SetScene(slicer.mrmlScene)
      transformNode.HideFromEditorsOn()
      transformNode.SetName("ras2lps")
      t = vtk.vtkTransform()
      t.Identity()
      t.Scale([-1, -1, 1])
      transformNode.SetMatrixTransformToParent(t.GetMatrix())
      slicer.mrmlScene.AddNode(transformNode)
    return transformNode
    
  def loadMesh(self, filename):
    slicer.util.loadModel(filename)
    name = os.path.splitext(os.path.basename(filename))[0]
    nodes = slicer.util.getNodes(name+'*')
    node = nodes.values()[len(nodes.values())-1]
    
    # specify transform
    transformNode = self.getTransformNode()
    node.SetAndObserveTransformNodeID(transformNode.GetID())
    
    node.CreateDefaultDisplayNodes()
    nd = node.GetDisplayNode()
    if node.GetPolyData().GetPointData().GetNumberOfArrays()>0:
      nd.SetActiveScalarName(node.GetPolyData().GetPointData().GetArrayName(0))
    
    if (str(os.path.basename(filename)).find('AirwayWallDeposition')!=-1):   
      colorLUT = slicer.util.getFirstNodeByClassByName('vtkMRMLColorTableNode','Warm1')
      if colorLUT: nd.SetAndObserveColorNodeID(colorLUT.GetID())
      nd.SetScalarRangeFlag(slicer.vtkMRMLDisplayNode.UseManualScalarRange)
      nd.SetAutoScalarRange(False)
      nd.SetScalarRange(0,10)
    
    if (str(os.path.basename(filename)).find('AirwayWall.vtk')!=-1):      
      colorLUT = slicer.util.getFirstNodeByClassByName('vtkMRMLColorTableNode','BlueRed')
      if colorLUT: nd.SetAndObserveColorNodeID(colorLUT.GetID())
      nd.SetScalarRangeFlag(slicer.vtkMRMLDisplayNode.UseManualScalarRange)
      nd.SetAutoScalarRange(False)
      nd.SetScalarRange(0,1)
    
    if (str(os.path.basename(filename)).find('AirwaySegments')!=-1):
      colorLUT = slicer.util.getFirstNodeByClassByName('vtkMRMLColorTableNode','lapdMouseSegments')
      if colorLUT: nd.SetAndObserveColorNodeID(colorLUT.GetID())
      nd.SetScalarRangeFlag(slicer.vtkMRMLDisplayNode.UseColorNodeScalarRange)
    
    if (str(os.path.basename(filename)).find('AirwayOutlets')!=-1):
      colorLUT = slicer.util.getFirstNodeByClassByName('vtkMRMLColorTableNode','lapdMouseOutlets')
      if colorLUT: nd.SetAndObserveColorNodeID(colorLUT.GetID())
      nd.SetScalarRangeFlag(slicer.vtkMRMLDisplayNode.UseColorNodeScalarRange)
      
    nd.SetScalarVisibility(True)
    nd.BackfaceCullingOff()
    nd.SetSliceIntersectionVisibility(True)
  
  def loadTree(self, filename):
    import lapdMouseVisualizer
    logic = lapdMouseVisualizer.lapdMouseVisualizerLogic()
    tree = logic.readMetaTree(filename)
    model = logic.tree2Model(tree)
    model.SetName(os.path.splitext(os.path.basename(filename))[0])
    model.SetScene(slicer.mrmlScene)
    model.CreateDefaultDisplayNodes()
    
    # specify transform  
    transformNode = self.getTransformNode()
    model.SetAndObserveTransformNodeID(transformNode.GetID())
    slicer.mrmlScene.AddNode(model)
    
    # change color
    if (str(os.path.basename(filename)).find('AirwayTree')!=-1):
      display = model.GetDisplayNode()
      display.SetActiveScalarName('BranchLabel')
      colorLUT = slicer.util.getFirstNodeByClassByName('vtkMRMLColorTableNode','Rainbow')
      if colorLUT: display.SetAndObserveColorNodeID(colorLUT.GetID())
      
  def loadMeasurements(self, filename):
    import lapdMouseVisualizer
    success = slicer.util.loadNodeFromFile(filename, 'TableFile')
    if not success: return
    measurementsTable = slicer.util.getNodesByClass('vtkMRMLTableNode')[-1]
    logic = lapdMouseVisualizer.lapdMouseVisualizerLogic()
    measurementsType = logic.getType(measurementsTable)
    model = logic.measurementsTable2Model(measurementsTable)
    if model.GetPolyData().GetNumberOfPoints()==0: # not compartments measurements
      return
    model.SetName(os.path.splitext(os.path.basename(filename))[0])
    model.SetScene(slicer.mrmlScene)
    model.CreateDefaultDisplayNodes()
        
    # specify transform  
    transformNode = self.getTransformNode()
    model.SetAndObserveTransformNodeID(transformNode.GetID())
    slicer.mrmlScene.AddNode(model)
    
    # change color
    display = model.GetDisplayNode()
    if measurementsType=='tree': display.SetActiveScalarName('BranchLabel')
    else: display.SetActiveScalarName('MeasurementMean')
    colorLUT = slicer.util.getFirstNodeByClassByName('vtkMRMLColorTableNode','Rainbow')
    if colorLUT: display.SetAndObserveColorNodeID(colorLUT.GetID())
    
  def turnLabelmapsToOutline(self):
    layoutManager = slicer.app.layoutManager()
    for sliceViewName in layoutManager.sliceViewNames():
      layoutManager.sliceWidget(sliceViewName).sliceController().showLabelOutline(True)
      
  def hrSize(self, bytes):
    if not bytes: return ''
    bytes = float(bytes)
    KB = bytes/1024
    if KB<1024: return "%.1f KB" % KB
    MB = KB/1024
    if MB<1024: return "%.1f MB" % MB
    GB = MB/1024
    return "%.1f GB" % GB

#
# lapdMouseDBBrowser
#

class lapdMouseDBBrowser(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "lapdMouseDBBrowser"
    self.parent.categories = ["lapdMouse"]
    self.parent.dependencies = []
    self.parent.contributors = ["Christian Bauer (Univeristy of Iowa)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
    Tool for accessing and viewing data from the of lapdMouse project data archive. For more details, visit the
    <a href="https://lapdmouse.iibi.uiowa.edu">lapdMouse project</a>.
    """
    self.parent.acknowledgementText = """
    This work was supported in part by NIH project R01ES023863.
""" # replace with organization, grant and thanks.
    lapdMouseDBBrowser.loadColorTables()
    
  @staticmethod
  def loadColorTables():
    lapdMouseDBBrowser.setupLobesColorTable()
    lapdMouseDBBrowser.setupSegmentsColorTable()
    lapdMouseDBBrowser.setupOutletsColorTable()
    
  @staticmethod
  def setupLobesColorTable():
    if len(slicer.util.getNodes('lapdMouseLobes'))>0: return
    colors = slicer.vtkMRMLColorTableNode()
    colors.SetTypeToUser()
    colors.SetAttribute("Category", "lapdMouse")
    colors.SetName('lapdMouseLobes')
    colors.SetHideFromEditors(True)
    colors.SetNumberOfColors(6)
    colors.NamesInitialisedOn()
    colors.GetLookupTable().SetRange(0,5)
    colors.SetColor(0,'background',0,0,0,0)
    colors.SetColor(1,'left lobe',1,0,0,1)
    colors.SetColor(2,'right cranial lobe',0,1,0,1)
    colors.SetColor(3,'right middle lobe',0,0,1,1)
    colors.SetColor(4,'right caudal lobe',1,1,0,1)
    colors.SetColor(5,'right accessory lobe',0,1,1,1)
    slicer.mrmlScene.AddNode(colors)
    
  @staticmethod
  def setupSegmentsColorTable():
    if len(slicer.util.getNodes('lapdMouseSegments'))>0: return
    numSegments = 5000
    colors = slicer.vtkMRMLColorTableNode()
    colors.SetTypeToUser()
    colors.SetAttribute("Category", "lapdMouse")
    colors.SetName('lapdMouseSegments')
    colors.SetHideFromEditors(True)
    colors.SetNumberOfColors(numSegments)
    colors.NamesInitialisedOn()
    colors.GetLookupTable().SetRange(0,numSegments)
    colors.SetColor(0,'background',0,0,0,0)
    import random
    random.seed(3) # seed 3: nothing too dark and first few generations reasonably well contrasted
    for i in range (1,numSegments):
      colors.SetColor(i, str(i),random.uniform(0.0,1.0),random.uniform(0.0,1.0),random.uniform(0.0,1.0),1)
    slicer.mrmlScene.AddNode(colors)
  
  @staticmethod
  def setupOutletsColorTable():
    if len(slicer.util.getNodes('lapdMouseOutlets'))>0: return
    numSegments = 5000
    colors = slicer.vtkMRMLColorTableNode()
    colors.SetTypeToUser()
    colors.SetAttribute("Category", "lapdMouse")
    colors.SetName('lapdMouseOutlets')
    colors.SetHideFromEditors(True)
    colors.SetNumberOfColors(numSegments)
    colors.NamesInitialisedOn()
    colors.GetLookupTable().SetRange(0,numSegments)
    colors.SetColor(0,'wall',1,0.67,0,1)
    import random
    random.seed(3) # seed 3: nothing too dark and first few generations reasonably well contrasted
    for i in range (1,numSegments):
      colors.SetColor(i, str(i),random.uniform(0.0,1.0),random.uniform(0.0,1.0),random.uniform(0.0,1.0),1)
    slicer.mrmlScene.AddNode(colors)

#
# lapdMouseDBBrowserWidget
#

class lapdMouseDBBrowserWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    
    settings = qt.QSettings()
    if settings.value("lapdMouseDBBrowserLocalCacheFolder", "")=="":
      settings.setValue("lapdMouseDBBrowserLocalCacheFolder", "./lapdMouse")
      settings.sync()
    databaseDirectory = settings.value("lapdMouseDBBrowserLocalCacheFolder")
    
    self.browserWindow = lapdMouseBrowserWindow()
    self.browserWindow.localCashFolder = databaseDirectory
    self.browserWindow.load()
    self.browserWindow.show()

    self.logic = lapdMouseDBBrowserLogic()

    # Instantiate and connect widgets ...

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "lapdMouse database"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    # extract/merge
    self.openBrowserWindowButton = qt.QPushButton("Show browser")
    self.openBrowserWindowButton.toolTip = "Open lapdMouse database browser window."
    self.openBrowserWindowButton.connect('clicked()', self.browserWindow.show)
    parametersFormLayout.addRow("Window:",self.openBrowserWindowButton)
    
    settingsCollapsibleButton = ctk.ctkCollapsibleButton()
    settingsCollapsibleButton.text = "Settings"
    self.layout.addWidget(settingsCollapsibleButton)
    settingsGridLayout = qt.QGridLayout(settingsCollapsibleButton)
    settingsCollapsibleButton.collapsed = False
    
    self.storagePath = self.browserWindow.localCashFolder
    storagePathLabel = qt.QLabel("Storage Folder: ")
    self.storagePathButton = ctk.ctkDirectoryButton()
    self.storagePathButton.directory = self.storagePath
    settingsGridLayout.addWidget(storagePathLabel,0,0,1,1)
    settingsGridLayout.addWidget(self.storagePathButton,0,1,1,4)
      
    self.storagePathButton.connect('directoryChanged(const QString &)',self.onStorageChanged)

    self.layout.addStretch(1)
  
  def onStorageChanged(self):
    self.browserWindow.localCashFolder = self.storagePathButton.directory
    self.browserWindow.load()
    settings = qt.QSettings() 
    settings.setValue("lapdMouseDBBrowserLocalCacheFolder", self.browserWindow.localCashFolder)
    settings.sync()

#
# lapdMouseDBBrowserSelectionLogic
#

class lapdMouseDBBrowserLogic(ScriptedLoadableModuleLogic):

  def __init__(self):
    pass

  def __del__(self):
    pass

#
# lapdMouseDBBrowserTest
#

class lapdMouseDBBrowserTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_lapdMouseDBBrowser1()

  def test_lapdMouseDBBrowser1(self):
    self.delayDisplay('Test passed!')

