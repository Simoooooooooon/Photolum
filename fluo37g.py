import sys
from PyQt5 import QtCore, QtWidgets, uic  #, QtGui
import glob
from matplotlib.backends.backend_qt5agg import (NavigationToolbar2QT as NavigationToolbar)
import numpy as np
from scipy.stats import linregress
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QButtonGroup
from datetime import datetime
import matplotlib.pyplot as plt
import csv
import pandas as pd
from scipy import interpolate
from scipy.interpolate import UnivariateSpline
from scipy.integrate import simps
from numpy import trapz
import os


qtCreatorFile = "ui37.ui"
Ui_MainWindow, QtBaseClass = uic.loadUiType(qtCreatorFile)


class MyWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        #Actions menus
        self.actionOpen.triggered.connect(self.open_files)
        self.actionQuit.triggered.connect(self.quit)
        self.actionSave_dat.triggered.connect(self.save) 
        self.actionOpen_Data_Measure.triggered.connect(self.open_mesure)
        self.actionOpen_Calibration.triggered.connect(self.calibrationSonde)
        self.actionSave_Calibration.triggered.connect(self.sauver_calibration)
        self.actionSelect_Calibration_File.triggered.connect(self.select_calibration)
        self.actionCalibration_Preview.triggered.connect(self.calibration_preview)
        self.actionAbout.triggered.connect(self.about)
        
        

        #Push Buttons
        self.pushButton_quit.clicked.connect(self.quit)
        self.pushButton.clicked.connect(self.verifflag)
        #Radio Buttons
        self.radioButton_Full_Plot.toggled.connect(self.multi_plot)
        self.radioButton_Simple_Plot.toggled.connect(self.wave)
        self.radioButton_Ratios.toggled.connect(self.multi_wave)
        self.radioButton_Maximas.toggled.connect(self.multi_wave)
        self.radioButton_ratio_surf.toggled.connect(self.multi_wave)
        self.radioButton_maximasDeriv_nulle.toggled.connect(self.multi_wave)
        self.radioButton_methodeRatio.toggled.connect(self.mesure)
        self.radioButton_MethodeMax.toggled.connect(self.mesure)
        self.radioButton_MethodeDeriv.toggled.connect(self.mesure)
        self.radioButton_MethodeAire.toggled.connect(self.mesure)       
        self.radioButton_plot_mesure.toggled.connect(self.mesure)   
        self.radioButton_plot_mes.toggled.connect(self.plot_mesure)      
        self.radioButton_calib_mode.clicked.connect(self.gestion_modes)#.clicked au lieu de toggle pour agir seulemnt si coché
        self.radioButton_mes_mode.clicked.connect(self.gestion_modes)
        
        #Groupes de boutons
        self.group_mode = QButtonGroup()
        self.group_mode.addButton(self.radioButton_calib_mode)
        self.group_mode.addButton(self.radioButton_mes_mode)
        
        self.group_methode = QButtonGroup()
        self.group_methode.addButton(self.radioButton_methodeRatio)
        self.group_methode.addButton(self.radioButton_MethodeMax)
        self.group_methode.addButton(self.radioButton_MethodeDeriv)
        self.group_methode.addButton(self.radioButton_MethodeAire)
             
        #TO DO : CREER UN AUTRE GROUPE AVEC LES AUTRES BOUTONS
       
        #commencer en mpde calibration
        self.radioButton_calib_mode.setChecked(True) 
        self.gestion_modes()

        #Spin Box
        self.doubleSpinBox_Lamba1.valueChanged.connect(self.wave)
        self.doubleSpinBox_Lamba2.valueChanged.connect(self.wave)      
        self.spinBox_numero.valueChanged.connect(self.wave)
        #Toolbar batplotlib
        self.addToolBar(NavigationToolbar(self.MplWidget.canvas, self))
        #Appels fonction initialisation
        self.cacher_label_simple_plot()
        #definition de variables
        self.Tempe_interpol_calib = []
        self.flag_Neoptix = 0 #pour ne pas appliquer plusieur fois la correction de decalage de temps lors des plots de neoptix
        self.flag_mesure = 0
        
        self.wave1 = 600 #A MODIFIER IL FAUT LES CALCULER AU TRAITEMENT DES FICHIERS
        self.wave2 = 650
        
    def verifflag(self):
        print('tps min',min(self.Horodat))
        print('flag neo',self.flag_Neoptix)
        print('flag mesure',self.flag_mesure)
    def open_files(self):
          """si on a deja ouvert un dossier, on rouvre le même, convertir et ploter"""
          if 'self.dossier' in globals():
              self.fileNames = QFileDialog.getOpenFileNames(self,"Open Spectra", self.dossier,"Text File (*.txt)")            
          else:           
              self.fileNames = QFileDialog.getOpenFileNames(self,"Open Spectra", "","Text File (*.txt)")
              self.dossier = os.path.dirname(self.fileNames[0][0])
               
          self.conversion_fichier()
          self.multi_plot()
          self.radioButton_Full_Plot.setChecked(True)  

          
    def conversion_fichier(self):
        self.nbre_fichiers = len(self.fileNames[0])
        self.spinBox_numero.setMaximum(self.nbre_fichiers)
        self.label_Scans.setText(str(self.nbre_fichiers))     
        self.manip = [[],[]]
        self.deriv = [[],[],[],[]]
        
        self.Horodat = []
        for fichier in self.fileNames[0]:
            f=open(fichier,"r")
            lines=f.readlines()
            X = []
            Y = []
            #rechercher la fin de l'en tête (ou le debut des donnees)
            for k in range(0,20):
                if lines[k] == '>>>>>Begin Spectral Data<<<<<\n':
                    fin_en_tete = k+1                       
            #chercher date et heure dans l'en tête et les convertir en secondes
            # self.Horodat est une liste contenant l'heure de debut de scan de chaque fichier
            for m in range(0,fin_en_tete):
                if lines[m][0:5] == 'Date:':                
                    heures = lines[m].split(':')[1][-2:]
                    minutes = lines[m].split(':')[2][0:2]
                    secondes = lines[m].split(':')[3][0:2]
                    self.horodat = 3600*float(heures) + 60*float(minutes) + float(secondes)
                    self.Horodat.append(self.horodat)     
                    
            
                          
            #recuperer les donnees et les mettre dans des listes (lambda dans liste X et Intens dans liste Y)
            for l in range(fin_en_tete,len(lines)):      
                lines[l] = lines[l].replace(',', '.')            
                x = float((lines[l].split('\t')[0]))
                y = float((lines[l].split('\n')[0]).split(('\t'))[1])                
                X.append(x)
                Y.append(y)             
            #manip est un liste contenant une liste de lambda et une liste d'intensités
            self.manip[0].append(X)
            self.manip[1].append(Y)

            f.close()  
        # conversion de la liste en tableau    
        self.tableau_manip = np.array(self.manip)
        self.temps_corr = []
        #convertir le tableau self.Horodat en temps initialisé à zéro
        for i in range (0,len(self.Horodat)):
            self.temps_corr.append(self.Horodat[i]-min(self.Horodat)) 
            
            
    def calibrationSonde(self):
        
        
        self.radioButton_plot_calib.setChecked(True)
        self.MplWidget.canvas.ax1.clear()
        self.MplWidget.canvas.ax2.clear() #ax2 est l'axe secondaire utilisé pour tracer la dérivée
        self.plot_neoptix()
        
        ###############################  
        # if self.flag_Neoptix == 0:#il ne faut appliquer le recalage de temps que la premiere fois que le fichier est ouvert
        # for i in range (0,len(self.Horodat)):
        #     self.Horodat[i] = self.Horodat[i] - self.t0Neo #pour 'syncroniser les scans et la neoptics, le temps initial est fixé comme etant celui de la neoptix
       ################################
       
        
        
        
        for t in range (0,len(self.temps_corr)): 
            
            
            #  temperature interpolée de la mesure neoptix, on lit dans le fichier mesure le temps et on vient le reporter sur fichier neoptix pour extrapoler temperature
            
            # temperature_interpol_calib = np.interp(self.Horodat[t],self.tableau_calib[0][0],self.tableau_calib[1][0])
            temperature_interpol_calib = np.interp(self.temps_corr[t],self.tableau_calib[0][0],self.tableau_calib[1][0])
            self.Tempe_interpol_calib.append(temperature_interpol_calib)
         
        
        # self.plot_interpolation(self.Horodat,self.Tempe_interpol_calib) 
        self.plot_interpolation(self.temps_corr,self.Tempe_interpol_calib) 
        self.MplWidget.canvas.ax1.set_facecolor("lightyellow")
        self.MplWidget.canvas.figure.set_facecolor("lightyellow")
        self.MplWidget.canvas.ax1.set_title('Interpolation of the time of each calibration scan file to convert them into temperature with the Neoptix curve')
        self.MplWidget.canvas.draw()
        # self.radioButton_ratio_surf.setChecked(True) 
        
        
    def plot_interpolation(self,abscice,ordonnee):
        """Plot des interpolations avec lignes verticales et horizontales"""
        # self.MplWidget.canvas.ax1.vlines(x,0,y, color="grey",linestyle='dashed')  
        # self.MplWidget.canvas.ax1.hlines(y,0,x,color="grey",linestyle='dashed')
        
        

        # self.MplWidget.canvas.ax1.axhline(y = temperature_interpol_calib,color="grey",linestyle='--') 
        for i in range (0,len(abscice)):
            self.MplWidget.canvas.ax1.axvline(x = abscice[i], color="grey",linestyle='--')  
            self.MplWidget.canvas.ax1.axhline(y = ordonnee[i] , color="grey",linestyle='--') 
        self.MplWidget.canvas.ax1.plot(abscice,ordonnee, 'o', color='orange')
        
        # self.MplWidget.canvas.ax1.spines["left"].set_position(("data", 0))
        # self.MplWidget.canvas.ax1.spines["bottom"].set_position(("data", 0))
        
    def simple_plot(self):
        """Plotter le scan correspondant au numero choisi avec la spinbox"""
        #cocher le bouton Silmple Plot (si la spinbox lambda1 ou 2 est changée qd on est sur l'affichage d'une autre courbe)    
        if self.spinBox_numero.value() < self.nbre_fichiers:
            self.numero = self.spinBox_numero.value()
        else:
            print('messagebox') #A ENLEVER???
            
        self.spinBox_numero.setVisible(True) 
        self.label_3.setVisible(True)        
        self.MplWidget.canvas.ax1.clear()  
        self.MplWidget.canvas.ax2.clear() #ax2 est l'axe secondaire utilisé pour tracer la dérivée
        #plot scan          
        self.MplWidget.canvas.ax1.plot(self.tableau_manip[0][self.numero],self.tableau_manip[1][self.numero],label="Scan #"+str(self.numero))

        #Colorer l'aire sous pic
        self.MplWidget.canvas.ax1.fill_between(self.tableau_manip[0][self.numero],self.tableau_manip[1][self.numero],where = (self.tableau_manip[0][self.numero]<=self.wave2), color='yellow')
        self.MplWidget.canvas.ax1.fill_between(self.tableau_manip[0][self.numero],self.tableau_manip[1][self.numero],where = (self.tableau_manip[0][self.numero]>self.wave2), color='pink')
        
        self.MplWidget.canvas.ax1.set_xlabel('Wavelength (nm)')
        self.MplWidget.canvas.ax1.set_ylabel('Intensity (u.a.)')
        self.MplWidget.canvas.ax1.legend()
        self.MplWidget.canvas.draw()
               
        
    def multi_plot(self):  
        """Plotter tous les scans du dossier"""
        self.MplWidget.canvas.ax1.clear() 
        self.MplWidget.canvas.ax2.clear() #ax2 est l'axe secondaire utilisé pour tracer la dérivée
        #cacher valeurs pic individuel
        self.cacher_label_simple_plot()
        for i in range (0,self.nbre_fichiers):
            self.MplWidget.canvas.ax1.plot(self.tableau_manip[0][i],self.tableau_manip[1][i],label="Curve #"+str(i))
            self.MplWidget.canvas.ax1.legend()
            self.MplWidget.canvas.ax1.set_xlabel('Wavelength (nm)')
            self.MplWidget.canvas.ax1.set_ylabel('Intensity (u.a.)')       
        
        if self.radioButton_calib_mode.isChecked():
            self.MplWidget.canvas.ax1.set_facecolor("lightyellow")
            self.MplWidget.canvas.figure.set_facecolor("lightyellow")
        else:
            self.MplWidget.canvas.ax1.set_facecolor("white")
            self.MplWidget.canvas.figure.set_facecolor("White")
        self.MplWidget.canvas.draw()
         
    def read_wave(self): 
         """recuperer les valeurs des spinbox pour lambda 1 et lambda2"""      
         self.wave1 = self.doubleSpinBox_Lamba1.value()
         self.wave2 = self.doubleSpinBox_Lamba2.value() 
 
    def wave(self):
        """affiche les scan choisi et les points correspondant à lambda1 , lambda2 et maxi"""
        if self.radioButton_Simple_Plot.isChecked():      
                self.wave1 = self.doubleSpinBox_Lamba1.setDisabled(False)
                self.wave2 = self.doubleSpinBox_Lamba2.setDisabled(False)
                self.read_wave()    
                self.MplWidget.canvas.ax1.clear() 
                self.MplWidget.canvas.ax2.clear() #ax2 est l'axe secondaire utilisé pour tracer la dérivée
                self.simple_plot()   
                #les lignes horizontales et verticales des points correspondant à lambda 1 et lambda 2
                self.MplWidget.canvas.ax1.axvline(x=self.wave1,color="grey",linestyle='--')
                self.MplWidget.canvas.ax1.axvline(x=self.wave2 ,color="grey",linestyle='--')  
                
                # Retrouver les intensités intens 1 et 2 correspondant à lambda 1 et lambda 2
                self.intens1 = np.interp(self.wave1, self.tableau_manip[0][self.numero],self.tableau_manip[1][self.numero])  
                self.intens2 = np.interp(self.wave2, self.tableau_manip[0][self.numero],self.tableau_manip[1][self.numero])
               
                #definir le maxi
                self.Ipic = max(self.tableau_manip[1][self.numero])                     #trouver le point maxi des intensités du scan
                index_pic = np.where(self.tableau_manip[1][self.numero]== self.Ipic)    #trouver l'index dans le tableau numpy du maxi
                self.wave_pic = self.tableau_manip[0][self.numero][index_pic][0]        #trouver la longueur d'onde correspondant
                #arrondir les valeurs avant de les mettre dans les labels            
                text_Ipic = self.arrondi(str(self.Ipic),1)
                text_wave_pic = self.arrondi(str(self.wave_pic),1)
                text_intens1 = self.arrondi(str(self.intens1),1)
                text_intens2 = self.arrondi(str(self.intens2),1)  
                #ecrire les valeurs des differentes coordonnes dans les labels
                self.label__Ipic.setText(str(text_Ipic))
                self.label_Lamba_pic.setText(str(text_wave_pic))       
                self.label_I1.setText(str(text_intens1))
                self.label_I2.setText(str(text_intens2))      
                #mettre des markers aux points correspondants à lamda lambda 2 et maxi
                self.MplWidget.canvas.ax1.plot(self.wave1,self.intens1,'ro',markersize=4)
                self.MplWidget.canvas.ax1.plot(self.wave2 ,self.intens2,'ro',markersize=4)
                self.MplWidget.canvas.ax1.plot(self.wave_pic ,self.Ipic,'darkred',marker = '+',markersize=16)  
                #Retrouver les intensités intens 1 et 2 correspondant à lambda 1 et lambda 2
                self.intens1 = np.interp(self.wave1, self.tableau_manip[0][self.numero],self.tableau_manip[1][self.numero])  #LIGNES EN DOUBLON???
                self.intens2 = np.interp(self.wave2 , self.tableau_manip[0][self.numero],self.tableau_manip[1][self.numero])    #LIGNES EN DOUBLON???
                self.MplWidget.canvas.ax1.axhline(y = self.intens1,color="grey",linestyle='--')
                self.MplWidget.canvas.ax1.axhline(y = self.intens2,color="grey",linestyle='--')
                self.MplWidget.canvas.draw()
                
                #ligne verticale au maxi (methode max liste)
                self.MplWidget.canvas.ax1.axvline(x=self.wave_pic,color="green",label='pic max liste',linestyle='--')
                
                #definir le pic avec methode derivee 
                self.deriv = [[],[],[],[]]
                #plot de la dérivée  
                self.derivee(self.manip[0][self.numero],self.manip[1][self.numero])
                self.deriv[0].append(self.XderivGamme12)
                self.deriv[1].append(self.YderivGamme12)
                self.deriv[2].append(self.XderivGamme12_triee)
                self.deriv[3].append(self.YderivGamme12_triee)
                self.tableau_deriv = np.array(self.deriv)
                # self.MplWidget.canvas.ax1.plot(self.deriv[0][0],self.deriv[1][0],label="Derivee #"+str(self.numero))
                # self.MplWidget.canvas.ax2.clear() #ax2 est l'axe secondaire utilisé pour tracer la dérivée
                self.MplWidget.canvas.ax2.plot(self.deriv[0][0],self.deriv[1][0],label="Derivee #"+str(self.numero)) 
                self.MplWidget.canvas.ax2.axhline(y=0.0,color="orange",linestyle='--')
       
                self.pic_methode_deriv = np.interp(0.0,self.deriv[3][0],self.deriv[2][0]) 
                
                self.MplWidget.canvas.ax1.axvline(x=self.pic_methode_deriv,color="orange",label='pic max liste derivee',linestyle='--')

        else:
            
                self.doubleSpinBox_Lamba1.setDisabled(True)
                self.doubleSpinBox_Lamba2.setDisabled(True)
                self.doubleSpinBox_Lamba1.setValue(600)
                self.doubleSpinBox_Lamba2.setValue(650)
        self.MplWidget.canvas.draw()             
    def multi_wave(self):
        """sur tous les scans , determiner les points correspondant à lambda1 , lambda2 et maxi. Calculer les ratios et plotter soit les ratios
        soit les maxi en fonction du numero de scan"""  
        self.read_wave()        #recuperer les valeur de lambda 1 et lambda2      
        Ratio = []
        # self.Scan = []
        self.Points = []
        self.WavePic = []
        self.WavePicD2 = []
        self.WavePicDnul = []
        self.Ratio_surface = []
        self.deriv = [[],[],[],[]]
        for scan in range (0,self.nbre_fichiers):                   
            # Retrouver les intensités intens 1 et 2 correspondant à lambda 1 et lambda 2
            self.intens1 = np.interp(self.wave1, self.tableau_manip[0][scan],self.tableau_manip[1][scan])  
            self.intens2 = np.interp(self.wave2, self.tableau_manip[0][scan],self.tableau_manip[1][scan])
            # recuprer valeurs de ratio et ajouter à la liste
            self.calcul_ratio()
            Ratio.append(self.ratio) 
            #trouver la valeur max d'intensité
            self.Ipic = max(self.tableau_manip[1][scan])
            index_pic = np.where(self.tableau_manip[1][scan]== self.Ipic)    #trouver l'index dans le tableau numpy du maxi
            self.wave_pic = self.tableau_manip[0][scan][index_pic][0]        #trouver la longueur d'onde correspondant
            self.WavePic.append(self.wave_pic)
        
            #definir le pic avec methode derivee 

            self.derivee(self.manip[0][scan],self.manip[1][scan])# EN TEST
            self.deriv[0].append(self.XderivGamme12)
            self.deriv[1].append(self.YderivGamme12)
            self.deriv[2].append(self.XderivGamme12_triee)
            self.deriv[3].append(self.YderivGamme12_triee)
   

            self.pic_methode_deriv = np.interp(0.0,self.deriv[3][scan],self.deriv[2][scan])
   
            self.WavePicDnul.append(self.pic_methode_deriv)
                  
            Index_sup_wave2 = []

            Yavant_wave2 = []
            Yapres_wave2 = []
            for i in range (0,len(self.manip[0][scan])):
                if self.manip[0][scan][i]>self.wave2:
                    Index_sup_wave2.append(i)
            index_coupe = min(Index_sup_wave2)
            Yavant_wave2 = self.tableau_manip[1][scan][:index_coupe]
            Yapres_wave2 = self.tableau_manip[1][scan][index_coupe:]
            Yavant_wave2_tab = np.array(Yavant_wave2)
            Yapres_wave2_tab = np.array(Yapres_wave2)
            surface1 = simps(Yavant_wave2_tab, dx = 1)
            surface2 = simps(Yapres_wave2_tab , dx = 1)
            ratio_surface = surface1/surface2
            self.Ratio_surface.append(ratio_surface)

        self.Points.append(self.Tempe_interpol_calib)
        self.Points.append(Ratio)
        self.Points.append(self.WavePic) 
        self.Points.append(self.WavePicDnul)
        self.Points.append(self.Ratio_surface)
        self.MplWidget.canvas.ax1.clear()
        self.MplWidget.canvas.ax2.clear() #ax2 est l'axe secondaire utilisé pour tracer la dérivée

        if self.radioButton_Ratios.isChecked():
            #cacher valeurs pic individuel
            self.cacher_label_simple_plot()  
            #plotter les ratios en fonction du numero de scan
            self.MplWidget.canvas.ax1.plot(self.Points[0],self.Points[1],'r-s')
            self.MplWidget.canvas.ax1.set_xlabel('Temperature (°C)')
            self.MplWidget.canvas.ax1.set_ylabel( 'I1/I2 Ratio')
            self.MplWidget.canvas.ax1.set_title('Interpolation of the ratio of each calibration scan file to convert them into temperature')
        
        if self.radioButton_Maximas.isChecked():
            #cacher valeurs pic individuel
            self.cacher_label_simple_plot()
            #plotter les longueur d'onde des maxis en fonction du numero de scan
            self.MplWidget.canvas.ax1.plot(self.Points[0],self.Points[2],'g-o')  
            self.MplWidget.canvas.ax1.set_xlabel('Temperature (°C)')
            self.MplWidget.canvas.ax1.set_ylabel( 'Maxi Wavelength (nm)') 
            self.MplWidget.canvas.ax1.set_title('Interpolation of the wavelength of peak of each calibration scan file to convert them into temperature')
        
        if self.radioButton_ratio_surf.isChecked():
            #cacher valeurs pic individuel
            self.cacher_label_simple_plot()
            self.MplWidget.canvas.ax1.plot(self.Points[0],self.Points[4],'m-+') 
            self.MplWidget.canvas.ax1.set_xlabel('Temperature (°C)')
            self.MplWidget.canvas.ax1.set_ylabel( 'Area Ratio') 
            self.MplWidget.canvas.ax1.set_title('Interpolation of area ratios of each calibration scan file to convert them into temperature')
          
        
        if self.radioButton_maximasDeriv_nulle.isChecked():
            #cacher valeurs pic individuel
            self.cacher_label_simple_plot()
            self.MplWidget.canvas.ax1.plot(self.Points[0],self.Points[3],'k-x') 
            self.MplWidget.canvas.ax1.set_xlabel('Temperature (°C)')
            self.MplWidget.canvas.ax1.set_ylabel( 'Maxi Wavelength (nm)-From deriv null.') 
            self.MplWidget.canvas.ax1.set_title('Interpolation of the wavelength of peak (deriv null) of each calibration scan file to convert them into temperature')
     
            
        self.MplWidget.canvas.draw()

    def sauver_calibration(self):
              
        sauvegarde_calib, _ = QFileDialog.getSaveFileName(self,"QFileDialog.getSaveFileName()","","Pickle (*.pkl)")
       
        if sauvegarde_calib:
        
            calibration = list(zip(self.Points[0],self.Points[1],self.Points[2],self.Points[3],self.Points[4]))
            df_calibration = pd.DataFrame(calibration,columns = ['Temperature','Ratio','Wavelength Peak','wavelength Peak Deriv','Area Ratio'])
            
            df_calibration.to_pickle(sauvegarde_calib)
   
    def open_mesure(self):
        self.flag_Neoptix = 0
        self.open_files()
        self.conversion_fichier()
        self.radioButton_Ratios.setChecked(False)
        self.radioButton_Maximas.setChecked(False)      
        self.multi_wave()
        self.radioButton_plot_mesure.setChecked(True)
        self.radioButton_methodeRatio.setChecked(True)
        # On obtient des listes self.Ratio et self.Wave_pic
    
    def select_calibration(self):
        
        self.fichier_calib = QFileDialog.getOpenFileNames(self,"Open Calibration", " ","Pickle (*.pkl)")
        nbre_fichiers = len(self.fichier_calib[0])
       
        #creer un dataframe vide avec noms de colonnes
      
        self.df_calibration_lue =  pd.read_pickle(self.fichier_calib[0][0])
   
        # liste_calib = []
        for i in range (1,nbre_fichiers):
           
            self.df_calibration_lue = self.df_calibration_lue + pd.read_pickle(self.fichier_calib[0][i])#lire le fichier de calibration pkl selectionné 
            
        
        
        self.df_calibration_lue = self.df_calibration_lue.div(nbre_fichiers)
    
        
        # sauvegarde_calib, _ = QFileDialog.getSaveFileName(self,"QFileDialog.getSaveFileName()","","Pickle (*.pkl)")
        self.df_calibration_lue.to_pickle('Calib_moyenne_temp.pkl')

        
        
        
        
    def calibration_preview(self):
        preview_calib = QFileDialog.getOpenFileNames(self,"Open Calibration", " ","Pickle (*.pkl)")
        self.MplWidget.canvas.ax1.clear()
        self.MplWidget.canvas.ax2.clear() #ax2 est l'axe secondaire utilisé pour tracer la dérivée
      
        fig, axes = plt.subplots(2,2,num="Calibration Files Preview")
        
      
        for i in range (0,len(preview_calib[0])):
            
            df_preview_calib = pd.read_pickle(preview_calib[0][i])

            label1 = preview_calib[0][i].split("/")[-1]
            
            df_preview_calib.plot(x='Temperature' , y='Ratio', ax = axes[0,0],label=label1,marker='.')
            axes[0,0].legend()          
            axes[0,0].set_title('Ratio')
            #ne pas afficher les legende des x des 2 courbes du haut pour eviter superposition
            x_axis = axes[0,0].axes.get_xaxis()
            x_axis.set_visible(False)
            
            df_preview_calib.plot(x='Temperature' , y='Wavelength Peak', ax = axes[0,1],label=label1,marker='.')
            axes[0,1].legend() 
            axes[0,1].set_title('Wavelength Peak')
            x_axis = axes[0,1].axes.get_xaxis()
            x_axis.set_visible(False)
            
            
            df_preview_calib.plot(x='Temperature' , y='wavelength Peak Deriv', ax = axes[1,0],label=label1,marker='.')
            axes[1,0].legend() 
            axes[1,0].set_title('Wavelength Peak Deriv')
            df_preview_calib.plot(x='Temperature' , y='Area Ratio', ax = axes[1,1],label=label1,marker='.')
            axes[1,1].legend() 
            axes[1,1].set_title('Area Ratio')
            
        
       
       
        
    
    def mesure(self):
        """Aller lire le fichier de calibration s'en servir pour convertir les ratios de chaque fichier en temperature"""
        
       
        self.Calib_lue = [[],[],[]]
        self.Tempe_interpol_mesure = []     
      
        
        # df_calibration_lue = pd.read_pickle(self.fichier_calib[0])#lire le fichier de calibration pkl selectionné                
        temperature_cal = self.df_calibration_lue['Temperature'].tolist()
        ratio_cal = self.df_calibration_lue['Ratio'].tolist()
        peak_cal = self.df_calibration_lue['Wavelength Peak'].tolist() # POUR LE MOMENT LA CALIBRATION N'EST POSSIBLE QUE SUR LES RATIOS
        peak_deriv_cal =  self.df_calibration_lue['wavelength Peak Deriv'].tolist()
        ratio_surf_cal = self.df_calibration_lue['Area Ratio'].tolist()
        
        self.MplWidget.canvas.ax1.clear()
        self.MplWidget.canvas.ax2.clear() #ax2 est l'axe secondaire utilisé pour tracer la dérivée
              
        if self.radioButton_methodeRatio.isChecked():

            self.MplWidget.canvas.ax1.plot(temperature_cal,ratio_cal,'r-s')
            self.MplWidget.canvas.ax1.set_xlabel('Temperature (°C)')
            self.MplWidget.canvas.ax1.set_ylabel( 'I1/I2 Ratio')
            self.MplWidget.canvas.ax1.set_title('Interpolation of the ratio of each measure scan file to convert them into temperature')
            ratio_cal, temperature_cal = zip(*sorted(zip(ratio_cal, temperature_cal)))
            
            for i in range(0,len(self.Points[1])):
                temperature_interpol_mesure = np.interp(self.Points[1][i],ratio_cal,temperature_cal)
                self.Tempe_interpol_mesure.append(temperature_interpol_mesure)
            self.plot_interpolation(self.Tempe_interpol_mesure,self.Points[1])
            
        if self.radioButton_MethodeMax.isChecked():
            self.MplWidget.canvas.ax1.plot(temperature_cal,peak_cal,'g-o')
            self.MplWidget.canvas.ax1.set_xlabel('Temperature (°C)')
            self.MplWidget.canvas.ax1.set_ylabel( 'Max')
            self.MplWidget.canvas.ax1.set_title('Interpolation of the max of each measure scan file to convert them into temperature')
            
            peak_cal, temperature_cal = zip(*sorted(zip(peak_cal, temperature_cal)))
            for i in range(0,len(self.Points[2])):
                temperature_interpol_mesure = np.interp(self.Points[2][i],peak_cal,temperature_cal)
                self.Tempe_interpol_mesure.append(temperature_interpol_mesure)
            self.plot_interpolation(self.Tempe_interpol_mesure,self.Points[2])
                  
            
        if self.radioButton_MethodeDeriv.isChecked():
            self.MplWidget.canvas.ax1.plot(temperature_cal,peak_deriv_cal,'k-x')
            self.MplWidget.canvas.ax1.set_xlabel('Temperature (°C)')
            self.MplWidget.canvas.ax1.set_ylabel( 'Wavelength of max (deriv method)')
            self.MplWidget.canvas.ax1.set_title('Interpolation of the wavelength of max (deriv method) of each measure scan file to convert them into temperature')
            peak_deriv_cal, temperature_cal = zip(*sorted(zip(peak_deriv_cal, temperature_cal)))
            
            for i in range(0,len(self.Points[3])):
                temperature_interpol_mesure = np.interp(self.Points[3][i],peak_deriv_cal,temperature_cal)
                self.Tempe_interpol_mesure.append(temperature_interpol_mesure)
            self.plot_interpolation(self.Tempe_interpol_mesure,self.Points[3])
            
        if self.radioButton_MethodeAire.isChecked():
            self.MplWidget.canvas.ax1.plot(temperature_cal,ratio_surf_cal,'m-+')
            self.MplWidget.canvas.ax1.set_xlabel('Temperature (°C)')
            self.MplWidget.canvas.ax1.set_ylabel( 'Area Ratio)')
            self.MplWidget.canvas.ax1.set_title('Interpolation of the area ratios of each measure scan file to convert them into temperature')
            ratio_surf_cal, temperature_cal = zip(*sorted(zip(ratio_surf_cal, temperature_cal)))
            
            for i in range(0,len(self.Points[4])):
                temperature_interpol_mesure = np.interp(self.Points[4][i],ratio_surf_cal,temperature_cal)
                self.Tempe_interpol_mesure.append(temperature_interpol_mesure)
            self.plot_interpolation(self.Tempe_interpol_mesure,self.Points[4])
            
   
        self.MplWidget.canvas.draw()
       

    def plot_mesure(self):      
        """" Afficher le graph  de la temperature en fonction du temps en se basant sur l'interpolation des ratios"""       
        self.MplWidget.canvas.ax1.clear()
        self.MplWidget.canvas.ax2.clear() #ax2 est l'axe secondaire utilisé pour tracer la dérivée
        
        if self.radioButton_check_neo.isChecked():   
            self.plot_neoptix()         
            self.MplWidget.canvas.ax1.plot(self.temps_corr,self.Tempe_interpol_mesure,'r-o') 
            
        else: 
            self.MplWidget.canvas.ax1.plot(self.temps_corr,self.Tempe_interpol_mesure,'r-o') 
            
        # else: 
                      
        #     mini_Horodat = min(self.Horodat)

        #     if self.flag_mesure == 0:
        #         self.Horodat_corr = []
        #         for i in range (0,len(self.Horodat)):
        #             horodat_corr = self.Horodat[i] - mini_Horodat
        #             self.Horodat_corr.append(horodat_corr)
        #     self.MplWidget.canvas.ax1.plot(self.Horodat_corr,self.Tempe_interpol_mesure,'r-o') 
        #     self.flag_mesure+=1
            
        self.MplWidget.canvas.ax1.set_title('Temperature calculated in function of measurment scan file')
        self.MplWidget.canvas.draw()

        
    def plot_neoptix(self):
        """Ploter les temperatures mesurees par Neoptix en fonction du temps"""
        if 'self.dossier' in globals():
            self.fileNameCalib = QFileDialog.getOpenFileName(self,"Open Calibration File", self.dossier,"Text File (*.txt)")            
        else:           
            self.fileNameCalib = QFileDialog.getOpenFileName(self,"Open Calibration File", "","Text File (*.txt)")
        
        
        
        # self.fileNameCalib = QFileDialog.getOpenFileName(self,"Open Calibration File", " ","Text File (*.txt)")
        fichierSonde = open(self.fileNameCalib[0],"r")
        lines=fichierSonde.readlines()
        TempsCalib = []
        TureCalib = []
        self.Calib = [[],[]]
        self.Tempe_interpol_calib = []
        # self.Delta_time = []
        for l in  range (1,len(lines)):
            #recuperer temps initial neoptix
            if  'Acq Start Time' in lines[l]:
                strt0 = lines[l].split('\t')[-1] #recuperer la chaine de caractere correspondant à l'heure
                t0Neo_sec = float((strt0.split(':'))[-1])
                t0Neo_min = float((strt0.split(':'))[1])
                t0Neo_heur = float((strt0.split(':'))[0])
                self.t0Neo = 3600*t0Neo_heur + 60*t0Neo_min + t0Neo_sec-min(self.Horodat)
                
                # if self.flag_Neoptix == 0:#il ne faut appliquer le recalage de temps que la premiere fois que le fichier est ouvert
                for i in range (0,len(self.temps_corr)):
                    self.temps_corr[i] = self.temps_corr[i] - self.t0Neo #pour 'syncroniser les scans et la neoptics, le temps initial est fixé comme etant celui de la neoptix
                
                    
                self.flag_Neoptix+=1
                # recuperer les colonnes temps et temperatures des fichiers neoptix
            tempsCalib = float((lines[l].split('\t')[0]))
            tureCalib = float((lines[l].split('\t')[1])) 
            TempsCalib.append(tempsCalib)
            TureCalib.append(tureCalib)
            
        #tableau calibration avec temps et temperature de Neoptix
        self.Calib[0].append(TempsCalib)
        self.Calib[1].append(TureCalib)
        self.tableau_calib = np.array(self.Calib) 
        #tracer profil en temperature Neoptix 
        self.MplWidget.canvas.ax1.plot(TempsCalib,TureCalib)
        self.MplWidget.canvas.ax1.set_xlabel('Time(s)')
        self.MplWidget.canvas.ax1.set_ylabel('Temperature(°C)')
        self.MplWidget.canvas.draw()
        

    def calcul_ratio(self):
        """calcul du ratio, en prenant en compte que le point 1 a pu passer à droite du point 2"""
        if self.wave1>self.wave2:
            self.ratio = self.intens2/self.intens1
        else:
            self.ratio = self.intens1/self.intens2        
                           
                    
    def derivee(self,X,Y): 
        self.Xderiv = []
        self.Yderiv = []
      
        self.Xderiv = []
        self.Yderiv = []
        #TO DO/ OPTIMISER LE PAS OU LE METTRE ACCESSIBLE A L UTILISATEUR
        pas_deriv = 5 #Le pas de la dérivee , plus la valeur est importante , plus c'st lissé
        ampli_deriv = 60 #pour ''zoomer sur la derivéé
        for i in range (0+pas_deriv,len(X)-pas_deriv):
            xderiv = X[i]
            yderiv = (Y[i+pas_deriv]-Y[i-pas_deriv])/((X[i+pas_deriv]-X[i-pas_deriv]))*ampli_deriv             
            self.Xderiv.append(xderiv)
            self.Yderiv.append(yderiv)

        
        self.XderivGamme12 = []
        self.YderivGamme12 = []
        self.XderivGamme12_triee = []
        self.YderivGamme12_triee = []
        
        
        for i in range (0,len(self.Xderiv)):
            if self.wave1<self.Xderiv[i]<self.wave2:
                self.XderivGamme12.append(self.Xderiv[i])
                self.YderivGamme12.append(self.Yderiv[i])
    
        # trier par ordre croissant de y derivee (les x suivent),c'est necessaire pour le np.inter pour trouver la derivee nulle
        self.YderivGamme12_triee,self.XderivGamme12_triee = zip(*sorted(zip(self.YderivGamme12, self.XderivGamme12)))
        
        return self.XderivGamme12,self.YderivGamme12,self.XderivGamme12_triee,self.YderivGamme12_triee
     
    
    def save(self):
        """Sauvegarder dans un fichier texte col0 = numero du scan col1 = rati col2 = lambda du maxi"""
        col0 = self.Horodat_corr
        col1 = self.Tempe_interpol_mesure
        data = np.column_stack([col0,col1])
        #TO DO CHANGER LE FORMAT DE LA BOITE DE DIALOGUE
        #configuration de la boite de dialogue sauvegarde
        # options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog
        sauvegarde, _ = QFileDialog.getSaveFileName(self,"QFileDialog.getSaveFileName()","","All Files (*);;Text Files (*.txt)")#, options=options)
        if sauvegarde:
                np.savetxt(sauvegarde , data, fmt=['%f','%f'])
        
    def arrondi(self,machaine,nbre_chiffres):
         """arrondi pour affichage dans label et équation"""
         newchaine = machaine.split('.')
         machaine = newchaine[0]+'.'+newchaine[1][0:nbre_chiffres]
         return machaine
     
    def cacher_label_simple_plot(self):
            #Ne plus afficher les valeurs pour pic individuel
            self.label__Ipic.setVisible(False)
            self.label_Lamba_pic.setVisible(False)
            self.label_6.setVisible(False)
            self.label_7.setVisible(False)
            self.spinBox_numero.setVisible(False) #on ne peut pas choisir quel scan afficher, ils le sont tous
            self.label_I1.setVisible(False)
            self.label_I2.setVisible(False)
            self.label_4.setVisible(False)
            self.label_5.setVisible(False)
            self.label_3.setVisible(False)
            
    def gestion_modes(self):
       
        #TO DO : ENABLE/DISABLE RADIO BUTTONS?
        if self.radioButton_calib_mode.isChecked():
            self.actionOpen.setEnabled(True)
            self.actionOpen_Calibration.setEnabled(True)  
            self.actionSave_Calibration.setEnabled(True)
            # self.menuCheck_Calibration_File.setEnabled(False)
            self.actionOpen_Data_Measure.setEnabled(False)
            self.actionSave_dat.setEnabled(False)
            self.actionSelect_Calibration_File.setEnabled(False)
     
            
        if self.radioButton_mes_mode.isChecked():
            # self.radioButton_Ratios.setEnabled(False)
            self.actionOpen.setEnabled(False)
            self.actionOpen_Calibration.setEnabled(False)  
            self.actionSave_Calibration.setEnabled(False)
            # self.menuCheck_Calibration_File.setEnabled(True)
            self.actionOpen_Data_Measure.setEnabled(True)
            self.actionSave_dat.setEnabled(True)
            self.actionSelect_Calibration_File.setEnabled(True)
            
    def about(self):
        QMessageBox.about(self, "About", "NanoThermo NCO LPCNO INSA Toulouse Coded by Simon Cayez 2022")

    def quit(self):   
         
        QtCore.QCoreApplication.instance().quit()
        QtWidgets.QMainWindow.close(self)  


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())
