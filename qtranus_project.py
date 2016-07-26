#encoding=UTF-8

from __future__ import unicode_literals
from os import listdir
from os.path import isfile, join


from .tranus import TranusProject

from qgis.core import QgsVectorLayer, QgsMapLayerRegistry, QgsField, QgsFeature, QgsRendererRangeV2, QgsStyleV2, QgsGraduatedSymbolRendererV2 , QgsSymbolV2, QgsVectorJoinInfo 

from PyQt4.QtCore import QVariant
from PyQt4.QtGui import QColor

from qgis.core import QgsMessageLog  # for debugging
from classes.GeneralObject import GeneralObject
from classes.Indicator import Indicator
from classes.MapData import MapData
from classes.Stack import Stack


import os
import re
import random
import string

class Scenario:

    def __init__(self):
        pass

    def readFields(self, lines):
        self.fieldNames = lines[0].strip().split(',')
        self.fields = self.fieldNames[3:]
        print(self.fields)

    def readId(self, lines):
        self.id = lines[1].split(',')[0].strip()

    def loadSectors(self, lines):
        sectorSet = set()
        zoneSet = set()
        for i in range(1, len(lines)):
            sectorSet.add(lines[i].split(',')[1].strip().split(' ')[1].strip())
            zoneSet.add(lines[i].split(',')[2].strip().split(' ')[0].strip())
        self.sectors = sectorSet
        self.zones   = zoneSet

    def load(self, lines):
        self.readFields(lines)
        self.readId(lines)
        self.loadSectors(lines)

        self.values = {}
        for zoneId in self.zones:
            self.values[zoneId] = {}

        for i in range(1, len(lines)):
            line = lines[i].strip().split(',')
            sector = line[1].strip().split(' ')[1].strip()
            zone = line[2].strip().split(' ')[0].strip()
            self.values[zone][sector] = {}
            for j in range(3, len(line)):
                self.values[zone][sector][self.fieldNames[j].strip()] = float(line[j].strip())
        

    #    for i in range(1, len(lines)):

    def __str__(self):
        st = "Fields: " + str(self.fieldNames) + "\n"
        st = st + "Id: " + str(self.id) + "\n"
        return st

def tokenize(string):
    tokens = []
    i = 0
    while i < len(string):
        if string[i]=='(' or string[i]==')' or string[i]=='*' or string[i]=='/' or string[i]=='+' or string[i]=='-':
            tokens.append(string[i])
            i = i + 1
        elif string[i]==' ' or string[i]=='\t':
            i = i + 1
        elif string[i].isdigit():
            start = i
            while i < len(string) and (string[i].isdigit() or string[i]=='.'):
                i = i + 1
            nextToken = string[start:i]
            tokens.append(nextToken)
        elif string[i].isalpha() or string[i]=='[':
            start = i
            while i < len(string) and (string[i].isalpha() or string[i]=='.' or string[i]=='[' or string[i]==']' or string[i].isdigit()):
                i = i + 1
            nextToken = string[start:i]
            tokens.append(nextToken)
        else:
            print("Unexpected token: " + string[i])
    return tokens

def isOperator(st):
    return st=='+' or st=='-' or st=='*' or st=='/'

def keepIterating(o1, o2):
    return (o1=='-' and isOperator(o2)) or (o1=='/' and (o2=='/' or o2=='*')) or (o1=='+' and (o2=='*' or o2=='/'))

def apply(v1, v2, op):
    if op=='+':
        return v1 + v2
    elif op=='-':
        return v1 - v2
    elif op=='*':
        return v1 * v2
    elif op=='/':
        return v1 / v2
    return None

def evalExpression(postfix, zone_values, field):
    stack = Stack()
    for x in postfix:
        if isOperator(x):
            v1 = stack.pop()
            v2 = stack.pop()
            stack.push(apply(v2, v1, x))
        elif x[0].isdigit():
            stack.push(float(x))
        else:    # identifier
            stack.push(float(zone_values[x][field]))
    return stack.top()

