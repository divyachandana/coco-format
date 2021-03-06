#
import glob
import json
from PIL import Image
import datetime
from shapely.geometry import Polygon
import numpy as np
import os
import shutil



INFO = {
    "description": "tree trunk detection",
    "url": "",
    "version": "0.1.0",
    "year": 2020,
    "contributor": "divya_njit",
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
        'name': 'trunk',
        'supercategory': '',
    }
]

# annotations = []




# ---------------------------------------------------------------------------------

def create_image_info(image_id, file_name, image_size,
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

# ---------------------------------------------------------------------------------


# ==================================================================================
def create_annotation_info(annotation_id, image_id, category_info, segmentation,
                               image_size=None, tolerance=2, bounding_box=None):
    try:
        annotation_info=[]
        polygon = Polygon(np.squeeze(segmentation))
        # print("-------")
        # print(type(polygon))
        area =polygon.area
        # print(area)
        original_segmentation = np.concatenate(segmentation)
        segmentation = list(np.concatenate(segmentation))

        # # after padding and subtracting 1 we may get -0.5 points in our segmentation
        bbx =[0 if i < 0 else int(i) for i in list(polygon.bounds)]
        segmentation = [0 if i < 0 else int(i) for i in segmentation]
        # xPoints = original_segmentation[1::2]
        # yPoints = original_segmentation[::2]
        # xmin = int(min(xPoints))
        # ymin = int(min(yPoints))
        # xmax = int(max(xPoints))
        # ymax = int(max(yPoints))
        # width = int(xmax-xmin)
        # height = int(ymax-ymin)
        # bbx = [xmin,ymin,width,height]
        bbx[2] = bbx[2]-bbx[0] +5
        bbx[3] = bbx[3]-bbx[1] +5
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
# ==================================================================================

# ==================================================================================
def polygonToArr(data,id,image_size,annotations):
    # polyPoints = []
    for poly in data:
        singlePolyPoints = []
        # print(data["polygon"])
        i = False
        firstPoint = []
        for p in poly["polygon"]:
            if i==False: 
                firstPoint.append(p["x"])
                firstPoint.append(p["y"])
                i = True       
            point = []
            point.append(p["x"])
            point.append(p["y"])        
            singlePolyPoints.append(point)  
        # singlePolyPoints.append(firstPoint)      
        # polyPoints.append(singlePolyPoints)
        category_info ={'id':1,"is_crowd":0}
        # create annotation
        if(len(annotations)==0):
            newid = 1
        else :
            newid = annotations[-1]["id"]+1
        annotations.append(create_annotation_info(newid,id,category_info,singlePolyPoints,image_size))
    # return polyPoints

# ---------------------------------------------------------------------------------
def getjson(filenames,name,annotations,id,folder):
    # annotations = annotate
    # print(filenames)
    coco_output = {
                "info": INFO,
                "licenses": LICENSES,
                "categories": CATEGORIES,
                "images": [],
                "annotations": []
            }
    images = []
    for file in filenames:
        id+=1
        with open(file) as f:
            data = json.load(f)
            # print(file)
            if(not 'file' in data): continue
            file_name = "a/"+data["file"]
            # shutil.copy(file_name, folder)
            im = Image.open(file_name)
            image_size = im.size
            # id = data["_id"]
            img = create_image_info(id, data["file"], image_size)
            images.append(img)
            polygonToArr(data["objects"],id,image_size,annotations)
    coco_output["images"] = images
    coco_output["annotations"] = annotations
    # print(coco_output)
    out_file = open(name+".json", "w")      
    json.dump(coco_output, out_file, indent = 4)      
    out_file.close() 
# ---------------------------------------------------------------------------------

filenames = glob.glob('a/output/*.json')
length = len(filenames)
testing = filenames[0:int(length/4)]
training = filenames[int(length/4):length]
# training = filenames[0:int(length/4)]
print(length)
print(len(training))
print(len(testing))
annotate1 = []
annotate2 = []
id1 = 1000
id2 = 100000
imagesFolder1 = "train"
imagesFolder2 = "test"
getjson(training,"train",annotate1,id1,imagesFolder1)
getjson(testing,"test",annotate2,id2,imagesFolder2)
