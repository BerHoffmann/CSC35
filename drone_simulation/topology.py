#from mininet.net import Mininet
#from mininet.node import Controller
#from mininet.link import TCLink
import sys, os

from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mn_wifi.link import wmediumd, adhoc
from mn_wifi.wmediumdConnector import interference
from mn_wifi.replaying import ReplayingMobility
import multiprocessing
from socket import socket, AF_INET, SOCK_STREAM
from flask import Flask, request, jsonify
import random
import threading


app = Flask(_name_)
net = Mininet_wifi(link=wmediumd, wmediumd_mode=interference)
drones = []
path = os.path.dirname(os.path.abspath(_file_)) + '/replayingMobility2/'

def create_topology(args):
    global net, drones
    drones = []
    # Create Drones
    kwargs = {}
    if '-a' in args:
        kwargs['range'] = 100
        
    
    initial_positions = ['10.0, 10.0, 0.0', '20.0, 10.0, 0.0', '30.0, 10.0, 0.0', '40.0, 10.0, 0.0', '50.0, 10.0, 0.0', '60.0, 10.0, 0.0', '70.0, 10.0, 0.0', '80.0, 10.0, 0.0', '90.0, 100.0, 0.0']
    
    for i in range(1, 10):
    	ip_address = '10.0.0.{}'.format(i) 
        drone = net.addStation('drone{}'.format(i), ip6=ip_address, position = initial_positions[i-1],speed=4,**kwargs)
        drones.append(drone)
        
    
    net.setPropagationModel(model="logDistance", exp=5)
    
    net.configureNodes()
    protocols = ['babel', 'batman_adv', 'batmand', 'olsrd', 'olsrd2']
    kwargs = {}
    for proto in args:
        if proto in protocols:
            kwargs['proto'] = proto
    i = 1
    for drone in drones:
        net.addLink(drone, cls=adhoc, intf='drone{}-wlan0'.format(i), ssid='adhocNet', mode='g', channel=1, ht_cap='HT40+',**kwargs)
        drone.setIP6('10.0.0.{}/8'.format(i+1), intf="drone{}-wlan0".format(i))
        i = i+1
    
    net.isReplaying = True
    
    path = os.path.dirname(os.path.abspath(_file_)) + '/replayingMobility2/'
    
    i = 1
    for drone in drones:
        drone.p = []
        set_position(drone, 10 + 2*i, 10 + 2*i)
        i=i+1
        
    net.plotGraph(max_x=200, max_y=200)

def set_position(sta, pos_x, pos_y):
    if len(sta.p) is not 0:
        new_trace = sta.p
    else:
        new_trace = []
    for _ in range(1000):
        pos = float(pos_x), float(pos_y), 0.0
        new_trace.append(pos)
    sta.p = new_trace
    
            	
def set_route(sta, i, final_x, final_y, n=1):
    final_x = final_x + 1.3 * i
    final_y = final_y + 1.3 * i
    initial_x = sta.position[0]
    initial_y = sta.position[1]
    
    trace = []
    dx = abs(final_x - initial_x)
    dy = abs(final_y - initial_y)
    sx = 1 if initial_x < final_x else -1
    sy = 1 if initial_y < final_y else -1
    err = dx - dy
    
    while True:
    	pos = float(initial_x), float(initial_y), 0.0
        trace.append(pos)
        
        if initial_x == final_x and initial_y == final_y:
            break
        
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            initial_x += sx
        if e2 < dx:
            err += dx
            initial_y += sy
            
        for _ in range(n - 1):
            if initial_x == final_x and initial_y == final_y:
                break
            pos = float(initial_x), float(initial_y), 0.0
            trace.append(pos)
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                initial_x += sx
            if e2 < dx:
                err += dx
                initial_y += sy
                
    sta.p = trace
    set_position(sta, final_x, final_y)
            
    
               
def create_server(net):
    app = Flask(_name_)
    @app.route('/getPosition', methods=['POST'])
    def get_position():
        number = request.get_json()
        drone = net.get('drone{}'.format(number))
        return jsonify(drone.position)

    @app.route('/setDestiny', methods=['POST'])
    def set_destiny():
        drone_number = request.get_json().get('drone')
        destiny = request.get_json().get('position')
        drone = net.get('drone{}'.format(drone_number))
        set_route(drone, int(drone_number), destiny[0], destiny[1])
        return jsonify(drone.position)  
    
    return app 
    
    
def run_mininet():
    setLogLevel('info')
    create_topology(sys.argv)
    net.build()
    
    ReplayingMobility(net)
    
    server = create_server(net)
    
    th = threading.Thread(target=server.run, kwargs={'debug': False, 'host': '0.0.0.0', 'port': 4993})
    th.daemon=True
    th.start()
    CLI(net)
    net.stop()
    
    
if _name_ == '_main_':
    setLogLevel('info')  
    global net, drones
    
    run_mininet()