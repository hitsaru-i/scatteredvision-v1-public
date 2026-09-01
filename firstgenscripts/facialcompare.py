from PIL import Image
import face_recognition
import os

# Modify these two directories where startdir is your known entities, and compdir is a directory of various faces you wish to match to known
startdir = '/home/USER/Pictures/facestocompare/'
compdir = '/home/USER/Pictures/allthefaces/'

dir = os.walk(startdir)
tolerancesetting = 0.50

totalpositive = 0
totalnegative = 0
print (dir)
for i in dir:
	print (i)
	print ("Starting Directory:	", i[0])
	print ("Using a tolerance settign of "+str(tolerancesetting))
	for j in i[2]:
		positivecounter = 0
		negativecounter = 0
		fullpath = startdir+"/"+j
		print (fullpath)
		sourceimage = face_recognition.load_image_file(fullpath)
		try:
			sourceencoded = face_recognition.face_encodings(sourceimage)[0]
			simage = [sourceencoded]
			print (j)
			print ('''\n''')
			dir2 = os.walk(compdir)
			for x in dir2:
				for file in (x[2]):
					print (file)
					try:
						compimage = compdir+"/"+file
						imagevar = face_recognition.load_image_file(compimage)
						varencoded = face_recognition.face_encodings(imagevar)[0]
						comparison = face_recognition.compare_faces(simage, varencoded, tolerance=tolerancesetting)
						if comparison[0] == True:
							print ("----FACE MATCH---")
							positivecounter +=1
						else:
							print ("No Matching Faces")
							negativecounter += 1
					except Exception as e:
					    print (e)
		except Exception as e:
			print (e)
		print ("Comparison results: "+str(positivecounter)+" positives, "+str(negativecounter)+" negatives")
		totalpositive += positivecounter
		totalnegative += negativecounter
print ('''\n''')
print ("Total Positives: "+str(totalpositive)+"")
print ("Total Negatives: "+str(totalnegative)+"")
total = totalpositive+totalnegative
positivepercent = ((totalpositive/total)*100)
print ("For "+str(positivepercent)+"% positive match.")
print ("At tolerance "+str(tolerancesetting)+"")
