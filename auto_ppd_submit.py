# -*- coding:utf-8 -*-
# This is a Python3 script.
# author: wpf999[in]equn.com 
# release date: 20160216
# release date: 20170920
# release date: 20200405 , fix 5 bugs  

import sys
if sys.version_info.major != 3 :
	print( 'python3 is needed. \npress enter to exit...' )
	sys.stdin.readline()
	exit(-1)


import os
import time
import xml.dom.minidom
import platform
import urllib.request, urllib.parse, urllib.error
import http.client
import logging
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

def hms_to_sec(s):
	#s[0,1]:s[3,4]:s[6,7]
	hour=int( s[0:2] )
	min =int( s[3:5] )
	sec =int( s[6:8] )
	return 3600*hour + 60*min + sec
#end def

def read_log(fah_log):
	f=open(fah_log, mode='rb')
	bytes_list=f.readlines()
	f.close()
	#print(type(bytes_list), len(bytes_list)) #debug
	
	contents=[]
	for b in bytes_list:
		contents.append( b.decode( 'UTF-8', errors='ignore') )
	#print(contents)
	#print(type(contents), len(contents)) #debug
	return contents
#end def

def get_os_info(log_lines):
	for line in log_lines:
		if 'OS:' in line:
			os=line.split('OS:')[1].split()
			if os[0]=='Linux':
				os_name=os[0]
			else:
				os_name=os[0]+' '+os[1]
		
		if 'OS Arch:' in line:
			arch=line.split('OS Arch:')[1]
			break
			
	return { 'name':os_name.strip(),  'arch':arch.strip() }
#end def

def get_gpu_count(log_lines):
	for line in log_lines:
		if 'GPUs:' in line:
			gpu_count=line.split('GPUs:')[1]
			return int(gpu_count.strip())
	return -1
#end def

def get_gpu_count_v2(log_lines):
	for index,line in enumerate(log_lines):
		if 'GPUs:' in line:
			gpu_count=line.split('GPUs:')[1]
			return int(gpu_count.strip()), index
	return -1,-1
#end def

def get_gpu_list(log_lines):
	gpu_count,index=get_gpu_count_v2(log_lines)
	if gpu_count<=0 :
		return []
	
	x=[]
	for i in range( 0, gpu_count ):
		tmp=log_lines[index+1+i].split('GPU')[1].strip()
		#gpu_name=tmp.split('[')[1].strip(']')
		gpu_name=tmp.split('[')[1].split(']')[0]
		x.append(gpu_name)
	return x
#end def

def get_config(lines):
	c=len(lines)
	i_begin=i_end=0
	for i in range(c-1, 0, -1):
		if '</config>' in lines[i]:
			i_end=i
		if '<config>' in lines[i]:
			i_begin=i
			break
	
	if i_begin==i_end:
		raise Exception('can not find <config>')
	
	config=lines[i_begin:i_end+1]
	s=''
	for i in range( 0, len(config) ):
		s = s + config[i][len('00:00:00:'):]
		
	#print("config:\n"+s)#debug
	return s
#end def

def get_user_and_team(lines):
	config_xml = get_config(lines)
	DOMTree = xml.dom.minidom.parseString(config_xml)
	root = DOMTree.documentElement
	u = root.getElementsByTagName('user')[0].getAttribute('v').strip()
	t = root.getElementsByTagName('team')[0].getAttribute('v').strip()
	#print( u, t )
	return u,t
#end def

def get_num_of_slots(lines):
	config_xml = get_config(lines)
	DOMTree = xml.dom.minidom.parseString(config_xml)
	root = DOMTree.documentElement
	n_slots = len(root.getElementsByTagName('slot'))
	return n_slots
#end def
	
def get_starting_index(log_lines):
	c=len(log_lines)
	index_list=[]
	for i in range(c-1, 0, -1):
		if log_lines[i].strip().endswith('Starting'):
			index_list.append(i)
	return index_list
#end def

def get_last_starting_WUxxFSxx(line):
	return line[9:18]
#end def
	
def get_last_starting_slot(line):
	slot_id=get_last_starting_WUxxFSxx(line).split('FS')[1]
	return slot_id,int(slot_id)
