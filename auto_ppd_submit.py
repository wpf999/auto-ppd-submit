# -*- coding:utf-8 -*-
# This is a Python3 script.
# author: wpf999[in]equn.com 
# release date: 20160216
# release date: 20170920
# release date: 20200405   #fix 5 bugs  
# release date: 20200406   #detect ImportError
# release date: 20200407   #fix bug in function get_gpu_list
# release date: 20200408   #fix bug for os name map
# release date: 20200410   #refine

import sys
if sys.version_info.major != 3 :
	print( 'python3 is needed. \npress enter to exit...' )
	sys.stdin.readline()
	exit(-1)
try:
	import os
	import platform
	import time
	import xml.dom.minidom
	import logging
	import urllib.parse
	import ssl
	ssl._create_default_https_context = ssl._create_unverified_context
	import http.client
	
except:
	t,v,_ = sys.exc_info()
	print(t,v)
	print( 'press enter to exit...' )
	print('$PATH:',os.getenv('PATH'))
	sys.stdin.readline()
	exit(-1)

def hms_to_sec(s):
	#s[0,1]:s[3,4]:s[6,7]
	hour = int( s[0:2] )
	min  = int( s[3:5] )
	sec  = int( s[6:8] )
	return 3600*hour + 60*min + sec
#end def

def read_log(fah_log):
	f = open(fah_log, mode='rb')
	bytes_list = f.readlines()
	f.close()
	#print(type(bytes_list), len(bytes_list)) #debug
	
	contents = []
	for b in bytes_list:
		contents.append( b.decode( 'UTF-8', errors='ignore') )
	#print(contents)
	#print(type(contents), len(contents)) #debug
	return contents
#end def

def get_os_info():
	uname = platform.uname()
	os_name = uname.system + uname.release
	if uname.system.upper() == 'Windows'.upper():
		os_name = uname.system + uname.release
	else:
		os_name = uname.system

	return {
		'name':os_name ,
		'arch':uname.machine
	}
#end def

def get_num_gpus(log_lines):
	for index,line in enumerate(log_lines):
		if 'GPUs:' in line:
			gpu_count=line.split('GPUs:')[1]
			return int(gpu_count.strip()), index
	return -1,-1
#end def

def get_gpu_list(log_lines):
	num_gpus,index = get_num_gpus(log_lines)
	if num_gpus<=0 :
		return []
	
	x = []
	gpu = 0
	i = index
	while True:
		i = i + 1 
		lineX = log_lines[i]
		if ( 'GPU' in lineX ) and ( '[' in lineX ) and ( ']' in lineX ):
			tmp=lineX.split('GPU')[1].strip()
			gpu_name=tmp.split('[')[1].split(']')[0]
			x.append(gpu_name)
			gpu = gpu + 1
			if gpu == num_gpus :
				break
		if '*'*70 in lineX :   #end system section in the log 
			break
	return x
#end def

def get_config(lines):
	c=len(lines)
	i_begin=i_end=0
	for i in range(c-1, 0, -1):
		if '</config>' == lines[i].lstrip('0123456789:').strip():
			i_end=i
		if '<config>' == lines[i].lstrip('0123456789:').strip():
			i_begin=i
			break
	
	if i_begin==i_end:
		raise Exception('can not find <config>')
	
	cfg_lines=lines[i_begin:i_end+1]

	config_xml = ''
	for i in range( 0, len(cfg_lines) ):
		config_xml += cfg_lines[i].lstrip('0123456789:')

	user,team,num_slots = parse_config_xml(config_xml)
	
	return {
		'user':user,
		'team':team,
		'num_slots':num_slots
	}
#end def

def parse_config_xml(config_xml):
	
	DOMTree = xml.dom.minidom.parseString(config_xml)
	root = DOMTree.documentElement
	user = root.getElementsByTagName('user')[0].getAttribute('v').strip()
	team = root.getElementsByTagName('team')[0].getAttribute('v').strip()
	n_slots = len(root.getElementsByTagName('slot'))
	return user,team,n_slots
#end def

def get_WU_index_list(log_lines):
	c=len(log_lines)
	index_list=[]
	for i in range(c-1, 0, -1):
		if log_lines[i].strip().endswith('Starting'):
			index_list.append(i)
	return index_list
#end def

def get_WUxxFSxx(line):
	return line[9:18]
#end def
	
def get_WU_slot(line):
	slot_id=get_WUxxFSxx(line).split('FS')[1]
	return slot_id,int(slot_id)
#end def

