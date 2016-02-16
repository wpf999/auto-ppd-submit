# -*- coding:utf-8 -*-  
import os
import time
import commands
import string
import math
import xml.dom.minidom
import platform
import subprocess

def hms_to_sec(str):
	#s[0,1]:s[3,4]:s[6,7]
	hour=string.atoi( str[0:2] )
	min =string.atoi( str[3:5] )
	sec =string.atoi( str[6:8] )
	return 3600*hour+60*min+sec
#end def

def read_log(file):
	f=open(file)
	lines=f.readlines()
	f.close()
	return lines
#end def

def get_os_info(log_lines):
	os=log_lines[32].split('OS:')[1].split()
	if os[0]=='Linux':
		os_name=os[0]
	else:
		os_name=os[0]+' '+os[1]
	
	arch=log_lines[33].split('OS Arch:')[1]
	return { 'name':os_name.strip(),  'arch':arch.strip() }
#end def

def get_gpu_count(log_lines):
	gpu_count=log_lines[34].split('GPUs:')[1]
	return string.atoi(gpu_count.strip())
#end def

def get_gpu_list(log_lines):
	gpu_count=get_gpu_count(log_lines)
	list=[]
	for i in range(gpu_count):
		tmp=log_lines[35+i].split('GPU')[1].strip()
		gpu_name=tmp.split('[')[1].strip(']')
		list.append(gpu_name)
	return list
#end def

def get_config(lines):
	c=len(lines)
	for i in range(c-1, 0, -1):
		if '</config>' in lines[i]:
			i_end=i
			break
	for i in range(i_end,0,-1):
		if '<config>' in lines[i]:
			i_begin=i
			break
			
	config=lines[i_begin:i_end+1]
	s=''
	for i in range(len(config)):
		config[i]=config[i][len('00:00:00:'):]
		s=s+config[i]
	return s
#end def

def get_user_and_team(lines):
	config_xml = get_config(lines)
	DOMTree = xml.dom.minidom.parseString(config_xml)
	root = DOMTree.documentElement
	u = root.getElementsByTagName('user')[0].getAttribute('v').strip()
	t = root.getElementsByTagName('team')[0].getAttribute('v').strip()
	#print u,t
	return u,t
#end def

def get_num_of_slots(lines):
	config_xml = get_config(lines)
	DOMTree = xml.dom.minidom.parseString(config_xml)
	root = DOMTree.documentElement
	num_of_slots = len(root.getElementsByTagName('slot'))
	return num_of_slots
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
	return slot_id,string.atoi(slot_id)
#end def

def get_gpu_id_by_slot(slot_id,lines):
	tag='Enabled folding slot '+slot_id
	for i in range(len(lines)-1,0,-1):
		if (tag in lines[i]) and ('gpu:' in lines[i]):
			gpu_id=lines[i].split(tag)[1].split('gpu:')[1].split(':')[0]
			return int(gpu_id)
	return -1 # this slot do not use GPU
#end def

def get_last_starting_core(lines):
	WUxxFSxx=get_last_starting_WUxxFSxx(lines[0])
	for line in lines:
		if WUxxFSxx in line:
			if ':Project:' in line:
				core =line.split(':Project:')[0].split(WUxxFSxx+':')[1]
				return core
	return -1 #some exception
#end def

def get_last_starting_project(lines):
	WUxxFSxx=get_last_starting_WUxxFSxx(lines[0])
	for line in lines:
		if WUxxFSxx in line:
			if ':Project:' in line:
				tmp = line.split(':Project:')
				project_num = tmp[1].split()[0]
				project     = tmp[1].strip()
				return string.atoi(project_num), project
	return -1 #some exception
#end def

def get_last_starting_WU_project_and_core(lines):
	WUxxFSxx=get_last_starting_WUxxFSxx(lines[0])
	for line in lines:
		if WUxxFSxx in line:
			if ':Project:' in line:
				project_num=line.split(':Project:')[1].split()[0]
				core       =line.split(':Project:')[0].split(WUxxFSxx+':')[1]
				return string.atoi(project_num),core
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
	wuxx=line.split(':')[3]
	slot=line.split(':')[4]
	core=line.split(':')[5]
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
					project_num=string.atoi(project.split()[0])
					return project_num,core,wuxx,slot,i,j,project
	return -1
#end def
	