def checkExpression(expr, field, scenario, indicators):
    tokens = tokenize(expr)
    #print tokens
    #print indicators

    for token in tokens:
        #print "Token = "+token
        #print "ind[sce] = "+str(indicators[scenario])
        #print "Zones = "+str(indicators[scenario].zones)
        #print "Sectors = "+str(indicators[scenario].sectors)


        if token[0].isalpha():
            if token not in indicators[scenario].sectors:
                return False
        elif token[0]=='[':
            parts = token.split('.')
            scen = parts[0][1:len(parts[0])-1]
            idname = parts[1]
            if idname not in indicators[scen].sectors:
                return False

    output = Stack()
    operators = Stack()

    # now check the grammar
    # now parse it with shuting-yard algorithm
    try:
        for token in tokens:
            if token[0].isdigit() or token[0].isalpha(): # number or id
                output.push(token)
            elif token=='(':
                operators.push(token)
            elif token==')':
                while operators.top() != '(':
                    output.push(operators.pop())
                operators.pop()
            else:   # operators
                while not operators.empty() and keepIterating(token, operators.top()):
                    output.push(operators.pop())
                operators.push(token)
        while not operators.empty():
            output.push(operators.pop())
    except Exception:
        return False

    print "Second part"

    nOperators = 0
    nOperands = 0
    for x in output.data:
        if isOperator(x):
            nOperators = nOperators + 1
        else:
            nOperands = nOperands + 1

    print nOperators
    print nOperands
    print nOperators+1
    print nOperands
    print nOperators+1 != nOperands

    if nOperators+1 != nOperands:
        print "Returning False"
        return False, None

    # we could simulate the evaluation... if the stack gets empty and we have an operator, return False
    print "Returning True"
    return True, output



            
def evaluateExpression(scenario, expr, field):
    # first tokenize the expression
    tokens = tokenize(expr)

    output = Stack()
    operators = Stack()

    # now parse it with shuting-yard algorithm
    for token in tokens:
        if token[0].isdigit() or token[0].isalpha(): # number or id
            output.push(token)
        elif token=='(':
            operators.push(token)
        elif token==')':
            while operators.top() != '(':
                output.push(operators.pop())
            operators.pop()
        else:   # operators
            while not operators.empty() and keepIterating(token, operators.top()):
                output.push(operators.pop())
            operators.push(token)
    while not operators.empty():
        output.push(operators.pop())

    # expression parsed. Now we have to evaluate it for every zone

    #print(scenario.zones)
    #print(scenario.values['32']['Indus'][field])
    #print(output)

    result = {}
    
    #print("sc:")
    #print(scenario)

    for zone in scenario.zones:
        result[zone] = evalExpression(output.data, scenario.values[zone], field)

    return result


def loadIndicators(fn):
    ''' Loads s indicator file into a list and returns it'''
    f = open(fn)
    lines = f.readlines()
    scenario = Scenario()
    scenario.load(lines)

    f.close()
    return scenario
    
def loadProjectIndicators(path):
    files = [f for f in listdir(path) if isfile(join(path, f))]
    prog = re.compile('location_indicators_(.*)\..*')
    allIndicators = {}
    for fn in files:
        result=prog.match(fn)
        if result != None:
            allIndicators[result.group(1)] = loadIndicators(path+"/"+fn)
    return allIndicators
    
def load_map_indicators(path):
    files = [f for f in listdir(path) if isfile(join(path, f))]
    prog = re.compile('location_indicators_(.*)\..*')
    indicators = Indicator()
    for fn in files:
        result=prog.match(fn)
        if result != None:
            indicators.load_indicator_file(path+"/"+fn)
    return indicators
    
