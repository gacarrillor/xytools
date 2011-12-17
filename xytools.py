"""
/***************************************************************************
 XyTools
                                 A QGIS plugin
 Tools for managing tabular data with x y columns
                              -------------------
        begin                : 2011-08-19
        copyright            : (C) 2011 by webmapper
        email                : richard@webmapper.net
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
# Import the PyQt and QGIS libraries
import inspect
import types
from os import path
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from xytoolsdialog import XyToolsDialog

class XyTools:

    MSG_BOX_TITLE = "XY tools Plugin "
    XY_COMBO_MSG = "Please select one column"

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        # map with layer info
        self.layerInfo = {}
        self.layer = None


    def initGui(self):
        # we add the action to the same action group as another digitize action
        # in combination with the setCheckable it makes it will be unchecked automagically
        self.action = QAction(QIcon(":/plugins/xytools/icon.png"), \
                "XY tools", self.iface.actionCapturePoint().actionGroup())
        self.action.setCheckable(True)
        # connect the action to the run method
        QObject.connect(self.action, SIGNAL("triggered(bool)"), self.xyToolClick)

        # about
        self.aboutAction = QAction(QIcon(":/plugins/xytools/help.png"), \
                              "About", self.iface.mainWindow())
        self.aboutAction.setWhatsThis("Xy Tools Plugin About")
        self.iface.addPluginToMenu("&XY tools", self.aboutAction)
        QObject.connect(self.aboutAction, SIGNAL("activated()"), self.about)
        # help
        self.helpAction = QAction(QIcon(":/plugins/xytools/help.png"), \
                              "Help", self.iface.mainWindow())
        self.helpAction.setWhatsThis("Xy Tools Plugin Help")
        self.iface.addPluginToMenu("&XY tools", self.helpAction)
        QObject.connect(self.helpAction, SIGNAL("activated()"), self.help)
        # save as shape
        self.shapeSaveAction = QAction(QIcon(":/plugins/xytools/icon.png"), \
                              "Save attribute table as Point shape file", self.iface.mainWindow())
        self.shapeSaveAction.setWhatsThis("Xy Tools Plugin Save attribute table as Shape file (using xy-Column values for geometries!)")
        self.iface.addPluginToMenu("&XY tools", self.shapeSaveAction)
        QObject.connect(self.shapeSaveAction, SIGNAL("activated()"), self.shapeSave)
        # save as excel
        self.excelSaveAction = QAction(QIcon(":/plugins/xytools/icon.png"), \
                              "Save attribute table as Excel file", self.iface.mainWindow())
        self.excelSaveAction.setWhatsThis("Xy Tools Plugin Save Attribute Table as Excel File")
        self.iface.addPluginToMenu("&XY tools", self.excelSaveAction)
        QObject.connect(self.excelSaveAction, SIGNAL("activated()"), self.excelSave)
        # open excel file
        self.excelOpenAction = QAction(QIcon(":/plugins/xytools/icon.png"), \
                              "Open Excel file as attribute table or Point layer", self.iface.mainWindow())
        self.excelOpenAction.setWhatsThis("Xy Tools Plugin Open Excel file as Attribute table or Point layer")
        self.iface.addPluginToMenu("&XY tools", self.excelOpenAction)
        QObject.connect(self.excelOpenAction, SIGNAL("activated()"), self.excelOpen)
        # open open/libreoffice file
        self.unoOpenAction = QAction(QIcon(":/plugins/xytools/icon.png"), \
                              "Open Libre/OpenOffice Calc file as attribute table or Point layer", self.iface.mainWindow())
        self.unoOpenAction.setWhatsThis("Xy Tools Plugin Open Libre/OpenOffice Calc file as Attribute table or Point layer")
        self.iface.addPluginToMenu("&XY tools", self.unoOpenAction)
        QObject.connect(self.unoOpenAction, SIGNAL("activated()"), self.unoOpen)

        # add xypick button to edit/digitize toolbar
        editMenu = self.iface.digitizeToolBar()
        editMenu.addAction(self.action)
        # disable action in digitize menu untill 
        self.action.setEnabled(False)
        editMenu.update()

        QObject.connect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.currentLayerChanged)
        QObject.connect(self.iface.actionToggleEditing(), SIGNAL("changed()"), self.toggleEditing)

        self.xytool = GetPointTool(self.canvas, self.mapClick)


    def xyToolClick(self, checked):
        if checked and not self.canvas == None:
            if self.layerInfo.has_key(self.layer) or self.getXyColumns(self.layer):
                self.canvas.setMapTool(self.xytool)
            else:
                self.action.setChecked(False)


    def shapeSave(self):
        if self.layer == None:
            QMessageBox.warning(self.iface.mainWindow(), "No active layer", "Please make an vector layer active before saving it to shape file.")
            return
        if self.layerInfo.has_key(self.layer) or self.getXyColumns(self.layer):
            self.writeToShape()


    def excelOpen(self):
        filename = QFileDialog.getOpenFileName(self.iface.mainWindow(),
                    "Please choose an Excel spreadsheet file to open...",
                    ".",
                    "Excel files (*.xls)",
                    "Filter list for selecting files from a dialog box")
        if len(filename)==0:
            return
        try:
            from providers import excel
        except:
            QMessageBox.warning(self.iface.mainWindow(), "Unable to load Python module", "There is a problem with loading a python module which is needed to read/write Excel files. Please see documentation/help how to install python xlw and xlrd libraries.")
            return
        provider = excel.Reader(filename)
        # now load in layer
        self.loadSheetAsLayer(provider)


    def unoOpen(self):
        filename = QFileDialog.getOpenFileName(self.iface.mainWindow(),
                    "Please choose an Libre/OpenOffice spreadsheet file to open...",
                    ".",
                    "Libre/OpenOffice OOcalc files (*.ods)",
                    "Filter list for selecting files from a dialog box")
        if len(filename)==0:
            return
        try:
            from providers import libreoffice
        except:
            QMessageBox.warning(self.iface.mainWindow(), "Unable to load Python module", "There is a problem with loading a python module which is needed to read/write Libre/OpenOffice spreadsheet files. Please see documentation/help how to install these python-uno libraries.")
            return
        provider = libreoffice.Reader(filename)
        # now load in layer
        self.loadSheetAsLayer(provider)


    def loadSheetAsLayer(self, provider):
        try:
            rows = provider.openFile()
        except:
            QMessageBox.warning(self.iface.mainWindow(), "Unable to open file", "Unable to open file: " + unicode(filename))
            return
        layer = self.createMemoryLayer()
        if len(rows) == 0:
            QMessageBox.warning(self.iface.mainWindow(), "No rows found", "Please choose a spreadsheet with more then one row filled.")
            return
        attrCount = len(rows[0])
        for col in rows[0]:
            layer.dataProvider().addAttributes([QgsField(unicode(col), QVariant.String)])
        # see: http://osgeo-org.1803224.n2.nabble.com/Add-attributes-to-memory-provider-with-python-td6073149.html
        layer.updateFieldMap()
        xyOk = False
        if self.getXyColumns(layer):
            xyOk = True
        # fill rows
        for row in rows:
            if not row == rows[0]:
                f = QgsFeature()
                if xyOk:
                    x=row[self.layerInfo[self.layer].xIdx]
                    y=row[self.layerInfo[self.layer].yIdx]
                    if type(x) in types.StringTypes or type(y) in types.StringTypes:
                        # mmm, we have strings as values... try to cast to float
                        try:
                            x = float(x)
                            y = float(y)
                        except:
                            QMessageBox.warning(self.iface.mainWindow(), "Non numeric value found", "This spreadsheet contained non numeric values in one of the x or y columns. Values found: '" + unicode(x) + "' and '" + unicode(y) + "'.\nYou can open it without x and y columns by NOT choosing x and y columns (click Cancel in that dialog).\nRemoving the layer...")
                            QgsMapLayerRegistry.instance().removeMapLayer(layer.id())
                            return
                    f.setGeometry(QgsGeometry.fromPoint( QgsPoint(x,y) ) )
                else:
                    f.setGeometry( QgsGeometry.fromWkt('POINT(0 0)') )
                f.setAttributeMap( dict(zip( range(0,len(row)) ,row ))  )
                layer.dataProvider().addFeatures([f])
        layer.updateExtents()
        layer.reload()
        # trying to force a repaint
        self.canvas.updateFullExtent()
        self.canvas.setDirty(True)
        self.canvas.refresh()
        self.canvas.zoomByFactor(0.99)


    def excelSave(self):
        if self.layer == None: 
            QMessageBox.warning(self.iface.mainWindow(), "No active layer", "Please make an vector layer active before saving it to excel file.")
            return
        filename = QFileDialog.getSaveFileName(self.iface.mainWindow(),
                    "Please save excel file as...",
                    ".",
                    "Excel files (*.xls)",
                    "Filter list for selecting files from a dialog box")
        fn, fileExtension = path.splitext(unicode(filename))
        if len(fn) == 0: # user choose cancel
            return
        print fileExtension
        if fileExtension != '.xls':
            filename = filename + '.xls'
        try:
            from providers import excel
        except:
            QMessageBox.warning(self.iface.mainWindow(), "Unable to load Python module", "There is a problem with loading a python module which is needed to read/write Excel files. Please see documentation/help how to install python xlw and xlrd libraries.")
            return
        xlw = excel.Writer(filename)
        self.layer = self.iface.activeLayer()
        prov = self.layer.dataProvider()
        selection = None
        if self.layer.selectedFeatureCount() > 0:
            if QMessageBox.question(self.iface.mainWindow(), 
                self.MSG_BOX_TITLE, 
                ("You have a selection in this layer. Only export this selection?\n" "Click Yes to export selection only, click No to export all rows."), 
                QMessageBox.No, QMessageBox.Yes) == QMessageBox.Yes:
                    selection = self.layer.selectedFeaturesIds()
        prov.select(prov.attributeIndexes())
        feature = QgsFeature();
        rowNr = 0
        while prov.nextFeature(feature):
            # attribute names
            if rowNr == 0:
                values = []
                for (i, field) in prov.fields().iteritems():
                    values.append(field.name().trimmed())
                xlw.writeAttributeRow( rowNr, values )
                rowNr+=1
            # and attribute values, either for all or only for selection
            if selection == None or feature.id() in selection:
                values = feature.attributeMap().values()
                xlw.writeAttributeRow( rowNr, values )
                rowNr+=1
        xlw.saveFile()
        QMessageBox.information(self.iface.mainWindow(), "Success", "Successfully saved as xls file")


    def writeToShape(self):
        filename = QFileDialog.getSaveFileName(self.iface.mainWindow(),
                    "Please save shape file as...",
                    ".",
                    "Esri shape files (*.shp)",
                    "Filter list for selecting files from a dialog box")
        # Check that a file was selected
        if len(filename) == 0: # user choose cancel
            return
        fields = self.layer.dataProvider().fields()
        writer = QgsVectorFileWriter(unicode(filename), "UTF8", fields, QGis.WKBPoint, None)
        feature = QgsFeature();
        prov = self.layer.dataProvider()
        #   with  ALL attributes, WITHIN extent, WITHOUT geom, AND NOT using Intersect instead of bbox
        prov.select(prov.attributeIndexes(), prov.extent(), False, False)
        while prov.nextFeature(feature):
            x=feature.attributeMap()[self.layerInfo[self.layer].xIdx].toFloat()
            y=feature.attributeMap()[self.layerInfo[self.layer].yIdx].toFloat()
            feature.setGeometry(QgsGeometry.fromPoint(QgsPoint(x[0],y[0])))
            writer.addFeature(feature)
        # flush and delete
        del writer
        QMessageBox.information(self.iface.mainWindow(), "Success", "Successfully saved as shape")


    def getXyColumns(self, layer):
        dlg = XyToolsDialog(self.XY_COMBO_MSG, layer.dataProvider().fields(), layer.name())
        xyOK = False
        while not xyOK:
            dlg.show()
            if dlg.exec_() ==0:
                break
            else: # user hit OK, check valid x and y column index?
                idx = dlg.getXindex()
                idy = dlg.getYindex()
                if idx >= 0 and idy >= 0 and not (idx == idy):
                    self.layerInfo[layer] = XyTable(layer, self.canvas)
                    self.layerInfo[layer].setXYColumnIndex(idx, idy)
                    xyOK = True
                else:
                    QMessageBox.warning(self.iface.mainWindow(), self.MSG_BOX_TITLE, \
                            ("Please select the columns to use for x and y \n (cannot be the same column)"), \
                            QMessageBox.Ok, QMessageBox.Ok)
        return xyOK


    def unload(self):
        # Remove the plugin menu item and icon
        #self.iface.removePluginMenu("&XY tools",self.action)
        self.iface.removePluginMenu("&XY tools",self.helpAction)
        self.iface.removePluginMenu("&XY tools",self.aboutAction)
        self.iface.removePluginMenu("&XY tools",self.shapeSaveAction)
        self.iface.removePluginMenu("&XY tools",self.excelSaveAction)
        self.iface.removePluginMenu("&XY tools",self.excelOpenAction)
        self.iface.removePluginMenu("&XY tools",self.unoOpenAction)
        self.iface.removeToolBarIcon(self.action)

        # remove xypick button to edit/digitize toolbar
        editMenu = self.iface.digitizeToolBar()
        editMenu.removeAction(self.action)
        editMenu.update()

        self.cleanupXyMarkers();
        self.layerInfo = {}
        self.layer = None

        QObject.disconnect(self.action, SIGNAL("triggered(bool)"), self.xyToolClick)
        QObject.disconnect(self.aboutAction, SIGNAL("activated()"), self.about)
        QObject.disconnect(self.helpAction, SIGNAL("activated()"), self.help)
        QObject.disconnect(self.shapeSaveAction, SIGNAL("activated()"), self.shapeSave)
        QObject.disconnect(self.excelSaveAction, SIGNAL("activated()"), self.excelSave)
        QObject.disconnect(self.excelOpenAction, SIGNAL("activated()"), self.excelOpen)
        QObject.disconnect(self.unoOpenAction, SIGNAL("activated()"), self.unoOpen)
        QObject.disconnect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.currentLayerChanged)
        QObject.disconnect(self.iface.actionToggleEditing(), SIGNAL("changed()"), self.toggleEditing)


    def toggleEditing(self):
        self.layer = self.iface.activeLayer()
        if not self.iface.actionToggleEditing().isChecked():
            # disable stuff (for this layer)
            self.action.setChecked(False)
            self.action.setEnabled(False)
            self.canvas.unsetMapTool(self.xytool)
            # edit tools itself will ask for a potential save of edits
            return
        if not self.layer == None and self.layer.type() == 0: # only vector layers
            self.action.setEnabled(True)


    def currentLayerChanged(self, currentLayer):
        if currentLayer == None: return
        self.cleanupXyMarkers()
        self.layer = self.iface.activeLayer()
        if currentLayer.isEditable():
            self.action.setEnabled(True)
        else:
            self.action.setEnabled(False)
            self.action.setChecked(False)

    def cleanupXyMarkers(self):
        for lyr in self.layerInfo:
            self.layerInfo[lyr].deleteMarker()

    def createMemoryLayer(self, crs=None):
        layer = QgsVectorLayer("Point", "Temporary Layer (volatile)", "memory")
        if crs:
            crs = QgsCoordinateReferenceSystem(crs, QgsCoordinateReferenceSystem.PostgisCrsId)
        else:
            crs = self.canvas.mapRenderer().destinationCrs()
        layer.setCrs(crs)
        QgsMapLayerRegistry.instance().addMapLayer(layer)
        return layer

    def help(self):
        file = inspect.getsourcefile(XyTools)
        file = 'file://' + path.join(path.dirname(file),'docs/index.html')
        file = file.replace("\\","/")
        self.iface.openURL(file, False)

    def about(self):
        infoString = QString("Written by Richard Duivenvoorde\nEmail - richard@duif.net\n")
        infoString = infoString.append("Company - http://www.webmapper.net\n")
        infoString = infoString.append("Source: http://hub.qgis.org/projects/xytools/")
        QMessageBox.information(self.iface.mainWindow(), \
                            "XY tools Plugin About", infoString)

    def mapClick(self, xy):
        self.layerInfo[self.layer].setXY(xy.x(), xy.y())


class XyTable():

    MSG_BOX_TITLE = "XY tools Plugin "

    def __init__(self, layer, mapCanvas):
        self.layer = layer
        self.canvas = mapCanvas
        self.xIdx = None
        self.yIdx = None
        self.marker = None
        # connect selection change events of this layer 
        QObject.connect(self.layer, SIGNAL("selectionChanged()"), self.selectionChanged)
        #QObject.connect(self.layer, SIGNAL("editingStarted()"), self.editingStarted)
        QObject.connect(self.layer, SIGNAL("editingStopped()"), self.editingStopped)

    def setXYColumnIndex(self, xIdx, yIdx):
        self.xIdx = xIdx
        self.yIdx = yIdx

    def deleteMarker(self):
        if self.marker != None:
            self.canvas.scene().removeItem(self.marker)
            self.maker = None

    def setXY(self, x, y):
        fid = self.checkGetSelectedFeatureId()
        if fid==None:
            return
        self.layer.changeAttributeValue(fid, self.xIdx, float(x))
        self.layer.changeAttributeValue(fid, self.yIdx, float(y))
        self.setMarker(x,y)
        # windows does not repaint the attribute table
        self.layer.reload()

    def checkGetSelectedFeatureId(self):
        ids = self.layer.selectedFeaturesIds()
        # ONLY ONE ALLOWED FOR NOW !!
        if len(ids)==0:
            QMessageBox.warning(None, self.MSG_BOX_TITLE, ("Please select one record in the attribute table\n to update x and y for.\n(Open Attribute table if neccesary)"), QMessageBox.Ok, QMessageBox.Ok)
            return None
        elif len(ids)>1:
            QMessageBox.warning(None, self.MSG_BOX_TITLE, ("Too many records in attribute table selected, please select just one."), QMessageBox.Ok, QMessageBox.Ok)
            return None
        return ids[0]

    def selectionChanged(self):
        # do this because apparently there are two events, first one with NO selection returned
        ids = self.layer.selectedFeaturesIds()
        if len(ids)==0 or not self.layer.isEditable():
            return
        fid = self.checkGetSelectedFeatureId()
        if fid==None or self.xIdx == None or self.yIdx == None:
            return
        f = QgsFeature()
        self.layer.featureAtId(fid, f, True, True)
        # x and y are QVariants
        y = f.attributeMap()[self.yIdx]
        x = f.attributeMap()[self.xIdx]
        if x.canConvert(QVariant.Double) and y.canConvert(QVariant.Double): # not NULL
            xd = x.toDouble()[0]
            yd = y.toDouble()[0]
            xy = QgsPoint(xd,yd)
            self.setMarker(xd, yd)
            if not self.canvas.extent().contains(xy) and (xd>0 and yd>0):
                width = self.canvas.extent().width()
                height = self.canvas.extent().height()
                self.canvas.setExtent(QgsRectangle(xd-width/2,yd-height/2,xd+width/2,yd+height/2))
                self.canvas.refresh()

    def setMarker(self, x,y):
        self.deleteMarker()
        if x != 0 and y != 0 and x != None and y != None:
            self.marker = QgsVertexMarker(self.canvas)
            # make marker better visible:
            self.marker.setPenWidth(5)
            self.marker.setCenter(QgsPoint(x, y))

    def editingStopped(self):
        self.deleteMarker()




class GetPointTool(QgsMapTool):

    def __init__(self, canvas, callback):
        QgsMapTool.__init__(self, canvas)
        self.callback = callback
        self.canvas = canvas
        self.cursor = QCursor(QPixmap(["16 16 4 1", "  c None", ". c #000000", "+ c #FFFFFF", "- c #FF0000",
                                    "                ",
                                    "       +.+      ",
                                    "      ++.++     ",
                                    "     +.....+    ",
                                    "    +.     .+   ",
                                    "   +.   .   .+  ",
                                    "  +.    .    .+ ",
                                    " ++.    -    .++",
                                    " ... ..---.. ...",
                                    " ++.    -    .++",
                                    "  +.    .    .+ ",
                                    "   +.   .   .+  ",
                                    "   ++.     .+   ",
                                    "    ++.....+    ",
                                    "      ++.++     ",
                                    "       +.+      "]))

    def canvasPressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.pos = self.toMapCoordinates(e.pos())

    def canvasReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.callback(self.pos)

    def activate(self):
        self.canvas.setCursor(self.cursor)