#end def

def get_gpu_id_by_slot(slot_id,lines):
	tag='Enabled folding slot '+slot_id
	c = len(lines)
	for i in range( c-1, 0, -1 ):
		if (tag in lines[i]) and ('gpu:' in lines[i]):
			gpu_id=lines[i].split(tag)[1].split('gpu:')[1].split(':')[0]
			return int(gpu_id)
	return -1 # this slot do not use GPU
#end def

def get_last_starting_core(lines):
	WUxxFSxx = get_last_starting_WUxxFSxx(lines[0])
	for line in lines:
		if WUxxFSxx in line:
			if ':Project:' in line:
				core = line.split(':Project:')[0].split(WUxxFSxx+':')[1]
				return core
	return -1 #some exception
#end def

def get_last_starting_project(lines):
	WUxxFSxx = get_last_starting_WUxxFSxx(lines[0])
	for line in lines:
		if WUxxFSxx in line:
			if ':Project:' in line:
				tmp = line.split(':Project:')
				project_num = tmp[1].split()[0]
				project     = tmp[1].strip()
				return int(project_num), project
	return -1 #some exception
#end def

def get_last_starting_WU_project_and_core(lines):
	WUxxFSxx=get_last_starting_WUxxFSxx(lines[0])
	for line in lines:
		if WUxxFSxx in line:
			if ':Project:' in line:
				project_num=line.split(':Project:')[1].split()[0]
				core       =line.split(':Project:')[0].split(WUxxFSxx+':')[1]
				return int(project_num),core
	return -1 #some exception
#end def

def get_last_starting_pid(lines):
	WUxxFSxx=get_last_starting_WUxxFSxx(lines[0])
	for line in lines:
		if WUxxFSxx+':Core PID:' in line:
			pid = line.split(':Core PID:')[1].strip()
			#print 'pid',pid
			return int(pid)
	return -1 #some exception
#end def

def get_last_starting_WU_id(lines):
	WUxxFSxx=get_last_starting_WUxxFSxx(lines[0])
	for line in lines:
		if WUxxFSxx in line:
			if 'Unit:' in line:
				return line.split('Unit:')[1].strip()
	return -1 #some exception
#end def

def get_core_WUxxFSxx(line):
	x = line.split(':')
	wuxx = x[3]
	slot = x[4]
	core = x[5]
	return core,wuxx,slot
#end def

def get_info_by_id(id,lines):
	total_line=len(lines)
	for i in range(total_line-1, 0, -1):
		if ('Unit: '+id) in lines[i]:
			core,wuxx,slot = get_core_WUxxFSxx(lines[i])
			tag = wuxx+':'+slot+':'+core+':Project:'
			for j in range(i-1,0,-1):
				if tag in lines[j]:
					project=lines[j].split(tag)[1].strip()
					project_num= int(project.split()[0])
					return project_num,core,wuxx,slot,i,j,project
	return -1
#end def
	
def get_last_starting_WU_time_and_steps(lines):
	x={}
	WUxxFSxx=get_last_starting_WUxxFSxx(lines[0])
	for line in lines:
		if (WUxxFSxx in line) and ('out of' in line) and ('steps' in line):
			t,tmp = line.split(':'+WUxxFSxx+':')
			#print(t) #debug
			t = hms_to_sec(t)
			#print(t) #debug
			step = tmp.split('steps')[1].strip().strip('(%)')
			step = int(step)
			x[step] = t
	return x
#end def

def nvapi_detect_clock(pci_bus):
	
	buf = os.popen( 'GPU_nvapi_using.exe  ' + pci_bus ).read()
	print(buf)
	for line in buf.splitlines():
		if 'core frequency=' in line:
			core_f = line.split('=')[1].strip('MHz').strip()
		if 'mem frequency=' in line:
			mem_f = line.split('=')[1].strip('MHz').strip()
	return core_f,mem_f
#end def

