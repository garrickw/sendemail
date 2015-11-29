#!/usr/bin/env python 
# _*_ coding: utf8 _*_

import pickle
import os
import argparse
import smtplib 
import zipfile
import tempfile
from email.header import Header   
from email import encoders
from email.mime.text import MIMEText 
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart



#SENDER_INFO is used to save the information about the sender so that we can use it in the function emial_dir_zepped   
SENDER_INFO = {}


def get_user_info(username=None):
	with open('/home/garrick/python/smtp.conf','r') as f:
		users = pickle.load(f)

	if not username:                   #use default user
		user,postfix = users['default'].split('@')
		password = users[users['default']]
	elif username in users:                                #use a  specific user
		user,postfix = username.split('@')
		password = users[username]
	else :                                   #can't find a user name called username
		return 

	SENDER_INFO['user'] = user
	SENDER_INFO['password'] = password
	SENDER_INFO['host'] = 'smtp' +  '.' + postfix


#judge  any  wildcard in the seq
def contain_anywildcard(seq, cset=('*', '?')):
	for c in cset:
		if c in seq:
			return True
	return False

def email_files(sub, brief_msg, files, recipients ):

	mail_user = SENDER_INFO['user']
	mail_host = SENDER_INFO['host']
	mail_pass = SENDER_INFO['password']
	mail_postfix = mail_host[5:]


	zf = tempfile.NamedTemporaryFile(prefix='mail', suffix='.zip')      #create a templefie called mail*.zip, which would be deleted automatically when the process stop.
	zip = zipfile.ZipFile(zf, 'w',zipfile.ZIP_DEFLATED )
	print "Zipping the files to be sent..."
	for file_name in  files:
		if os.path.isdir(file_name):                                
			for root, dirs, allfiles in os.walk(file_name):
				for eachfile in allfiles:
					zip.write(os.path.join(root,eachfile))

		if contain_anywildcard(file_name):                      #check if file_name have any wildcard 
			for eachfile in glob.glob(file_name):
				zip.write(eachfile)
		else :
			zip.write(file_name)
	zip.close()
	zf.seek(0)

	print "Creating email message..."
	me="garrick"+"<"+mail_user+"@"+mail_postfix+">"   
	msg = MIMEMultipart()        
	msg['Subject'] = sub   
	msg['From'] = me
	msg['To'] = ";".join(recipients) 

	test_message  = MIMEText(brief_msg, 'plain', 'utf-8')
	att = MIMEBase('application', 'zip')
	att.set_payload(zf.read())
	att.add_header('Content-Disposition', 'attachment', filename=Header('documents.zip','utf8').encode())
	encoders.encode_base64(att)

	msg.attach(att)
	msg.attach(test_message)
	msg = msg.as_string()

	print "Sending email message...."
	try:
		smtp = smtplib.SMTP(mail_host)
		# smtp.set_debuglevel(1)
		smtp.login(mail_user, mail_pass)
		smtp.sendmail(me, recipients, msg)
	except Exception, e:
		print "Error: {}".format(e)
	finally:
		smtp.close()


if __name__ == '__main__':
	
	parser = argparse.ArgumentParser(description='Email Example')
	parser.add_argument('-r','--rec', action='store', dest='rec', nargs='+')     # rec is a list , mutirecipient
	parser.add_argument('--sub', action='store', dest='sub')     #subtile 
	parser.add_argument('-u', '--user',action='store', dest='user')
	parser.add_argument('-f', '--file', action='store',dest='files', nargs='+')
	parser.add_argument('-m', '--message', action='store', dest='msg')
	given_args = parser.parse_args()


	print given_args.rec

	#get the user information and set SENDER_INFO
	get_user_info()

	#user have to  provide the  recipients and the content of email.
	if SENDER_INFO and given_args.rec and ( given_args.msg or given_args.files) :      
		email_files(given_args.sub, given_args.msg, given_args.files, given_args.rec)
	else :
		print 'wrong usage!!!'