class QTranusProject(object):
    def __init__(self, proj):
        self.proj = proj
        self.tranus_project = None
        self.shape = None
        self.load()
        self.map_data = MapData()


    def load(self):
        self.tranus_project = None
        self.load_tranus_folder()
        self.load_shapes()
        self.load_scenarios()

    def checkExpression(self, expr, field, scenario):
        field = field.strip()
        print expr
        print field
        print scenario
        project = self.shape[0:max(self.shape.rfind('\\'), self.shape.rfind('/'))]
        indicators = loadProjectIndicators(project)
        result, output = checkExpression(expr, field, scenario, indicators) 
        return result, output

        # analize()
        
    def addLayer(self, layerName, expression, scenario, fieldname, stackOfExpession):
        
        if scenario is None:
            print  ("Please select an scenario.")
            return False
        
        #print("Add:"+layerName+" "+expression+" "+scenario)
        registry = QgsMapLayerRegistry.instance()
        layersCount = len(registry.mapLayers())
        #print ('Number of Layers: {0}'.format(layersCount))
        group = self.get_layers_group()
        layer = QgsVectorLayer(self.shape, layerName, 'ogr') # memory???
        registry.addMapLayer(layer, False)
        if not layer.isValid():
            self['zones_shape'] = ''
            self['zones_shape_id'] = ''
            return False
        
        # Gets shape's file folder
        project = self.shape[0:max(self.shape.rfind('\\'), self.shape.rfind('/'))]
        #print(project)
        
        # Gets field name
        fieldname = fieldname.strip()
        
        # Creation of CSV file to be used for JOIN operation
        result, minValue, maxValue, rowCounter = self.map_data.create_csv_file(layerName, expression, scenario, fieldname, project, stackOfExpession)
        if result:
            csvFile_uri = "file:///" + project + "/" + layerName + ".csv?delimiter=,"
            #print(csvFile_uri)
            csvFile = QgsVectorLayer(csvFile_uri, layerName, "delimitedtext")
            registry.addMapLayer(csvFile, False)
            shpField = 'zoneID'
            csvField = 'ZoneId'
            joinObject = QgsVectorJoinInfo()
            joinObject.joinLayerId = csvFile.id()
            joinObject.joinFieldName = csvField
            joinObject.targetFieldName = shpField
            joinObject.memoryCache = True
            layer.addJoin(joinObject)
            
            print(minValue, maxValue, rowCounter)
            
            myStyle = QgsStyleV2().defaultStyle()
            defaultColorRampNames = myStyle.colorRampNames()        
            ramp = myStyle.colorRamp(defaultColorRampNames[0])
            ranges  = []
            nCats = ramp.count()
            #print("nCats: {0}".format(nCats))
            print("Total colors: "+str(nCats))
            rng = maxValue - minValue
            red0 = 255
            red1 = 0
            green0 = 255
            green1 = 0
            blue0 = 255
            blue1 = 255
            nCats = 50
            for i in range(0,nCats):
                v0 = minValue + rng/float(nCats)*i
                v1 = minValue + rng/float(nCats)*(i+1)
                symbol = QgsSymbolV2.defaultSymbol(layer.geometryType())
                red = red0 + float(i)/float(nCats-1)*(red1-red0)
                green = green0 + float(i)/float(nCats-1)*(green1-green0)
                blue = blue0 + float(i)/float(nCats-1)*(blue1-blue0)
                symbol.setColor(QColor(red, green, blue))
                myRange = QgsRendererRangeV2(v0,v1, symbol, "")
                ranges.append(myRange)
            
            # The first parameter refers to the name of the field that contains the calculated value (expression) 
            renderer = QgsGraduatedSymbolRendererV2(layerName + "_JoinField" + fieldname, ranges)
            
            renderer.setSourceColorRamp(ramp)
            layer.setRendererV2(renderer)

            group.insertLayer((layersCount+1), layer)
            self['zones_shape'] = layer.source()
            self['zones_shape_id'] = layer.id()

        return True
        
    def load_scenarios(self):
        pass #self.scenarios = loadProjectIndicators(self['tranus_folder'])

    def load_tranus_folder(self, folder=None):
        folder = folder or self['tranus_folder']
        path = os.path.join(folder, 'W_TRANUS.CTL')
        print (path)
        try:
            tranus_project = TranusProject.load_project(path)
        except Exception as e:
            print (e)
            self.tranus_project = None
            return False
        else:
            self.tranus_project = tranus_project
            self['tranus_folder'] = folder
            return True

    def load_zones_shape(self, shape): #, expr):
        self.shape = shape
        #print("self.shape: "+self.shape)
        registry = QgsMapLayerRegistry.instance()
        group = self.get_layers_group()
        layer = QgsVectorLayer(shape, 'Zonas', 'ogr')
        if not layer.isValid():
            self['zones_shape'] = ''
            self['zones_shape_id'] = ''
            return False
            
        project = shape[0:max(shape.rfind('\\'), shape.rfind('/'))]     

        #project = self.shape[0:max(self.shape.rfind('\\'), self.shape.rfind('/'))]            
        self.indicators = loadProjectIndicators(project)
        if self.map_data.indicators is not None:
            if len(self.map_data.indicators.scenarios) == 0:
                self.map_data.indicators = load_map_indicators(project)
                self.map_data.load_dictionaries()
        #print(indicators)

        #print(project)
  #      indicators = loadProjectIndicators(project)
  #      table = evaluateExpression(indicators['01A'], expr, "Price")
