## Facial recognition based script to delete all image files that face_recognition CAN NOT detect a face in from a recurrsive directory.

from PIL import Image
import face_recognition
import os
import shutil

dirlist = []
# Starting directory location- CHANGE THIS for your use
startdir = '/home/user/Pictures'
dir = os.walk(startdir)




for i in dir:
	savepred = ''
#	print ("---Directory")
	directory = i[0]
#	print (directory)
	dirpath = (directory.split('/'))
	upperdir = dirpath[len(dirpath)-1]
	dirlen = (len(dirpath))
	if dirlen >=  8:
		filedirs = (dirpath[7:])
		for z in filedirs:
			savepred += z
			savepred += '-'
#		print ("----savepred:")
#		print (savepred)
#	print ("----dirlen")
#	print (dirlen)
#	print ("---upperdir")
#	print (upperdir)
#	print ('<----------------------------------------------------------------------->')
#	print ('Files Within')
	for x in i[2]:
		try:
#			print (x)
			absolutepath = ""+directory+"/"+x+""
#			print ("--directory")
#			print (directory)
			filename = savepred+x
#			print (filename)
			if '.git' not in absolutepath:
#				print (absolutepath)
					# Load the jpg file into a numpy array
				image = face_recognition.load_image_file(absolutepath)
# Find all the faces in the image using the default HOG-based model.
# This method is fairly accurate, but not as accurate as the CNN model and not GPU accelerated.
# See also: find_faces_in_picture_cnn.py
				face_locations = face_recognition.face_locations(image)
#			print face_locations
				faces= (len(face_locations))
#				print("I found {} face(s) in this photograph.".format(len(face_locations)))
				for face_location in face_locations:
    # Print the location of each face in this image
					top, right, bottom, left = face_location
#					print("A face is located at pixel location Top: {}, Left: {}, Bottom: {}, Right: {}".format(top, left, bottom, right))

    # You can access the actual face itself like this:
					face_image = image[top:bottom, left:right]
    	#				pil_image = Image.fromarray(face_image)
	#			pil_image.show()
				if faces < 1:
					print ("NO FACES FOUND IN IMAGE.")
#					print ("ABSOLUTE PATH:")
					print (absolutepath)
					print ("FILENAME:")
					print (filename)
					if os.path.exists(absolutepath):
						os.remove(absolutepath)
						print (f"FILE '{absolutepath}' has been deleted.")
					else:
						print(f"Error: The File '{absolutepath}' does not exist")
		except Exception as e: print (e)
		print ("______________________________________________________________")
