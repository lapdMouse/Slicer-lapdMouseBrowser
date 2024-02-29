import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import json
import sys
import urllib
import datetime
import time, sys, ssl, urllib.request, urllib.error

class lapdMouseDBUtil():

  def __init__(self, remoteFolderUrl):
    self.gdriveURL = remoteFolderUrl
    if 'lapdMouseDBBrowser' in slicer.util.moduleNames():
      self.modulePath = slicer.modules.lapdmousedbbrowser.path.replace("lapdMouseDBBrowser.py","")
    else:
      self.modulePath = '.'

  def _canAccess(self):
    # Create a secure SSL context
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ctx.options |= 0x4  # OP_LEGACY_SERVER_CONNECT

    try:
      httpCode = urllib.request.urlopen(self.gdriveURL+'m01/MD5SUMS',context=ctx).getcode()
      if (httpCode == 200):
        return True
      else:
        print(f"Unexpected HTTP error ({httpCode}.")
        return False
    except urllib.error.HTTPError as e:
      print('The server couldn\'t fulfill the request.')
      print('Error code: ', e.code)
      return False
    except urllib.error.URLError as e:
      print('We failed to reach a server.')
      print('Reason: ', e.reason)
      return False
    except:
      print("Unexpected error:", sys.exc_info()[0])
      return False

  def listDirectory(self, dirname='',depth=0):
    return self._listFolderRemote(dirname, depth)
    
  def downloadFile(self, src, dst):
    if not os.path.exists(os.path.dirname(dst)):
      os.makedirs(os.path.dirname(dst))
    self._downloadFileFromRemote(src, dst)

  def _downloadFileFromRemote(self, src, destination):
    requestUrl = self.gdriveURL + src
    request = urllib.request.Request(requestUrl)
    response = urllib.request.urlopen(request)
    self._downloadURLStreaming(response, destination)

  def _downloadURLStreaming(self,response,destination):
    if response.getcode() == 200:
      destinationFile = open(destination, "wb")
      bufferSize = 1024*1024
      while True:
        buffer = response.read(bufferSize)
        if not buffer:
          break
        destinationFile.write(buffer)
      destinationFile.close()

  def _listFolderRemote(self,dirname,depth=0):
    # Read file with file names and metadata
    try:
      with open(os.path.join(self.modulePath,'Resources','allfiles.json')) as infile:
        data = infile.read()
      allcontent = json.loads(data)
    except:
      return []

    dircontent = []
    for oneFile in allcontent:
      if (dirname == '.' or os.path.commonprefix([dirname,oneFile['name']]) == dirname):
        remainingPath = oneFile['name'][len(dirname)+1:]
        if (remainingPath.count('/') <= depth):
          oneFile['name'] = os.path.basename(oneFile['name'])
          dircontent.append(oneFile)
    return dircontent

  def _splitPath(self, p):
    a,b = os.path.split(p)
    return (self._splitPath(a) if len(a) and len(b) else []) + [b]

def humanReadableSize(size):
  if size==None:
    return ""
  sizeString = "%.1f B"%size
  if (size>pow(1024.0,1)):
    sizeString="%.1f KB"%(size/pow(1024.0,1))
  if (size>pow(1024.0,2)):
    sizeString="%.1f MB"%(size/pow(1024.0,2))
  if (size>pow(1024.0,3)):
    sizeString="%.1f GB"%(size/pow(1024.0,3))
  if (size>pow(1024.0,4)):
    sizeString="%.1f TB"%(size/pow(1024.0,4))
  return sizeString

def humanReadableTime(seconds):
  return time.strftime("%H:%M:%S", time.gmtime(seconds))

def getStatus(item):
  remoteSize = item['size']
  remoteModificationTime = item['modificationTimestamp']/1000
  realPath = os.path.realpath(os.path.expanduser(item['localName']))
  status = 'require download'
  if os.path.exists(realPath):
    localModificationTime = os.path.getmtime(realPath)
    status = 'downloaded'
    if not item['isFolder']:
      localSize = os.path.getsize(realPath)
      if remoteSize!=localSize or \
        remoteModificationTime>localModificationTime:
        status = 'require update'
  return status

