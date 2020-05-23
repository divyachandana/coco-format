from osgeo import gdal, gdalnumeric, ogr, gdal_array
import sys
sys.path.append(r'C:\Program Files\GDAL')


# import ogr
# import gdal_array
from skimage import measure
import numpy as np
import json
import os
import datetime
from shapely.geometry import Polygon


# get all the fillpath in the directory  include sub-directory
def getfilepath(curDir, filelist, ext=('.TIF', '.tif')):
    if os.path.isfile(curDir):
        if curDir.lower().endswith(ext):
            filelist.append(curDir)
    else:
        dir_or_files = os.listdir(curDir)
        for dir_file in dir_or_files:
            dir_file_path = os.path.join(curDir, dir_file)

            # check is file or directory
            if os.path.isdir(dir_file_path):
                getfilepath(dir_file_path, filelist, ext)
            else:
                # extension_ = dir_file_path.split('.')[-1]
                # if (extension_.lower() in ext):

                if dir_file_path.endswith(ext):
                    filelist.append(dir_file_path)

#
def raster2array(rasters,band_no=1):
    """
    Arguments:
    rast            A gdal Raster object
    band_no         band numerical order

    Example :
    raster = gdal.Open(rasterfn)
    raster2array(raster,1)
    """
    bands = rasters.RasterCount
    if band_no>0 and band_no <=bands:
        band = rasters.GetRasterBand(band_no)
        array = band.ReadAsArray()
    else:
        array = rasters.ReadAsArray()

    return array

# This function will convert the rasterized clipper shapefile
# to a mask for use within GDAL.
def imageToArray(i):
    """
    Converts a Python Imaging Library array to a
    gdalnumeric image.
    """
    a=gdalnumeric.fromstring(i.tobytes(),'b')
    a.shape=i.im.size[1], i.im.size[0]
    return a

#
def coord2pixelOffset(geotransform, x, y):
    """
    Arguments:
    geotransform            A gdal transform object
    x               world coordinate x
    y               world coordinate y
    return  pixel position in image

    Example :
    raster = gdal.Open(rasterfn)
    geotransform = raster.GetGeoTransform()
    coord2pixel(geotransform,xCoord,yCoord)
    """

    #left top
    originX = geotransform[0]
    originY = geotransform[3]

    #pixel resolution
    pixelWidth = geotransform[1]
    pixelHeight = geotransform[5]

    #ax rotate (here not used)
    rotateX = geotransform[2]
    rotateY = geotransform[4]


    xOffset = int((x - originX) / pixelWidth)
    yOffset = int((y - originY) / pixelHeight)
    return xOffset, yOffset

#
def pixeloffset2coord(geoTransform,pixel_xOffset,pixel_yOffset):
    """
    geoTransform: a gdal geoTransform object
    pixel_xOffset:
    pixel_yOffset:
    return:  coords
    """

    #left top
    originX = geoTransform[0]
    originY = geoTransform[3]

    #pixel resolution
    pixelWidth = geoTransform[1]
    pixelHeight = geoTransform[5]


    # calculate coordinates
    coordX = originX+ pixelWidth*pixel_xOffset
    coordY = originY+pixelHeight*pixel_yOffset

    return coordX,coordY


INFO = {
    "description": "sidewalk test Dataset",
    "url": "",
    "version": "0.1.0",
    "year": 2019,
    "contributor": "czh_njit",
    "date_created": datetime.datetime.utcnow().isoformat(' ')
}

LICENSES = [
    {
        "id": 1,
        "name": "Attribution-NonCommercial-ShareAlike License",
        "url": "http://creativecommons.org/licenses/by-nc-sa/2.0/"
    }
]

CATEGORIES = [
    {
        'id': 1,
        'name': 'sidewalk',
        'supercategory': '',
    },
    # {
    #     'id': 2,
    #     'name': 'background',
    #     'supercategory': '',
    # },
]