def get_WU_core_PID(lines):
	WUxxFSxx = get_WUxxFSxx(lines[0])
	for line in lines:
		if WUxxFSxx in line and ':Core PID:' in line:
			pid = line.split(':Core PID:')[1].strip()
			#print 'pid',pid
			return int(pid)
	return -1  # some exception
#end def

def get_WU_info(lines):
	WUxxFSxx = get_WUxxFSxx(lines[0])
	for line in lines:
		if WUxxFSxx in line and ':Project:' in line:
			tmp = line.split(':Project:')
			core = tmp[0].split(':')[-1]
			project_num = tmp[1].split()[0]
			project     = tmp[1].strip()
			return core, int(project_num), project
	return -1 #some exception
#end def

def get_WU_UID(lines):
	WUxxFSxx = get_WUxxFSxx(lines[0])
	for line in lines:
		if WUxxFSxx in line and ':Unit:' in line:
				return line.split('Unit:')[1].strip()
	return -1  # some exception
#end def

def get_WU_time_and_steps(lines):
	x={}
	WUxxFSxx=get_WUxxFSxx(lines[0])
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

def get_nv_smi():

	util_paths={}
	util_paths[0] = r'/usr/bin/nvidia-smi'
	util_paths[1] = str(os.getenv('SYSTEMDRIVE')) + r'\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe'
	util_paths[2] = str(os.getenv('SYSTEMDRIVE')) + r'\Windows\System32\nvidia-smi.exe' 
	
	util_cmd = ''
	
	for i in range( 0, len(util_paths) ):
		if os.path.exists( util_paths[i] ):
			util_cmd = util_paths[i]
			break
	
	if util_cmd != '' :
		#because of space characters in the path, we need to plus "" 
		if '\x20' in util_cmd:
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

def get_manho_html():
	username = 'wpf'
	team = '3213'

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
		conn.request('POST', '/gpu_statistics.php?a=add', params, header)
		resp = conn.getresponse()
		if resp.status != 200:
			print('===========HTTP response code is not 200 !===========')
			return ''

		resp_data = resp.read()
		html = resp_data.decode('utf-8')
		#print(html) #debug
		conn.close()
	except:
		t, v, _ = sys.exc_info()
		print(t, v)
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
	os_table = {'Windows XP'        	: '1',
             'Windows Vista'         	: '2',
             'Windows 2008 Server'   	: '2',
             'Windows 7'             	: '3',
             'Windows 2008 Server R2'	: '3',
             'Windows 8'             	: '4',
             'Windows 2012 Server'   	: '4',
             'Windows 8.1'           	: '5',
             'Windows 10'            	: '6',
             'Linux'                 	: '7'}

	t = {}
	for item in os_table.keys():
		x = item.replace('\x20','')
		t[x] = os_table[item]
	return t

#end def

def fill_form( user,team, core,project_num,tpf_min,tpf_sec, gpu_info, os_info ):
	
	html=get_manho_html()
	if html=='' :
		return None
	
	gpu_table = get_manho_gpu_table(html)
	os_table  = get_manho_os_table(html)

	gpuname=gpu_info['name']   # gpu_info['name'] is an official GPU name
	gpuname=gpuname.replace('\x20','').upper() # delete space char for 1660Ti ~ 1660 Ti
	
	# #手动处理特殊情况 
	# if gpuname.endswith('SUPER') :
	# 	gpuname = gpuname.replace('SUPER','S')   #manho's GPU name is not an official name 

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
		

	if os_info['arch'] == 'AMD64' or os_info['arch']=='x86_64':
		arch='64'
	else:
		arch='32'
	
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
			'arch':arch
			}

#end def


def post_form(form_para):
	if form_para == None:
		return -2

	user = form_para['user']
	team = form_para['team']

	post_body = form_para
	post_body['submit'] = ''
	post_body['auto'] = '1'

	params = urllib.parse.urlencode(post_body)

	cookie = 'username='+user+'; team='+team
	header = {'Content-type': 'application/x-www-form-urlencoded',   'Cookie': cookie}

	html = ''  # html needs a initial value
	try:
		conn = http.client.HTTPSConnection('fah.manho.org')
		conn.request('POST', '/gpu_statistics.php?a=add', params, header)
		resp = conn.getresponse()
		if resp.status != 200:
			print('===========HTTP response code is not 200 !===========')
			return -1

		resp_data = resp.read()
		html = resp_data.decode('utf-8')
		conn.close()
	except:
		t, v, _ = sys.exc_info()
		print(t, v)
		print('网络异常，本次提交失败。下一次继续重试...')
		return -2

	#print( html ) #debug
	if ('您输入的数据已经成功提交' in html) or ('未找到符合用户名的记录' in html):
		logging.info('===========Submit  OK ! ===========')
		logging.info(post_body)
		print('===========Submit  OK ! ===========')
		return 0
	else:
		print(html)
		print('===========Submit Error!===========')
		return -1

