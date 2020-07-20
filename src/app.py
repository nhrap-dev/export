import ctypes
import sys
from hazpy.legacy import StudyRegion, getStudyRegions
import os
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
from tkinter import OptionMenu
from tkinter import StringVar
from tkinter import ttk
from tkinter import PhotoImage
from tkinter import Label
from tkinter import Canvas
from tkinter.ttk import Progressbar
from tkinter import TOP, RIGHT, LEFT, BOTTOM
from tkinter import N, S, E, W
from PIL import ImageTk, Image
from time import time, sleep
import json


class App():
    # TODO update tab through menu
    # TODO update output directory auto change
    # TODO add more progress steps
    # TODO building count in buildingDamageByType looks high! check fail2
    def __init__(self):
        # Create app
        self.root = tk.Tk()
        # self.root.grid_propagate(0)

        # load config
        config = json.loads(open('src/config.json').read())
        # debug
        self.debug = config['debug']

        # global styles
        themeId = config['activeThemeId']
        theme = list(filter(
            lambda x: config['themes'][x]['themeId'] == themeId, config['themes']))[0]
        self.globalStyles = config['themes'][theme]['style']
        self.backgroundColor = self.globalStyles['backgroundColor']
        self.foregroundColor = self.globalStyles['foregroundColor']
        self.hoverColor = self.globalStyles['hoverColor']
        self.fontColor = self.globalStyles['fontColor']
        self.textEntryColor = self.globalStyles['textEntryColor']
        self.starColor = self.globalStyles['starColor']
        self.padl = 15
        # tk styles
        self.textBorderColor = self.globalStyles['textBorderColor']
        self.textHighlightColor = self.globalStyles['textHighlightColor']

        # ttk styles classes
        self.style = ttk.Style()
        self.style.configure("BW.TCheckbutton", foreground=self.fontColor,
                             background=self.backgroundColor, bordercolor=self.backgroundColor, side='LEFT')
        self.style.configure('TCombobox', background=self.backgroundColor, bordercolor=self.backgroundColor, relief='flat',
                             lightcolor=self.backgroundColor, darkcolor=self.backgroundColor, borderwidth=4, foreground=self.foregroundColor)
        

        # App parameters
        self.root.title('Export Tool')
        self.root.configure(background=self.backgroundColor,highlightcolor='#fff')

        # App images
        self.root.wm_iconbitmap('src/assets/images/Hazus.ico')
        self.img_data = ImageTk.PhotoImage(Image.open(
            "src/assets/images/data_blue.png").resize((20, 20), Image.BICUBIC))
        self.img_edit = ImageTk.PhotoImage(Image.open(
            "src/assets/images/edit_blue.png").resize((20, 20), Image.BICUBIC))
        self.img_folder = ImageTk.PhotoImage(Image.open(
            "src/assets/images/folder_icon.png").resize((20, 20), Image.BICUBIC))

        # Init dynamic row
        self.row = 0

    def updateProgressBar(self, value, message):
        """ Updates the progress bar text and position when processing
        """
        self.label_progress.config(text=message)
        self.root.update_idletasks()
        self.bar_progress['value'] = value

    def browsefunc(self):
        """ Opens a file explorer window and sets the ouputDirectory as the selection
        """
        self.outputDirectory = filedialog.askdirectory()
        self.outputDirectory = self.outputDirectory.replace('\n', '')
        self.text_outputDirectory.delete("1.0", 'end-1c')
        if len(self.dropdown_studyRegion.get()) > 0:
            self.text_outputDirectory.insert(
                "1.0", self.outputDirectory + '/' + self.dropdown_studyRegion.get())
            self.root.update_idletasks()
        else:
            self.text_outputDirectory.insert("1.0", self.outputDirectory)
            self.root.update_idletasks()

    def on_field_change(self, index, value, op):
        """ Updates the output directory and input study region on dropdown selection
        """
        try:
            self.outputDirectory = str(
                self.text_outputDirectory.get("1.0", 'end-1c'))
            self.outputDirectory = self.outputDirectory.replace('\n', '')
            check = self.input_studyRegion in self.outputDirectory
            if (len(self.outputDirectory) > 0) and (not check):
                self.outputDirectory = '/'.join(
                    self.outputDirectory.split('/')[0:-1])
                self.text_outputDirectory.delete('1.0', 'end')
                self.text_outputDirectory.insert(
                    "1.0", self.outputDirectory + '/' + self.input_studyRegion)
            self.root.update_idletasks()
        except:
            pass

    def getTextFields(self):
        """ Retrieves the text from all app text fields
        """
        dict = {
            'title': self.text_title.get("1.0", 'end-1c'),
            'subtitle': self.text_subtitle.get("1.0", 'end-1c'),
            'ouputDirectory': '/'.join(self.text_outputDirectory.get("1.0", 'end-1c').split('/')[0:-1])
        }
        return dict

    def focus_next_widget(self, event):
        event.widget.tk_focusNext().focus()
        return("break")

    def on_enter_dir(self, e):
        self.button_outputDir['background'] = self.hoverColor

    def on_leave_dir(self, e):
        self.button_outputDir['background'] = self.backgroundColor

    def on_enter_run(self, e):
        self.button_run['background'] = '#006b96'

    def on_leave_run(self, e):
        self.button_run['background'] = '#0078a9'

    def run(self):
        try:
            # init time
            t0 = time()

            # make sure all options are selected and get all info
            if not self.validateRequiredFields():
                ctypes.windll.user32.MessageBoxW(
                    None, u"Please select these required fields prior to exporting: {e}".format(e=self.selection_errors), u'HazPy - Message', 0)
                return None

            # add progress bar
            self.addWidget_progress()

            # calculate  progress bar increments
            exportOptionsCount = sum([x for x in self.exportOptions.values()])
            if self.exportOptions['report']:
                exportOptionsCount += 2
            exportOptionsCount + 3
            progressIncrement = 100 / exportOptionsCount
            progressValue = 0
            
            # create a directory for the output files
            if not os.path.exists(self.outputDirectory):
                os.mkdir(self.outputDirectory)

            # get bulk of results
            try:
                progressValue = progressValue + progressIncrement
                msg = 'Retrieving base results'
                self.updateProgressBar(progressValue, msg)
                results = self.studyRegion.getResults()
                essentialFacilities = self.studyRegion.getEssentialFacilities()

                # check if the study region contains result data
                if len(results) < 1:
                    tk.messagebox.showwarning(
                        'HazPy', 'No results found. Please check your study region and try again.')
            except:
                ctypes.windll.user32.MessageBoxW(None, u"Unexpected error retrieving base results: " + str(sys.exc_info()[0]), u'HazPy - Message', 0)


            if self.exportOptions['csv']:
                try:
                    progressValue = progressValue + progressIncrement
                    msg = 'Writing results to CSV'
                    self.updateProgressBar(progressValue, msg)
                    try:
                        results.toCSV(self.outputDirectory + '/results.csv')
                    except:
                        print('Base results not available to export.')
                    try:
                        buildingDamageByOccupancy = self.studyRegion.getBuildingDamageByOccupancy()
                        buildingDamageByOccupancy.toCSV(self.outputDirectory + '/building_damage_by_occupancy.csv')
                    except:
                        print('Building damage by occupancy not available to export.')
                    try:
                        buildingDamageByType = studyRegion.getBuildingDamageByType()
                        buildingDamageByType.toCSV(self.outputDirectory + '/building_damage_by_type.csv')
                    except:
                        print('Building damage by type not available to export.')
                    try:
                        essentialFacilities.toCSV(self.outputDirectory + '/damaged_facilities.csv')
                    except:
                        print('Damaged facilities not available to export.')
                except:
                    ctypes.windll.user32.MessageBoxW(
                        None, u"Unexpected error exporting CSVs: " + str(sys.exc_info()[0]), u'HazPy - Message', 0)

            if self.exportOptions['shapefile']:
                try:
                    progressValue = progressValue + progressIncrement
                    msg = 'Writing results to Shapefile'
                    self.updateProgressBar(progressValue, msg)
                    try:
                        results.toShapefile(
                            self.outputDirectory + '/results.shp')
                    except:
                        print('Base results not available to export.')
                    try:
                        essentialFacilities.toShapefile(
                            self.outputDirectory + '/damaged_facilities.shp')
                    except:
                        print('Damaged facilities not available to export.')
                except:
                    ctypes.windll.user32.MessageBoxW(
                        None, u"Unexpected error exporting Shapefile: " + str(sys.exc_info()[0]), u'HazPy - Message', 0)

            if self.exportOptions['geojson']:
                try:
                    progressValue = progressValue + progressIncrement
                    msg = 'Writing results to GeoJSON'
                    self.updateProgressBar(progressValue, msg)
                    try:
                        results.toGeoJSON(
                            self.outputDirectory + '/results.geojson')
                    except:
                        print('Base results not available to export.')
                    try:
                        essentialFacilities.toGeoJSON(
                            self.outputDirectory + '/damaged_facilities.geojson')
                    except:
                        print('Damaged facilities not available to export.')
                except:
                    ctypes.windll.user32.MessageBoxW(
                        None, u"Unexpected error exporting GeoJSON: " + str(sys.exc_info()[0]), u'HazPy - Message', 0)

            if self.exportOptions['report']:
                try:
                    progressValue = progressValue + progressIncrement
                    msg = 'Writing results to PDF (exchanging patience for maps)'
                    self.updateProgressBar(progressValue, msg)
                    reportTitle = self.text_reportTitle.get("1.0", 'end-1c')
                    if len(reportTitle) > 0:
                        self.studyRegion.report.title = reportTitle
                    reportSubtitle = self.text_reportSubtitle.get("1.0", 'end-1c')
                    if len(reportSubtitle) > 0:
                        self.studyRegion.report.subtitle = reportSubtitle
                    self.studyRegion.report.buildPremade()
                    self.studyRegion.report.save(self.outputDirectory + '/report_summary.pdf')
                except:
                    ctypes.windll.user32.MessageBoxW(
                        None, u"Unexpected error exporting the PDF: " + str(sys.exc_info()[0]), u'HazPy - Message', 0)

                self.updateProgressBar(100, 'Complete')
                print('Results available at: ' + self.outputDirectory)
                print('Total elapsed time: ' + str(time() - t0))
                tk.messagebox.showinfo("HazPy", "Success! Output files can be found at: " +
                                    self.outputDirectory)
                self.removeWidget_progress()

        except:
            if 'bar_progress' in dir(self):
                self.removeWidget_progress()
            ctypes.windll.user32.MessageBoxW(
                None, u"Unexpected export error: " + str(sys.exc_info()[0]), u'HazPy - Message', 0)
    
    def validateRequiredFields(self):
        try:
            self.selection_errors = []
            validated = True
            # validate dropdown menus
            if self.dropdown_studyRegion.winfo_ismapped():
                value = self.dropdown_studyRegion.get()
                if len(value) > 0:
                    self.studyRegion = StudyRegion(str(value))
                else:
                    self.selection_errors.append('Study Region')
                    validated = False
            if 'dropdown_scenario' in dir(self) and self.dropdown_scenario.winfo_ismapped():
                value = self.dropdown_scenario.get()
                if len(value) > 0:
                    self.studyRegion.setScenario(value)
                else:
                    self.selection_errors.append('Scenario')
                    validated = False
            if 'dropdown_hazard' in dir(self) and self.dropdown_hazard.winfo_ismapped():
                value = self.dropdown_hazard.get()
                if len(value) > 0:
                    self.studyRegion.setHazard(value)
                else:
                    self.selection_errors.append('Hazard')
                    validated = False
            if 'dropdown_returnPeriod' in dir(self) and self.dropdown_returnPeriod.winfo_ismapped():
                value = self.dropdown_returnPeriod.get()
                if len(value) > 0:
                    self.studyRegion.setReturnPeriod(value)
                else:
                    self.selection_errors.append('Return Period')
                    validated = False
            print('dropdown menus validated')

            # validate export checkboxes
            self.exportOptions = {}
            self.exportOptions['csv'] = self.opt_csv.get()
            self.exportOptions['shapefile'] = self.opt_shp.get()
            self.exportOptions['geojson'] = self.opt_geojson.get()
            self.exportOptions['report'] = self.opt_report.get()

            exportOptionsCount = sum([x for x in self.exportOptions.values()])
            if exportOptionsCount == 0:
                self.selection_errors.append('export checkbox')
                validated = False
            print('export options validated')

            # validate output directory
            self.outputDirectory = self.text_outputDirectory.get("1.0",'end')
            self.outputDirectory = self.outputDirectory.replace('\n', '')
            if len(self.outputDirectory) == 0:
                self.selection_errors.append('output directory')
                validated = False
            print('output directory validated')
            
            return validated
        except:
            validated = False
            ctypes.windll.user32.MessageBoxW(
                None, u"Unexpected export error: " + str(sys.exc_info()[0]), u'HazPy - Message', 0)


    def addWidget_report(self, row):
        # report title
        self.label_reportTitle = tk.Label(
            self.root, text='Report Title', font='Helvetica 10 bold', background=self.backgroundColor, fg=self.fontColor)
        self.label_reportTitle.grid(row=row, column=1, padx=0, pady=(20, 5), sticky=W)
        row += 1
        # report title text input
        self.text_reportTitle = tk.Text(self.root, height=1, width=37, font='Helvetica 10', background=self.textEntryColor, relief='flat',
                                highlightbackground=self.textBorderColor, highlightthickness=1, highlightcolor=self.textHighlightColor)
        self.text_reportTitle.grid(row=row, column=1, padx=(0, 0), pady=(0, 0), sticky=W)
        # report title icon
        self.img_reportTitle = tk.Label(
            self.root, image=self.img_edit, background=self.backgroundColor)
        self.img_reportTitle.grid(row=row, column=2, padx=(0, self.padl), pady=(0, 0), sticky=W)
        row += 1

        # report subtitle
        # report subtitle label
        self.label_reportSubtitle = tk.Label(
            self.root, text='Report Subtitle', font='Helvetica 10 bold', background=self.backgroundColor, fg=self.fontColor)
        self.label_reportSubtitle.grid(row=row, column=1, padx=0, pady=(20, 5), sticky=W)
        row += 1
        # report subtitle text input
        self.text_reportSubtitle = tk.Text(self.root, height=1, width=37, font='Helvetica 10', background=self.textEntryColor, relief='flat',
                        highlightbackground=self.textBorderColor, highlightthickness=1, highlightcolor=self.textHighlightColor)
        self.text_reportSubtitle.grid(row=row, column=1, padx=(0, 0), pady=(0, 0), sticky=W)
        # report subtitle icon
        self.img_reportSubtitle = tk.Label(self.root, image=self.img_edit, background=self.backgroundColor)
        self.img_reportSubtitle.grid(row=row, column=2, padx=(0, self.padl), pady=(0, 0), sticky=W)
    
    def removeWidget_report(self):
        self.label_reportTitle.grid_forget()
        self.text_reportTitle.grid_forget()
        self.text_reportTitle.delete('1.0', 'end')
        self.img_reportTitle.grid_forget()

        self.label_reportSubtitle.grid_forget()
        self.text_reportSubtitle.grid_forget()
        self.text_reportSubtitle.delete('1.0', 'end')
        self.img_reportSubtitle.grid_forget()

    def handle_reportCheckbox(self):
        val = self.opt_report.get()
        if val == 0:
            self.removeWidget_report()
        if val == 1:
            self.addWidget_report(self.row_report)  

    def addWidget_hazard(self, row):
        # requred label
        self.required_hazard = tk.Label(
            self.root, text='*', font='Helvetica 14 bold', background=self.backgroundColor, fg=self.starColor)
        self.required_hazard.grid(row=row, column=0, padx=(self.padl, 0), pady=(20, 5), sticky=W)
        # # hazard label
        self.label_hazard = tk.Label(
            self.root, text='Hazard', font='Helvetica 10 bold', background=self.backgroundColor, fg=self.fontColor)
        self.label_hazard.grid(
            row=row, column=1, padx=0, pady=(20, 5), sticky=W)
        row += 1
        # # hazard dropdown
        self.dropdown_hazard = ttk.Combobox(
            self.root, textvar=self.value_hazard, values=self.options_hazard, width=40, style='H.TCombobox')
        self.dropdown_hazard.grid(row=row, column=1,
                            padx=(0, 0), pady=(0, 0), sticky=W)
    
    def removeWidget_hazard(self):
            self.required_hazard.grid_forget()
            self.label_hazard.grid_forget()
            self.dropdown_hazard.grid_forget()
            self.dropdown_hazard.set('')

    def addWidget_scenario(self, row):
        # requred label
        self.required_scenario = tk.Label(
            self.root, text='*', font='Helvetica 14 bold', background=self.backgroundColor, fg=self.starColor)
        self.required_scenario.grid(row=row, column=0, padx=(
            self.padl, 0), pady=(20, 5), sticky=W)
        # scenario label
        self.label_scenario = tk.Label(
            self.root, text='Scenario', font='Helvetica 10 bold', background=self.backgroundColor, fg=self.fontColor)
        self.label_scenario.grid(
            row=row, column=1, padx=0, pady=(20, 5), sticky=W)
        row += 1
        # scenario dropdown
        self.dropdown_scenario = ttk.Combobox(
            self.root, textvar=self.value_scenario, values=self.options_scenario, width=40, style='H.TCombobox')
        self.dropdown_scenario.grid(row=row, column=1,
                            padx=(0, 0), pady=(0, 0), sticky=W)

    def removeWidget_scenario(self):
        self.required_scenario.grid_forget()
        self.label_scenario.grid_forget()
        self.dropdown_scenario.grid_forget()
        self.dropdown_scenario.set('')
    
    def addWidget_returnPeriod(self, row):
        # required label
        self.required_returnPeriod = tk.Label(
            self.root, text='*', font='Helvetica 14 bold', background=self.backgroundColor, fg=self.starColor)
        self.required_returnPeriod.grid(row=row, column=0, padx=(
            self.padl, 0), pady=(20, 5), sticky=W)
        # return period label
        self.label_returnPeriod = tk.Label(
            self.root, text='Return Period', font='Helvetica 10 bold', background=self.backgroundColor, fg=self.fontColor)
        self.label_returnPeriod.grid(
            row=row, column=1, padx=0, pady=(20, 5), sticky=W)
        row += 1
        # return period dropdown
        self.dropdown_returnPeriod = ttk.Combobox(
            self.root, textvar=self.value_returnPeriod, values=self.options_returnPeriod, width=40, style='H.TCombobox')
        self.dropdown_returnPeriod.grid(row=row, column=1,
                            padx=(0, 0), pady=(0, 0), sticky=W)

    def removeWidget_returnPeriod(self):
        self.required_returnPeriod.grid_forget()
        self.label_returnPeriod.grid_forget()
        self.dropdown_returnPeriod.grid_forget()
        self.dropdown_returnPeriod.set('')

    def addWidget_progress(self):
        row = self.row_progress

        self.bar_progress = Progressbar(mode='indeterminate')
        self.bar_progress.grid(row=row, column=1, pady=(0, 10), padx=50, sticky='nsew')
        self.root.update_idletasks()
        row += 1
        self.label_progress = tk.Label(
            self.root, text='Initializing', font='Helvetica 8', background=self.backgroundColor, fg=self.foregroundColor)
        self.label_progress.grid(
            row=row, pady=(0, 10), column=1, sticky='nsew')
        row += 1
        self.label_progress.config(
            text='Initializing')
        self.bar_progress['value'] = 0
        self.root.update_idletasks()
        self.root.update()

    def removeWidget_progress(self):
        self.bar_progress.grid_forget()
        self.label_progress.grid_forget()

    def handle_studyRegion(self, name, index, operation):
        try:
            value = self.value_studyRegion.get()
            if value != '':
                self.studyRegion = StudyRegion(str(value))
                print('Study Region set as ' + str(value))
                self.options_hazard = self.studyRegion.getHazardsAnalyzed()
                self.options_scenario = self.studyRegion.getScenarios()
                self.options_returnPeriod = self.studyRegion.getReturnPeriods()
                try:
                    self.removeWidget_hazard()
                except:
                    pass
                try:
                    self.removeWidget_scenario()
                except:
                    pass
                try:
                    self.removeWidget_returnPeriod()
                except:
                    pass
                if len(self.options_hazard) > 1:
                    self.addWidget_hazard(self.row_hazard)
                if len(self.options_scenario) > 1:
                    self.addWidget_scenario(self.row_scenario)
                if len(self.options_returnPeriod) > 1:
                    self.addWidget_returnPeriod(self.row_returnPeriod)

                # update the output directory
                if len(self.text_outputDirectory.get("1.0", 'end-1c')) > 0:
                    self.text_outputDirectory.delete("1.0", 'end-1c')
                    self.text_outputDirectory.insert(
                        "1.0", self.outputDirectory + '/' + self.studyRegion.name)
        except:
            ctypes.windll.user32.MessageBoxW(
                None, u"Unable to initialize the Study Region. Please select another Study Region to continue. Error: " + str(sys.exc_info()[0]), u'HazPy - Message', 0)

    def handle_hazard(self, name, index, operation):
        value = self.value_hazard.get()
        if value != '':
            self.studyRegion.setHazard(value)
            print('Hazard set as ' + str(value))
            self.options_scenario = self.studyRegion.getScenarios()
            try:
                self.removeWidget_scenario()
            except:
                pass
            if len(self.options_scenario) > 1:
                self.addWidget_scenario()
    
    def handle_scenario(self, name, index, operation):
        value = self.value_scenario.get()
        if value != '':
            self.studyRegion.setScenario(value)
            print('Scenario set as ' + str(value))
            self.options_returnPeriod = self.studyRegion.getReturnPeriods()
            try:
                self.removeWidget_returnPeriod()
            except:
                pass
            if len(self.options_returnPeriod) > 1:
                self.addWidget_returnPeriod()

    def handle_returnPeriod(self, name, index, operation):
        value = self.value_returnPeriod.get()
        if value != '':
            self.studyRegion.setReturnPeriod(value)
            print('Return Period set as ' + str(value))
        

    def build_gui(self):
        try:
            # initialize dropdown options
            options_studyRegion = getStudyRegions()
            self.value_studyRegion = StringVar(name='studyRegion')
            self.value_studyRegion.trace('w', self.handle_studyRegion)

            self.options_hazard = []
            self.value_hazard = StringVar(name='hazard')
            self.value_hazard.trace('w', self.handle_hazard)

            self.options_scenario = ['a', 'b', 'c']
            self.value_scenario = StringVar(name='scenario')
            self.value_scenario.trace(W, self.handle_scenario)

            self.options_returnPeriod = ['a', 'b', 'c']
            self.value_returnPeriod = StringVar(name='returnPeriod')
            self.value_returnPeriod.trace(W, self.handle_returnPeriod)

            # requred label
            self.required_studyRegion = tk.Label(
                self.root, text='*', font='Helvetica 14 bold', background=self.backgroundColor, fg=self.starColor)
            self.required_studyRegion.grid(row=self.row, column=0, padx=(
                self.padl, 0), pady=(20, 5), sticky=W)
            # Study Region label
            self.label_studyRegion = tk.Label(
                self.root, text='Study Region', font='Helvetica 10 bold', background=self.backgroundColor, fg=self.fontColor)
            self.label_studyRegion.grid(
                row=self.row, column=1, padx=0, pady=(20, 5), sticky=W)
            self.row += 1
            # Study Region dropdown
            self.dropdown_studyRegion = ttk.Combobox(
                self.root, textvar=self.value_studyRegion, values=options_studyRegion, width=40, style='H.TCombobox')
            self.dropdown_studyRegion.grid(row=self.row, column=1,
                                padx=(0, 0), pady=(0, 0), sticky=W)
            # Study Region icon
            self.img_scenarioName = tk.Label(
                self.root, image=self.img_data, background=self.backgroundColor)
            self.img_scenarioName.grid(
                row=self.row, column=2, padx=(0, self.padl), pady=(0, 0), sticky=W)
            self.row += 1

            # requred label
            self.required_export = tk.Label(
                self.root, text='*', font='Helvetica 14 bold', background=self.backgroundColor, fg=self.starColor)
            self.required_export.grid(row=self.row, column=0, padx=(
                self.padl, 0), pady=(20, 5), sticky=W)
            # export label
            self.label_export = tk.Label(
                self.root, text='Export', font='Helvetica 10 bold', background=self.backgroundColor, fg=self.fontColor)
            self.label_export.grid(
                row=self.row, column=1, padx=0, pady=(20, 5), sticky=W)
            self.row += 1

            # export options
            xpadl = 200
            # CSV
            self.opt_csv = tk.IntVar(value=1)
            ttk.Checkbutton(self.root, text="CSV", variable=self.opt_csv, style='BW.TCheckbutton').grid(
                row=self.row, column=1, padx=(xpadl, 0), pady=0, sticky=W)
            self.row += 1
            # shapefile
            self.opt_shp = tk.IntVar(value=1)
            ttk.Checkbutton(self.root, text="Shapefile", variable=self.opt_shp, style='BW.TCheckbutton').grid(
                row=self.row, column=1, padx=(xpadl, 0), pady=0, sticky=W)
            self.row += 1
            # geojson
            self.opt_geojson = tk.IntVar(value=1)
            ttk.Checkbutton(self.root, text="GeoJSON", variable=self.opt_geojson, style='BW.TCheckbutton').grid(
                row=self.row, column=1, padx=(xpadl, 0), pady=0, sticky=W)
            self.row += 1
            # report
            self.opt_report = tk.IntVar(value=1)
            ttk.Checkbutton(self.root, text="Report", variable=self.opt_report, style='BW.TCheckbutton', command=self.handle_reportCheckbox).grid(
                row=self.row, column=1, padx=(xpadl, 0), pady=0, sticky=W)
            self.row += 1

            # hazard
            self.row_hazard = self.row
            self.row += 2
            
            # scenario
            self.row_scenario = self.row
            self.row += 2

            # return period
            self.row_returnPeriod = self.row
            self.row += 2

            # report title
            self.row_report = self.row
            if self.opt_report.get() == 1:
                self.addWidget_report(self.row_report)
            self.row += 4

            # requred label
            self.label_required1 = tk.Label(
                self.root, text='*', font='Helvetica 14 bold', background=self.backgroundColor, fg=self.starColor)
            self.label_required1.grid(row=self.row, column=0, padx=(
                self.padl, 0), pady=(20, 5), sticky=W)
            # output directory label
            self.label_outputDirectory = tk.Label(self.root, text='Output Directory',
                                            font='Helvetica 10 bold', background=self.backgroundColor, fg=self.fontColor)
            self.label_outputDirectory.grid(
                row=self.row, column=1, padx=0, pady=(10, 0), sticky=W)
            self.row += 1
            # output directory form
            self.text_outputDirectory = tk.Text(self.root, height=1, width=37, font='Helvetica 10', background=self.textEntryColor,
                                        relief='flat', highlightbackground=self.textBorderColor, highlightthickness=1, highlightcolor=self.textHighlightColor)
            self.text_outputDirectory.grid(
                row=self.row, column=1, padx=(0, 0), pady=(0, 0), sticky=W)
            # output directory icon
            self.button_outputDirectory = tk.Button(self.root, text="", image=self.img_folder, command=self.browsefunc,
                                            relief='flat', background=self.backgroundColor, fg='#dfe8e8', cursor="hand2", font='Helvetica 8 bold')
            self.button_outputDirectory.grid(
                row=self.row, column=2, padx=(0, self.padl), pady=(0, 0), sticky=W)
            self.row += 1

            # run button
            self.button_run = tk.Button(self.root, text='Export', width=5, command=self.run,
                                        background='#0078a9', fg='#fff', cursor="hand2", font='Helvetica 8 bold', relief='flat')
            self.button_run.grid(row=self.row, column=1, columnspan=1,
                                sticky='nsew', padx=50, pady=(30, 20))
            self.row += 2

            # progress bar
            self.row_progress = self.row
            self.row += 1

        except:
            messageBox = ctypes.windll.user32.MessageBoxW
            messageBox(0, "Unable to build the app: " + str(sys.exc_info()[0]) + " | If this problem persists, contact hazus-support@riskmapcds.com.", "HazPy", 0x1000)


    # Run app
    def start(self):
        self.build_gui()
        self.root.mainloop()


# Start the app
app = App()
app.start()
