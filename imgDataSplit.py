import cv2
import math
import os
from PIL import Image,ImageDraw
import czhUtils
import torch
import torch.utils.data as data
import torch.nn.functional as F

class CzhSideWalkCOCODataset(data.Dataset):
    def __init__(self):
        # super.__init__()
        pass

#
class tiffCropandMerge():
    """
    reference to : http://karthur.org/2015/clipping-rasters-in-python.html
    """
    def __init__(self,inputPath,outputPath):
        self.inputPath = inputPath
        self.outputPath = outputPath

    def setOutputPath(self,outputPath):
        self.outputPath = outputPath


    def cropImages(self,xRange,yRange,padding,out_bands=[]):
        """

        :param prefix_output:
        :param xRange:
        :param yRange:
        :param padding: overlap
        :param out_bands:
        :return:
        """
        czhUtils.gdal.UseExceptions()

        #get images in inputPath
        imgFiles =[]
        czhUtils.getfilepath(self.inputPath,imgFiles)
        cnt = 0
        if len(imgFiles)>0:
            for imgFilePath in imgFiles:
                cnt += 1
                print("Processing: {} / {}, {}".format(cnt, len(imgFiles), imgFilePath))
                rasters = czhUtils.gdal.Open(imgFilePath)
                srcArray = czhUtils.gdalnumeric.LoadFile(imgFilePath)
                img_Width = rasters.RasterXSize
                img_Height = rasters.RasterYSize
                geoTrans = rasters.GetGeoTransform()

                #get full path of file without ext
                filename,fileext = os.path.splitext(os.path.basename(imgFilePath))

                #origin point world coordinate
                # originX = geoTrans[0]
                # originY = geoTrans[3]

                h0,w0 =0,0
                col,row = 1,1
                while (h0<img_Height):
                    while(w0<img_Width):
                        #recalculate originX and originY
                        # originX,originY = czhUtils.pixeloffset2coord(geoTrans,w0,h0)
                        #crop image
                        # clip, pixel_ul_x, pixel_ul_y, geoTrans2 = self.cropImage(rasters,srcArray,originX,originY,xRange,yRange,out_bands)
                        clip, pixel_ul_x, pixel_ul_y, geoTrans2 = self.cropImage(rasters, srcArray, w0, h0,xRange, yRange, out_bands)
                        #save image
                        # rasterOutputPath = czhUtils.os.path.join(self.outputPath,filename +"_{}_{}".format(row,col)+fileext)
                        rasterOutputPath = czhUtils.os.path.join(self.outputPath,filename + "_{}_{}".format(row, col))

                        self.saveCropImage(rasters,clip,rasterOutputPath,pixel_ul_x,pixel_ul_y,geoTrans2)
                        #moving window along x-axil
                        w0 =w0+xRange-padding
                        col = col+1

                    #moving window alogn y_axil
                    h0 = h0+yRange-padding
                    w0=0
                    col=1
                    row =row+1

    def cropImage(self,rasters,srcArray,originX,originY,xRange,yRange,out_bands=[]):
        czhUtils.gdal.UseExceptions()

        #get source data's data type
        srcDataType = czhUtils.raster2array(rasters).dtype
        band_nums = rasters.RasterCount

        geoTrans = rasters.GetGeoTransform()

        imgWidth = rasters.RasterXSize
        imgHeight = rasters.RasterYSize
        # pixel resolution
        pixelWidth = geoTrans[1]
        pixelHeight = geoTrans[5]

        # pixel_ul_x,pixel_ul_y = czhUtils.coord2pixelOffset(geoTrans,originX,originY)
        pixel_ul_x, pixel_ul_y = originX,originY
        #check current crop image whether extend source image extent
        #if extend then adjust xRange or yRange
        if pixel_ul_x+xRange>imgWidth:
            # xRange = imgWidth-pixel_ul_x
            pixel_ul_x = imgWidth-xRange



        if pixel_ul_y+yRange>imgHeight:
            # yRange= imgHeight-pixel_ul_y
            pixel_ul_y = imgHeight - yRange


        outImage_pixel_width = xRange  #abs(int(xRange/pixelWidth))
        outImage_pixel_height =yRange  # abs(int(yRange/pixelHeight))

        # pixel_lr_x,pixel_lr_y = czhUtils.coord2pixelOffset(geoTrans,originX+xRange*pixelWidth,originY+yRange*pixelHeight)
        pixel_lr_x, pixel_lr_y = pixel_ul_x+xRange,pixel_ul_y+yRange

        if len(out_bands) == 0 :
            clip_bands =[_ for _ in range(band_nums)]
        else:
            clip_bands = [band - 1 for band in out_bands]

        # Multi-band image?
        try:
            clip = srcArray[clip_bands, pixel_ul_y:pixel_lr_y, pixel_ul_x:pixel_lr_x]

        # Nope: Must be single-band
        except IndexError:
            clip = srcArray[ pixel_ul_y:pixel_lr_y, pixel_ul_x:pixel_lr_x]

        # clip = srcArray[clip_bands, pixel_ul_y:pixel_lr_y, pixel_ul_x:pixel_lr_x]

        #create rectangle for mask
        # poly = czhUtils.pixelrect2georect()
        pixels=[]
        pixels.append((pixel_ul_x,pixel_ul_y))
        pixels.append((pixel_lr_x,pixel_ul_y))
        pixels.append((pixel_lr_x,pixel_lr_y))
        pixels.append((pixel_ul_x,pixel_lr_y))
        # pixels.append((pixel_ul_x,pixel_ul_y))

        rasterRect = Image.new("L", (outImage_pixel_width, outImage_pixel_height), 0)
        # mask = czhUtils.imageToArray(rasterRect)
        rasterize = ImageDraw.Draw(rasterRect)
        rasterize.polygon(pixels,0)
        mask = czhUtils.imageToArray(rasterRect)

        # Create a new geomatrix for the image
        geoTrans2 = list(geoTrans)
        originX, originY = czhUtils.pixeloffset2coord(geoTrans, pixel_ul_x, pixel_ul_y)

        geoTrans2[0] = originX
        geoTrans2[3] = originY

        # print(clip.shape)
        # print(mask.shape)
        # Clip the image using the mask
        clip = czhUtils.gdalnumeric.choose(mask,(clip, -9999)).astype(srcDataType)#

        rasterRect = None
        rasterize = None
        return clip,pixel_ul_x,pixel_ul_y,geoTrans2

    def saveCropImage(self,rasters,clip,rasterOutputPath,pixel_ul_x,pixel_ul_y,geoTran=None):#rasterInputPath
        # gtiffDriver = czhUtils.gdal.GetDriverByName('GTiff')
        # if gtiffDriver is None:
        #     raise ValueError("Can't find GeoTiff Driver")

        # ds = czhUtils.gdal.Open(czhUtils.gdalnumeric.GetArrayFilename(clip))
        ds = czhUtils.gdal_array.OpenArray(clip)
        #
        czhUtils.gdalnumeric.CopyDatasetInfo(rasters, ds, xoff=pixel_ul_x, yoff=pixel_ul_y)
        if geoTran is not None:
            ds.SetGeoTransform(geoTran)
        #prototyp can by dataset or str format
        rastersFilepath = rasterOutputPath +".tif"
        rastersTfwFile= rasterOutputPath +".tfw"

        if czhUtils.os.path.exists(rastersFilepath):
            czhUtils.os.remove(rastersFilepath)

        if czhUtils.os.path.exists(rastersTfwFile):
            czhUtils.os.remove(rastersTfwFile)

        # czhUtils.gdalnumeric.SaveArray(clip, rasterOutputPath, format="GTiff", prototype=rasters)
        czhUtils.gdalnumeric.SaveArray(clip, rastersFilepath, format="GTiff", prototype=rasters)
        with open(rastersTfwFile,'wt') as TfwFile:
            if geoTran is not None:
                TfwFile.write("%0.10f\n" % geoTran[1])
                TfwFile.write("%0.10f\n" % geoTran[2])
                TfwFile.write("%0.10f\n" % geoTran[4])
                TfwFile.write("%0.10f\n" % geoTran[5])
                TfwFile.write("%0.10f\n" % geoTran[0])
                TfwFile.write("%0.10f\n" % geoTran[3])
            TfwFile.close()

    #maybe exist error in understanding  padding  so here padding always be zero
    # def mergeImages(self,image_dic,out_dic,t_w,t_h,n_w,n_h,padding=0,overlap=0):
    def mergeImages(self, image_dic, out_dic, t_w, t_h, n_w, n_h,  overlap=0):
        pngs =[]
        #（filename ,row ,col)
        fileSplits =[]
        pathSplits =[]

        czhUtils.getfilepath(image_dic,pngs,('png','PNG'))
        for png in pngs:
            png_base,_ = czhUtils.os.path.splitext(czhUtils.os.path.basename(png))
            png_path = czhUtils.os.path.dirname(png)
            fileSplits.append(png_base.split('_'))
            pathSplits.append(png_path)

        #loop fileSplits
        fileNames = czhUtils.getUniqueValue(fileSplits,1)

        #bug if n_w/t_w or n_h/t_h is exactly divisible
        # if (n_w+2*padding) % t_w ==0:
        if (n_w-overlap)%(t_w-overlap)==0:
            # maxRows = math.floor((n_w+padding)/t_w)
            maxRows = math.floor((n_w-overlap)/(t_w-overlap))
        else:
            # maxRows = math.floor((n_w+padding)/t_w)+1
            maxRows = math.floor((n_w - overlap) / (t_w - overlap)) + 1

        # if (n_h+2*padding)%t_h ==0:
        if (n_h - overlap) / (t_h - overlap)==0:
            # maxCols = math.floor((n_h+padding)/t_h)
            maxCols = math.floor((n_h - overlap) / (t_h - overlap))
        else:
            # maxCols = math.floor((n_h+padding)/t_h)+1
            maxCols = math.floor((n_h - overlap) / (t_h - overlap)) + 1

        for filename in fileNames:
            #reconstruct image
            #calculate rows and colsl
            rows = max([int(filesplit[1]) for filesplit in fileSplits if filesplit[0]==filename])
            cols = max([int(filesplit[2]) for filesplit in fileSplits if filesplit[0] == filename])
            bStart = True
            #topleft point
            # cur_l = 0
            # cur_t = 0

            for row in range(rows):
                # cur_l=padding
                cur_l = 0
                if row ==0:
                    # img_t = padding  #tile image
                    img_t =0
                    cur_t = 0
                else:
                    # get image data in roi
                    cur_t = cur_t + t_h - img_t
                    if cur_t + t_h - img_t > n_h:
                        img_t = imgH - n_h + cur_t
                    else:
                        img_t = overlap

                for col in range(cols):
                    #check file exist
                    #get image width and height
                    try:
                        idx = fileSplits.index([filename,str(row+1),str(col+1)])
                    except:
                        idx =-1
                    if idx != -1 :
                        png_path = pathSplits[idx]+"\\"+"{}_{}_{}.png".format(filename,row+1,col+1)
                        img = cv2.imread(png_path)
                        imgH = img.shape[0]
                        imgW = img.shape[1]
                        assert imgH == t_h
                        assert imgW == t_w

                        channels=img.shape[2]
                        dType = img.dtype
                        if bStart:
                            dst = czhUtils.np.zeros((n_h,n_w,channels),dtype=dType)
                            bStart = False

                        #calculate actual valid image left top point
                        if col ==0:
                            # img_l = padding
                            img_l = 0
                        else:
                            #get image data in roi
                            cur_l = cur_l + t_w - img_l
                            if cur_l +t_w-img_l>n_w:
                                img_l = imgW-n_w+cur_l
                            else:
                                img_l = overlap
                        roi = img[img_t:imgH,img_l:imgW,:]
                        dst[cur_t:cur_t+imgH-img_t,cur_l:cur_l+imgW-img_l] =roi

            #write image file if possible export tif with tfw file.
            cv2.imwrite(out_dic+"\\"+filename+".tif",dst)


    def rasters2vector(self,srcFilePath,rasterPath):
        # czhUtils.geoReferenceImage()
        pass

