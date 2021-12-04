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
# release date: 20200411   #delete unused function
# release date: 20200412   #delete unused function
# release date: 20200412   #improve string matching for fah log
# release date: 20200413   #improve & refine & fix bug
# release date: 20200414   fix bug
# release date: 20200415   refine
# release date: 20200504   refine
# release date: 20211204   fix bug for new GPU driver

__version__='20211204'

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

def read_log(fah_logfile: str):
    contents = []
    FS_index = {}
    cfg_begin = cfg_end = 0
    
    f = open(fah_logfile, mode='rb')
    bytes_list = f.readlines()
    f.close()
    
    for i,b in enumerate(bytes_list):
        line=b.decode('UTF-8', errors='ignore').strip() 
        contents.append( line )

        item=line.split(':')
        
        # get last WU index for echo slot
        if (len(item) == 6) and (item[-1] == 'Starting') and ( item[4].startswith('FS') ) and ( item[3].startswith('WU') ):
            FSxx = item[4]
            FS_index[FSxx] = i  #it is great, only records the last starting index

        if (len(item) == 4) and (item[-1] == '<config>'):
            cfg_begin = i

        if (len(item) == 4) and (item[-1] == '</config>'):
            cfg_end = i

    cfg_index = (cfg_begin, cfg_end)

    return contents, FS_index, cfg_index  
#end def

def get_config(log_lines, cfg_index):
    i_begin, i_end = cfg_index

    if i_begin >= i_end :
        raise Exception('can not find <config>')
    
    config_xml = '' 
    for i in range( i_begin, i_end+1 ):
        config_xml += log_lines[i].lstrip('1234567890:')
        #config line maybe contain ':', so split(':') method causes a bug

    user,team,num_slots = parse_config_xml(config_xml)
    
    return {
        'user':user,
        'team':team,
        'num_slots':num_slots
    }
#end def

def parse_config_xml(config_xml: str):
    
    DOMTree = xml.dom.minidom.parseString(config_xml)
    root = DOMTree.documentElement
    user = root.getElementsByTagName('user')[0].getAttribute('v').strip()
    team = root.getElementsByTagName('team')[0].getAttribute('v').strip()
    n_slots = len(root.getElementsByTagName('slot'))
    return user,team,n_slots
#end def

def get_WUxxFSxx(line: str):
    #return line[9:18]
    item = line.split(':')
    WUxx = item[3]
    FSxx = item[4]
    return WUxx,FSxx
#end def

def get_WU_info(log_lines, index: int):
    WUxx, FSxx = get_WUxxFSxx(log_lines[index])
    #slot = FSxx.strip('FS')
    found = 0
    time_step_array = []
    c = len(log_lines)
    for i in range(index, c-1 ):
        line = log_lines[i]
        item = line.split(':')
        if len(item)<5 :
            #drop some line
            #print('continue:',line)
            continue
        if (item[3]!=WUxx) or (item[4]!=FSxx) :
            #drop some line
            #print('continue:',line)
            continue

        # get_WU_core_PID
        # The line likes '06:32:23:WU02:FS04:Core PID:3920'
        if (len(item)==7) and ( item[-2] == 'Core PID') :
            core_PID = int(item[-1])
            found += 1
            continue
        
        # get_WU_core_and_project
        # The line likes '06:32:23:WU02:FS04:0x22:Project: 14543 (Run 0, Clone 1319, Gen 22)'
        if (len(item)==8) and (item[-2] == 'Project') :
            core = item[-3]
            project = item[-1].strip()
            project_num = project.split()[0]
            found += 1
            continue
        
        # get_WU_time_and_steps
        # The line likes '05:54:27:WU04:FS03:0x22:Completed 4350000 out of 5000000 steps (87%)'
        # item[-1] likes 'Completed 6000000 out of 8000000 steps (75%)'
        if (len(item)==7) and ('out of' in item[-1]) and ('steps' in item[-1]) :
            hour = int(item[0])
            min  = int(item[1])
            sec  = int(item[2])
            t = 3600*hour + 60*min + sec
            
            step = item[-1].split()[-1].strip('(%)')
            step = int(step)
            time_step_array.append((t, step))
    #end for

    if found == 2 :
        return {
            'slot':FSxx, #slot
            'core_PID':core_PID,
            'core':core, 
            'project_num':project_num, 
            'project':project,
            'time_step_array':time_step_array
        }
    else:
        raise Exception('WU info not found') #some exception
#end def

