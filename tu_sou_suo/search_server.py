#-*-coding:utf-8-*-
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.gen
import tornado.httpclient
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor

import urllib
import urlparse
import json
import datetime
import subprocess
import time
import os
import sys

#import traceback

from tornado.options import define,options

os.chdir(os.getcwd())
sys.path.append('.')

import darknet as dn
import pdb
import base64

import numpy as np
import pandas as pd

define("port", default=8002, help="run on given port", type = int)

#dn.set_gpu(0)
net = dn.load_net("core/e.cf", "core/e.w", 0)
#meta = dn.load_meta("cfg/coco.data")


def diff_file_name(filename):
    #fname="/home/tu_sou_suo/tuku/"+now+r"_0.jpg"
    if os.path.exists(filename):
        f= filename.split("_")[0:-2]
        n = int(filename.split("_")[-1].split(".")[0])
        f_name = f+"_"+str(n+1)+".jpg"
        print "file:%s exists..." %(f_name)
        diff_file_name(f_name)
    else:
        print "file %s not exist" %(filename)
        return filename

def calc_dist_func(ff1, ff2):
    f1 = ff1

    ff2 = ff2.split("[")[1].split("]")[0].split(",")
    f2 = [float(s) for s in ff2]

    cos_dist = np.dot(f1, f2) / (np.linalg.norm(f1) * np.linalg.norm(f2))
    return round(cos_dist, 3)

pd.set_option('max_colwidth', 200000)
features_df = pd.read_csv("core/i_f.csv", header=0, sep=',')
#print features_df.describe()
def search_bank(in_feature):
    print "start search"
    #print in_feature[0:100]
    dist_df = pd.DataFrame(columns=["img_name","distance"])
    global features_df
    dist_df["img_name"] = features_df["img_name"]

#    print features_df["feature"][0][0:100]
#    print features_df["feature"][1][0:100]
    #global calc_dist
    global calc_dist_func
    calc_dist = lambda x: calc_dist_func(in_feature, x)
    dist_df["distance"] = features_df["feature"].apply(calc_dist)

    #print dist_df.describe()
    dist_df.sort_values(by="distance", ascending=False, inplace=True)

    ret=""
    for i in xrange(3):
        ret += "["+dist_df.iloc[i]['img_name']+","+str(dist_df.iloc[i]['distance'])+"]"
	
    print "search finished!"
    return ret
	
def det_img(img, length):

    im = dn.load_mem_image(img, length, 0, 0, 3)
    #im = dn.load_image(fname, 0, 0)
    #print im.w,im.h,im.c
    if (im.w == 0) or (im.h == 0) or (im.c == 0):
        return []
    r = dn.extract(net, im)
    #r = dn.detect(net, meta, fname)#D:/workspace/alex_darknet_180628/build/darknet/x64/
    #r = dn.detect_mem(net, meta, img, length)
    dn.free_image(im)
    #print type(r)#,len(r)
    print "extract finished!"
    return r

class hiveHandler(tornado.web.RequestHandler):
    executor = ThreadPoolExecutor(2)
    @tornado.web.asynchronous
    def get(self):
        self.__do()
    @tornado.web.asynchronous
    def post(self):
        self.__do()

    @tornado.gen.engine
    def __do(self):
        dec_data = ''
        self.set_header("Content-Type","application/json");
        if self.request.method == "POST":
            body = self.request.body

            query = urlparse.parse_qs(body)
            args_str = query.get("args", [""])[0]
            print "args:"
            print (args_str)

            print("from device:")
            print self.get_body_arguments("fromdevice",None)[0].encode('utf-8')
            print("image type:")
            print self.get_body_arguments("imagetype",None)[0].encode('utf-8')
            print("image reg_img:")
            global bReg_img
            bReg_img =  int(self.get_body_arguments("reg_img",None)[0])
            #print int(bReg_img) + 19, type(reg_img)    

            img_data = self.get_body_arguments("image",None)[0].encode('utf-8')
            
            dec_data = base64.b64decode(img_data)
            
            global fname
            now = time.strftime("%Y-%m-%d-%H_%M_%S",time.localtime(time.time())) 
            if bReg_img == 1:
                fname = diff_file_name("/home/proj_img_search/tu_sou_suo/tuku/"+now+r"_0.jpg")
            else:
                fname = diff_file_name("/home/proj_img_search/img_s/"+now+r".jpg")
            print fname
            rcv_img = open(fname,'wb')
            rcv_img.write(dec_data)
            rcv_img.close()
            print "received image saved!"
        elif self.request.method == "GET" or (self.request.method == "POST" and \
                                                self.request.headers.get("Content-Type","")\
                                                == "application/x-www-form-urlencoded"):
            args_str = self.get_argument("args","")
        try:
            if args_str <> "":
                args_dict = json.loads(args_str,'utf-8')
                result_data = yield self.getData(args_dict, dec_data, len(dec_data))
                result_data = json.dumps(result_data)
                print "result:"
                print result_data
        
                if result_data:
                    self.write(str(result_data))
                else:
                    self.write("wrong script.")
                self.finish()
            else:
                self.write("pleas type args")
        except:
            self.write(str(sys.exc_info()))
            self.write("please type correct args")

    @run_on_executor
    def getData(self, args, buf, length):
        feature = det_img(buf, length)
        if type(feature)==list and len(feature) == 1000:
            global bReg_img
            if bReg_img == 1:
                print "start to register image..."
                reg_name = fname.split("/")[-1]
                print reg_name
                global features_df
                #print features_df["img_name"].tail(3)
                #print len(features_df)
                features_df.loc[len(features_df)] = (reg_name, feature)
                #print features_df["img_name"].tail(3)
                #print len(features_df)
                dn.append_feature_to_bank(reg_name, feature)
                return "image %s registration OK!" %(reg_name)
            else:
                result = search_bank(feature)
                return result
        else:
            return "data error"

class HttpServerWrapper(object):
    def __init__(self, port):
        self.port = port
        self.handlers = []
    
    def register(self):
        self.handlers.append((r'/analytics',hiveHandler))
    
    def run(self):
        print "server start...!"
        tornado.options.parse_command_line()
        app = tornado.web.Application(handlers=self.handlers)
        http_server = tornado.httpserver.HTTPServer(app)
        http_server.listen(self.port)
        tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    web_obj = HttpServerWrapper(options.port)
    web_obj.register()
    web_obj.run()




