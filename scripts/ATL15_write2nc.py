#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 24 10:45:47 2020

@author: ben05
"""
import numpy as np
import  os, h5py, csv, re
import ast
import importlib.resources
from netCDF4 import Dataset
import matplotlib.pyplot as plt
import matplotlib as mpl
import cartopy.crs as ccrs
import cartopy.feature
from scipy import stats
from ATL14_attrs_meta import write_atl14meta

def ATL15_write2nc(args):

    def make_dataset(field,fieldout,data,field_attrs,file_obj,group_obj,nctype,dimScale=False):
        # where field is the name from ATL15_output_attrs.csv file
        # where fieldout is the name of the output variable in the .nc file
        dimensions = field_attrs[field]['dimensions'].split(',')
        dimensions = tuple(x.strip() for x in dimensions)
        if field_attrs[field]['datatype'].startswith('int'):
            fill_value = np.iinfo(np.dtype(field_attrs[field]['datatype'])).max
        elif field_attrs[field]['datatype'].startswith('float'):
            fill_value = np.finfo(np.dtype(field_attrs[field]['datatype'])).max
        data = np.nan_to_num(data,nan=fill_value)

        if dimScale:
            group_obj.createDimension(field_attrs[field]['dimensions'],data.shape[0])

        dsetvar = group_obj.createVariable(fieldout,
                                           nctype[field_attrs[field]['datatype']],
                                           dimensions,
                                           fill_value=fill_value, zlib=True,
                                           least_significant_digit=ast.literal_eval(field_attrs[field]['least_significant_digit']))
            
        dsetvar[:] = data
        for attr in attr_names:
            if attr != 'group description':
                dsetvar.setncattr(attr,field_attrs[field][attr])
        # add attributes for projection
        if not field.startswith('time'):
            dsetvar.setncattr('grid_mapping','Polar_Stereographic')
        if field == 'x':
            dsetvar.standard_name = 'projection_x_coordinate'
        if field == 'y':
            dsetvar.standard_name = 'projection_y_coordinate'

        return file_obj
    
    dz_dict ={'time':'t',     # for non-lagged vars. {ATL15 outgoing var name: hdf5 incoming var name}          
              'time_lag1':'t',
              'time_lag4':'t',
              'time_lag8':'t',
              'x':'x',
              'y':'y',
              'cell_area':'cell_area',
              'ice_mask':'mask',
              'data_count':'count',
              'misfit_rms':'misfit_rms',
              'misfit_scaled_rms':'misfit_scaled_rms',
              'delta_h':'dz',
              'delta_h_sigma':'sigma_dz',
              'delta_h_10km':'avg_dz_10000m',
              'delta_h_sigma_10km':'sigma_avg_dz_10000m',
              'delta_h_20km':'avg_dz_20000m',
              'delta_h_sigma_20km':'sigma_avg_dz_20000m',
              'delta_h_40km':'avg_dz_40000m',
              'delta_h_sigma_40km':'sigma_avg_dz_40000m',
              }
    nctype = {'float64':'f8',
              'float32':'f4',
              'int8':'i1'}

    lags = {
            'file' : ['FH','FH_lag1','FH_lag4','FH_lag8'],
            'vari' : ['','_lag1','_lag4','_lag8'],
            'varigrp' : ['delta_h','dhdt_lag1','dhdt_lag4','dhdt_lag8']
           }
    avgs = ['','_10km','_20km','_40km']

    # open data attributes file
    with importlib.resources.path('surfaceChange','resources') as pp:
        with open(os.path.join(pp,'ATL15_output_attrs.csv'),'r', encoding='utf-8-sig') as attrfile:
            reader=list(csv.DictReader(attrfile))

    attr_names=[x for x in reader[0].keys() if x != 'field' and x != 'group']
    
    for kk,ave in enumerate(avgs):  
        # establish output file, one per average
        if ave=='':
            fileout = args.base_dir.rstrip('/') + '/ATL15_' + args.region + '_' + args.cycles + '_01km_' + args.Release + '_' + args.version + '.nc'
        else:
            fileout = args.base_dir.rstrip('/') + '/ATL15_' + args.region + '_' + args.cycles + ave + '_' + args.Release + '_' + args.version + '.nc'
#        print('output file:',fileout)
    
        with Dataset(fileout,'w',clobber=True) as nc:
            nc.setncattr('GDAL_AREA_OR_POINT','Area')
            nc.setncattr('Conventions','CF-1.6')
            
            # make tile_stats group (ATBD 4.1.2.1, Table 3)
            tilegrp = nc.createGroup('tile_stats')   
            tile_stats = {'x': { 'data': [], 'description':'tile-center x-coordinate, in projected coordinates', 'mapped':np.array(())},
                          'y': { 'data': [], 'description':'tile-center y-coordinate, in projected coordinates', 'mapped':np.array(())},
                          'N_data': { 'data': [], 'description':'number of data used in fit', 'mapped':np.array(())},
                          'RMS_data': { 'data': [], 'description':'root mean of squared, scaled data misfits', 'mapped':np.array(())},
                          'RMS_bias': { 'data': [], 'description':'root mean of squared, scaled bias values', 'mapped':np.array(())},
                          'N_bias': { 'data': [], 'description':'number of bias values solved for', 'mapped':np.array(())},
                          'RMS_d2z0dx2': { 'data': [], 'description':'root mean square of the constraint equation residuals for the second spatial derivative of z0', 'mapped':np.array(())},
                          'RMS_d2zdt2': { 'data': [], 'description':'root mean square of the constraint equation residuals for the second temporal derivative of dz', 'mapped':np.array(())},
                          'RMS_d2zdx2dt' : { 'data': [], 'description':'root mean square of the constraint equation residuals for the second temporal derivative of dz/dt', 'mapped':np.array(())}
                          }
            
            # work through the tiles in all three subdirectories
            for sub in ['centers','edges','corners']:
                files = os.listdir(os.path.join(args.base_dir,sub))
                for file in files:
                    try:
                        tile_stats['x']['data'].append(int(re.match(r'^.*E(.*)\_.*$',file).group(1)))
                    except Exception as e:
                        print(f'ATL15_write2nc; unexpected file name {file}, skipping')
                        continue
                    tile_stats['y']['data'].append(int(re.match(r'^.*N(.*)\..*$',file).group(1)))
                    with h5py.File(os.path.join(args.base_dir,sub,file),'r') as h5:
                        tile_stats['N_data']['data'].append( np.sum(h5['data']['three_sigma_edit'][:]) )
                        tile_stats['RMS_data']['data'].append( h5['RMS']['data'][()] )  # use () for getting a scalar.
                        tile_stats['RMS_bias']['data'].append( np.sqrt(np.mean((h5['bias']['val'][:]/h5['bias']['expected'][:])**2)) )
                        tile_stats['N_bias']['data'].append( len(h5['bias']['val'][:]) )  #### or all BUT the zeros.
                        tile_stats['RMS_d2z0dx2']['data'].append( h5['RMS']['grad2_z0'][()] )
                        tile_stats['RMS_d2zdt2']['data'].append( h5['RMS']['d2z_dt2'][()] )
                        tile_stats['RMS_d2zdx2dt']['data'].append( h5['RMS']['grad2_dzdt'][()] )
                        
            # establish output grids
            for key in tile_stats.keys():
                if 'x' == key or 'y' == key or 'N_data' == key:  #integers
                    tile_stats[key]['mapped'] = np.zeros( [len(np.arange(np.min(tile_stats['y']['data']),np.max(tile_stats['y']['data'])+40,40)),
                                                           len(np.arange(np.min(tile_stats['x']['data']),np.max(tile_stats['x']['data'])+40,40))], 
                                                           dtype=int)
                else:
                    tile_stats[key]['mapped'] = np.zeros( [len(np.arange(np.min(tile_stats['y']['data']),np.max(tile_stats['y']['data'])+40,40)),
                                                           len(np.arange(np.min(tile_stats['x']['data']),np.max(tile_stats['x']['data'])+40,40))],
                                                           dtype=float)
    
            # fill grids
            for i, (yt,xt) in enumerate(zip(tile_stats['y']['data'],tile_stats['x']['data'])):
                for key in tile_stats.keys():
                    if 'x' not in key and 'y' not in key:
                        tile_stats[key]['mapped'][int((yt-np.min(tile_stats['y']['data']))/40),int((xt-np.min(tile_stats['x']['data']))/40)] = \
                        tile_stats[key]['data'][i]
                        tile_stats[key]['mapped'] = np.ma.masked_where(tile_stats[key]['mapped'] == 0, tile_stats[key]['mapped'])   

            # make dimensions
            tilegrp.createDimension('y',len(np.arange(np.min(tile_stats['y']['data']),np.max(tile_stats['y']['data'])+40,40)))
            y = tilegrp.createVariable('y', np.dtype('int32'), ('y',))
            y[:]=np.arange(np.min(tile_stats['y']['data']),np.max(tile_stats['y']['data'])+40,40) 
            y.units = 'meter'
            y.description = tile_stats['y']['description']
            y.grid_mapping = 'Polar_Stereographic'
            
            tilegrp.createDimension('x',len(np.arange(np.min(tile_stats['x']['data']),np.max(tile_stats['x']['data'])+40,40)))
            x = tilegrp.createVariable('x', np.dtype('int32'), ('x',))
            x[:]=np.arange(np.min(tile_stats['x']['data']),np.max(tile_stats['x']['data'])+40,40)
            x.units = 'meter'
            x.description = tile_stats['x']['description']
            x.grid_mapping = 'Polar_Stereographic'

            # create tile_stats/ variables in .nc file
            for key in tile_stats.keys():
                if 'x' not in key and 'y' not in key:
                    if 'N_data' == key:
                        dsetvar = tilegrp.createVariable(key,np.dtype('int32'),('y','x'),fill_value=np.iinfo(np.dtype('int32')).max, zlib=True)
                    else:
                        dsetvar = tilegrp.createVariable(key,np.dtype('float64'),('y','x'),fill_value=np.finfo(np.dtype('float64')).max, zlib=True)
                        dsetvar.least_significant_digit = 4
                    dsetvar[:] = tile_stats[key]['mapped'][:]
                    dsetvar.setncattr('description',tile_stats[key]['description'])
                    dsetvar.setncattr('grid_mapping','Polar_Stereographic')
            
            crs_var = projection_variable(args.region,tilegrp)

#            # make comfort figures
#            extent=[np.min(tile_stats['x']['data'])*fact,np.max(tile_stats['x']['data'])*fact,
#                    np.min(tile_stats['y']['data'])*fact,np.max(tile_stats['y']['data'])*fact]
#            cmap = mpl.cm.get_cmap("viridis").copy()
#            cmnan = mpl.cm.get_cmap(cmap)
#            cmnan.set_bad(color='white')
#            
#            for i,key in enumerate(tile_stats.keys()):
#                makey = np.ma.masked_where(tile_stats[key]['mapped'] == 0, tile_stats[key]['mapped'])   
#                fig,ax=plt.subplots(1,1)
#                ax = plt.subplot(1,1,1,projection=ccrs.NorthPolarStereo(central_longitude=-45))
#                ax.add_feature(cartopy.feature.LAND)
#                ax.coastlines(resolution='110m',linewidth=0.5)
#                ax.set_extent([-10,90,70,90],crs=ccrs.PlateCarree())
#                ax.gridlines(crs=ccrs.PlateCarree())
#                h=ax.imshow(makey,extent=extent,vmin=np.min(makey.ravel()),vmax=np.max(makey.ravel()),cmap=cmnan,origin='lower')
#                fig.colorbar(h,ax=ax)
#                ax.set_title(f'{key}')
#                fig.savefig(f"{os.path.join(args.base_dir,'tile_stats_' + key + '.png')}",format='png')
#                
#            plt.show(block=False)
#            plt.pause(0.001)
#            input('Press enter to end.')
#            plt.close('all')
#            exit(-1)

            # loop over dz*.h5 files for one ave
            for jj in range(len(lags['file'])):
                filein = args.base_dir.rstrip('/')+'/dz'+ave+lags['vari'][jj]+'.h5'
                if not os.path.isfile(filein):
                    print('No file:',args.base_dir.rstrip('/')+'/'+os.path.basename(filein))
                    continue
                else:
                    print('Reading file:',args.base_dir.rstrip('/')+'/'+os.path.basename(filein))
                lags['file'][jj] = h5py.File(filein,'r')  # file object
                dzg=list(lags['file'][jj].keys())[0]      # dzg is group in input file
    
                nc.createGroup(lags['varigrp'][jj])
                print(lags['varigrp'][jj])
                
                # make projection variable for each group
                crs_var = projection_variable(args.region,nc.groups[lags['varigrp'][jj]])
                                   
                # dimension scales for each group
                for field in ['x','y']:
                    data = np.array(lags['file'][jj][dzg][dz_dict[field]])
                    if field == 'x':
                        x = data
                        xll = np.min(x)
                        dx = x[1]-x[0]
                    if field == 'y':
                        y = data
                        yll = np.max(y)
                        dy = y[0]-y[1]
                    field_attrs = {row['field']: {attr_names[ii]:row[attr_names[ii]] for ii in range(len(attr_names))} for row in reader if field in row['field'] if row['group']=='height_change'+ave}
                    make_dataset(field,field,data,field_attrs,nc,nc.groups[lags['varigrp'][jj]],nctype,dimScale=True)
                crs_var.GeoTransform = (xll,dx,0,yll,0,dy)

                if jj==0:  # no lag
                    field = 'time'
                    data = np.array(lags['file'][jj][dzg]['t'])
                    # convert to decimal days from 1/1/2018
                    data = (data-2018.)*365.25
                    field_attrs = {row['field']: {attr_names[ii]:row[attr_names[ii]] for ii in range(len(attr_names))} for row in reader if field in row['field'] if row['group']=='height_change'+ave}
                    make_dataset(field,field,data,field_attrs,nc,nc.groups[lags['varigrp'][jj]],nctype,dimScale=True)
                    
                    for fld in ['cell_area','delta_h','delta_h_sigma','ice_mask','data_count','misfit_rms','misfit_scaled_rms']:  # fields that can be ave'd but not lagged
                        if kk>0 and (fld.startswith('misfit') or fld=='ice_mask' or fld=='data_count'): # not in ave'd groups
                            break
                        field = fld+ave
                        field_attrs = {row['field']: {attr_names[ii]:row[attr_names[ii]] for ii in range(len(attr_names))} for row in reader if field == row['field'] if row['group']=='height_change'+ave}
                        if fld.startswith('delta_h'):  # fields with complicated name changes
                            data = np.array(lags['file'][jj][dzg][dz_dict[field]]) 
                            for tt in range(data.shape[-1]):
                                data[:,:,tt][np.isnan(cell_area_mask)] = np.nan
                            if fld=='delta_h':  # add group description
                                nc.groups[lags['varigrp'][jj]].setncattr('description',field_attrs[field]['group description'])
                        else:
                            data = np.array(lags['file'][jj][dzg][dz_dict[fld]])
                        if len(data.shape)==3:
                            data = np.moveaxis(data,2,0)  # t, y, x
                        if fld == 'cell_area':
                            data[data==0.0] = np.nan 
                            cell_area_mask = data # where cell_area is invalid, so are delta_h and dhdt variables.

                        make_dataset(field,fld,data,field_attrs,nc,nc.groups[lags['varigrp'][jj]],nctype,dimScale=False)

                else:  # one of the lags
                    field = 'time'+lags['vari'][jj]
                    data = np.array(lags['file'][jj][dzg]['t'])
                    # convert to decimal days from 1/1/2018
                    data = (data-2018.)*365.25
                    field_attrs = {row['field']: {attr_names[ii]:row[attr_names[ii]] for ii in range(len(attr_names))} for row in reader if field in row['field'] if row['group']=='height_change'+ave}
                    make_dataset(field,'time',data,field_attrs,nc,nc.groups[lags['varigrp'][jj]],nctype,dimScale=True)
                    
                    field = 'dhdt'+lags['vari'][jj]+ave
                    data = np.array(lags['file'][jj][dzg][dzg])
                    for tt in range(data.shape[-1]):
                        data[:,:,tt][np.isnan(cell_area_mask)] = np.nan
                    data = np.moveaxis(data,2,0)  # t, y, x
                    field_attrs = {row['field']: {attr_names[ii]:row[attr_names[ii]] for ii in range(len(attr_names))} for row in reader if field in row['field'] if row['group']=='height_change'+ave}
                    make_dataset(field,'dhdt',data,field_attrs,nc,nc.groups[lags['varigrp'][jj]],nctype,dimScale=False)
                    # add group description
                    nc.groups[lags['varigrp'][jj]].setncattr('description',field_attrs[field]['group description'])
                    
                    field = 'dhdt'+lags['vari'][jj]+'_sigma'+ave
                    data = np.array(lags['file'][jj][dzg]['sigma_'+dzg])
                    for tt in range(data.shape[-1]):
                        data[:,:,tt][np.isnan(cell_area_mask)] = np.nan
                    data = np.moveaxis(data,2,0)  # t, y, x
                    field_attrs = {row['field']: {attr_names[ii]:row[attr_names[ii]] for ii in range(len(attr_names))} for row in reader if field in row['field'] if row['group']=='height_change'+ave}
                    make_dataset(field,'dhdt_sigma',data,field_attrs,nc,nc.groups[lags['varigrp'][jj]],nctype,dimScale=False)
                        
            for jj in range(len(lags['file'])):
                try:
                    lags['file'][jj].close()
                except:
                    pass
        
            ncTemplate="atl14_metadata_template.nc"
            write_atl14meta(nc, fileout, ncTemplate, args)

    return fileout
    

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  fromfile_prefix_chars='@')
    parser.add_argument('-b','--base_dir', type=str, default=os.getcwd(), help='directory in which to look for mosaicked .h5 files')
    parser.add_argument('-rr','--region', type=str, help='2-letter region indicator \n'
                                                         '\t AA: Antarctica \n'
                                                         '\t AK: Alaska \n'
                                                         '\t CN: Arctic Canada North \n'
                                                         '\t CS: Arctic Canada South \n'
                                                         '\t GL: Greeland and peripheral ice caps \n'
                                                         '\t IC: Iceland \n'
                                                         '\t SV: Svalbard \n'
                                                         '\t RU: Russian Arctic')
    parser.add_argument('-c','--cycles', type=str, help="4-digit number specifying first/last cycles for output filename")
    parser.add_argument('-R','--Release', type=str, help="3-digit release number for output filename")
    parser.add_argument('-v','--version', type=str, help="2-digit version number for output filename")
    parser.add_argument('-list11','--ATL11_lineage_dir', type=str, help='directory in which to look for ATL11 .h5 filenames')
    parser.add_argument('-tiles','--tiles_dir', type=str, help='directory in which to look for tile .h5 files')
    args, unknown = parser.parse_known_args()
    print('args',args)
    
    def projection_variable(region,group):
        if region in ['AK','CN','CS','GL','IC','SV','RU']:
            crs_var = group.createVariable('Polar_Stereographic',np.byte,())
            crs_var.standard_name = 'Polar_Stereographic'
            crs_var.grid_mapping_name = 'polar_stereographic'
            crs_var.straight_vertical_longitude_from_pole = -45.0
            crs_var.latitude_of_projection_origin = 90.0
            crs_var.standard_parallel = 70.0
            crs_var.scale_factor_at_projection_origin = 1.
            crs_var.false_easting = 0.0
            crs_var.false_northing = 0.0
            crs_var.semi_major_axis = 6378.137
            crs_var.semi_minor_axis = 6356.752
            crs_var.inverse_flattening = 298.257223563
            crs_var.spatial_epsg = '3413'
            crs_var.spatial_ref = 'PROJCS["WGS 84 / NSIDC Sea Ice Polar Stereographic North",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Polar_Stereographic"],PARAMETER["latitude_of_origin",70],PARAMETER["central_meridian",-45],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],AUTHORITY["EPSG","3413"]]'
            crs_var.crs_wkt = ('PROJCS["WGS 84 / NSIDC Sea Ice Polar Stereographic North",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Polar_Stereographic"],PARAMETER["latitude_of_origin",70],PARAMETER["central_meridian",-45],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],AUTHORITY["EPSG","3413"]]')
        elif region == 'AA':
            crs_var = group.createVariable('Polar_Stereographic',np.byte,())
            crs_var.standard_name = 'Polar_Stereographic'
            crs_var.grid_mapping_name = 'polar_stereographic'
            crs_var.straight_vertical_longitude_from_pole = 0.0
            crs_var.latitude_of_projection_origin = -90.0
            crs_var.standard_parallel = -71.0
            crs_var.scale_factor_at_projection_origin = 1.
            crs_var.false_easting = 0.0
            crs_var.false_northing = 0.0
            crs_var.semi_major_axis = 6378.137
            crs_var.semi_minor_axis = 6356.752
            crs_var.inverse_flattening = 298.257223563
            crs_var.spatial_epsg = '3031'
            crs_var.spatial_ref = 'PROJCS["WGS 84 / Antarctic Polar Stereographic",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Polar_Stereographic"],PARAMETER["latitude_of_origin",-71],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["EPSG","3031"]]'
            crs_var.crs_wkt = ('PROJCS["WGS 84 / Antarctic Polar Stereographic",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Polar_Stereographic"],PARAMETER["latitude_of_origin",-71],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["EPSG","3031"]]')
        return crs_var

    fileout = ATL15_write2nc(args)