def get_nv_smi():

	util_path={}
	util_path[0] = r'/usr/bin/nvidia-smi'
	util_path[1] = str(os.getenv('SYSTEMDRIVE')) + r'\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe'
	util_path[2] = str(os.getenv('SYSTEMDRIVE')) + r'\Windows\System32\nvidia-smi.exe' 
	
	util_find = False
	
	for i in range( 0, len(util_path) ):
		if os.path.exists( util_path[i] ):
			util_cmd = util_path[i]
			util_find = True
			break
	
	if util_find :
		#because of space characters in the path, we need to plus "" 
		if chr(0x20) in util_cmd:
			util_cmd = '"' + util_cmd + '"'

		return util_cmd
	else:
		raise Exception( 'can not find nvidia-smi! exit...' )
	
#end def 

def get_nv_gpu_info():
	util_cmd = get_nv_smi()

	utils_output_xml=os.popen( util_cmd + ' -q -x').read()
	#print utils_output_xml,len(utils_output_xml)  #debug
	DOMTree = xml.dom.minidom.parseString(utils_output_xml)
	root = DOMTree.documentElement
	driver_version = root.getElementsByTagName('driver_version') 
	#print len(driver_version) ,driver_version[0].nodeType, driver_version[0].childNodes[0].data #.tagName
	driver_version_str = driver_version[0].childNodes[0].data
	#print driver_version_str    #debug
	gpu_list=[]
	gpus = root.getElementsByTagName('gpu') 
	for gpu in gpus :
		#gpu.hasAttribute('id')
		product_name=gpu.getElementsByTagName('product_name')[0].childNodes[0].data
		#print product_name
		uuid = gpu.getElementsByTagName('uuid')[0].childNodes[0].data
		#print( uuid )
		graphics_clock = gpu.getElementsByTagName('clocks')[0].getElementsByTagName('graphics_clock')[0].childNodes[0].data
		mem_clock      = gpu.getElementsByTagName('clocks')[0].getElementsByTagName('mem_clock')[0].childNodes[0].data
		
		
		pci_bus    = gpu.getElementsByTagName('pci')[0].getElementsByTagName('pci_bus')[0].childNodes[0].data
		#print('%15s'%'pci_bus:',pci_bus)
		#print graphics_clock,  mem_clock
		pci_gpu_link_info_item = gpu.getElementsByTagName('pci')[0].getElementsByTagName('pci_gpu_link_info')[0]
		pci_gen    = pci_gpu_link_info_item.getElementsByTagName('pcie_gen')[0].getElementsByTagName('current_link_gen')[0].childNodes[0].data
		pci_speed = pci_gpu_link_info_item.getElementsByTagName('link_widths')[0].getElementsByTagName('current_link_width')[0].childNodes[0].data
		#print pci_gen, pci_speed
		
		map_pid_pname={}
		process_info_list = gpu.getElementsByTagName('processes')[0].getElementsByTagName('process_info') 
		#print 'len(process_info_list)', len(process_info_list)#[0].childNodes[0].data
		for process_info in process_info_list:
			pid = process_info.getElementsByTagName('pid')[0].childNodes[0].data
			pid = int(pid)
			process_name = process_info.getElementsByTagName('process_name')[0].childNodes[0].data
			map_pid_pname[pid]= process_name
		#end for
		
		#n/a处理
		if  ( graphics_clock=='N/A' ) or ( mem_clock=='N/A' ):
			#graphics_clock,mem_clock = nvapi_detect_clock(pci_bus)
			raise Exception('can not detect GPU clock')
			
		#end if
		
		ginfo = {	'driver':driver_version_str,
					'uuid':uuid,
					'pci_bus':pci_bus,
					'name':product_name,
					'graphics_clock':graphics_clock,
					'mem_clock':mem_clock,
					'pci_gen':pci_gen,
					'pci_speed':pci_speed,
					'pid_list':map_pid_pname
				}
		
		gpu_list.append(ginfo)
	#end for 
	
	#print gpu_list
	return gpu_list
#end def

def get_gpu_info():
	#'only for nvidia GPU now!'
	return get_nv_gpu_info()
#end def