#        table = evaluateExpression(indicators['01A'], "(Indus+2*Govm)/(Health+1)", "Price")
        
       # print(table)
            
#        vpr = layer.dataProvider()
        
        #fields = vpr.fields()
        
        #print(fields)
        
            
        #print("test")        

        if self['zones_shape_id']:
            existing_tree = self.proj.layerTreeRoot().findLayer(self['zones_shape_id'])
            if existing_tree:
                existing = existing_tree.layer()
                registry.removeMapLayer(existing.id())   # OJO TODO: esto lo movi a la derecha, estaba fuera del if
            
        # key = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        # #Random.ran
            
        # pr = layer.dataProvider()
        # pr.addAttributes([QgsField(key, QVariant.Double)])
        # layer.updateFields()
        
        # #print("Voy")
        # #print(pr.fieldNameMap())
        
        # i = 0

        # iter = layer.getFeatures()
        # for feature in iter:
            # att = key
            # #feature[att] = 666
            # #print(feature.id)
            # print(feature[0])
            # value = table[str(int(feature[0]))]
            # pr.changeAttributeValues({feature.id() : {pr.fieldNameMap()[att] : value}})
            # i = i + 1
            
            
        # #layer.startEditing()            
        # #layer.addAttribute(QgsField("ComputedValue", QVariant.Double))
        # #layer.updateFields()        
        # #layer.changeAttributeValue(7, fieldIndex, value)
        
      # #  newFeature = QgsFeature()
        
        # #iter = layer.getFeatures()
        # #for feature in iter:
        # #    feature['computedValue'] = 666
            # #feature.setAttributes([feature[0], feature[1], feature[2], feature[3], 666])
            
        # #layer.commitChanges()
        # #layer.updateExtents()
            
        # iter = layer.getFeatures()    
        # for feature in iter:
            # print(str(feature[0])+"  "+str(feature[1])+"  "+str(feature[2])+"  "+str(feature[3])+" "+str(feature[key]))
            
        #1/0

        registry.addMapLayer(layer, False)
        group.insertLayer(0, layer)
        self['zones_shape'] = layer.source()
        self['zones_shape_id'] = layer.id()
        return True

    def __getitem__(self, key):
        value, _ = self.proj.readEntry('qtranus', key)
        return value

    def __setitem__(self, key, value):
        self.proj.writeEntry('qtranus', key, value)


    def is_created(self):
        return not not self['project_name']

    def is_valid(self):
        return not not (self['zones_shape'] and self['project_name'] and self['tranus_folder'])

    def get_layers_group(self):
        group_name = self['layers_group_name'] or 'QTRANUS'
        layers_group = self.proj.layerTreeRoot().findGroup(group_name)
        if layers_group is None:
            layers_group = self.proj.layerTreeRoot().addGroup(group_name)
        return layers_group

    def load_shapes(self):
        zones_shape = self['zones_shape']
        layers_group = self.get_layers_group()
        
        for layer in layers_group.findLayers():
            if layer.layer().source() == zones_shape:
                self['zones_shape_id'] = layer.layer().id()