def get_last_starting_WU_time_list(lines):
	list={}
	WUxxFSxx=get_last_starting_WUxxFSxx(lines[0])
	for line in lines:
		if (WUxxFSxx in line) and ('out of' in line) and ('steps' in line):
			t,tmp=line.split(':'+WUxxFSxx+':')
			#print t
			percent=tmp.split('steps')[1].strip().strip('(').strip(')').strip('%')
			t=hms_to_sec(t)
			#print t
			percent=int(percent)
			#print percent
			list[percent]=t
	return list
#end def

def get_nv_gpu_info():
	util_path={}
	util_path[0] = r'/usr/bin/nvidia-smi'
	util_path[1] = str(os.getenv('SYSTEMDRIVE'))+ r'\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe'
	
	util_find = False
	
	for i in util_path.keys():
		if os.path.exists( util_path[i] ):
			util_cmd = util_path[i] 
			if chr(32) in  util_cmd:
				util_cmd = '"' + util_cmd+'"'  #because of space characters in the path, we need to plus "" 
			#print 'i=',i , util_cmd
			util_find = True
			break
			
	if 	util_find == False :
		print 'NVIDIA driver may be not installed!'
		return []
					
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
		#print uuid
		graphics_clock = gpu.getElementsByTagName('clocks')[0].getElementsByTagName('graphics_clock')[0].childNodes[0].data
		mem_clock      = gpu.getElementsByTagName('clocks')[0].getElementsByTagName('mem_clock')[0].childNodes[0].data
		#print graphics_clock,  mem_clock
		
		pci_gpu_link_info_item = gpu.getElementsByTagName('pci')[0].getElementsByTagName('pci_gpu_link_info')[0]
		pci_gen    = pci_gpu_link_info_item.getElementsByTagName('pcie_gen')[0].getElementsByTagName('current_link_gen')[0].childNodes[0].data
		pci_speed = pci_gpu_link_info_item.getElementsByTagName('link_widths')[0].getElementsByTagName('current_link_width')[0].childNodes[0].data
		#print pci_gen, pci_speed
		
		pid_list={}
		process_info_list = gpu.getElementsByTagName('processes')[0].getElementsByTagName('process_info') 
		#print 'len(process_info_list)', len(process_info_list)#[0].childNodes[0].data
		for process_info in process_info_list:
			pid = process_info.getElementsByTagName('pid')[0].childNodes[0].data
			pid = int(pid)
			process_name = process_info.getElementsByTagName('process_name')[0].childNodes[0].data
			pid_list[pid]= process_name
		#end for
		
		ginfo = {	'driver':driver_version_str,
					'uuid':uuid,
					'name':product_name,
					'graphics_clock':graphics_clock,
					'mem_clock':mem_clock,
					'pci_gen':pci_gen,
					'pci_speed':pci_speed,
					'pid_list':pid_list
				}
		gpu_list.append(ginfo)
	#end for 
	
	#print gpu_list
	return 	gpu_list
#end def

def get_gpu_info():
	'only for nvidia GPU now!'
	return get_nv_gpu_info()
#end def