def get_html():
	username='wpf'
	team='3213'

	#post_body={}
	#post_body['username']=username
	#post_body['team']=team
	#params = urllib.parse.urlencode(post_body)
	#cookie=""
	#header={"Content-type": "application/x-www-form-urlencoded",   "Cookie": cookie }
	#html=""  #html needs a initial value 
	# conn = http.client.HTTPSConnection('fah.manho.org')
	# conn.request("POST", "/gpu_statistics.php?a=add", params , header)
	# resp = conn.getresponse()
	# if resp.status!=200 :
		# print('===========HTTP response code is not 200 !===========')
		# return ""
	# resp_data = resp.read()
	# html= resp_data.decode( 'utf-8' )
	# conn.close()
	#print(html)

	cookie='username='+username+'; team='+team
	header={"Content-type": "application/x-www-form-urlencoded",   "Cookie": cookie }
	post_body={}
	params = urllib.parse.urlencode(post_body)

	html=''
	try:
		conn = http.client.HTTPSConnection('fah.manho.org')
		conn.request('POST', '/gpu_statistics.php?a=add', params , header)
		resp = conn.getresponse()
		if resp.status!=200 :
			print('===========HTTP response code is not 200 !===========')
			return ''
			
		resp_data = resp.read()
		html= resp_data.decode( 'utf-8' )
		#print(html) #debug
		conn.close()
	except:
		t,v,_ = sys.exc_info()
		print(t,v)
		print('Network exception: can not visit fah.manho.org')
		return ''
		
	return html

#end def

def get_manho_gpu_table(html):

	html_select_gpu = html.split('<select name="gpuid">')[1].split('</select>')[0]

	op_list = html_select_gpu.split('</option>')
	#print len(op_list)
	op_list.pop()       #remove the last item, it is a ""
	#print len(op_list)
	#print op_list

	map_gpuname_id = {}
	for hh in op_list:
		tmp = hh.split('>')
		gpuname = tmp[1].strip().replace('\x20','').upper()
		gpuid   = tmp[0].split('=')[1].strip().strip('"')
		map_gpuname_id[gpuname] = gpuid

	#print( map_gpuname_id ) #debug
	return map_gpuname_id 
#end def

def get_manho_os_table(html):
	#html may be checked in the future
	return {'Windows XP'            	:'1',
			'Windows Vista'         	:'2', 
			'Windows Server 2008'   	:'2',
			'Windows 7'             	:'3', 
			'Windows Server 2008 R2'	:'3',
			'Windows 8'             	:'4',
			'Windows Server 2012'   	:'4',
			'Windows 8.1'           	:'5',
			'Windows 10'            	:'6',
			'Linux'                 	:'7'}

#end def

def fill_form( user,team, core,project_num,tpf_min,tpf_sec, gpu_info, os_info ):
	
	html=get_html()
	if html=='' :
		return None
	
	gpu_table = get_manho_gpu_table(html)
	os_table  = get_manho_os_table(html)

	gpuname=gpu_info['name']   # gpu_info['name'] is official GPU name
	gpuname=gpuname.replace('\x20','').upper() # delete space char for 1660Ti ~ 1660 Ti
	
	if gpuname in gpu_table.keys():
		gpuid = gpu_table[gpuname]
	else:
		raise Exception( 'can not find your GPU id on fah.manho.org, exit...' )
		
		
	core_ver    = core.strip('0x')
	project_num = str(project_num)
	tpf_min     = str(tpf_min)
	tpf_sec     = str(tpf_sec)
	
	driver         = gpu_info['driver']
	graphics_clock = gpu_info['graphics_clock'].strip('MHz').strip()
	mem_clock      = gpu_info['mem_clock'].strip('MHz').strip()
	pci_gen        = gpu_info['pci_gen']
	pci_speed      = gpu_info['pci_speed'].strip('x').strip()
	
	#deal with N/A value
	if graphics_clock=='N/A':
		graphics_clock='0000'
	if mem_clock=='N/A':
		mem_clock='0000'
	if pci_gen=='N/A':
		pci_gen='3'        #when the value is N/A, assume PCIE3.0*16
	if pci_speed=='N/A':
		pci_speed='16'
		
	if '1'==pci_gen:
		pci_gen    = '1.1'
	if '2'==pci_gen:
		pci_gen    = '2.0'
	if '3'==pci_gen:
		pci_gen    = '3.0'
	
	if os_info['name'] in os_table.keys():
		os_id=os_table[ os_info['name'] ]
	else:
		raise Exception( 'can not find your OS id on fah.manho.org, exit...' )
		

	if os_info['arch'] == 'AMD64':
		os_arch_num='64'
	else:
		os_arch_num='32'
	
	return {'user':user,
			'team':team,
			'gpuid':gpuid,
			'corever':core_ver,
			'projectnum':project_num,
			'tpfmin':tpf_min,
			'tpfsec':tpf_sec,
			'driver':driver,
			'gpucoreclock':graphics_clock,
			'gpumemclock':mem_clock,
			'pciever':pci_gen,
			'pciespeed':pci_speed,
			'os':os_id,
			'arch':os_arch_num
			}

