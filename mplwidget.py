# -*- coding: utf-8 -*-
"""
Created on Wed Oct  6 17:47:55 2021

@author: cayez
"""

from PyQt5.QtWidgets import*

from matplotlib.backends.backend_qt5agg import FigureCanvas

from matplotlib.figure import Figure



    
class MplWidget(QWidget):
    
    def __init__(self, parent = None):

        QWidget.__init__(self, parent)
        
        self.canvas = FigureCanvas(Figure())
        
        vertical_layout = QVBoxLayout()
        vertical_layout.addWidget(self.canvas)
        
        self.canvas.ax1 = self.canvas.figure.add_subplot(111)
        self.canvas.ax2 = self.canvas.ax1.twinx()
        # self.canvas.ax0 = self.canvas.figure.add_subplot(111)
        
        self.setLayout(vertical_layout)
        # self.layout.addWidget(NavigationToolbar(self.canvas, self))