def form_para_table():

	os_k_v={'Windows XP'            	:'1',
			'Windows Vista'         	:'2', 
			'Windows Server 2008'   	:'2',
			'Windows 7'             	:'3', 
			'Windows Server 2008 R2'	:'3',
			'Windows 8'             	:'4',
			'Windows Server 2012'   	:'4',
			'Windows 8.1'           	:'5',
			'Windows 10'            	:'6',
			'Linux'                 	:'7'}

	html = '<option value="95">Radeon R9 Fury X</option><option value="97">Radeon R9 Fury Nano</option><option value="96">Radeon R9 Fury</option><option value="98">Radeon R9 390X</option><option value="99">Radeon R9 390</option><option value="100">Radeon R9 380</option><option value="101">Radeon R9 370</option><option value="103">Radeon R9 295X2</option><option value="104">Radeon R9 290X</option><option value="105">Radeon R9 290</option><option value="107">Radeon R9 285</option><option value="106">Radeon R9 280X</option><option value="108">Radeon R9 280</option><option value="109">Radeon R9 270X</option><option value="110">Radeon R9 270</option><option value="102">Radeon R7 360</option><option value="111">Radeon R7 265</option><option value="112">Radeon R7 260X</option><option value="113">Radeon R7 260</option><option value="114">Radeon R7 250X</option><option value="115">Radeon R7 250</option><option value="116">Radeon R7 240</option><option value="117">Radeon R5 230</option><option value="118">Radeon HD 7990</option><option value="119">Radeon HD 7970 GE</option><option value="120">Radeon HD 7970</option><option value="121">Radeon HD 7950 Boost</option><option value="122">Radeon HD 7950</option><option value="123">Radeon HD 7870 XT (1536SP</option><option value="124">Radeon HD 7870</option><option value="125">Radeon HD 7850</option><option value="126">Radeon HD 7790</option><option value="127">Radeon HD 7770</option><option value="128">Radeon HD 7750</option><option value="129">Radeon HD 7730</option><option value="6">GeForce GTX TITAN Z</option><option value="1">GeForce GTX TITAN X</option><option value="7">GeForce GTX TITAN BLACK</option><option value="8">GeForce GTX TITAN</option><option value="58">GeForce GTX 980M</option><option value="2">GeForce GTX 980 Ti</option><option value="3">GeForce GTX 980</option><option value="59">GeForce GTX 970M</option><option value="4">GeForce GTX 970</option><option value="60">GeForce GTX 965M</option><option value="61">GeForce GTX 960M</option><option value="5">GeForce GTX 960</option><option value="62">GeForce GTX 950M</option><option value="130">GeForce GTX 950</option><option value="66">GeForce GTX 880M</option><option value="67">GeForce GTX 870M</option><option value="68">GeForce GTX 860M</option><option value="69">GeForce GTX 850M</option><option value="74">GeForce GTX 780M</option><option value="9">GeForce GTX 780 Ti</option><option value="10">GeForce GTX 780</option><option value="75">GeForce GTX 770M</option><option value="11">GeForce GTX 770</option><option value="76">GeForce GTX 760M</option><option value="12">GeForce GTX 760 Ti</option><option value="13">GeForce GTX 760</option><option value="14">GeForce GTX 750 Ti</option><option value="15">GeForce GTX 750</option><option value="16">GeForce GTX 745</option><option value="21">GeForce GTX 690</option><option value="84">GeForce GTX 680MX</option><option value="85">GeForce GTX 680M</option><option value="22">GeForce GTX 680</option><option value="86">GeForce GTX 675MX</option><option value="87">GeForce GTX 675M</option><option value="88">GeForce GTX 670MX</option><option value="89">GeForce GTX 670M</option><option value="23">GeForce GTX 670</option><option value="90">GeForce GTX 660M</option><option value="24">GeForce GTX 660 Ti</option><option value="25">GeForce GTX 660</option><option value="26">GeForce GTX 650 Ti</option><option value="27">GeForce GTX 650</option><option value="28">GeForce GTX 645</option><option value="35">GeForce GTX 590</option><option value="36">GeForce GTX 580</option><option value="37">GeForce GTX 570</option><option value="38">GeForce GTX 560 Ti</option><option value="40">GeForce GTX 560 SE</option><option value="39">GeForce GTX 560</option><option value="42">GeForce GTX 555</option><option value="41">GeForce GTX 550 Ti</option><option value="47">GeForce GTX 480</option><option value="48">GeForce GTX 470</option><option value="49">GeForce GTX 465</option><option value="51">GeForce GTX 460 SE V2</option><option value="52">GeForce GTX 460 SE</option><option value="50">GeForce GTX 460</option><option value="53">GeForce GTS 450</option><option value="63">GeForce GT 940M</option><option value="64">GeForce GT 930M</option><option value="65">GeForce GT 920M</option><option value="70">GeForce GT 840M</option><option value="71">GeForce GT 830M</option><option value="72">GeForce GT 820M</option><option value="73">GeForce GT 810M</option><option value="77">GeForce GT 755M</option><option value="78">GeForce GT 750M</option><option value="79">GeForce GT 745M</option><option value="80">GeForce GT 740M</option><option value="17">GeForce GT 740</option><option value="81">GeForce GT 735M</option><option value="82">GeForce GT 730M</option><option value="18">GeForce GT 730</option><option value="83">GeForce GT 720M</option><option value="19">GeForce GT 720</option><option value="20">GeForce GT 710</option><option value="91">GeForce GT 650M</option><option value="92">GeForce GT 645M</option><option value="29">GeForce GT 645</option><option value="93">GeForce GT 640M LE</option><option value="94">GeForce GT 640M</option><option value="30">GeForce GT 640</option><option value="31">GeForce GT 630</option><option value="32">GeForce GT 620</option><option value="33">GeForce GT 610</option><option value="34">GeForce GT 605</option><option value="43">GeForce GT 545</option><option value="44">GeForce GT 530</option><option value="45">GeForce GT 520</option><option value="46">GeForce GT 510</option><option value="54">GeForce GT 440</option><option value="55">GeForce GT 430</option><option value="56">GeForce GT 420</option><option value="57">GeForce GT 405</option>'
	kv_list=html.split('</option>')
	#print len(kv_list)
	kv_list.pop()       #remove last item, it is a ""
	#print len(kv_list)
	#print kv_list
	gpu_k_v={}
	for kv in kv_list:
		key   = kv.split('>')[1].strip()
		value = kv.split('>')[0].split('=')[1].strip().strip('"')
		gpu_k_v[key]=value
	#print gpu_k_v
	return os_k_v , gpu_k_v 