class czhTiff2Json():
    """
       create annotation file from tiff file,used for satellite image or aerial image object detection/instance segmentation

    """
    def __init__(self,tifFns,lbltiffPath,jsonFn,shpFn="",mode=0):
        """
        geotiff?
        Arguments:
        tifFn: tif file name or path (in)
        jsonFn:json file name (out)
        shpFn: shapefile name (in)
        mode: two ways to get json file,one get from tiff file ,another from shape file
        """
        self.tifFns = tifFns
        self.lbltiffPath = lbltiffPath
        self.jsonFn = jsonFn
        self.mode = mode
        if mode ==1 :
            self.shpFn = shpFn





    def createJson(self):
        if self.mode ==1:
            self.createJsonFromShape()
        else:
            self.createJsonFromTiffs()

    def createJsonFromShape(self):
        pass

    def createJsonFromTiffs(self):

        #check  self.tifFns  if it's file open or traverse directory
        #no directory nest?
        lstTiff=[]
        if os.path.isdir(self.tifFns):
            getfilepath(self.tifFns, lstTiff)
        elif os.path.isfile(self.tifFns):
            # self.createJsonFromTiffFile(self.tifFns)
            lstTiff.append(self.tifFns)
        else:
            print("input path or directory is error!")

        if len(lstTiff)>0:
            print(lstTiff)
            self.createJsonFromTiffFiles(lstTiff)


    def createJsonFromTiffFiles(self,tiffFns):
        #check json if exist open else create
        # open json
        if os.path.exists(self.jsonFn):
            self.coco_output = json.load(self.jsonFn)
        else:
            self.coco_output = {
                "info": INFO,
                "licenses": LICENSES,
                "categories": CATEGORIES,
                "images": [],
                "annotations": []
            }

        annotation_idx =1
        for img_idx,tiffn in enumerate(tiffFns):
            self.createJsonFromTiffFile(tiffn,img_idx+1,1,annotation_idx+10000*img_idx)

        with open(self.jsonFn, 'w') as output_json_file:
            json.dump(self.coco_output, output_json_file)

    def createJsonFromTiffFile(self,tiff_filepath,img_idx,band_no=1,annotation_idx=1):

        print("Processing: ", tiff_filepath)

        rasters = gdal.Open(tiff_filepath)
        raster_array = raster2array(rasters,band_no)

        #get size of image
        img_Width = rasters.RasterXSize
        img_Height = rasters.RasterYSize
        img_size = [img_Width,img_Height]

        #create image_info
        tiff_filepath = os.path.join(self.lbltiffPath, os.path.basename(tiff_filepath))

        image_info = self.create_image_info(img_idx,tiff_filepath,img_size)
        self.coco_output["images"].append(image_info)

        # create annotation
        polygons = self.binaryMask2Polygon(raster_array)

        for idx,polygon in enumerate(polygons):
            # print(type(polygon), polygon.size)
            if polygon.size > 7:
                category_info ={'id':1,"is_crowd":0}
                annotatin_info =self.create_annotation_info(idx+annotation_idx,img_idx,category_info,polygon,img_size)
                self.coco_output["annotations"].append(annotatin_info)


    def binaryMask2Polygon(self,binaryMask):
        polygons =[]

        padded_binary_mask = np.pad(binaryMask, pad_width=1, mode='constant', constant_values=0)
        contours = measure.find_contours(padded_binary_mask,0.5)
        contours = np.subtract(contours, 1)

        def closeContour(contour):
            if not np.array_equal(contour[0], contour[-1]):
                contour = np.vstack((contour, contour[0]))
            return contour

        for contour in contours:
            contour = closeContour(contour)
            contour = measure.approximate_polygon(contour, 1)

            if len(contour)<3:
                continue
            contour = np.flip(contour,axis =1)
            # segmentation = contour.ravel().tolist()
            #
            # # after padding and subtracting 1 we may get -0.5 points in our segmentation
            # segmentation = [0 if i < 0 else i for i in segmentation]
            # polygons.append(segmentation)
            polygons.append(contour)
        return polygons

    def create_image_info(self,image_id, file_name, image_size,
                          date_captured=datetime.datetime.utcnow().isoformat(' '),
                          license_id=1, coco_url="", flickr_url=""):

        image_info = {
            "id": image_id,
            "file_name": file_name,
            "width": image_size[0],
            "height": image_size[1],
            "date_captured": date_captured,
            "license": license_id,
            "coco_url": coco_url,
            "flickr_url": flickr_url
        }

        return image_info


    def create_annotation_info(self,annotation_id, image_id, category_info, segmentation,
                               image_size=None, tolerance=2, bounding_box=None):
        try:
            polygon = Polygon(np.squeeze(segmentation))
            # print(type(polygon))
            area =polygon.area

            segmentation = segmentation.ravel().tolist()

            # # after padding and subtracting 1 we may get -0.5 points in our segmentation
            bbx =[0 if i < 0 else int(i) for i in list(polygon.bounds)]
            segmentation = [0 if i < 0 else int(i) for i in segmentation]

            annotation_info = {
                "id": annotation_id,
                "image_id": image_id,
                "category_id": category_info["id"],
                "iscrowd": category_info["is_crowd"],
                "area": area,
                "bbox": bbx,
                "segmentation": [segmentation],
                "width": image_size[0],
                "height": image_size[1],
            }
        except Exception as e:
            print("Error in create_annotation_info():", e)

        return annotation_info


# test = czhTiff2Json("D:\\2019\\njit learning\\201909\\sidewalk extract\\czhSidewalkExtract\\val\\label","D:\\2019\\njit learning\\201909\\sidewalk extract\\czhSidewalkExtract\\val\\images\\","D:\\2019\\njit learning\\201909\\sidewalk extract\\czhSidewalkExtract\\val\\label\\sidewalk_val.json")
test = czhTiff2Json(r"L:\NewYorkCity_sidewalks\COCO\Train256\Labels", r"L:\NewYorkCity_sidewalks\COCO\Train256\Images", r"L:\NewYorkCity_sidewalks\COCO\Train256\sidewalk_train.json")
test.createJson()

