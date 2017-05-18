from ..general.FileManagement import FileManagement
from Level import Level
import csv, numpy as np
from PyQt4.Qt import QMessageBox

class NetworkDataAccess(object):
    def __init__(self):
        self.variables_dic = {}
        self.scenarios = []
        self.operators_dic = {}
        self.routes_dic = {}
        self.networ_matrices = []
        
    def __del__(self):
        """
            @summary: Destroys the object
        """
        print (self.__class__.__name__, "destroyed")
        
    def get_variables_dic(self):
        """
            @summary: Returns variables dictionary
        """
        return {0:"StVeh/Cap", 1:"StVeh", 2:"TotVeh", 3:"ServLev", 4:"Demand", 5:"Dem/Cap", 6:"FinSpeed", 7:"FinWait", 8:"Energy" }
    
    def get_valid_network_scenarios(self, projectPath):
        return FileManagement.get_scenarios_from_filename(projectPath, 'Assignment_SWN(.*)', '\..*')
    
    def get_scenario_operators(self, projectPath, scenario):
        operatorsMatrix = None
        operators_dic = {}
        networkMatrix = FileManagement.get_np_matrix_from_csv(projectPath, 'Assignment_SWN', scenario, '\..*') 
        if networkMatrix is not None:
            if networkMatrix.data_matrix.size > 0:
                operatorsMatrix = np.unique(networkMatrix.data_matrix[['OperId', 'OperName']])
                operatorsMatrix.sort(order='OperId')
                 
                for item in np.nditer(operatorsMatrix):
                    operators_dic[item.item(0)[0]] = item.item(0)[1]
                    
        return operators_dic 
    
    def get_scenario_routes(self, projectPath, scenario):
        routesMatrix = None
        routes_dic = {}
        networkMatrix = FileManagement.get_np_matrix_from_csv(projectPath, 'Assignment_SWN', scenario, '\..*') 
        if networkMatrix is not None:
            if networkMatrix.data_matrix.size > 0:
                routesMatrix = np.unique(networkMatrix.data_matrix[['RouteId', 'RouteName']])
                routesMatrix.sort(order='RouteId')
                
                for item in np.nditer(routesMatrix):
                    routes_dic[item.item(0)[0]] = item.item(0)[1]
        
        return routes_dic
    
    def __get_network_ids(self, networkMatrix):
        if networkMatrix is not None:
            if networkMatrix.data_matrix.size > 0:
                routesMatrix = np.unique(networkMatrix.data_matrix[['Id', 'Orig', 'Dest']])
                #routesMatrix.sort(order='Id')
                return routesMatrix
        
        return None
    
    def __getrows(self, origin, destination, networkMatrix):
        rowsData = None
        rowsData = networkMatrix.data_matrix[
                                          (networkMatrix.data_matrix['Orig'] == origin)
                                          &
                                          (networkMatrix.data_matrix['Dest'] == destination)
                                         ]
        if rowsData is not None:
            if rowsData.size > 0:
                return rowsData 
    
    
    def __evaluate_network_expression(self, layerName, scenariosExpression, networkExpression, variable, level, projectPath):
    
        rowData = None
        rowsData = None
        matrixData = None
        try:
            if level == Level.Total:
                networkMatrix = FileManagement.get_np_matrix_from_csv(projectPath, 'Assignment_SWN', scenariosExpression.pop(), '\..*')
                oriDestPairs = self.__get_network_ids(networkMatrix)
                types = oriDestPairs.dtype
                
                if oriDestPairs is not None:
                    for pair in np.nditer(oriDestPairs):
                        rowsData = self.__getrows(pair['Orig'], pair['Dest'], networkMatrix)
                        result = None
                        resultType = None
                        if rowsData is not None:
                            if variable == 'StVeh/Cap':
                                stVehSum = rowsData['StVeh'].sum(axis=0)
                                cap = rowsData['LinkCap'][0]
                                if np.isinf(cap):
                                        result = 0
                                else:
                                    cap = float(cap)
                                    if cap == 0:
                                        result = 0
                                    else:
                                        result = stVehSum / cap
                                resultType = rowsData[0]['StVeh'].dtype
                                            
                            if variable == 'StVeh':
                                result = rowsData['StVeh'].sum(axis=0)
                                resultType = rowsData[0]['StVeh'].dtype
                            
                            if variable == 'TotVeh':
                                result = rowsData['Vehics'].sum(axis=0)
                                resultType = rowsData[0]['Vehics'].dtype
                                
                            if variable == 'Demand':
                                result = rowsData['Demand'].sum(axis=0)
                                resultType = rowsData[0]['Demand'].dtype
                                
                            if variable == 'Energy':
                                result = rowsData['Energy'].sum(axis=0)
                                resultType = rowsData[0]['Energy'].dtype
                            
                            if variable == 'ServLev':
                                result = rowsData['ServLev'][0]
                                resultType = rowsData[0]['ServLev'].dtype
                                
                            if variable == 'Dem/Cap':
                                sumDeman = rowsData['Demand'].sum(axis=0)
                                cap = rowsData['Capac'].sum(axis=0)
                                if np.isinf(cap):
                                        result = 0
                                else:
                                    cap = float(cap)
                                    if cap == 0:
                                        result = 0
                                    else:
                                        result = sumDeman / cap
                                resultType = rowsData[0]['Demand'].dtype
                                
                            if variable == 'FinSpeed':
                                result = rowsData['FinSpeed'].max(axis=0)
                                resultType = rowsData[0]['FinSpeed'].dtype
                                
                            if variable == 'FinWait':
                                result = rowsData['FinWait'].sum(axis=0)
                                resultType = rowsData[0]['FinWait'].dtype
                            
                            rowData = np.array([(pair['Id'], result)], 
                                                   dtype = [('Id', pair.dtype[0]), 
                                                            ('Result', resultType)])
                            
                            if matrixData is None:
                                matrixData = rowData
                            else:
                                matrixData = np.concatenate((matrixData, rowData))

            #else:
                

        except Exception as inst:
            print(inst)
            matrixData = None
            QMessageBox.warning(None, "Error", "Unexpected error: {0}".format(inst))
        except:
            QMessageBox.warning(None, "Network expression", "Unexpected error: {0}".format(sys.exc_info()[0]))
            print("Unexpected error:", sys.exc_info()[0])
            matrixData = None
        finally:
            del rowData
            del rowsData
            
        return matrixData    
    
    def create_network_csv_file(self, layerName, scenariosExpression, networkExpression, variable, level, projectPath):
        rowCounter = 0
        networkMatrixResult = None

        if scenariosExpression.tp > 1:
            return True
        else:
            networkMatrixResult = self.__evaluate_network_expression(layerName, scenariosExpression, networkExpression, variable, level, projectPath)
        
        if networkMatrixResult is None:
            QMessageBox.warning(None, "Network matrix data", "There is not data to evaluate.")
            print ("There is not data to evaluate.")
            return False
        
        csvFile = open(projectPath + "\\" + layerName + ".csv", "wb")
        newFile = csv.writer(csvFile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        newFile.writerow(['Id', 'Result'])
        for rowItem in np.nditer(networkMatrixResult):
            newFile.writerow([rowItem['Id'], rowItem['Result']])
                    
        del newFile
        csvFile.close
        del csvFile
        
        return True