#end def

def build_form_para(user,team, core,project_num,tpf_min,tpf_sec,gpu_info,os_info):
	
	os_key_value, gpu_key_value = form_para_table()
	
	if gpu_info['name'] in gpu_key_value.keys():
		gpu_id = gpu_key_value[gpu_info['name']]  
	else:
		print 'can not find GPU id, exit...'
		exit(-1)
		
	core_ver = core.strip('0x')
	project_num = str(project_num)
	tpf_min = str(tpf_min)
	tpf_sec = str(tpf_sec)
	
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
		
	if '.' not in pci_gen:
		pci_gen    = pci_gen+'.0'
	
	if os_info['name'] in os_key_value.keys():
		os_id=os_key_value[ os_info['name'] ]
	else:
		print 'can not find OS id, exit...'
		exit(-1)
		
	
	if os_info['arch'] == 'AMD64':
		os_arch_num='64'
	else:
		os_arch_num='32'
	
	return {'user':user,
			'team':team,
			'gpu_id':gpu_id,
			'core_ver':core_ver,
			'project_num':project_num,
			'tpf_min':tpf_min,
			'tpf_sec':tpf_sec,
			'driver':driver,
			'graphics_clock':graphics_clock,
			'mem_clock':mem_clock,
			'pci_gen':pci_gen,
			'pci_speed':pci_speed,
			'os_id':os_id,
			'os_arch_num':os_arch_num		
	}
#end def

def post_data(form_para):
	user			= form_para['user']
	team			= form_para['team']
	gpu_id			= form_para['gpu_id']
	core_ver		= form_para['core_ver']
	project_num		= form_para['project_num']
	tpf_min			= form_para['tpf_min']
	tpf_sec			= form_para['tpf_sec']
	driver			= form_para['driver']
	graphics_clock	= form_para['graphics_clock']
	mem_clock		= form_para['mem_clock']
	pci_gen			= form_para['pci_gen']
	pci_speed		= form_para['pci_speed']
	os_id			= form_para['os_id']
	os_arch_num 	= form_para['os_arch_num']
	
	post_body=''
	post_body+='gpuid='+gpu_id+'&corever='+core_ver+'&projectnum='+project_num
	post_body+='&tpfmin='+tpf_min+'&tpfsec='+tpf_sec
	post_body+='&driver='+driver +'&gpucoreclock='+graphics_clock+'&gpumemclock='+mem_clock+'&pciever='+pci_gen+'&pciespeed='+pci_speed
	#post_body+='&driver=000.00&gpucoreclock=0000&gpumemclock=0000&pciever=3.0&pciespeed=16'
	#post_body+='&driver=UNKNOWN&gpucoreclock=UNKNOWN&gpumemclock=UNKNOWN&pciever=UNKNOWN&pciespeed=UNKNOWN'
	post_body+='&os='+os_id+'&arch='+os_arch_num+'&submit=&auto=1'
	
	cookie='username='+user+'; team='+team
	
	#print 'post_body:',post_body #debug
	#return #debug
	cmd='curl -i -b "'+cookie+'"  --data-binary "'+post_body+'" http://fah.manho.org/gpu_statistics.php?a=add'
	cmd=cmd+' 2>'+platform.DEV_NULL
	
	stdout=os.popen(cmd)
	http_response=stdout.read().decode('utf8')
	stdout.close()
	#print http_response #debug
	if ('HTTP/1.1 200 OK' in http_response)  and ( u'您输入的数据已经成功提交' in http_response):
		print '===========Submit  OK ! ==========='
		return 0
	else:
		print '===========Submit Error!==========='
		return -1
	
#end def