def compute_TPF(time_step_array: list):
    if len(time_step_array) < 2: return 0,0,0,0,0,0
    
    t0, step0 = time_step_array[0]
    tx, stepx = time_step_array[-1]
    
    #异常
    if (tx-t0) < 0 : # next day
        tx = tx + 24*3600

    tpf = 1.0*(tx-t0)/(stepx-step0)
    tpf = int( round(tpf) )
    tpf_min = tpf//60
    tpf_sec = tpf%60

    return step0,stepx,t0,tx,tpf_min,tpf_sec
#end def

def get_nv_smi()-> str:
    util_paths=[
        r'/usr/bin/nvidia-smi' ,
        str(os.getenv('SYSTEMDRIVE')) + r'\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe' ,
        str(os.getenv('SYSTEMDRIVE')) + r'\Windows\System32\nvidia-smi.exe' 
    ]
    
    util_cmd = ''
    
    for p in util_paths:
        if os.path.exists(p) and os.path.isfile(p):
            util_cmd = p
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
    gpu_list=[]

    utils_output_xml=os.popen( util_cmd + ' -q -x').read()
    if 'NVIDIA-SMI has failed' in utils_output_xml:
        print('NVIDIA-SMI has failed')
        return []
    #print utils_output_xml,len(utils_output_xml)  #debug
    DOMTree = xml.dom.minidom.parseString(utils_output_xml)
    root = DOMTree.documentElement
    driver_version = root.getElementsByTagName('driver_version') 
    #print len(driver_version) ,driver_version[0].nodeType, driver_version[0].childNodes[0].data #.tagName
    driver_version_str = driver_version[0].childNodes[0].data
    #print driver_version_str    #debug
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
            print('can not detect GPU clock')
            #raise Exception('can not detect GPU clock')
            
        #end if
        product_name = product_name.strip('NVIDIA').strip()
        ginfo = {   'driver':driver_version_str,
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
    return gpu_list
#end def

def get_gpu_info():
    #'only for nvidia GPU now!'
    return get_nv_gpu_info()
#end def

def get_manho_html()-> str:
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
        conn = http.client.HTTPSConnection('fah.manho.org', timeout=10)
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
        print(time.asctime(time.localtime()),': Network exception: can not visit fah.manho.org')
        return ''

    return html
#end def

def get_manho_gpu_table(html: str):

    html_select_gpu = html.split('<select name="gpuid">')[1].split('</select>')[0]

    op_list = html_select_gpu.split('</option>')
    #print len(op_list)
    op_list.pop()       #remove the last item, it is a ""
    #print len(op_list)
    #print op_list

    map_gpuname_gpuid = {}
    for hh in op_list:
        tmp = hh.split('>')
        gpuname = tmp[1].strip().replace('\x20','').upper()
        gpuid   = tmp[0].split('=')[1].strip().strip('"')
        map_gpuname_gpuid[gpuname] = gpuid

    #print( map_gpuname_id ) #debug
    return map_gpuname_gpuid 
#end def

def get_manho_os_table(html: str):
    #html may be checked in the future
    os_table = {'Windows XP'            : '1',
             'Windows Vista'            : '2',
             'Windows 2008 Server'      : '2',
             'Windows 7'                : '3',
             'Windows 2008 Server R2'   : '3',
             'Windows 8'                : '4',
             'Windows 2012 Server'      : '4',
             'Windows 8.1'              : '5',
             'Windows 10'               : '6',
             'Linux'                    : '7'}

    t = {}
    for item in os_table.keys():
        x = item.replace('\x20','')
        t[x] = os_table[item]
    return t
#end def

def get_manho_table():
    html = get_manho_html()
    if html == '' :
        return None
    
    gpu_table = get_manho_gpu_table(html)
    os_table  = get_manho_os_table(html)

    return {
        'gpu_table':gpu_table,
        'os_table':os_table
    }
#end def

def fill_form( user: str, team: str, WU_info, gpu_info, os_info, manho_table ):
    
    driver         = gpu_info['driver']
    graphics_clock = gpu_info['graphics_clock'].strip('MHz').strip()
    mem_clock      = gpu_info['mem_clock'].strip('MHz').strip()
    pci_gen        = gpu_info['pci_gen']
    pci_speed      = gpu_info['pci_speed'].strip('x').strip()
    
    #deal with N/A value
    if graphics_clock=='N/A' or mem_clock=='N/A':
        return None
    
    if (pci_gen=='N/A')  or ('Error' in pci_gen):
        pci_gen='3'        #when the value is N/A, assume PCIE3.0*16
     
    if '1'==pci_gen:
        pci_gen    = '1.1'
    if '2'==pci_gen:
        pci_gen    = '2.0'
    if '3'==pci_gen:
        pci_gen    = '3.0'

    if pci_speed not in ('1','4','8','16'):
        pci_speed='16'
    #################################################################
    
    gpu_table = manho_table['gpu_table']

    gpuname=gpu_info['name']   # gpu_info['name'] is an official GPU name
    gpuname=gpuname.replace('\x20','').upper() # delete space char for 1660Ti ~ 1660 Ti
    
    # #手动处理特殊情况 
    # if gpuname.endswith('SUPER') :
    #   gpuname = gpuname.replace('SUPER','S')   #manho's GPU name is not an official name 

    if gpuname in gpu_table.keys():
        gpuid = gpu_table[gpuname]
    else:
        raise Exception( 'can not find your GPU id on fah.manho.org, exit...' )

    #################################################################
    os_table  = manho_table['os_table']

    if os_info['name'] in os_table.keys():
        os_id=os_table[ os_info['name'] ]
    else:
        raise Exception( 'can not find your OS id on fah.manho.org, exit...' )
    
    if os_info['arch'] == 'AMD64' or os_info['arch']=='x86_64':
        arch='64'
    else:
        arch='32'
    #################################################################
    core_ver    = WU_info['core'].strip('0x')
    project_num = WU_info['project_num']
    tpf_min     = str(WU_info['tpf_min'])
    tpf_sec     = str(WU_info['tpf_sec'])

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

def post_form(form_para)-> int:
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
        conn = http.client.HTTPSConnection('fah.manho.org', timeout=10)
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

# def split_log(log_lines, FS_index):
#   slot_log = {}
#   for FS in FS_index.keys():
#       slot_log[FS] = []
    
#   index_min = min( FS_index.values() )
#   c = len(log_lines)
#   for i in range(index_min, c-1):
#       line = log_lines[i]
#       item = log_lines[i].split(':')
#       if(len(item)<5):
#           continue
#       else:
#           if item[4].startswith('FS') and item[3].startswith('WU'):
#               FSxx = item[4]
#               slot_log[FSxx].append(line)
#           else:
#               #print(line) #debug
#               continue

#   for FS, log in slot_log.items():
#       slot_log[FS] = get_last_starting(log)


#   return slot_log
# #end def

# def get_last_starting(FS_log):
#   c=len(FS_log)
#   for i in range(c-1, -1 ,-1):
#       if FS_log[i].endswith(':Starting'):
#           return FS_log[i:]
#   return None
# #end def

def do_slot_log(log_lines, index: int, user: str, team: str, os_info, gpu_info_list, manho_table):
    global FAH_GPU_CORES
    global submit_db
    
    WU_info = get_WU_info(log_lines, index)
    FSxx = WU_info['slot']
    core = WU_info['core']
    project_num = WU_info['project_num']
    project = WU_info['project']
    
    print('='*60)
    print('%20s'%'Slot ID:',FSxx)
    print('%20s'%'Core:',core)
    print('%20s'%'Project:',project_num)
    print('%20s'%'Project(RCG):',project) 
        
    time_step_array = WU_info['time_step_array'] #get_WU_time_and_steps(lines)

    if len(time_step_array) < 5 : 
        print('data is not enough! skip...')
        return -1

    step0,stepx,t0,tx,tpf_min,tpf_sec = compute_TPF(time_step_array)
    print('%20s'%'progress:'   , [step0,stepx] )
    print('%20s'%'running sec:', [t0,tx] )
    print('%20s'%'TPF:',tpf_min,'min',tpf_sec,'sec')

    WU_info['tpf_min']=tpf_min
    WU_info['tpf_sec']=tpf_sec

    if core not in FAH_GPU_CORES :
        print('skip cpu slot...') 
        return -2 #skip cpu slot
    
    # if len(gpu_info_list) == 1 :     #only cope with one GPU
    #   gpu_info = gpu_info_list[0]   #bug!
    # else:
    #'需要找到本slot对应的GPU'
    #'按PID寻找GPU'
    core_PID = WU_info['core_PID']
    gpu_info = None

    for ginfo in gpu_info_list:
        #print( 'keys:',ginfo['pid_list'].keys() ) #debug
        if core_PID in ginfo['pid_list'].keys() :
            gpu_info = ginfo
            #'找到了！'

    if gpu_info is None :
        #print('Can not find GPU running on process #'+str(core_PID))
        #return -1
        gpu_info = gpu_info_list[0]
    #end if
    
    print('%20s'%'GPU:'       , gpu_info['name'])
    print('%20s'%'GPU Driver:', gpu_info['driver'])
    print('%20s'%'GPU Clock:' , gpu_info['graphics_clock'])
    print('%20s'%'GMem Clock:', gpu_info['mem_clock'])
    print('%20s'%'pci_gen:'   , gpu_info['pci_gen'])
    print('%20s'%'pci_speed:' , gpu_info['pci_speed'])
    print('%20s'%'pci_bus:'   , gpu_info['pci_bus'] )
    sys.stdout.flush()

    if project in submit_db:
        print( 'No results need to be submitted. Sleeping...' )
        return 0
    else:
        formXXX = fill_form(user,team, WU_info, gpu_info, os_info, manho_table)
        ret     = post_form( formXXX ) #send to fah.manho.org
        if ret==0 : #submit OK!
            submit_db.add(project)
        
        print('%20s'%'submit_db:', (project in submit_db))
        return 0

#end def

def auto_ppd_submit_main():
    ############################################################################
    print('-'*80)
    print('Starting some check...')
    print('--check fah.manho.org...')
    manho_table = get_manho_table()
    if manho_table is None: 
        print('can not visit fah.manho.org, try to submit result later')
        return
    print('--check fah.manho.org: Done')
    
    print('--check GPU and its status...')
    gpu_info_list = get_gpu_info()
    if len(gpu_info_list) < 1: raise Exception('No GPU in your system! exit...')
    print('--check GPU and its status: Done')

    print('--check fah log existence...')
    f = search_fah_log()
    print('--check fah log existence: Done')

    ############################################################################
    print('Scanning fah log...')
    print('-'*80)
    log_lines, FS_index, cfg_index = read_log(f)

    config  = get_config(log_lines, cfg_index)
    user    = config['user']
    team    = config['team']
    n_slots = config['num_slots']

    os_info = get_os_info( )
    
    print('%20s'%'User:'       , user )
    print('%20s'%'Team:'       , team )
    print('%20s'%'Total Slots:', n_slots )
    print('%20s'%'OS:'         , os_info['name'] )
    print('%20s'%'OS Arch:'    , os_info['arch'] )
    print('%20s'%'Last config Index:', list(cfg_index) )
    print('%20s'%'Last WU Index:'    , FS_index )      #FS_index: last WU starting index for echo slot

    if (len(FS_index) == 0):
        print('### not enough data. sleep...')
        return 

    # slots_log = split_log(log_lines, FS_index)

    # # for FS, log in slots_log.items():
    # for log in slots_log.values():
    #   # print('='*60)
    #   # print('FS:',FS)
    #   # print(''*80)
    #   # print('\r\n'.join(log))
    #   do_slot_log(log, user,team, os_info, gpu_info_list, manho_table )

    for index in FS_index.values():
        do_slot_log(log_lines, index, user, team, os_info, gpu_info_list, manho_table)

    print('-'*80)
    print(time.asctime(time.localtime()), '\n\n')
    sys.stdout.flush()
#end def

def init():
    try:
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

        #check fah log
        print('fah log file:', search_fah_log() )

        #set my log 
        logging.basicConfig(filename='auto_ppd_submit.log',  level=logging.DEBUG,  format='[%(asctime)s] %(name)s:%(levelname)s: %(message)s' )
    except:
        t, v, errinfo = sys.exc_info()
        print(t, v, '\nerror line:',errinfo.tb_lineno)
        print('press enter to exit...')
        sys.stdin.readline()
        exit(-1)
    #end try
#end def

def search_fah_log()-> str:
    log_paths = [
        'log.txt' , #current dir
        str(os.getenv('SYSTEMDRIVE')) + r'\Program Files (x86)\FAHClient\log.txt' ,
        str(os.getenv('SYSTEMDRIVE')) + r'\Users\root\AppData\Roaming\FAHClient\log.txt'
    ]
    
    for p in log_paths:
        if  os.path.exists( p ) and os.path.isfile( p ) :
            return p

    print('#'*60)
    print('')
    print('can not find folding@home log file!')
    print('please put auto_ppd_submit.py in folding@home work dir.' )
    print('')
    print('#'*60)
    raise Exception('NO fah log file')

#end def

def main():
    DEBUG = False
    
    init()
    ########## main loop ##########
    while True:
        try:
            auto_ppd_submit_main()
        except:
            t, v, errinfo = sys.exc_info()
            print(t, v, '\nerror line:',errinfo.tb_lineno)
            # never exit if error
        #end try

        try:
            time.sleep(60 if not DEBUG else 1) 
        except:
            t, v, errinfo = sys.exc_info()
            print(t, v, '\nerror line:',errinfo.tb_lineno)
            print('press enter to exit...')
            sys.stdin.readline()
            exit(-1)
        #end try
    #end while

# ##################################################################################################
FAH_GPU_CORES = ('0x15', '0x16', '0x17', '0x18', '0x19', '0x20', '0x21', '0x22')
submit_db = set()

if __name__ == '__main__':
    main()