def summarizeItems(items):
  summaryString = ''
  remoteFiles = items
  summaryString += 'Matching files/folders: total='+str(len(remoteFiles))
  if len(remoteFiles)>0:
    summaryString+='('+humanReadableSize(sum(i['size'] for i in remoteFiles))+')'
  filesAlreadyDownloaded = [i for i in remoteFiles if i['status']=='downloaded']
  summaryString += ', downloaded='+str(len(filesAlreadyDownloaded))
  if len(filesAlreadyDownloaded)>0:
    summaryString+='('+humanReadableSize(sum(i['size'] for i in filesAlreadyDownloaded))+')'
  filesForDownload = [i for i in remoteFiles if i['status']=='require download']
  summaryString += ', require download='+str(len(filesForDownload))
  if len(filesForDownload)>0:
    summaryString+='('+humanReadableSize(sum(i['size'] for i in filesForDownload))+')'
  filesOutOfDate = [i for i in remoteFiles if i['status']=='require update']
  summaryString += ', require update='+str(len(filesOutOfDate))
  if len(filesOutOfDate)>0:
    summaryString+='('+humanReadableSize(sum(i['size'] for i in filesOutOfDate))+')'
  print(summaryString)

def listItem(item):
  remoteName = item['remoteName'] 
  localName = item['localName']
  message = remoteName
  if item['isFolder']:
    message+=' -> '+localName+' (folder)'
  else:
    message+=' -> '+localName+' ('+item['status']+'; '+humanReadableSize(item['size'])+')'
  print(message)

def downloadItem(item, db):
  listItem(item)
  remoteName = item['remoteName']
  localName = item['localName']
  realPath = os.path.realpath(os.path.expanduser(localName))
  isFolder = item['isFolder']
  if os.path.exists(realPath) and os.path.isfile(realPath):
    os.remove(realPath)
  if isFolder and not(os.path.exists(realPath)):
    os.makedirs(realPath)
    return
  if not isFolder and not(os.path.exists(os.path.dirname(realPath))):
    os.makedirs(os.path.dirname(realPath))

  sys.stdout.write('  Downloading ...')
  sys.stdout.flush()
  t0 = time.time()
  try:
    db.downloadFile(remoteName, realPath)
  except:
    print("Unexpected error:", sys.exc_info()[0])
    if os.path.exists(realPath) and os.path.isfile(realPath):
      os.remove(realPath)
  t1 = time.time()
  downloadSucceeded = os.path.exists(realPath)
  sys.stdout.write( ( '[DONE]' if downloadSucceeded else ' [ERROR]')+' time: '+time.strftime("%M:%S", time.gmtime(t1-t0))+'(mm:ss)\n')
  if not downloadSucceeded:
    return 'ERROR: download failed for file: '+localName
  else:
    return None

def testDBAccess(db):
  serverStatus = 'unknown'
  if lapdMouseDBUtil._canAccess():
    serverStatus = 'available'
  else:
    serverStatus = 'unavailable'
  print('DB access status: '+serverStatus)
  return True if serverStatus=='available' else False


