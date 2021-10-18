"""April 2021 Colin Lindeman, clindeman@niyamit.com, colinlindeman@gmail.com

Requirements: Python 3, Hazpy 0.0.1, Anaconda with hazus_env installed

Recursively finds .hpr files in input folder (and subdirectories).

How to use: Define your input folder containing hpr files and define
            an output folder to export the results and files to. This
            must be run from the python from the Anaconda virtual
            environment named hazus_env that is installed when the regular
            export tool is run.

            Start by going to the bottom of this script
            to change the user inputs, then open a terminal in anaconda
            hazus_env, navigate to this scripts directory, activate
            python in the terminal and run this script.

"""
# Standard library imports
from datetime import timedelta
import os
from pathlib import Path
import sys
import time
import uuid

# Third party imports
import pandas as pd

# Local application imports
from studyregion import StudyRegion


def getAnalysisLogDate(logfile):
    """Find the date of analysis from a AnalysisLog.txt

        Key Argument:
            logfile: string -- the path to the logfie
        Returns:
            analysisLogDate: string -- The date the flAnalysisLog was created in YYYY-MM-DD
        Notes:
            1st Line of flAnalysisLog.txt:
                2021/04/20 11:49:28.227 File: "C:\HazusData\Regions\nora\nora_08\\flAnalysisLog.txt" created on-the-fly from MSSQL
            1st line of TsunamiLog.txt:
                5/5/2018 2:07:20 PM Start Hazard Process
            
    """
    try:
        file = open(logfile, 'r')
        date = file.readline().split(' ')[0].split('/')
        if len(date) == 3:
            if len(date[0]) > 2:
                year = date[0]
                month = date[1]
                day = date[2]
            elif len(date[2]) > 2:
                year = date[2]
                month = date[0]
                day = date[1]
            analysisLogDate = f"{year}-{month}-{day}"
            return analysisLogDate
        return 'FIX ME: YYYY-MM-DD'
    except Exception as e:
        print('\nUnexpected error getflAnalysisLogDate')
        print(e)

