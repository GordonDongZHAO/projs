#-*-coding:utf-8-*-
import json
import urllib
import urllib2
import base64

import glob as gb

url='http://localhost:8002/analytics'
#url='http://39.105.82.189:8002/analytics'

def get(args):
	s = url + '?args''='+args
	print s
	req = urllib2.Request(s)
	return urllib2.urlopen(req).read()

def post(args):
	data = {}
	data['fromdevice'] = "PC"
	data['clientip'] = "10.1.1.1"
	data['imagetype'] = "jpg"
	data['reg_img'] = 0
	data['args'] = args

	data['image'] = base64.b64encode(img)
	print "data ready!"

	coded_data = urllib.urlencode(data)
	print "data encoded!"

	req = urllib2.Request(url, data = coded_data)
	req.add_header("Content-Type","application/x-www-form-urlencoded")
	print "header added!"

	try:
		resq = urllib2.urlopen(req)
		content = resq.read()
		print content
		print "response  obtained!"

	except urllib2.HTTPError,e:
	    print e.code
	    print e.reason
	    print e.geturl()
	    print e.read()

if __name__ == '__main__':

	img_path = gb.glob(r"/home/proj_img_search/tu_sou_suo/tuku/*.jpg")

	for path in img_path:
		print "start...."
		print path
		file_object=open(path,'rb')
		img = file_object.read()
		file_object.close()
		
		post('1')
		raw_input()