class lapdMouseBrowserWindow(qt.QMainWindow):

  def __init__(self, parent=None):
    super().__init__(parent)
    self.table = None
    self.workingDirectory = None
    self.isEditing = False
    self.datasets = []
    self.remoteFolderUrl = 'https://cebs-ext.niehs.nih.gov/cahs/file/download/lapd/'
    self.localCacheFolder = os.path.join(os.path.expanduser("~"),'lapdMouse')
    self.projectUrl='https://cebs-ext.niehs.nih.gov/cahs/report/lapd/web-download-links/'
    self.notesUrl='https://cebs-ext.niehs.nih.gov/cahs/file/lapd/pages/notes/'
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
    text += " For more details about available datasets, data representation, other software, and support, please visit the <a href=\""
    text += self.projectUrl
    text +="\">lapdMouse archive</a>"
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
    self.customFormDatasetInfo = qt.QLabel('<a href=\"'+self.projectUrl+'\">project info</a>')
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
    self.datasets = [d['name'] for d in lapdMouseDBUtil(self.remoteFolderUrl).listDirectory() if d["isFolder"]==True]
    if os.path.exists(self.localCacheFolder):
      localFolders = [d for d in os.listdir(self.localCacheFolder) if \
        os.path.isdir(os.path.join(self.localCacheFolder,d))]
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
    url = self.notesUrl+datasetname+'_notes.pdf'
    self.customFormDatasetInfo.text = f'<a href="{url}">{datasetname}_notes.pdf</a>'
    datasetFiles = self.listFilesForDataset(datasetname)    
    self.customFormFiles.setRowCount(len(datasetFiles))
    for i in range(len(datasetFiles)):
      fname = datasetFiles[i]["name"]
      fsize = datasetFiles[i]["size"]
      remoteName = os.path.join(datasetname,fname.replace('/',os.sep))
      localName = os.path.join(self.localCacheFolder,remoteName)
      downloaded = os.path.exists(localName)
      self.customFormFiles.setItem(i,0,qt.QTableWidgetItem())
      self.customFormFiles.item(i,0).setIcon(self.storedIcon if downloaded else self.downloadIcon)
      self.customFormFiles.item(i,0).setToolTip('downloaded' if downloaded else 'available for download')
      self.customFormFiles.setItem(i,1,qt.QTableWidgetItem(fname))
      self.customFormFiles.setItem(i,2,qt.QTableWidgetItem(self.hrSize(fsize)))
  
  def listFilesForDataset(self,datasetname):
    remoteFolderContent = lapdMouseDBUtil(self.remoteFolderUrl).listDirectory(datasetname, 0)
    files = [f for f in remoteFolderContent if not f['isFolder']]
    filenames = [f['name'] for f in files]
    localDatasetDirectory = os.path.join(self.localCacheFolder,datasetname)
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
    if datasetId==-1:
      return
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
    if datasetId==-1:
      return
    datasetname = self.datasets[datasetId]
    files = self.getSelectedFiles()
    self.downloadFiles(datasetname, files)
    self.updateForm()
    
  def onDeleteSelectedDataset(self):
    datasetId = self.getSelectedId()
    if datasetId==-1:
      return
    datasetname = self.datasets[datasetId]
    files = self.getSelectedFiles()
    self.deleteFiles(datasetname, files)
    self.updateForm()
    
  def downloadFiles(self, datasetname, files, askForConfirmation=True):
    if askForConfirmation:
      filestats = self.listFilesForDataset(datasetname)
      filesToDownload = [f for f in filestats if f['name'] in files and \
        not os.path.exists(os.path.join(self.localCacheFolder,datasetname,f['name']))]
      if len(filesToDownload)==0:
        return True
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
      if pd.wasCanceled:
        break
      pd.setValue(files.index(f)+1)
      slicer.app.processEvents()   
      remoteName = os.path.join(datasetname,f.replace('/',os.sep))
      localName = os.path.join(self.localCacheFolder,remoteName)
      if not os.path.exists(localName):
        print('downloading '+remoteName)
        try:
          lapdMouseDBUtil(self.remoteFolderUrl).downloadFile(remoteName, localName)
        except:
          print('error downloading file: ')
          print(sys.exc_info()[0])
    pd.setValue(len(files)+2)
    return True
    
  def deleteFiles(self, datasetname, files):
    for f in files:
      remoteName = os.path.join(datasetname,f.replace('/',os.sep))
      localName = os.path.join(self.localCacheFolder,remoteName)
      if os.path.exists(localName):
        print("deleting file "+localName)
        os.remove(localName)
      
  def onLoadDataset(self):
    datasetId = self.getSelectedId()
    if datasetId==-1:
      return
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
    if datasetId==-1:
      return
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
      if pd.wasCanceled:
        break
      pd.setValue(files.index(f)+1)
      slicer.app.processEvents()
      remoteName = os.path.join(datasetname,f.replace('/',os.sep))
      localName = os.path.join(self.localCacheFolder,remoteName)
      if not os.path.exists(localName):
        continue
      try:
        print('loading '+localName)
        self.loadFile(localName)
      except:
        print('error loading file: ')
        print(sys.exc_info()[0])
    pd.setValue(len(files)+2)
    pd.hide()
  
  def loadFile(self, filename):
    lapdMouseDBBrowser.loadColorTables()
    name, extension = os.path.splitext(filename)
    if extension=='.mha':
      self.loadVolume(filename)
    elif extension=='.nrrd':
      self.loadLabelmap(filename)
    elif extension=='.vtk':
      self.loadMesh(filename)
    elif extension=='.meta':
      self.loadTree(filename)
    elif extension=='.csv':
      self.loadMeasurements(filename)
    else:
      print('Warning: can\'t load: '+filename)


  # .mha  
  def loadVolume(self, filename):
    slicer.util.loadVolume(filename)
    
    name = os.path.splitext(os.path.basename(filename))[0]
    nodes = slicer.util.getNodes(name+'*') # Returns OrderedDict
    nodeKey = next(reversed(nodes)) # Get last node
    node = nodes[nodeKey] # Get id of last node
    
    node.CreateDefaultDisplayNodes()
    nd = node.GetDisplayNode()
    
    if (str(os.path.basename(filename)).find('Aerosol')!=-1):
      colorLUT = slicer.util.getFirstNodeByClassByName('vtkMRMLColorTableNode','Red')
      if colorLUT:
        nd.SetAndObserveColorNodeID(colorLUT.GetID())
      nd.SetAutoWindowLevel(False)
      if (str(os.path.basename(filename)).find('Normalized')!=-1):
        nd.SetWindowLevel(10,5)
      else:
        nd.SetWindowLevel(1000,500)
      
    if (str(os.path.basename(filename)).find('Autofluorescent')!=-1):
      colorLUT = slicer.util.getFirstNodeByClassByName('vtkMRMLColorTableNode','Green')
      if colorLUT:
        nd.SetAndObserveColorNodeID(colorLUT.GetID())
      nd.SetAutoWindowLevel(False)
      nd.SetWindowLevel(3000,1500)


 # .nrrd 
  def loadLabelmap(self, filename):
    self.turnLabelmapsToOutline()
    slicer.util.loadLabelVolume(filename)
    
    name = os.path.splitext(os.path.basename(filename))[0]
    nodes = slicer.util.getNodes(name+'*') # Returns OrderedDict
    nodeKey = next(reversed(nodes)) # Get last node
    node = nodes[nodeKey] # Get id of last node
    
    colorLUT = None
    if (str(os.path.basename(filename)).find('Lobes.nrrd')!=-1):
      colorLUT = slicer.util.getFirstNodeByClassByName('vtkMRMLColorTableNode','lapdMouseLobes')
    else:
      colorLUT = slicer.util.getFirstNodeByClassByName('vtkMRMLColorTableNode','lapdMouseSegments')
    if colorLUT:
      nd=node.GetDisplayNode()
      nd.SetAndObserveColorNodeID(colorLUT.GetID())
  
  # Sets and hides a transform
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

  # .vtk  
  def loadMesh(self, filename):
    slicer.util.loadModel(filename)
    name = os.path.splitext(os.path.basename(filename))[0]
    nodes = slicer.util.getNodes(name+'*') # Returns OrderedDict
    nodeKey = next(reversed(nodes)) # Get last node
    node = nodes[nodeKey] # Get id of last node
    
    node.CreateDefaultDisplayNodes()
    nd = node.GetDisplayNode()
    if node.GetPolyData().GetPointData().GetNumberOfArrays()>0:
      nd.SetActiveScalarName(node.GetPolyData().GetPointData().GetArrayName(0))
    
    if (str(os.path.basename(filename)).find('AirwayWallDeposition')!=-1): 
      colorLUT = slicer.util.getFirstNodeByClassByName('vtkMRMLColorTableNode','Warm1')
      if colorLUT:
        nd.SetAndObserveColorNodeID(colorLUT.GetID())
      nd.SetScalarRangeFlag(slicer.vtkMRMLDisplayNode.UseManualScalarRange)
      nd.SetAutoScalarRange(False)
      nd.SetScalarRange(0,10)
    
    if (str(os.path.basename(filename)).find('AirwayWall.vtk')!=-1):    
      colorLUT = slicer.util.getFirstNodeByClassByName('vtkMRMLColorTableNode','BlueRed')
      if colorLUT:
        nd.SetAndObserveColorNodeID(colorLUT.GetID())
      nd.SetScalarRangeFlag(slicer.vtkMRMLDisplayNode.UseManualScalarRange)
      nd.SetAutoScalarRange(False)
      nd.SetScalarRange(0,1)
    
    if (str(os.path.basename(filename)).find('AirwaySegments')!=-1):
      colorLUT = slicer.util.getFirstNodeByClassByName('vtkMRMLColorTableNode','lapdMouseSegments')
      if colorLUT:
        nd.SetAndObserveColorNodeID(colorLUT.GetID())
      nd.SetScalarRangeFlag(slicer.vtkMRMLDisplayNode.UseColorNodeScalarRange)
    
    if (str(os.path.basename(filename)).find('AirwayOutlets')!=-1):
      colorLUT = slicer.util.getFirstNodeByClassByName('vtkMRMLColorTableNode','lapdMouseOutlets')
      if colorLUT:
        nd.SetAndObserveColorNodeID(colorLUT.GetID())
      nd.SetScalarRangeFlag(slicer.vtkMRMLDisplayNode.UseColorNodeScalarRange)
      
    nd.SetScalarVisibility(True)
    nd.BackfaceCullingOff()
    nd.SetVisibility2D(True)
  
  # .meta
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
      if colorLUT:
        display.SetAndObserveColorNodeID(colorLUT.GetID())

  # .csv    
  def loadMeasurements(self, filename):
    import lapdMouseVisualizer
    success = slicer.util.loadNodeFromFile(filename, 'TableFile')
    if not success:
      return
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
    if measurementsType=='tree':
      display.SetActiveScalarName('BranchLabel')
    else:
      display.SetActiveScalarName('MeasurementMean')
      display.SetOpacity(0.2)
    colorLUT = slicer.util.getFirstNodeByClassByName('vtkMRMLColorTableNode','Rainbow')
    if colorLUT:
      display.SetAndObserveColorNodeID(colorLUT.GetID())
    
  def turnLabelmapsToOutline(self):
    layoutManager = slicer.app.layoutManager()
    for sliceViewName in layoutManager.sliceViewNames():
      layoutManager.sliceWidget(sliceViewName).sliceController().showLabelOutline(True)
      
  def hrSize(self, bytes):
    if not bytes:
      return ''
    bytes = float(bytes)
    KB = bytes/1024
    if KB<1024:
      return "%.1f KB" % KB
    MB = KB/1024
    if MB<1024:
      return "%.1f MB" % MB
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
    self.parent.contributors = ["Christian Bauer (University of Iowa), Melissa Krueger (University of Washington)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
    Tool for accessing and viewing data from the of lapdMouse project data archive. For more details, visit the
    <a href="https://doi.org/10.25820/9arg-9w56">lapdMouse project</a>.
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
    if len(slicer.util.getNodes('lapdMouseLobes'))>0:
      return
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
    if len(slicer.util.getNodes('lapdMouseSegments'))>0:
      return
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
    if len(slicer.util.getNodes('lapdMouseOutlets'))>0:
      return
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
      settings.setValue("lapdMouseDBBrowserLocalCacheFolder", os.path.join(os.path.expanduser("~"),'lapdMouse'))
      settings.sync()
    databaseDirectory = settings.value("lapdMouseDBBrowserLocalCacheFolder")
    
    self.browserWindow = lapdMouseBrowserWindow()
    self.browserWindow.localCacheFolder = databaseDirectory
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
    
    self.storagePath = self.browserWindow.localCacheFolder
    storagePathLabel = qt.QLabel("Storage Folder: ")
    self.storagePathButton = ctk.ctkDirectoryButton()
    self.storagePathButton.directory = self.storagePath
    settingsGridLayout.addWidget(storagePathLabel,0,0,1,1)
    settingsGridLayout.addWidget(self.storagePathButton,0,1,1,4)
      
    self.storagePathButton.connect('directoryChanged(const QString &)',self.onStorageChanged)

    self.layout.addStretch(1)
  
  def onStorageChanged(self):
    self.browserWindow.localCacheFolder = self.storagePathButton.directory
    self.browserWindow.load()
    settings = qt.QSettings() 
    settings.setValue("lapdMouseDBBrowserLocalCacheFolder", self.browserWindow.localCacheFolder)
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