#end def

def post_form( form_para ):
	if form_para==None:
		return -2

	user = form_para['user']
	team = form_para['team']

	post_body=form_para
	post_body['submit'] = ''
	post_body['auto']   = '1'
	
	params = urllib.parse.urlencode(post_body)

	cookie = 'username='+user+'; team='+team
	header = {'Content-type': 'application/x-www-form-urlencoded',   'Cookie': cookie }
	
	html=''  #html needs a initial value 
	try:
		conn = http.client.HTTPSConnection('fah.manho.org')
		conn.request('POST', '/gpu_statistics.php?a=add', params , header)
		resp = conn.getresponse()
		if resp.status!=200 :
			print('===========HTTP response code is not 200 !===========')
			return -1
	
		resp_data = resp.read()
		html= resp_data.decode( 'utf-8' )
		conn.close()
	except:
		t,v,_ = sys.exc_info()
		print(t,v)
		print('网络异常，本次提交失败。下一次继续重试...')
		return -2
	
	#print( html ) #debug
	if  ( '您输入的数据已经成功提交' in html) or ('未找到符合用户名的记录' in html):
		logging.info('===========Submit  OK ! ===========')
		logging.info( post_body )
		print('===========Submit  OK ! ===========')
		return 0
	else:
		print(html)
		print('===========Submit Error!===========')
		return -1
	
#end def


def do_slot_log(lines,  user,team, os_info):
	global submit_db
	
	slot, _ = get_last_starting_slot(lines[0])
	core = get_last_starting_core(lines)
	project_num, project = get_last_starting_project(lines)
	
	print('%15s'%'Slot ID:',slot)
	print('%15s'%'Core:',core)
	print('%15s'%'Project:',project_num)
	print('%15s'%'Project(RCG):',project) 
	
	#wu_id=get_last_starting_WU_id(lines)
	#print get_info_by_id(wu_id,lines)
	
	map_time_steps = get_last_starting_WU_time_and_steps(lines)
	#print( 'map_time_steps len:',len(map_time_steps) )  #debug

	if len(map_time_steps) < 5 : 
		print('data is not enough! skip...')
		return -1
	
	step_min = min(map_time_steps.keys())
	step_max = max(map_time_steps.keys())
	t_min = map_time_steps[step_min]
	t_max = map_time_steps[step_max]
	
	#异常
	if (t_max-t_min) < 0 : # next day
		t_max = t_max + 24*3600

	tpf = 1.0*(t_max-t_min)/(step_max-step_min)
	tpf = int ( round(tpf) )
	tpf_min = tpf//60
	tpf_sec = tpf%60

	print('%15s'%'progress:'   , [step_min,step_max] )
	print('%15s'%'running sec:', [t_min,t_max] )
	print('%15s'%'TPF:',tpf_min,'min',tpf_sec,'sec')


	gpu_info_list = get_gpu_info()

	if len(gpu_info_list) < 1:
		print('There is no GPU in your computer!')
		return -1

	if len(gpu_info_list) == 1 :     #only cope with one GPU
		gpu_info = gpu_info_list[0]
	else:
		#'需要找到本slot对应的GPU'
		#'按PID寻找GPU'
		core_pid = get_last_starting_pid(lines)
		gpu_info = None
	
		for ginfo in gpu_info_list:
			#print( 'keys:',ginfo['pid_list'].keys() ) #debug
			if core_pid in ginfo['pid_list'].keys() :
				gpu_info = ginfo
				#'找到了！'

		if gpu_info is None :
			print('Can not find GPU running on process #'+str(core_pid))
			return -1
	#end if
	
	print('%15s'%'GPU:'       , gpu_info['name'])
	print('%15s'%'GPU Driver:', gpu_info['driver'])
	print('%15s'%'GPU Clock:' , gpu_info['graphics_clock'])
	print('%15s'%'GMem Clock:', gpu_info['mem_clock'])
	print('%15s'%'pci_gen:'   , gpu_info['pci_gen'])
	print('%15s'%'pci_speed:' , gpu_info['pci_speed'])
	print('%15s'%'pci_bus:'   , gpu_info['pci_bus'] )
	sys.stdout.flush()

	if project in submit_db:
		print( 'No results need to be submitted. Sleeping...' )
		return 0
	else:
		formXXX = fill_form(user,team,core,project_num,tpf_min,tpf_sec ,gpu_info, os_info)
		ret     = post_form( formXXX ) #send to fah.manho.org
		if ret==0 : #submit OK!
			submit_db.add(project)
		
		#print( '%15s'%'submit_db:', submit_db)
		print('%15s'%'submit_db:', (project in submit_db))
		return 0