def do_slot_log(lines,  user,team, os_info):
	global submit_db
	
	slot, _ = get_last_starting_slot(lines[0])
	print '%15s'%'Slot ID:',slot
	
	core = get_last_starting_core(lines)
	
	project_num, project = get_last_starting_project(lines)
	
	print '%15s'%'Core:',core
	print '%15s'%'Project:',project_num
	print '%15s'%'Project(RCG):',project 
	
	#wu_id=get_last_starting_WU_id(lines)
	#print get_info_by_id(wu_id,lines)


	list=get_last_starting_WU_time_list(lines)
	#print 'time list len:',len(list)
	if len(list)==0 :
		print 'no data now! skip...'
		return -1

	min_per=min(list.keys())
	max_per=max(list.keys())
	print '%15s'%'progress:',[min_per,max_per]
	t_min=list[min_per]
	t_max=list[max_per]
	print '%15s'%'running sec:',[t_min,t_max]
	
	#异常
	if(len(list)<3): 
		print 'data is not enough! skip...'
		return -1

	#异常
	if (t_max-t_min) < 0 :
		t_max=t_max+24*3600
	

	tpf = 1.0*(t_max-t_min)/(max_per-min_per)
	#tpf = int(math.ceil(tpf))
	tpf = int ( round(tpf) )
	#print 'TPF=',tpf,'sec'
	tpf_min = tpf/60
	tpf_sec = tpf%60
	print '%15s'%'TPF:',tpf_min,'min',tpf_sec,'sec'


	#gpu_id = get_gpu_id_by_slot(slot,lines)
	#print '%15s'%'GPU ID:',gpu_id
	#gpu=gpu_list[gpu_id]
	#print '%15s'%'GPU:',gpu

	gpu_info_list = get_gpu_info()

	if len(gpu_info_list)<1:
		print 'There is no GPU in your computer!'
		return -1

	if len(gpu_info_list) ==1 :     #only cope with one GPU
		gpu_info = gpu_info_list[0]
	else:
		'需要找到本slot对应的GPU'
		'按PID寻找GPU'
		core_pid = get_last_starting_pid(lines)
		gpu_info = None
	
		for ginfo in gpu_info_list:
			#print 'keys:',ginfo['pid_list'].keys()
			if core_pid in ginfo['pid_list'].keys():
				gpu_info = ginfo
				#'找到了！'

		if gpu_info == None :
			print 'Not find GPU run on process #'+str(core_pid)
			return -1
	#end if
	
	print '%15s'%'GPU:'       ,gpu_info['name']
	print '%15s'%'GPU Driver:',gpu_info['driver']
	print '%15s'%'GPU Clock:' ,gpu_info['graphics_clock']
	print '%15s'%'GMem Clock:',gpu_info['mem_clock']
	print '%15s'%'pci_gen:'   ,gpu_info['pci_gen']
	print '%15s'%'pci_speed:' ,gpu_info['pci_speed']

	if project in submit_db:
		return 
	
	form_para = build_form_para(user,team,core,project_num,tpf_min,tpf_sec ,gpu_info, os_info)
	ret=post_data(form_para) #send to fah.manho.org
	if ret==0 : #submit OK!
		submit_db.add(project)
	
	#print '%15s'%'submit_db:', submit_db
	print '%15s'%'submit_db:', (project in submit_db)

#end def


def do_log():
	lines =read_log('log.txt')

	user,team = get_user_and_team(lines)
	print '%15s'%'User:',user
	print '%15s'%'Team:',team

	num_of_slots = get_num_of_slots(lines)
	print '%15s'%'Total Slots:',num_of_slots

	print '%15s'%'Total GPUs:',get_gpu_count(lines)

	print '%15s'%'GPU List:',get_gpu_list(lines)

	os_info = get_os_info(lines)
	print '%15s'%'OS:'     ,os_info['name']
	print '%15s'%'OS Arch:',os_info['arch']

	index_list = get_starting_index(lines)
	print '%15s'%'index_list:',index_list

	s=set([])
	for index in index_list:
		#skip cpu slot
		core = get_last_starting_core(lines[index:])
		if core not in ('0x15','0x16','0x17','0x18','0x19','0x20','0x21','0x22') :
			continue
		
		slot, _ = get_last_starting_slot(lines[index])
		if slot in s:
			continue #only watch the last task for each slot
		else:
			s.add(slot)
			print 30*'='
			print '%15s'%'index:',index
			do_slot_log(lines[index:],user,team,os_info)
#end def

# ##################################################################################################

submit_db=set([])
if __name__ == '__main__':
	print os.path.split(os.path.realpath(__file__))[0]
	while True:
		print 60*'='
		do_log()
		time.sleep(5*60)
		