def exportHPR(hprFile, outputDir, deleteDB=1, deleteTempDir=1, outCsv=1, outShapefile=1, outReport=0, outJson=1):
    """This tool will use hazpy.legacy.hazuspackagregion to batch export
        hpr files in a directory to a user specified output directory.

        Keyword Arguments:
                hprFile: str -- a directory path containing hpr files
                outputDir: str -- a directory to write export files to
                deleteDB: int -- if 1, delete database, if 0 don't
                deleteTempDir: int -- if 1, delete temp dir, if 0 don't
                outCSV: int -- if 1: export CSV files; if 0: don't
                outShapefile: int -- if 1: export Zipped Shapefiles; if 0: don't
                outReport: int -- if 1: export PDF files; if 0: don't
                outJson: int -- if 1: export GeoJSON files; if 0: don't

        Notes: The hazpy legacy code has only been tested against USGS FIM
            Flood HPR files. It does not process HPR files in subdirectories
            of the main directory.
            
    """
    try:
        hpr = StudyRegion(studyRegion=None, hprFilePath=hprFile, outputDir=outputDir)
    except Exception as e:
        print('Unexpected error exporting HPR.')
        print(e)
        
    
    print("-----------------------------------------------------------------------------------------------------------------------------")
    print(f"User Defined hprFilePath: {hpr.hprFilePath}") #debug
    print(f"User Defined outputDir = {hpr.outputDir}") #debug
    print(f"tempDir = {hpr.tempDir}") #debug
    print(f"hpr zipfile comment: {hpr.hprComment}") #debug
    print(f"Hazus Version: {hpr.HazusVersion}") #debug
    print(f"Available Hazards: {hpr.Hazards}") #debug
    print()

    #DO NOT PROCESS HPR BELOW VERSION 3.1...
    if hpr.HazusVersion in ['Hazus 3.1','Hazus 4.0','Hazus 4.1','Hazus 4.2','Hazus 4.2.1','Hazus 4.2.2','Hazus 4.2.3','Hazus 5.0','Hazus 5.1']:
        try:
            hpr.restoreHPR()
        except Exception as e:
            print(e)

        try:
            print('\nGetting Return Periods...')
            hpr.getHazardsScenariosReturnPeriods()
            print(hpr.HazardsScenariosReturnPeriods) #debug

            #CREATE A DIRECTORY FOR THE OUTPUT FOLDERS...
            outputPath = hpr.outputDir
            if not os.path.exists(outputPath):
                os.mkdir(outputPath)
                        
            #CREATE HAZUS LOSS LIBRARY (HLL) METADATA TABLES...
            hllMetadataEvent = pd.DataFrame(columns=['id',
                                                    'name',
                                                    'geom',
                                                    'date',
                                                    'image'])

            hllMetadataScenario = pd.DataFrame(columns=['id',
                                                        'name',
                                                        'hazard',
                                                        'analysisType',
                                                        'date',
                                                        'source',
                                                        'modifiedInventory',
                                                        'geographicCount',
                                                        'geographicUnit',
                                                        'losses',
                                                        'lossesUnit',
                                                        'meta',
                                                        'event',
                                                        'geom'])

            hllMetadataDownload = pd.DataFrame(columns=['id',
                                                        'category',
                                                        'subcategory',
                                                        'name',
                                                        'icon',
                                                        'link',
                                                        'file',
                                                        'meta',
                                                        'analysis'])


            #ITERATE OVER THE HAZARD, SCENARIO, RETURNPERIOD AVAIALABLE COMBINATIONS...
            for hazard in hpr.HazardsScenariosReturnPeriods:
                print()
                print(f"Hazard: {hazard['Hazard']}") #debug
                
                #SET HPR HAZARD...
                hpr.hazard = hazard['Hazard']

                #EXPORT Hazus Package Region TO GeoJSON...
                exportPath = Path.joinpath(Path(outputPath))
                try:
                    print('\nWriting StudyRegionBoundary to geojson...')
                    studyRegionBoundary = hpr.getStudyRegionBoundary()
                    studyRegionBoundary.toGeoJSON(Path.joinpath(exportPath, 'StudyRegionBoundary.geojson'))
                except Exception as e:
                    print('\nStudyRegionBoundary not available to export to geojson')
                    print(e)

                #Event metadata...
                #ADD ROW TO hllMetadataEvent TABLE...
                hazardUUID = uuid.uuid4()
                filePath = Path.joinpath(exportPath, 'StudyRegionBoundary.geojson')
                #filePathRel = str(filePath.relative_to(Path(hpr.outputDir))) #excludes sr name; for non-aggregate hll metadata
                filePathRel = str(filePath.relative_to(Path(hpr.outputDir).parent)) #includes SR name; for aggregate hll metadata
                #need to add path to hazard boundary (is this unique for each returnperiod/download in FIMS?)
                hllMetadataEvent = hllMetadataEvent.append({'id':hazardUUID,
                                                            'name':hpr.dbName,
                                                            'geom':filePathRel}, ignore_index=True)

                #SCENARIOS/ANALYSIS
                for scenario in hazard['Scenarios']:
                    print(f"Scenario: {scenario['ScenarioName']}") #debug

                    #SET HPR SCENARIO...
                    hpr.scenario = scenario['ScenarioName']

                    #Analysis Metadata part one of two...
                    scenarioUUID = uuid.uuid4()
                    scenarioMETA = {"Hazus Version":f"{hpr.HazusVersion}"}
                    scenarioGEOM = '' #initialize variable to be changed later
                    analysisType = 'FIX ME: Deterministic, Historic, Probabilistic' #initialize variable to be changed later
                    analysisDate = 'FIX ME: (YYYY-MM-DD)' #initialize variable to be changed later
                    scenarioSource = 'FIX ME: USER INPUT NEEDED (100 chars max)' #default value, likely to change
                    downloadLink = '' #default value
                    scenarioGeographicCount = '' #initialize variable to be changed later
                    scenarioGeographicUnit = '' #initialize variable to be changed later
                    scenarioLosses = '' #initialize variable to be changed later
                    scenarioLossesUnit = '' #initialize variable to be changed later
                    
                    if hazard['Hazard'] == 'earthquake':
                        scenarioMETA["Magnitude"] = hpr.getEarthquakeMagnitude()
                        analysisType = hpr.getAnalysisType()
                        if analysisType in ['Probabilistic']:
                            scenarioSource = 'USGS National Hazard Maps'
                        if analysisType in ['Historic', 'Deterministic']:
                            scenarioSource = 'USGS ShakeMap'
                            downloadLink = hpr.getEarthquakeShakemapUrl()
                        analysisDate = hpr.getHPRFileDateTime(hpr.hprFilePath, 'AnalysisLog.txt')
                    if hazard['Hazard'] == 'flood':
                        analysisType = 'Deterministic' #USGS FIM
                        """i.e. 'C:\workspace\batchexportOutput\nora\nora_08\\flAnalysisLog.txt'"""
                        logfile = Path.joinpath(Path(hpr.tempDir), scenario['ScenarioName'],'flAnalysisLog.txt')
                        analysisDate = getAnalysisLogDate(logfile)
                    if hazard['Hazard'] == 'hurricane':
                        analysisType = hpr.getAnalysisType()
                    if hazard['Hazard'] == 'tsunami':
                        analysisType = 'Deterministic' 
                        logfile = Path.joinpath(Path(hpr.tempDir),'TsunamiLog.txt')
                        analysisDate = getAnalysisLogDate(logfile)

                    #RETURNPERIODS/DOWNLOAD
                    if isinstance(scenario['ReturnPeriods'], list):
                        returnPeriods = scenario['ReturnPeriods']
                    else:
                        returnPeriods = scenario['ReturnPeriods'].split()
                    for returnPeriod in returnPeriods:
                        skipHPR = 0

                        #SET HPR RETURNPERIOD...
                        hpr.returnPeriod = returnPeriod
                        print(f"hazard = {hpr.hazard}, scenario = {hpr.scenario}, returnPeriod = {returnPeriod}") #debug

                        #GET BULK OF RESULTS...
                        try:
                            print('\nGet bulk of results...')
                            results = hpr.getResults()
                            essentialFacilities = hpr.getEssentialFacilities()
                            if len(results) < 1:
                                print('\nNo results found. Please check your Hazus Package Region and try again.')
                                skipHPR = 1 #do not try processing the hpr
                        except Exception as e:
                            print(e)
                            
                        if skipHPR == 0:
                            #HLL Analysis/Scenario Metadata (some sceneario/analysis level info requires returnperiod/download input)...
                            geographicCountUnit = hpr.getGeographicCountUnitofResults(results)
                            scenarioGeographicCount = geographicCountUnit[0]
                            scenarioGeographicUnit = geographicCountUnit[1]
                            scenarioLosses = int(hpr.getTotalEconomicLoss())
                            scenarioLossesUnit = 'USD'
                            if scenarioLosses >= 1000 and scenarioLosses < 1000000:
                                scenarioLosses = str(round(scenarioLosses/1000,1))
                                scenarioLossesUnit = 'thousand'
                            elif scenarioLosses >= 1000000 and scenarioLosses < 1000000000:
                                scenarioLosses = str(round(scenarioLosses/1000000,1))
                                scenarioLossesUnit = 'million'
                            elif scenarioLosses >= 1000000000 and scenarioLosses < 1000000000000:
                                scenarioLosses = str(round(scenarioLosses/1000000000,1))
                                scenarioLossesUnit = 'billion'
                            elif scenarioLosses >= 1000000000000:
                                scenarioLosses = str(round(scenarioLosses/1000000000000,1))
                                scenarioLossesUnit = 'trillion'
                            else:
                                pass

                            #HLL ReturnPeriod/Downloads Metadata
                            downloadCategory = returnPeriod

                                                
                            #CREATE A DIRECTORY FOR THE OUTPUT FOLDERS (and set some HLL metadata values)...
                            if hazard['Hazard'] == 'earthquake' and analysisType in ['Deterministic', 'Historic']:
                                #Deterministic;Shakemap;Scenario
                                exportPath = Path.joinpath(Path(outputPath), str(hazard['Hazard']).strip(), str(scenario['ScenarioName']).strip())
                                downloadCategory = 'Results'
                            elif hazard['Hazard'] == 'earthquake' and analysisType in ['Probabilistic']:
                                #Probabilistic
                                exportPath = Path.joinpath(Path(outputPath), str(hazard['Hazard']).strip(), str(scenario['ScenarioName']).strip(), str(returnPeriod).strip()) 
                            elif hazard['Hazard'] == 'flood':
                                #USGS FIM Deterministic
                                exportPath = Path.joinpath(Path(outputPath), str(hazard['Hazard']).strip(), str(scenario['ScenarioName']).strip(), 'STAGE_' + str(returnPeriod).strip())
                            elif hazard['Hazard'] == 'hurricane' and analysisType in ['Deterministic', 'Historic']:
                                #Deterministic
                                exportPath = Path.joinpath(Path(outputPath), str(hazard['Hazard']).strip(), str(scenario['ScenarioName']).strip())
                                downloadCategory = 'Results'
                                if analysisType == 'Deterministic':
                                    scenarioSource = 'Hurrevac/Other'
                                if analysisType == 'Historic':
                                    scenarioSource = 'Historic'
                            elif hazard['Hazard'] == 'hurricane' and analysisType in ['Probabilistic']:
                                #Probabilistic
                                if str(downloadCategory) == '0':
                                    downloadCategory = 'Annualized'
                                exportPath = Path.joinpath(Path(outputPath), str(hazard['Hazard']).strip(), str(scenario['ScenarioName']).strip(), str(returnPeriod).strip())
                            elif hazard['Hazard'] == 'tsunami':
                                downloadCategory = 'Results'
                                exportPath = Path.joinpath(Path(outputPath), str(hazard['Hazard']).strip(), str(scenario['ScenarioName']).strip())
                            else:
                                exportPath = Path.joinpath(Path(outputPath), str(hazard['Hazard']).strip(), str(scenario['ScenarioName']).strip(), str(returnPeriod).strip()) 
                            Path(exportPath).mkdir(parents=True, exist_ok=True) #this may make the earlier HPR dir creation redundant

                            #EXPORT Hazus Package Region TO CSV...
                            if outCsv == 1:
                                try:
                                    try:
                                        print('\nWriting results to csv...')
                                        results.toCSV(Path.joinpath(exportPath, 'results.csv'))
                                        #ADD ROW TO hllMetadataDownload TABLE...
                                        downloadUUID = uuid.uuid4()
                                        filePath = Path.joinpath(exportPath, 'results.csv')
                                        #filePathRel = str(filePath.relative_to(Path(hpr.outputDir))) #excludes sr name; for non-aggregate hll metadata
                                        filePathRel = str(filePath.relative_to(Path(hpr.outputDir).parent)) #includes SR name; for aggregate hll metadata
                                        hllMetadataDownload = hllMetadataDownload.append({'id':downloadUUID,
                                                                                        'category':downloadCategory,
                                                                                        'subcategory':'Results',
                                                                                        'name':'Results.csv',
                                                                                        'icon':'spreadsheet',
                                                                                        'file':filePathRel,
                                                                                        'analysis':scenarioUUID}, ignore_index=True)
                                    except Exception as e:
                                        print('\nBase results not available to export to csv...')
                                        print(e)
                                    
                                    try:
                                        print('\nWriting building damage by occupancy to CSV')
                                        buildingDamageByOccupancy = hpr.getBuildingDamageByOccupancy()
                                        buildingDamageByOccupancy.toCSV(Path.joinpath(exportPath, 'building_damage_by_occupancy.csv'))
                                        #ADD ROW TO hllMetadataDownload TABLE...
                                        downloadUUID = uuid.uuid4()
                                        filePath = Path.joinpath(exportPath, 'building_damage_by_occupancy.csv')
                                        #filePathRel = str(filePath.relative_to(Path(hpr.outputDir))) #excludes sr name; for non-aggregate hll metadata
                                        filePathRel = str(filePath.relative_to(Path(hpr.outputDir).parent)) #includes SR name; for aggregate hll metadata
                                        hllMetadataDownload = hllMetadataDownload.append({'id':downloadUUID,
                                                                                        'category':downloadCategory,
                                                                                        'subcategory':'Building Damage',
                                                                                        'name':'Building Damage by Occupancy.csv',
                                                                                        'icon':'spreadsheet',
                                                                                        'file':filePathRel,
                                                                                        'analysis':scenarioUUID}, ignore_index=True)
                                    except Exception as e:
                                        print('\nBuilding damage by occupancy not available to export to csv...')
                                        print(e)
                                    
                                    try:
                                        print('\nWriting building damage by type to CSV')
                                        buildingDamageByType = hpr.getBuildingDamageByType()
                                        buildingDamageByType.toCSV(Path.joinpath(exportPath,'building_damage_by_type.csv'))
                                        #ADD ROW TO hllMetadataDownload TABLE...
                                        downloadUUID = uuid.uuid4()
                                        filePath = Path.joinpath(exportPath, 'building_damage_by_type.csv')
                                        #filePathRel = str(filePath.relative_to(Path(hpr.outputDir))) #excludes sr name; for non-aggregate hll metadata
                                        filePathRel = str(filePath.relative_to(Path(hpr.outputDir).parent)) #includes SR name; for aggregate hll metadata
                                        hllMetadataDownload = hllMetadataDownload.append({'id':downloadUUID,
                                                                                        'category':downloadCategory,
                                                                                        'subcategory':'Building Damage',
                                                                                        'name':'Building Damage by Type.csv',
                                                                                        'icon':'spreadsheet',
                                                                                        'file':filePathRel,
                                                                                        'analysis':scenarioUUID}, ignore_index=True)
                                    except Exception as e:
                                        print('\nBuilding damage by type not available to export to csv...')
                                        print(e)
                                    
                                    try:
                                        print('\nWriting damaged facilities to CSV')
                                        essentialFacilities.toCSV(Path.joinpath(exportPath, 'damaged_facilities.csv'))
                                        #ADD ROW TO hllMetadataDownload TABLE...
                                        downloadUUID = uuid.uuid4()
                                        filePath = Path.joinpath(exportPath, 'damaged_facilities.csv')
                                        #filePathRel = str(filePath.relative_to(Path(hpr.outputDir))) #excludes sr name; for non-aggregate hll metadata
                                        filePathRel = str(filePath.relative_to(Path(hpr.outputDir).parent)) #includes SR name; for aggregate hll metadata
                                        hllMetadataDownload = hllMetadataDownload.append({'id':downloadUUID,
                                                                                        'category':downloadCategory,
                                                                                        'subcategory':'Damaged Facilities',
                                                                                        'name':'Damaged Facilities.csv',
                                                                                        'icon':'spreadsheet',
                                                                                        'file':filePathRel,
                                                                                        'analysis':scenarioUUID}, ignore_index=True)
                                    except Exception as e:
                                        print('\nDamaged facilities not available to export to csv.')
                                        print(e)
                                    
                                    if hpr.hazard == 'earthquake' and analysisType in ['Historic', 'Deterministic']:
                                        try:
                                            print('\nWriting eqShakeMapScenario to CSV')
                                            EQShakeMapScenario = hpr.getEQShakeMapScenario()
                                            EQShakeMapScenario.toCSV(Path.joinpath(exportPath, 'ShakeMap_Scenario.csv'))
                                            #ADD ROW TO hllMetadataDownload TABLE...
                                            downloadUUID = uuid.uuid4()
                                            filePath = Path.joinpath(exportPath, 'ShakeMap_Scenario.csv')
                                            #filePathRel = str(filePath.relative_to(Path(hpr.outputDir))) #excludes sr name; for non-aggregate hll metadata
                                            filePathRel = str(filePath.relative_to(Path(hpr.outputDir).parent)) #includes SR name; for aggregate hll metadata
                                            hllMetadataDownload = hllMetadataDownload.append({'id':downloadUUID,
                                                                                            'category':downloadCategory,
                                                                                            'subcategory':'Metadata',
                                                                                            'name':'ShakeMap Scenario.csv',
                                                                                            'icon':'spreadsheet',
                                                                                            'file':filePathRel,
                                                                                            'analysis':scenarioUUID}, ignore_index=True)
                                        except Exception as e:
                                            print('\neqShakeMapScenario not available to export to csv.')
                                            print(e)

                                
                                except Exception as e:
                                    print('\nUnexpected error exporting CSVs')
                                    print(e)
                            else:
                                print('\nSkipping CSV exports')
                                    
                            #EXPORT Hazus Package Region TO Shapefile...
                            if outShapefile == 1:
                                try:
                                    try:
                                        print('\nWriting results to shapefile to zipfile...')
                                        results.toShapefiletoZipFile(Path.joinpath(exportPath, 'results.shp'), 'epsg:4326', 'epsg:4326')
                                        #ADD ROW TO hllMetadataDownload TABLE...
                                        downloadUUID = uuid.uuid4()
                                        filePath = Path.joinpath(exportPath, 'results.zip')
                                        #filePathRel = str(filePath.relative_to(Path(hpr.outputDir))) #excludes sr name; for non-aggregate hll metadata
                                        filePathRel = str(filePath.relative_to(Path(hpr.outputDir).parent)) #includes SR name; for aggregate hll metadata
                                        hllMetadataDownload = hllMetadataDownload.append({'id':downloadUUID,
                                                                                        'category':downloadCategory,
                                                                                        'subcategory':'Results',
                                                                                        'name':'Results.shp',
                                                                                        'icon':'spatial',
                                                                                        'file':filePathRel,
                                                                                        'analysis':scenarioUUID}, ignore_index=True)
                                    except Exception as e:
                                        #print('\nBase results not available to export to shapefile...')
                                        print('\nBase results not available to export to shapefile to zipfile...')
                                        print(e)
                                    
                                    try:
                                        print('\nWriting Damaged facilities to shapefile to zipfile.')
                                        essentialFacilities.toShapefiletoZipFile(Path.joinpath(exportPath, 'damaged_facilities.shp'), 'epsg:4326', 'epsg:4326')
                                        #ADD ROW TO hllMetadataDownload TABLE...
                                        downloadUUID = uuid.uuid4()
                                        filePath = Path.joinpath(exportPath, 'damaged_facilities.zip')
                                        #filePathRel = str(filePath.relative_to(Path(hpr.outputDir))) #excludes sr name; for non-aggregate hll metadata
                                        filePathRel = str(filePath.relative_to(Path(hpr.outputDir).parent)) #includes SR name; for aggregate hll metadata
                                        hllMetadataDownload = hllMetadataDownload.append({'id':downloadUUID,
                                                                                        'category':downloadCategory,
                                                                                        'subcategory':'Damaged Facilities',
                                                                                        'name':'Damaged Facilities.shp',
                                                                                        'icon':'spatial',
                                                                                        'file':filePathRel,
                                                                                        'analysis':scenarioUUID}, ignore_index=True)
                                    except Exception as e:
                                        #print('\nDamaged facilities not available to export to shapefile...')
                                        print('\nDamaged facilities not available to export to shapefile to zipfile...')
                                        print(e)

                                    try:
                                        print('\nWriting Hazard Boundary Polygon to shapefile to zipfile...')
                                        #The following two commented out lines encounter ODBC issues on some machines,
                                        #possibly due to 32 and 64bit access driver conflicts
                ##                            hpr.getFloodBoundaryPolyName('R')
                ##                            hpr.exportFloodHazardPolyToShapefileToZipFile(Path.joinpath(exportPath, 'hazardBoundaryPoly.shp'))

                                        hazardGDF = hpr.getHazardGeoDataFrame()
                                        hazardGDF.toShapefiletoZipFile(Path.joinpath(exportPath, 'hazardBoundaryPoly.shp'), 'epsg:4326', 'epsg:4326')
                                        #ADD ROW TO hllMetadataDownload TABLE...
                                        downloadUUID = uuid.uuid4()
                                        filePath = Path.joinpath(exportPath, 'hazardBoundaryPoly.zip')
                                        #filePathRel = str(filePath.relative_to(Path(hpr.outputDir))) #excludes sr name; for non-aggregate hll metadata
                                        filePathRel = str(filePath.relative_to(Path(hpr.outputDir).parent)) #includes SR name; for aggregate hll metadata
                                        hllMetadataDownload = hllMetadataDownload.append({'id':downloadUUID,
                                                                                        'category':downloadCategory,
                                                                                        'subcategory':'Hazard',
                                                                                        'name':'Hazard Boundary.shp',
                                                                                        'icon':'spatial',
                                                                                        'link':downloadLink,
                                                                                        'file':filePathRel,
                                                                                        'analysis':scenarioUUID}, ignore_index=True)
                                    except Exception as e:
                                        print('\nHazard Boundary not available to export to shapefile to zipfile...')
                                        print(e)
                                    
                                except Exception as e:
                                    print(u"Unexpected error exporting Shapefiles: ")
                                    print(e)
                            else:
                                print('\nSkipping Shapefile exports')
                                
                            #EXPORT Hazus Package Region TO GeoJSON...
                            if outJson == 1:
                                try:
                                    try:
                                        print('\nWriting Results to geojson...')
                                        results.toGeoJSON(Path.joinpath(exportPath, 'results.geojson'))
                                        #ADD ROW TO hllMetadataDownload TABLE...
                                        downloadUUID = uuid.uuid4()
                                        filePath = Path.joinpath(exportPath, 'results.geojson')
                                        #filePathRel = str(filePath.relative_to(Path(hpr.outputDir))) #excludes sr name; for non-aggregate hll metadata
                                        filePathRel = str(filePath.relative_to(Path(hpr.outputDir).parent)) #includes SR name; for aggregate hll metadata
                                        hllMetadataDownload = hllMetadataDownload.append({'id':downloadUUID,
                                                                                        'category':downloadCategory,
                                                                                        'subcategory':'Results',
                                                                                        'name':'Results.geojson',
                                                                                        'icon':'spatial',
                                                                                        'file':filePathRel,
                                                                                        'analysis':scenarioUUID}, ignore_index=True)
                                    except Exception as e:
                                        print('\nBase results not available to export to geojson')
                                        print(e)
                                    
                                    try:
                                        print('\nWriting Damaged Facilities to geojson...')
                                        essentialFacilities.toGeoJSON(Path.joinpath(exportPath, 'damaged_facilities.geojson'))
                                        #ADD ROW TO hllMetadataDownload TABLE...
                                        downloadUUID = uuid.uuid4()
                                        filePath = Path.joinpath(exportPath, 'damaged_facilities.geojson')
                                        #filePathRel = str(filePath.relative_to(Path(hpr.outputDir))) #excludes sr name; for non-aggregate hll metadata
                                        filePathRel = str(filePath.relative_to(Path(hpr.outputDir).parent)) #includes SR name; for aggregate hll metadata
                                        hllMetadataDownload = hllMetadataDownload.append({'id':downloadUUID,
                                                                                        'category':downloadCategory,
                                                                                        'subcategory':'Damaged Facilities',
                                                                                        'name':'Damaged Facilities.geojson',
                                                                                        'icon':'spatial',
                                                                                        'file':filePathRel,
                                                                                        'analysis':scenarioUUID}, ignore_index=True)
                                    except Exception as e:
                                        print('\nDamaged facilities not available to export to geojson.')
                                        print(e)                        

                                    try:
                                        print('\nWriting ImpactArea to geojson...')
                                        econloss = hpr.getEconomicLoss()
                                        if len(econloss.loc[econloss['EconLoss'] > 0]) > 0:
                                            econloss.toHLLGeoJSON(Path.joinpath(exportPath, 'impactarea.geojson'))
                                            #ADD ROW TO hllMetadataDownload TABLE...
                                            downloadUUID = uuid.uuid4()
                                            filePath = Path.joinpath(exportPath, 'impactarea.geojson')
                                            #filePathRel = str(filePath.relative_to(Path(hpr.outputDir))) #excludes sr name; for non-aggregate hll metadata
                                            filePathRel = str(filePath.relative_to(Path(hpr.outputDir).parent)) #includes SR name; for aggregate hll metadata
                                            hllMetadataDownload = hllMetadataDownload.append({'id':downloadUUID,
                                                                                            'category':downloadCategory,
                                                                                            'subcategory':'Hazard',
                                                                                            'name':'Impact Area.geojson',
                                                                                            'icon':'spatial',
                                                                                            'file':filePathRel,
                                                                                            'analysis':scenarioUUID}, ignore_index=True)
                                        else:
                                            print('\nno econ loss for HLL geojson')
                                        
                                    except Exception as e:
                                        print('\nImpactArea not available to export to geojson.')
                                        print(e)

                                    try:
                                        """This section is to write the same impact area geojson but at the scenario level."""
                                        print('\nWriting ImpactArea Scenario to geojson...')
                                        econloss = hpr.getEconomicLoss()
                                        if len(econloss.loc[econloss['EconLoss'] > 0]) > 0:
                                            econloss.toHLLGeoJSON(Path.joinpath(exportPath.parent, 'impactarea.geojson'))
                                            #ADD ROW TO hllMetadataDownload TABLE...
                                            filePath = Path.joinpath(exportPath.parent, 'impactarea.geojson')
                                            #filePathRel = str(filePath.relative_to(Path(hpr.outputDir))) #excludes sr name; for non-aggregate hll metadata
                                            scenarioGEOM = str(filePath.relative_to(Path(hpr.outputDir).parent)) #includes SR name; for aggregate hll metadata
                                        else:
                                            print('\nno econ loss for HLL Scenario geojson')
                                    except Exception as e:
                                        print('\nImpactArea Scenario not available to export to geojson.')
                                        print(e)
                                    
                                except Exception as e:
                                    print('\nUnexpected error exporting to GeoJSON:')
                                    print(e)
                            else:
                                print('\nSkipping GeoJSON exports')

                            #EXPORT Hazus Package Region TO PDF Reports...
                            if outReport == 1:
                                try:
                                    #TODO test this; CL
                                    print('\nWriting results to PDF...')
                                    hpr.setReport()
                                    hpr.report.title = 'Title'
                                    hpr.report.subtitle = 'SubTitle'
                                    # TODO: Adjust the location - BC
                                    #hpr.report.save(Path.joinpath(exportPath, 'report_summary.pdf'), premade='')
                                    hpr.report.save(exportPath, openFile=False, premade='')
                                    #ADD ROW TO hllMetadataDownload TABLE...
                                    downloadUUID = uuid.uuid4()
                                    filePath = Path.joinpath(exportPath, 'report_summary.pdf')
                                    #filePathRel = str(filePath.relative_to(Path(hpr.outputDir))) #excludes sr name; for non-aggregate hll metadata
                                    filePathRel = str(filePath.relative_to(Path(hpr.outputDir).parent)) #includes SR name; for aggregate hll metadata
                                    hllMetadataDownload = hllMetadataDownload.append({'id':downloadUUID,
                                                                                    'category': 'Results',
                                                                                    'subcategory':'Report',
                                                                                    'name':'report_summary.pdf',
                                                                                    'icon':'pdf',
                                                                                    'file':filePathRel,
                                                                                    'analysis':scenarioUUID}, ignore_index=True)
                                except Exception as e:
                                    print('\n')
                                    print(e)
                                    exc_type, exc_obj, exc_tb = sys.exc_info()
                                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                                    print(fname)
                                    print(exc_type, exc_tb.tb_lineno)
                                    print('\n')

                                    print('\nUnexpected error exporting to Report PDF:')
                                    print(e)
                            else:
                                print('\nSkiping Report exports')


                    #Analysis Metadata part two of two...
                    #ADD ROW TO hllMetadataScenario TABLE...
                    hllMetadataScenario = hllMetadataScenario.append({'id':scenarioUUID,
                                                                    'name':scenario['ScenarioName'],
                                                                    'hazard':hazard['Hazard'], #flood, hurricane, earthquake, tsunami, tornado
                                                                    'analysisType':analysisType, #historic, deterministic, probabilistic
                                                                    'date':analysisDate, #YYYY-MM-DD
                                                                    'source':scenarioSource, #Max100 chars
                                                                    'modifiedInventory':'false', #true/false
                                                                    'geographicCount':scenarioGeographicCount,
                                                                    'geographicUnit':scenarioGeographicUnit,
                                                                    'losses':scenarioLosses,
                                                                    'lossesUnit':scenarioLossesUnit,
                                                                    'meta':str(scenarioMETA).replace("'",'"'), #needs to be double quotes; one level Python dict/json
                                                                    'event':hazardUUID,
                                                                    'geom':scenarioGEOM}, #filepath to geojson
                                                                    ignore_index=True)
            
            #EXPORT HLL METADATA (NOTE: openpyxl (*et_xmlfile, &jdcal)) not installed, can't export to excel)...
            ##hllMetadataPath = str(Path.joinpath(Path(outputPath), "exportHLLMetadata.xlsx"))
            ##hllMetadata.to_excel(hllMetadataPath)
            
            hllMetadataEventPath = str(Path.joinpath(Path(outputPath), "Event.csv"))
            hllMetadataEvent.to_csv(hllMetadataEventPath, index=False)

            hllMetadataAnalysisPath = str(Path.joinpath(Path(outputPath), "Analysis.csv"))
            hllMetadataScenario.to_csv(hllMetadataAnalysisPath, index=False)

            hllMetadataDownloadPath = str(Path.joinpath(Path(outputPath), "Download.csv"))
            hllMetadataDownload.to_csv(hllMetadataDownloadPath, index=False)

            #DROP SQL SERVER HPR DATABASE...
            if deleteDB == 1:
                hpr.dropDB()

            #DELETE UNZIPPED HPR FOLDER...
            if deleteTempDir == 1:
                hpr.deleteTempDir()
        except Exception as e:
            print('\n')
            print(e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(fname)
            print(exc_type, exc_tb.tb_lineno)
            print('\n')
            
    else:
        print('\nHPR version not supported. HPR not processed')
    print("-----------------------------------------------------------------------------------------------------------------------------")


def aggregateHllMetadataFiles(directory):
    """This tool crawls a directory and subdirectory for hll metadata files and
    aggregates them into one at the root level.
    
    Keyword Arguments:
        directory: str -- a batchExport root directory

    Notes:
        The path should be the root folder containing all the exported hpr folder.
        'Event.csv','Analysis.csv','Download.csv'. Wath out for the relative path in
        the hll metadata.
    """
    print(directory) #user defined outputdir
    try:
        df = pd.concat(map(pd.read_csv, list(Path(directory).glob('**/Event.csv'))))
        df.to_csv(str(Path.joinpath(Path(directory), "Event.csv")), index=False)
    except Exception as e:
        print('\nUnexpected error aggregating HLL Metadata')
        print(e)
    try:
        df = pd.concat(map(pd.read_csv, list(Path(directory).glob('**/Analysis.csv'))))
        df.to_csv(str(Path.joinpath(Path(directory), "Analysis.csv")), index=False)
    except Exception as e:
        print('\nUnexpected error aggregating HLL Metadata')
        print(e)
    try:
        df = pd.concat(map(pd.read_csv, list(Path(directory).glob('**/Download.csv'))))
        #df['file'] = str(Path(directory).name) + df['file'].astype(str)
        df.to_csv(str(Path.joinpath(Path(directory), "Download.csv")), index=False)
    except Exception as e:
        print('\nUnexpected error aggregating HLL Metadata')
        print(e)
        
if __name__ == '__main__':
    print('\nRunning batch export...')
    startTime = time.time()
    print(time.ctime(startTime))
    print("startTime:", time.ctime(startTime))
    #USER DEFINED VALUES
    hprDir = Path.absolute(Path(r'./batch_input'))      #The directory containing hpr files
    outDir = Path.absolute(Path(r'./batch_output'))     #The directory for the output files
    _outCsv = 1         #Export csv files: 1 to export or 0 to skip
    _outShapefile = 1   #Export shapefiles: 1 to export or 0 to skip
    _outReport = 1      #Export report pdf files: 1 to export or 0 to skip
    _outJson = 1        #Export json files: 1 to export or 0 to skip

    #CREATE A DIRECTORY FOR THE OUTPUT FOLDERS...
    if not os.path.exists(outDir):
        os.mkdir(outDir)

    #print(f'Input Directory: {hprDir}') #debug
    #print(f'Output Directory: {outDir}') #debug
    
    print(f'HPR List:')
    fileExt = r'*.hpr'
    hprList = list(Path(hprDir).rglob(fileExt)) #recursively find .hpr files
    for hpr in hprList:
        print(hpr)

    if len(hprList) > 0:
        print(f'Processing HPRs...')

        stdout_fileno = sys.stdout
        logfile = Path.joinpath(Path(outDir),'batchexportlog.txt')
        sys.stdout = open(logfile, 'w+')
        sys.stderr = sys.stdout
        print("startTime:", time.ctime(startTime))
        
        for hpr in hprList:
            try:
                exportHPR(str(hpr), outDir, deleteDB=1, deleteTempDir=1, 
                          outCsv=_outCsv, outShapefile=_outShapefile, outReport=_outReport, outJson=_outJson)
            except Exception as e:
                print(e)

        endTime = time.time()
        print("endTime:", time.ctime(endTime))
        print("Elapsed Time (Hour:Minute:Seconds):", str(timedelta(seconds=endTime-startTime)))
        
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = stdout_fileno
        sys.stderr = sys.stdout
        print(f'Done. Check the {logfile}.')
        
        print('\nAggregating HLL Metadata...')
        aggregateHllMetadataFiles(outDir)
        print('\nDone.')
        print(time.ctime())

    else:
        print('\nno HPR files found')