def main():
    # import glob, os
    #
    # def rename(dir, pattern, titlePattern):
    #     for pathAndFilename in glob.iglob(os.path.join(dir, pattern)):
    #         title, ext = os.path.splitext(os.path.basename(pathAndFilename))
    #         os.rename(pathAndFilename,
    #                   os.path.join(dir, titlePattern % title + ext))
    #
    # rename()
    outputImageDirectory = r'L:\NewYorkCity_sidewalks\COCO\Test256\classified_padding10_432_2\merged'
    if not czhUtils.os.path.exists(outputImageDirectory):
        czhUtils.os.makedirs(outputImageDirectory)


    # outputLabelDirectory = czhUtils.os.getcwd()+"\\train\\sidewalk_annotations2"
    # if not czhUtils.os.path.exists(outputLabelDirectory):
    #     czhUtils.os.makedirs(outputLabelDirectory)
    #
    # outputvalImageDirectory = czhUtils.os.getcwd()+"\\val\\images2"
    # if not czhUtils.os.path.exists(outputvalImageDirectory):
    #     czhUtils.os.makedirs(outputvalImageDirectory)
    #
    #
    # outputvalLabelDirectory = czhUtils.os.getcwd()+"\\val\\label2"
    # if not czhUtils.os.path.exists(outputvalLabelDirectory):
    #     czhUtils.os.makedirs(outputvalLabelDirectory)

    # tcmImage= tiffCropandMerge(r"L:\NewYorkCity_sidewalks\Images\Train", outputImageDirectory)
    # tcm.cropImage("F:\\2019\\NewYorkCity_sidewalks\\Images\\0.TIF","test1",913316.0,125170.0,512,512,[1,2,3,4]) #125170-512
    # tcmImage.cropImages(256,256,0,[4,3,2])

    # tcmlabel = tiffCropandMerge("F:\\2019\\NewYorkCity_sidewalks\\\sidewalks\\0.TIF",outputLabelDirectory)
    # tcmlabel.cropImages(256,256, 0)
    #
    # tcmvalImage= tiffCropandMerge("F:\\2019\\NewYorkCity_sidewalks\\Images\\4.TIF",outputvalImageDirectory)
    # # tcm.cropImage("F:\\2019\\NewYorkCity_sidewalks\\Images\\0.TIF","test1",913316.0,125170.0,512,512,[1,2,3,4]) #125170-512
    # tcmvalImage.cropImages(256,256,0,[4,3,2])
    #
    # tcmvallabel = tiffCropandMerge("F:\\2019\\NewYorkCity_sidewalks\\\sidewalks\\4.TIF",outputvalLabelDirectory)
    # tcmvallabel.cropImages(256, 256, 0)

if __name__ == "__main__":
    main()
    # tcmImage= tiffCropandMerge("D:\sidewalk\yolact\Images_data","D:\sidewalk\yolact\Images_data")
    # tcmImage.mergeImages(tcmImage.outputPath,tcmImage.outputPath,550,550,5000,5000)

    # srcFile ="F:\\2019\\NewYorkCity_sidewalks\\sidewalks\\0.TIF"
    # rasterFile="D:\\2019\\njit learning\\201909\\sidewalk_train_test_data\\0.tif"
    # vecFile=".\\shape\\0"
    #
    # czhUtils.geoReferenceImage(srcFile,rasterFile)
    # czhUtils.Raster2VectorLayer(rasterFile,vecFile)

    pass

