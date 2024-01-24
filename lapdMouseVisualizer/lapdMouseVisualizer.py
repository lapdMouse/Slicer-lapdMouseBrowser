import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import time
import math

#
# lapdMouseVisualizer
#

class lapdMouseVisualizer(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "lapdMouseVisualizer"
    self.parent.categories = ["lapdMouse"]
    self.parent.dependencies = []
    self.parent.contributors = ["Christian Bauer (Univeristy of Iowa) and Melissa Krueger (University of Washington)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
    Visualize tree structures (*.meta) and compartment measurements (*.csv) from the lapdMouse project as mesh models.
    For more details, visit the <a href="https://cebs-ext.niehs.nih.gov/cahs/report/lapd/web-download-links/MzNhZGRkZGY5ZWU2OGU1ODgwYWQ4NjA2Njg0M2Q1YzMK">lapdMouse project</a>.
    """
    self.parent.acknowledgementText = """
    This work was supported in part by NIH project R01ES023863.
""" # replace with organization, grant and thanks.

#
# lapdMouseVisualizerWidget
#

class lapdMouseVisualizerWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    self.logic = lapdMouseVisualizerLogic()
    ScriptedLoadableModuleWidget.setup(self)

    # Instantiate and connect widgets ...  
    
    #
    # Parameters Area for Tree
    #
    treeCollapsibleButton = ctk.ctkCollapsibleButton()
    treeCollapsibleButton.text = "Tree structure"
    self.layout.addWidget(treeCollapsibleButton)

    # Layout within the dummy collapsible button
    treeFormLayout = qt.QFormLayout(treeCollapsibleButton)
    
    # input meta file selector
    self.treeInputSelector = ctk.ctkPathLineEdit()
    self.treeInputSelector.nameFilters = ["Tree structure (*.meta)"]
    self.treeInputSelector.setToolTip("Select the *.meta file containing the tree structure.")
    treeFormLayout.addRow("Input tree file: ", self.treeInputSelector)

    # output model selector
    self.treeOutputSelector = slicer.qMRMLNodeComboBox()
    self.treeOutputSelector.nodeTypes = ["vtkMRMLModelNode"]
    self.treeOutputSelector.selectNodeUponCreation = True
    self.treeOutputSelector.addEnabled = True
    self.treeOutputSelector.removeEnabled = True
    self.treeOutputSelector.renameEnabled = True
    self.treeOutputSelector.noneEnabled = False
    self.treeOutputSelector.showHidden = False
    self.treeOutputSelector.showChildNodeTypes = False
    self.treeOutputSelector.setMRMLScene( slicer.mrmlScene )
    self.treeOutputSelector.setToolTip( "Pick the output visualization mesh.")
    treeFormLayout.addRow("Output Model: ", self.treeOutputSelector)
    
    # apply button
    self.treeApplyButton = qt.QPushButton("Apply")
    self.treeApplyButton.toolTip = "Convert *.meta tree to mesh model"
    self.treeApplyButton.connect('clicked()', self.onTreeApply)
    treeFormLayout.addRow("Convert:",self.treeApplyButton)

    #
    # Parameters Area for Compartment Measurement Tables
    #
    measurementsCollapsibleButton = ctk.ctkCollapsibleButton()
    measurementsCollapsibleButton.text = "Compartment Measurements"
    self.layout.addWidget(measurementsCollapsibleButton)

    # Layout within the dummy collapsible button
    measurementsFormLayout = qt.QFormLayout(measurementsCollapsibleButton)
    
    # input csv file selector
    self.measurementsInputSelector = ctk.ctkPathLineEdit()
    self.measurementsInputSelector.nameFilters = ["Compartment Measurement table (*.csv)"]
    self.measurementsInputSelector.setToolTip("Select the *.csv file containing the compartment measurements.")
    measurementsFormLayout.addRow("Input measurements file: ", self.measurementsInputSelector)
    
    # input csv file selector
    self.measurementsInputTableSelector = slicer.qMRMLNodeComboBox()
    self.measurementsInputTableSelector.nodeTypes = ["vtkMRMLTableNode"]
    self.measurementsInputTableSelector.selectNodeUponCreation = True
    self.measurementsInputTableSelector.removeEnabled = True
    self.measurementsInputTableSelector.renameEnabled = True
    self.measurementsInputTableSelector.noneEnabled = True
    self.measurementsInputTableSelector.showHidden = False
    self.measurementsInputTableSelector.showChildNodeTypes = False
    self.measurementsInputTableSelector.setMRMLScene( slicer.mrmlScene )
    self.measurementsInputTableSelector.setToolTip( "Select table containing the compartment measurements.")
    measurementsFormLayout.addRow("Input measurements table: ", self.measurementsInputTableSelector)

    # output model selector
    self.measurementsOutputSelector = slicer.qMRMLNodeComboBox()
    self.measurementsOutputSelector.nodeTypes = ["vtkMRMLModelNode"]
    self.measurementsOutputSelector.selectNodeUponCreation = True
    self.measurementsOutputSelector.addEnabled = True
    self.measurementsOutputSelector.removeEnabled = True
    self.measurementsOutputSelector.renameEnabled = True
    self.measurementsOutputSelector.noneEnabled = False
    self.measurementsOutputSelector.showHidden = False
    self.measurementsOutputSelector.showChildNodeTypes = False
    self.measurementsOutputSelector.setMRMLScene( slicer.mrmlScene )
    self.measurementsOutputSelector.setToolTip( "Pick the output visualization mesh.")
    measurementsFormLayout.addRow("Output Model: ", self.measurementsOutputSelector)
    
    # apply button
    self.measurementsApplyButton = qt.QPushButton("Apply")
    self.measurementsApplyButton.toolTip = "Convert *.csv compartment measurement tables to mesh model"
    self.measurementsApplyButton.connect('clicked()', self.onMeasurementsApply)
    measurementsFormLayout.addRow("Convert:",self.measurementsApplyButton)
    
    self.layout.addStretch(1)
    
  def onTreeApply(self):
    filename = self.treeInputSelector.currentPath
    model = self.treeOutputSelector.currentNode()
    valid = model is not None and filename!=''
    if not valid:
      qt.QMessageBox.warning(None,'Info', \
      'Please specify input file and output model')
      return
    tree = self.logic.readMetaTree(filename)
    self.logic.tree2Model(tree, model)
    success = model.GetPolyData().GetNumberOfPoints()>0
    if not success:
      qt.QMessageBox.warning(None,'Error', \
      'Not able to create visualization. Potentially empty or invalid tree file.')
      return
    model.CreateDefaultDisplayNodes()
    display = model.GetDisplayNode()
    display.SetActiveScalarName('BranchLabel')

    # specify transform  
    transformNode = self.logic.getTransformNode()
    model.SetAndObserveTransformNodeID(transformNode.GetID())
    slicer.mrmlScene.AddNode(model)

    colorLUT = slicer.util.getFirstNodeByClassByName('vtkMRMLColorTableNode','Rainbow')
    if colorLUT:
      display.SetAndObserveColorNodeID(colorLUT.GetID())
    
  def onMeasurementsApply(self):
    filename = self.measurementsInputSelector.currentPath
    table = self.measurementsInputTableSelector.currentNode()
    model = self.measurementsOutputSelector.currentNode()
    valid = model is not None and ((table is not None) or filename!='')
    if not valid:
      qt.QMessageBox.warning(None,'Info', \
      'Please specify input file or table and output model')
      return
    if filename and not table:
      success = slicer.util.loadNodeFromFile(filename, 'TableFile')
      if not success:
        qt.QMessageBox.warning(None,'Error', \
        'Could not read file as table')
        return
      table = slicer.util.getNodesByClass('vtkMRMLTableNode')[-1]
      self.measurementsInputTableSelector.setCurrentNode(table)
    tableType = self.logic.getType(table)
    self.logic.measurementsTable2Model(table, model)
    success = model.GetPolyData().GetNumberOfPoints()>0
    if not success:
      qt.QMessageBox.warning(None,'Error', \
      'Not able to create visualization. Potentially empty or invalid measurements table.')
      return
    model.CreateDefaultDisplayNodes()
    display = model.GetDisplayNode()
    if tableType=='tree':
      display.SetActiveScalarName('BranchLabel')
    else:
      display.SetActiveScalarName('MeasurementMean')
      display.SetOpacity(0.2)

    # specify transform  
    transformNode = self.logic.getTransformNode()
    model.SetAndObserveTransformNodeID(transformNode.GetID())
    slicer.mrmlScene.AddNode(model)

    colorLUT = slicer.util.getFirstNodeByClassByName('vtkMRMLColorTableNode','Rainbow')
    if colorLUT:
      display.SetAndObserveColorNodeID(colorLUT.GetID())

#
# lapdMouseVisualizerSelectionLogic
#

class lapdMouseVisualizerLogic(ScriptedLoadableModuleLogic):
    
  def readMetaTree(self, filename):
    # read *.meta file and extracts 'Tube' objects
    tree = {}
    tube = None
    readNPoints = 0
    for line in open(filename,'r+'):
      line = line.rstrip('\n')
      if tube is not None:
        if readNPoints>0:
          tokens = [float(x) for x in line.split(' ')[0:-1]]
          tube['Coordinates'].append(tokens[0:3])
          tube['Radius'].append(tokens[3])
          tube['Color'].append(tokens[-5:-2])
          readNPoints = readNPoints-1
          if readNPoints==0:
            tree[tube['ID']] = tube
        if line.startswith('ID = '):
          tube['ID'] = int(line[len('ID = '):])
        if line.startswith('ParentID = '):
          tube['ParentID'] = int(line[len('ParentID = '):])
        if line.startswith('Name = '):
          tube['Name'] =(line[len('Name = '):])
        if line.startswith('NPoints = '):
          tube['NPoints'] = int(line[len('NPoints = '):])
        if line.startswith('Points = '):
          readNPoints = tube['NPoints']
          tube['Coordinates'] = []
          tube['Radius'] = []
          tube['Color'] = []
      if line.startswith('ObjectType = '):
        tube = {} if line.endswith('Tube') else None
          
    # establish list of child IDs for each tube
    for ID in tree.keys():
      tube = tree[ID]
      if ('ParentID' in tube) and (tube['ParentID'] in tree):
        parent = tree[tube['ParentID']]
        if 'ChildIDs' in parent:
          parent['ChildIDs'].append(tube['ID'])
        else:
          parent['ChildIDs'] = [tube['ID']]
    
    return tree
  
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

    
  def tree2Mesh(self, tree): 
    # convert tree structure to mesh representation
    # each airway segment is visualized as a cylinder
    # label values for labled branches are assigned
    mainBranchLabels = ['Trachea','LMB','RMB','CrRMB','MiRMB','CaRMB','AcRMB'] 
    appendFilter = vtk.vtkAppendPolyData()  
    for tubeID in tree.keys():
      tube = tree[tubeID]
      polyData = self.tube2CylinderMesh(tube)
      if polyData:
        branchName = tube['Name'] if 'Name' in tube else ''
        branchLabel = mainBranchLabels.index(branchName)+1 if branchName in mainBranchLabels else 0
        self.setPolyDataScalarValue(polyData, branchLabel, 'BranchLabel')
        appendFilter.AddInputDataObject(polyData)
    appendFilter.Update()
    return appendFilter.GetOutputDataObject(0)
  
  def tube2CylinderMesh(self, tube):
    # created oriented cylinder mesh following:
    # https://www.vtk.org/Wiki/VTK/Examples/Cxx/GeometricObjects/OrientedCylinder
    if (len(tube['Coordinates'])<2):
      return None
    radius = sum(tube['Radius'])/float(len(tube['Radius']))
    startPoint = tube['Coordinates'][0]
    endPoint = tube['Coordinates'][-1]
    center = [(startPoint[i]+endPoint[i])/2.0 for i in range(3)]
    direction = [0,0,0]
    vtk.vtkMath.Subtract(endPoint, startPoint, direction)
    length = vtk.vtkMath.Norm(direction)
    vtk.vtkMath.Normalize(direction)
    return self.createCylinderMesh(center, direction, radius, length)
  
  def setPolyDataScalarValue(self, polyData, value, name='Scalars'):
    # set point data of polydata object
    nPoints = polyData.GetNumberOfPoints()
    scalars = vtk.vtkFloatArray()
    scalars.SetNumberOfComponents(1)
    scalars.SetNumberOfTuples(nPoints)
    scalars.FillComponent(0,value)
    scalars.SetName(name)
    polyData.GetPointData().SetScalars(scalars)
    
  def tree2Model(self, tree, model=None):
    # convert the tree structure a vtkMRMLModelNode
    if model is None:
      model = slicer.vtkMRMLModelNode()
      model.SetName('Tree')
    mesh = self.tree2Mesh(tree)
    model.SetAndObserveMesh(mesh)
    return model
    
  def tube2Model(self, tube, model=None):
    # convert a single tubular structure to a vtkMRMLModelNode
    if model is None:
      model = slicer.vtkMRMLModelNode()
      name = 'Segment '+str(tube['ID'])+(' - '+tube['Name'] if 'Name' in tube else '')
      model.SetName(name)
    mesh = self.tube2CylinderMesh(tube)
    model.SetAndObserveMesh(mesh)
    return model
  
  def sphereMesh(self, centroid=[0,0,0], radius=1):
    # create a sphere mesh
    sphereSource = vtk.vtkSphereSource()
    sphereSource.SetCenter(centroid)
    sphereSource.SetRadius(radius)
    sphereSource.Update()
    return sphereSource.GetOutputDataObject(0)
    
  def volumeMeasurementsTable2Mesh(self, tableNode):
    # convert a measurements table to a mesh representation
    # the table node is assumed to contain columns:
    # (volume, mean, centroidX, centroidY, centroidZ)
    table = tableNode.GetTable()
    requiredColumns = {'volume', 'mean', 'centroidX', 'centroidY', 'centroidZ'}
    tableColumns = {table.GetColumnName(i) for i in range(table.GetNumberOfColumns())}
    if not requiredColumns.issubset(set(tableColumns)): # not a valid measurements table
      return vtk.vtkPolyData()
    appendFilter = vtk.vtkAppendPolyData()  
    for row in range(table.GetNumberOfRows()):
      volume = table.GetValueByName(row,'volume').ToFloat()
      radius = pow(volume*3.0/(4.0*math.pi),1.0/3.0)
      mean = table.GetValueByName(row,'mean').ToFloat()
      centroid = [
         table.GetValueByName(row,'centroidX').ToFloat(),
         table.GetValueByName(row,'centroidY').ToFloat(),
         table.GetValueByName(row,'centroidZ').ToFloat()]
      polyData = self.sphereMesh(centroid, radius)
      self.setPolyDataScalarValue(polyData, mean, 'MeasurementMean')
      appendFilter.AddInputDataObject(polyData)
    appendFilter.Update()
    return appendFilter.GetOutputDataObject(0)

  def areaMeasurementsTable2Mesh(self, tableNode):
    # convert a measurements table to a mesh representation
    # the table node is assumed to contain columns:
    # (volume, mean, centroidX, centroidY, centroidZ)
    table = tableNode.GetTable()
    requiredColumns = {'area', 'mean', 'centroidX', 'centroidY', 'centroidZ'}
    tableColumns = {table.GetColumnName(i) for i in range(table.GetNumberOfColumns())}
    if not requiredColumns.issubset(set(tableColumns)): # not a valid measurements table
      return vtk.vtkPolyData()
    appendFilter = vtk.vtkAppendPolyData()  
    for row in range(table.GetNumberOfRows()):
      area = table.GetValueByName(row,'area').ToFloat()
      radius = pow(area/(4.0*math.pi),1.0/2.0)
      mean = table.GetValueByName(row,'mean').ToFloat()
      centroid = [
         table.GetValueByName(row,'centroidX').ToFloat(),
         table.GetValueByName(row,'centroidY').ToFloat(),
         table.GetValueByName(row,'centroidZ').ToFloat()]
      polyData = self.sphereMesh(centroid, radius)
      self.setPolyDataScalarValue(polyData, mean, 'MeasurementMean')
      appendFilter.AddInputDataObject(polyData)
    appendFilter.Update()
    return appendFilter.GetOutputDataObject(0)

  def treeTable2Mesh(self, tableNode):
    # convert tree table to mesh representation
    # each airway segment is visualized as a cylinder
    # label values for labled branches are assigned
    mainBranchLabels = ['Trachea','LMB','RMB','CrRMB','MiRMB','CaRMB','AcRMB'] 
    appendFilter = vtk.vtkAppendPolyData()  
    table = tableNode.GetTable()
    for row in range(table.GetNumberOfRows()):
      radius = table.GetValueByName(row,'radius').ToFloat()
      height = table.GetValueByName(row,'length').ToFloat()
      branchName = table.GetValueByName(row,'name').ToString()
      centroid = [
         table.GetValueByName(row,'centroidX').ToFloat(),
         table.GetValueByName(row,'centroidY').ToFloat(),
         table.GetValueByName(row,'centroidZ').ToFloat()]
      direction = [
         table.GetValueByName(row,'directionX').ToFloat(),
         table.GetValueByName(row,'directionY').ToFloat(),
         table.GetValueByName(row,'directionZ').ToFloat()]
      polyData = self.createCylinderMesh(centroid, direction, radius, height)
      if polyData:
        branchLabel = mainBranchLabels.index(branchName)+1 if branchName in mainBranchLabels else 0
        self.setPolyDataScalarValue(polyData, branchLabel, 'BranchLabel')
        appendFilter.AddInputDataObject(polyData)
    appendFilter.Update()
    return appendFilter.GetOutputDataObject(0)

  def createCylinderMesh(self, center, direction, radius=1.0, height=1.0):
    startPoint = [center[i]-direction[i]*height/2.0 for i in range(3)]
    cylinderSource = vtk.vtkCylinderSource()
    cylinderSource.SetResolution(8)
    cylinderSource.SetRadius(radius)
    cylinderSource.Update()
    normalizedX = direction
    normalizedY = [0,0,0]
    normalizedZ = [0,0,0]
    vtk.vtkMath.Normalize(normalizedX)
    arbitrary = [1,1,1]
    vtk.vtkMath.Cross(normalizedX, arbitrary, normalizedZ)
    vtk.vtkMath.Normalize(normalizedZ)
    vtk.vtkMath.Cross(normalizedZ, normalizedX, normalizedY)
    matrix = vtk.vtkMatrix4x4()
    matrix.Identity()
    for i in range(3):
      matrix.SetElement(i, 0, normalizedX[i])
      matrix.SetElement(i, 1, normalizedY[i])
      matrix.SetElement(i, 2, normalizedZ[i])
    transform = vtk.vtkTransform()
    transform.Translate(startPoint)
    transform.Concatenate(matrix)
    transform.RotateZ(-90.0)
    transform.Scale(1.0, height, 1.0)
    transform.Translate(0, .5, 0)
    transformPD = vtk.vtkTransformPolyDataFilter()
    transformPD.SetTransform(transform)
    transformPD.SetInputConnection(cylinderSource.GetOutputPort())
    transformPD.Update()
    return transformPD.GetOutputDataObject(0)    
    
  def measurementsTable2Model(self, tableNode, model=None):
    # convert a measurements table to a mesh a vtkMRMLModelNode
    if model is None:
      model = slicer.vtkMRMLModelNode()
      model.SetName('Measurements')
    if self.getType(tableNode)=='tree':
      mesh = self.treeTable2Mesh(tableNode)
    elif self.getType(tableNode)=='areaMeasurements':
      mesh = self.areaMeasurementsTable2Mesh(tableNode)
    else:
      mesh = self.volumeMeasurementsTable2Mesh(tableNode)
    model.SetAndObserveMesh(mesh)
    return model

  def getType(self, tableNode):
    table = tableNode.GetTable()
    tableColumns = {table.GetColumnName(i) for i in range(table.GetNumberOfColumns())}
    types = {
      'volumeMeasurements': {'volume', 'mean', 'centroidX', 'centroidY', 'centroidZ'},
      'areaMeasurements': {'area', 'mean', 'centroidX', 'centroidY', 'centroidZ'},
      'tree': {'length', 'radius', 'centroidX', 'centroidY', 'centroidZ', 'directionX', 'directionY', 'directionZ'},
    }
    for key, value in types.items():
      if value.issubset(tableColumns):
        return key
    return None

#
# lapdMouseVisualizerTest
#

class lapdMouseVisualizerTest(ScriptedLoadableModuleTest):
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
    self.test_lapdMouseVisualizer1()

  def test_lapdMouseVisualizer1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    self._internalTest()
    self.delayDisplay('Test passed!')
  
  def _internalTest(self):
    # test loading of measurements file
    logic = lapdMouseVisualizerLogic()
    measurementsFile =  os.path.join(os.path.expanduser("~"),\
                                     'Documents/data/lapdMouseTest/test/test_LobesDeposition.csv')
    slicer.util.loadNodeFromFile(measurementsFile, 'TableFile')
    measurementsTable = slicer.util.getFirstNodeByClassByName('vtkMRMLTableNode','test_LobesDeposition')
    model = logic.measurementsTable2Model(measurementsTable)
    model.SetScene(slicer.mrmlScene)
    model.CreateDefaultDisplayNodes()
    slicer.mrmlScene.AddNode(model)
    
    # test loading of measurements file
    
    logic = lapdMouseVisualizerLogic()
    treeFilename =  os.path.join(os.path.expanduser("~"),\
                                 'Documents/data/lapdMouseTest/test/test_AirwayTree.meta')
    tree = logic.readMetaTree(treeFilename)   
    modelHierarchy = slicer.vtkMRMLModelHierarchyNode()
    model = logic.tree2Model(tree)
    model.SetScene(slicer.mrmlScene)
    model.CreateDefaultDisplayNodes()
    slicer.mrmlScene.AddNode(model)
    
    self.delayDisplay('Test passed!')