#end def

def do_slot_log(lines,  user,team, os_info):
	global FAH_GPU_CORES
	global submit_db
	
	slot, _ = get_WU_slot(lines[0])
	core, project_num, project = get_WU_info(lines)
	
	if core not in FAH_GPU_CORES :
			return #skip cpu slot
	
	print('='*60)
	print('%15s'%'Slot ID:',slot)
	print('%15s'%'Core:',core)
	print('%15s'%'Project:',project_num)
	print('%15s'%'Project(RCG):',project) 
	
	#wu_id=get_last_starting_WU_id(lines)
	#print get_info_by_id(wu_id,lines)
	
	map_time_steps = get_WU_time_and_steps(lines)
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
		core_PID = get_WU_core_PID(lines)
		gpu_info = None
	
		for ginfo in gpu_info_list:
			#print( 'keys:',ginfo['pid_list'].keys() ) #debug
			if core_PID in ginfo['pid_list'].keys() :
				gpu_info = ginfo
				#'找到了！'

		if gpu_info is None :
			print('Can not find GPU running on process #'+str(core_PID))
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

	lines = read_log(filename)

	config = get_config(lines)
	user,team,n_slots = config['user'], config['team'], config['num_slots']

	n_GPUs, _  = get_num_gpus(lines)
	if n_GPUs <= 0: 
		raise Exception('No GPU in your system! exit...')

	#gpu_list      = get_gpu_list(lines)
	os_info       = get_os_info( )
	WU_index_list = get_WU_index_list(lines)

	print('%15s'%'User:'       , user )
	print('%15s'%'Team:'       , team )
	print('%15s'%'Total Slots:', n_slots )
	print('%15s'%'Total GPUs:' , n_GPUs )
	#print('%15s'%'GPU List:'   , gpu_list )
	print('%15s'%'OS:'         , os_info['name'] )
	print('%15s'%'OS Arch:'    , os_info['arch'] )
	print('%15s'%'WU index:' , WU_index_list )

	s=set([])
	
	for index in WU_index_list:
		slot, _ = get_WU_slot(lines[index])
		if slot in s:
			continue #only watch the last task for each slot
		else:
			s.add(slot)
			do_slot_log(lines[index:],user,team,os_info)
#end def

def init():
	#set window title in Windows
	if platform.system() == 'Windows' :
		os.system('title auto_ppd_submit.py')

	#set work dir
	print('*'*80)
	print('my name:',__file__)
	pwd = os.path.split(os.path.realpath(__file__))[0]
	print('pwd:',pwd)
	os.chdir(pwd)
	print('current dir:', os.getcwd() )
	
	#check nvidia-smi tool
	print('nvidia-smi:' , get_nv_smi() )

	#set my log 
	logging.basicConfig(filename='auto_ppd_submit.log',  level=logging.DEBUG,  format='[%(asctime)s] %(name)s:%(levelname)s: %(message)s' )
	
#end def

def search_fah_log():
	log_paths = {}
	log_paths[0] = 'log.txt' #current dir
	log_paths[1] = str(os.getenv('SYSTEMDRIVE')) + r'\Program Files (x86)\FAHClient\log.txt'
	log_paths[2] = str(os.getenv('SYSTEMDRIVE')) + r'\Users\root\AppData\Roaming\FAHClient\log.txt'
	

	for i in range(0, len(log_paths)) :
		x = log_paths[i]
		if  os.path.exists( x ) and os.path.isfile( x ) :
			return x

	print('#'*60)
	print('')
	print('can not find folding@home log file!')
	print('please put auto_ppd_submit.py in folding@home work dir.' )
	print('')
	print('#'*60)
	raise Exception('NO fah log file')

#end def


# ##################################################################################################
FAH_GPU_CORES = ('0x15', '0x16', '0x17', '0x18', '0x19', '0x20', '0x21', '0x22')
submit_db = set([])

if __name__ == '__main__':
	try:
		init()
		fah_log_file = search_fah_log()
		# main loop
		while True:
			print('-'*80)
			do_log(fah_log_file)
			print(time.asctime(time.localtime(time.time())))
			print('-'*80)
			print('\n\n')
			sys.stdout.flush()
			time.sleep(60)
	except:
			t, v, _ = sys.exc_info()
			print(t, v)
			#os.system("pause")
			print('press enter to exit...')
			sys.stdin.readline()
			exit(-1)
