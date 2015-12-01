#!/usr/bin/env python
# _*_ coding: utf8 _*_

import re
from datetime import datetime
import pickle
import os
import logging 
import sys
import sqlite3
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
LOGFILE = '/home/garrick/email.log'



def validateEmail(email):
    if len(email) > 7:
        if re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", email) != None:
            return 1
    return 0



def get_real_address(recipients):
	for idx, value in enumerate(recipients):
		if not validateEmail(value):
			result = is_nickname_exits(value)
			if result:
				recipients[idx] = result
			else:
				raise ValueError



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
	"""
	zip the file and send email
	"""

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
		raise SystemError
	finally:
		smtp.close()


def init_recipients_db():
	conn = sqlite3.connect('/home/garrick/recipients.db')
	cursor = conn.cursor()
	" ceate table"

	sql = """
	        CREATE TABLE NICK_EMAIL
	        (
	        	ID INTEGER PRIMARY KEY AUTOINCREMENT,
	        	NICK_NAME TEXT NOT NULL,
	        	EMAIL_ADDRESS TEXT NOT NULL
	        )
	"""
	cursor.execute(sql)
	conn.commit()


def is_nickname_exits(nick_name):
	conn = sqlite3.connect('/home/garrick/recipients.db')
	cursor = conn.cursor()
	search_sql = "SELECT EMAIL_ADDRESS FROM NICK_EMAIL WHERE NICK_NAME = ?"
	cursor.execute(search_sql,(nick_name,))
	result =  cursor.fetchone()[0]
	cursor.close()
	conn.close()
	return result



def save_recipent(nick_name, email_address):
	if not os.path.isfile('/home/garrick/recipients.db') :   #判断是否已经初始化数据库
		init_recipients_db()
	conn  = sqlite3.connect('/home/garrick/recipients.db')
	cursor = conn.cursor()


	def insert_into_db(nick_name,email_address):
		insert_sql = "INSERT INTO NICK_EMAIL(NICK_NAME, EMAIL_ADDRESS) VALUES(?,?)"
		cursor.execute(insert_sql,(nick_name,email_address))
		conn.commit()

	def delete_from_db(nick_name):
		delete_sql = "DELETE FROM NICK_EMAIL WHERE NICK_NAME=?"
		cursor.execute(delete_sql,(nick_name,))
		conn.commit()


	result = is_nickname_exits(nick_name)
	if  not result:                                #没有重复的NICK_NAME, 可直接插入数据库
		insert_into_db(nick_name, email_address)
	else :                                              #昵称已经存在
		print "Nick_name exits! Would you want to replace the old one or give up?[Y/N]:  "
		reply =  raw_input()
		if reply.lower()  == 'y':                  #替换
			delete_from_db(nick_name)
			insert_into_db(nick_name, email_address)   
		else:     #give up ....
			print "Tips: You can use command 'sendmail -save emailaddress nickname ' to save it  as another nickname,"

	cursor.close()
	conn.close()

if __name__ == '__main__':
	
	parser = argparse.ArgumentParser(description='Email Example')
	parser.add_argument('-r','--rec', action='store', dest='rec', nargs='+')     # rec is a list , mutirecipient
	parser.add_argument('--sub', action='store', dest='sub')     #subtile 
	parser.add_argument('-u', '--user',action='store', dest='user')
	parser.add_argument('-f', '--file', action='store',dest='files', nargs='+')
	parser.add_argument('-m', '--message', action='store', dest='msg')
	parser.add_argument('-save', action='store', dest='nick')
	args = parser.parse_args()

	#get the user information and set SENDER_INFO
	get_user_info()

	#user have to  provide the  recipients and the content of email.
	if SENDER_INFO and args.rec and ( args.msg or args.files) :      
		try:
			get_real_address(args.rec)
			email_files(args.sub, args.msg, args.files, args.rec)
		except ValueError,e:
			print "Invalid recipients!",e
		except SystemError,e:
			print "Send email failed. ",e
		else :
			print "Email was sent successfully."
			logging.basicConfig(level=logging.INFO, filename=LOGFILE)
			logging.info("{time} :  {user} send  {files} to {rec} ".format(time=str(datetime.now()), user=SENDER_INFO['user'], files = args.files, rec=args.rec))
			#看是否需要保存为昵称
			if  args.nick:           
				save_recipent(args.nick, args.rec[0])
	else :
		print 'wrong usage!!!'


	