#end def

def do_log(filename):
	global FAH_GPU_CORES

	lines = read_log(filename)

	user,team  = get_user_and_team(lines)
	n_slots    = get_num_of_slots(lines)

	n_GPUs     = get_gpu_count(lines)
	if n_GPUs <= 0: 
		raise Exception('No GPU in your system! exit...')

	gpu_list   = get_gpu_list(lines)
	os_info    = get_os_info(lines)
	index_list = get_starting_index(lines)

	print('%15s'%'User:'       , user )
	print('%15s'%'Team:'       , team )
	print('%15s'%'Total Slots:', n_slots )
	print('%15s'%'Total GPUs:' , n_GPUs )
	print('%15s'%'GPU List:'   , gpu_list )
	print('%15s'%'OS:'         , os_info['name'] )
	print('%15s'%'OS Arch:'    , os_info['arch'] )
	print('%15s'%'index_list:' , index_list )

	s=set([])
	
	for index in index_list:
		core = get_last_starting_core(lines[index:])
		if core not in FAH_GPU_CORES :
			continue #skip cpu slot
		
		slot, _ = get_last_starting_slot(lines[index])
		if slot in s:
			continue #only watch the last task for each slot
		else:
			s.add(slot)
			print('='*60)
			print('%15s'%'index:', index )
			do_slot_log(lines[index:],user,team,os_info)
#end def

# ##################################################################################################
FAH_GPU_CORES = ('0x15','0x16','0x17','0x18','0x19','0x20','0x21','0x22')
submit_db = set([])

if __name__ == '__main__':
	FAH_LOG_FILE = 'log.txt'
	try:
		
		print('nvidia-smi:' , get_nv_smi() )
		print('my name:',__file__)
		pwd = os.path.split(os.path.realpath(__file__))[0]
		print('pwd:',pwd)
		os.chdir(pwd)
		print('current dir:', os.getcwd() )
		if not ( os.path.exists( FAH_LOG_FILE ) and os.path.isfile( FAH_LOG_FILE ) ):
			print('#'*60)
			print('')
			print('can not find folding@home log file!')
			print('please put auto_ppd_submit.py in folding@home work dir.' )
			print('')
			print('#'*60)
			raise Exception('no log file')
		
		logging.basicConfig(filename='auto_ppd_submit.log',  level=logging.DEBUG,  format='[%(asctime)s] %(name)s:%(levelname)s: %(message)s' )
		
		while True:
			print('-'*80)
			do_log( FAH_LOG_FILE )
			print(time.asctime( time.localtime(time.time()) ))
			print('-'*80)
			print('\n\n')
			sys.stdout.flush()
			time.sleep(60)
	except:
		t,v,_ = sys.exc_info()
		print(t,v)
		#os.system("pause")
		print( 'press enter to exit...' )
		sys.stdin.readline()
		exit(-1)
