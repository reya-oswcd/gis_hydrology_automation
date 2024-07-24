# -*- coding: utf-8 -*-import arcpyimport pathlibimport openpyxlimport datetimeclass Toolbox:    def __init__(self):        """Define the toolbox (the name of the toolbox is the name of the        .pyt file)."""        self.label = "Hydrology"        self.alias = "Hydrology"        # List of tool classes associated with this toolbox        self.tools = [Tool]class Tool:    def __init__(self):        """Define the tool (tool name is the name of the class)."""        self.label = "Hydrology"        self.description = ""    def getParameterInfo(self):        """Define parameter definitions"""        param0 = arcpy.Parameter(            displayName="Watershed Boundary Layer",            name="watershed",            datatype="GPFeatureLayer",            parameterType="Required",            multiValue=True,            direction="Input")        param1 = arcpy.Parameter(            displayName="Output Folder",            name="output_location",            datatype="DEFolder",            parameterType="Required",            direction="Input")        params = [param0, param1]        return params            def printMessages(*args):        """provide a list of messages to this method"""        out_str = ""        for arg in args:            out_str += str(arg)        arcpy.AddMessage("\n")        arcpy.AddMessage(out_str)        return    def execute(self, parameters, messages):        """The source code of the tool."""        # setup        log=self.printMessages        arcpy.env.overwriteOutput = True        project = arcpy.mp.ArcGISProject("Current")        # helper variables        orig_map = project.listMaps("Map")[0]        orig_layout = project.listLayouts("Layout")[0]        layouts = []        # read in parameters        watershed_layers = parameters[0].valueAsText.replace("'","").split(";")        output_folder_path = parameters[1].valueAsText        for watershed_layer in watershed_layers:            # utils            watershed_layer_id = watershed_layer.replace(" ","")            layers_to_remove = []            # create new map and make it active            active_map = project.copyItem(orig_map, watershed_layer)            active_map.openView()            cam = project.activeView.camera                        # create a new layout            new_layout = project.copyItem(orig_layout, watershed_layer)            new_layout.openView()            layouts.append(new_layout)                        # set layout's map to new map created            mf = new_layout.listElements("MAPFRAME_ELEMENT")[0]            mf.map = active_map            mf.name = watershed_layer                           hydrology_group_layer = active_map.listLayers("Hydrology Analysis")            if len(hydrology_group_layer) == 0:                hydrology_group_layer = active_map.createGroupLayer("Hydrology Analysis")            else:                hydrology_group_layer = active_map.listLayers("Hydrology Analysis")[0]            # clip land use raster            land_use_layer = active_map.listLayers("Land Use")[0]                    land_use_path = "{}\\{}_{}".format(arcpy.env.workspace, "cblc_clip", watershed_layer_id)            land_use_clip_layer = arcpy.management.Clip(land_use_layer, "", land_use_path, watershed_layer, "#", "ClippingGeometry")            land_use_clip_layer = active_map.addDataFromPath(land_use_clip_layer)            land_use_clip_layer.name = "Watershed Land Use Clip"            active_map.addLayerToGroup(hydrology_group_layer, land_use_clip_layer)            layers_to_remove.append(land_use_clip_layer)            # land use raster to polygon            land_use_polygon_path = "{}_{}".format(land_use_path, "to_polygon")                    land_use_polygon_layer = arcpy.conversion.RasterToPolygon(land_use_clip_layer, land_use_polygon_path, "NO_SIMPLIFY", "LandCover")            land_use_polygon_layer = active_map.addDataFromPath(land_use_polygon_layer)            land_use_polygon_layer.name = "Watershed Land Use Clip to Polygon"            active_map.addLayerToGroup(hydrology_group_layer, land_use_polygon_layer)            layers_to_remove.append(land_use_polygon_layer)                        # join raster fields (rcns and landcover fields)            arcpy.management.JoinField(land_use_polygon_layer, "LandCover", land_use_clip_layer, "LandCover", ["RCNA", "RCNB", "RCNC", "RCND"])            # intersect land cover and soils            soils_layer = active_map.listLayers("Soils")[0]              intersection_name = "land_use_soils_intersection_{}".format(watershed_layer_id)            land_use_soils_intersection = arcpy.analysis.PairwiseIntersect(["Watershed Land Use Clip to Polygon", "Soils/Soils"], intersection_name)            land_use_soils_intersection = active_map.addDataFromPath(land_use_soils_intersection)            active_map.addLayerToGroup(hydrology_group_layer, land_use_soils_intersection)            layers_to_remove.append(land_use_soils_intersection)            # add column for runoff curve number            arcpy.management.AddField(land_use_soils_intersection, "RCN", "Short", "", "", "", "Runoff Curve Number")            # populate runoff curve numbers based off of hydrologic soil group            with arcpy.da.UpdateCursor(land_use_soils_intersection, ["hydgrpdcd","RCN", "RCNA", "RCNB", "RCNC", "RCND"]) as cursor:                for row in cursor:                    hsg = row[0]                    if hsg == "A":                        row[1] = row[2]                    elif hsg == "B":                        row[1] = row[3]                    elif hsg == "C":                        row[1] = row[4]                    elif hsg == "D":                        row[1] = row[5]                    cursor.updateRow(row)            # delete unecessary fields            arcpy.management.DeleteField(land_use_soils_intersection, ["LandCover", "hydgrpdcd", "Hydrologic Group - Dominant Conditions", "RCN", "MUSYM"], "KEEP_FIELDS")                    # add acres field and calculate for land use / soils            if "Acres" not in [f.name for f in arcpy.ListFields(land_use_soils_intersection)]:                arcpy.management.AddField(land_use_soils_intersection, "Acres", "FLOAT", 2, 2)            arcpy.management.CalculateGeometryAttributes(in_features=land_use_soils_intersection.name, geometry_property=[["Acres", "AREA_GEODESIC"]], area_unit="ACRES_US")            # add acres field and calculate for watershed            if "Acres" not in [f.name for f in arcpy.ListFields(watershed_layer)]:                arcpy.management.AddField(watershed_layer, "Acres", "FLOAT", 2, 2)            arcpy.management.CalculateGeometryAttributes(in_features=watershed_layer, geometry_property=[["Acres", "AREA_GEODESIC"]], area_unit="ACRES_US")            acres = round(float([row[0] for row in arcpy.da.SearchCursor(watershed_layer, "Acres")][0]),2)                        # clip DEM raster            clip_1m_dem = active_map.listLayers("1m")[0]                    out_dem_path = "{}\\{}_{}".format(arcpy.env.workspace, "DEM_1m_clip", watershed_layer_id)            clip_1m_dem = arcpy.management.Clip(clip_1m_dem, "", out_dem_path, watershed_layer, "#", "ClippingGeometry")            clip_1m_dem = active_map.addDataFromPath(clip_1m_dem)            active_map.addLayerToGroup(hydrology_group_layer, clip_1m_dem)            layers_to_remove.append(clip_1m_dem)            # slope map            out_slope_path = "{}\\w{}_slope".format(arcpy.env.workspace, len(layouts))            # breaks the script for unknown reason, possibly related: https://community.esri.com/t5/arcgis-spatial-analyst-questions/using-arcpy-to-create-slope-surfaces/td-p/206039            #if arcpy.Exists(out_slope_path):            #    log("exists")            #    arcpy.management.Delete(out_slope_path)            slope_raster = arcpy.sa.Slope(clip_1m_dem.name, "PERCENT_RISE", "", "GEODESIC", "METER")            slope_raster.save(out_slope_path)            slope_raster = active_map.addDataFromPath(slope_raster)            active_map.addLayerToGroup(hydrology_group_layer, slope_raster)            layers_to_remove.append(slope_raster)            # zonal statistics            out_table_name = "zonalstatistics_{}".format(watershed_layer_id)            out_table_path = "{}\\{}".format(arcpy.env.workspace, out_table_name)            arcpy.sa.ZonalStatisticsAsTable(watershed_layer, "Name", slope_raster, out_table_name, "", "MEAN")            active_map.addDataFromPath(out_table_path)            mean_slope = round(float([row[0] for row in arcpy.da.SearchCursor(out_table_path, "MEAN")][0]),2)            # fill DEM to eventually find flow length of watershed            out_fill_path = "{}_{}".format(out_dem_path, "fill")            filled_dem = arcpy.sa.Fill(clip_1m_dem, 3.2808)            filled_dem.save(out_fill_path)            filled_dem = active_map.addDataFromPath(filled_dem)            active_map.addLayerToGroup(hydrology_group_layer, filled_dem)            layers_to_remove.append(filled_dem)            # calculate flow directions            out_flowdir_path = "{}\\flow_direction_{}".format(arcpy.env.workspace, watershed_layer_id)            flow_direction_raster = arcpy.sa.FlowDirection(filled_dem)            flow_direction_raster.save(out_flowdir_path)            flow_direction_raster = active_map.addDataFromPath(flow_direction_raster)            active_map.addLayerToGroup(hydrology_group_layer, flow_direction_raster)            layers_to_remove.append(flow_direction_raster)                        # find flow lengths of watershed            out_flow_length_path = "{}\\flow_length_{}".format(arcpy.env.workspace, watershed_layer_id)            flow_length_raster = arcpy.sa.FlowLength(flow_direction_raster, "DOWNSTREAM")            flow_length_raster.save(out_flow_length_path)            flow_length_raster = active_map.addDataFromPath(flow_length_raster)            active_map.addLayerToGroup(hydrology_group_layer, flow_length_raster)            layers_to_remove.append(flow_length_raster)                        # find maximum flow length            flow_length_maximum = int(float(arcpy.management.GetRasterProperties(flow_length_raster, "MAXIMUM").getOutput(0))*3.2808)            # setup hydrology worksheet locations            hydrology_worksheet = 'O:\Stream and Culvert Projects\Hydrology Data Form.xlsx'            output_worksheet_path = '{}\{}_hydrology.xlsx'.format(output_folder_path, watershed_layer_id)            output_worksheet_path = pathlib.PureWindowsPath(output_worksheet_path).as_posix()            # fill out hydrology worksheet                   hydrology_worksheet = openpyxl.load_workbook(hydrology_worksheet)            ws = hydrology_worksheet['Data']            ws["E1"] = project.filePath.split("\\")[-1][:-5]            ws['F2'] = datetime.date.today().isoformat()            ws['G2'] = datetime.datetime.now().strftime("%H:%M:%S")            ws['H2'] = watershed_layer            ws['G4'] = acres            ws['G6'] = flow_length_maximum            ws['G7'] = mean_slope            with arcpy.da.SearchCursor(land_use_soils_intersection, ["RCN", "Acres"]) as cursor:                idx = 4                for row in cursor:                    rcn = row[0]                    acres = row[1]                    ws["A"+str(idx)] = rcn                    ws["B"+str(idx)] = acres                                    idx += 1                                hydrology_worksheet.save(output_worksheet_path)            # zoom to layer in map object            watershed_layer = active_map.listLayers(watershed_layer)[0]            ext = arcpy.Describe(watershed_layer).extent            cam.setExtent(ext)            # zoom layout to last active map            mf = new_layout.listElements("MAPFRAME_ELEMENT")[0]            mf.camera.setExtent(mf.getLayerExtent(watershed_layer))            mf.camera.scale = mf.camera.scale * 1.1            # Need to close layouts for camera change to take effect            project.closeViews("LAYOUTS")                                             # remove old layers            for l in layers_to_remove:                active_map.removeLayer(l)        for layout in layouts:            layout.openView()                        # save and exit program successfully        project.save()                # open hydrology worksheet        os.startfile(output_folder_path)                return