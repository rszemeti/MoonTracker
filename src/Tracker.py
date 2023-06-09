import PySimpleGUI as sg
import serial
import serial.tools.list_ports
from skyfield.api import N,S,E, W, wgs84, load
from skyfield import almanac
import time
from datetime import timedelta, timezone

SETTINGS_PATH = '.'

class Target:

    def __init__(self, lat, lon, elev):
        
        self.lat = lat
        self.lon=lon
        self.elev=elev
        
        self.targetlist = [
            ('Moon', 'moon'),
            ('Sun', 'sun'),
            ('Venus', 'venus'),
            ('Jupiter', 'JUPITER BARYCENTER'),
            ('Mars', 'MARS BARYCENTER'),
            ('Saturn', 'SATURN BARYCENTER')
         ]
        
        self.target_dict = {key:value for key, value in self.targetlist}
        
        # Create a timescale and ask the current time.
        self.ts = load.timescale()
        self.is_above_horizon = False
        
        # Load the JPL ephemeris DE440s (covers 1849-2150).
        self.planets = load('de440s.bsp')
        self.earth = self.planets['earth']
        
        # 52.388211 N, 2.304344 W, 69m above sea level
        self.wgs = wgs84.latlon(self.lat, self.lon, self.elev)
        self.home = self.earth + self.wgs
        
    def set_home(self,lat,lon,elev):
        self.lat = lat
        self.lon=lon
        self.elev=elev
        
        self.wgs = wgs84.latlon(self.lat, self.lon, self.elev)
        self.home = self.earth + self.wgs
        
    def run(self, window):
        while True:
            window.write_event_value(('-TARGET-', self.observe()), 'Done!')
            time.sleep(1)  
        
    def observe(self): 
        t = self.ts.now()
        astrometric = self.home.at(t).observe(self.target)
        alt, az, d = astrometric.apparent().altaz()
        if alt.degrees > 0.0:
            self.is_above_horizon = True
        else:
            self.is_above_horizon = False 
        
        return alt.degrees, az.degrees, d, t.astimezone(timezone(timedelta(0)))

    def set_target(self, name):
        self.human_name = name
        self.target_name = self.target_dict[self.human_name]
        try:
            self.target = self.planets[self.target_name]
        except Exception as e:
            sg.eprint("Failed target name")
            sg.eprint(e)
        
    def get_planets(self):
        return self.planets
    
    def get_rise_set(self):
        t0 = self.ts.now() - timedelta(minutes=30)
        t1 = t0 + timedelta(hours=36)
        f = almanac.risings_and_settings(self.planets, self.target, self.wgs)
        t, y = almanac.find_discrete(t0, t1, f)
        return zip(t, y)  


class Device:

    def __init__(self, port, speed):
        self.speed = speed
        self.portId = port
        self.running = False
        self.error=''

    def set_port(self, port):
        self.portId = port

    def set_speed(self, speed):
        self.speed = speed

    def run(self, window):
        
        self.error=''
        window['-COMMSTATUS-'].update('Connecting')
        try:
            self.ser = serial.Serial(
                port=self.portId, \
                baudrate=self.speed, \
                parity=serial.PARITY_NONE, \
                stopbits=serial.STOPBITS_ONE, \
                bytesize=serial.EIGHTBITS, \
                timeout=5)
        
            # this will store the line
            line = []
        
            self.running = True
            window['Disconnect'].update(disabled=False)
            window['-COMMSTATUS-'].update('Connected')
        
            while  self.running:
                for c in self.ser.read():
                    line.append(chr(c))
                    if c == 10:
                        window.write_event_value(('-THREAD-', ''.join(line)), 'Done!')
                        line = []
                        break
            
            self.ser.close()
            window['Connect'].update(disabled=False)
            window['Disconnect'].update(disabled=True)
            window['-COMMSTATUS-'].update('Disconnected')
        except:
            window['Connect'].update(disabled=False)
            window['Disconnect'].update(disabled=True)
            self.error='Unable to open'
        
        window['-COMMSTATUS-'].update(self.error)
    
    def is_running(self): 
        return self.running
    
    def is_stopped(self): 
        return not self.running
                
    def stop(self):
        self.error='Closed'
        self.running = False
        if hasattr(self, 'ser'):
            while self.ser.is_open:
                time.sleep(1)
                
    def send(self, msg):
        if hasattr(self, 'ser') and self.ser.open:
            try:
                self.ser.write(msg.encode())
            except:
                self.error='Closed unexpectedly'
                self.running = False
                self.ser.close()
    
    def get_ports(self):
        return serial.tools.list_ports.comports()
    
    def get_port_speeds(self):
        return list([ 115200, 57600, 38400, 19200, 9600, 4800, 2400, 1200])

        
    def __del__(self):
        self.running = False
        self.ser.close()
        

        
def get_cal_popup():
    cal_pop = [ 
              [sg.Text('Target Position: ', size=15, font=("Arial", 14), justification='right'),
               sg.Text('', size=7, key='-TAR_AZ-', border_width=1, font=("Arial", 14), justification='right'),
               sg.Text('', size=7, key='-TAR_EL-', border_width=1, font=("Arial", 14), justification='right'),
              ],
              [sg.Text('Dish Position: ', size=15, font=("Arial", 14), justification='right'),
               sg.Text('', size=7, key='-CUR_AZ-', border_width=1, font=("Arial", 14), justification='right'),
               sg.Text('', size=7, key='-CUR_EL-', border_width=1, font=("Arial", 14), justification='right'), ],
            ]
    return cal_pop


def the_gui():

    sg.theme('Light Brown 3')
    
    menu_def = [['Settings', ['Home Position', 'Limits', 'Comms' ]], ['About']]
    
    angles = [ 
              [sg.Text('Target Position: ', size=15, font=("Arial", 14), justification='right'),
               sg.Text('', size=7, key='-TAR_AZ-', border_width=1, font=("Arial", 14), justification='right'),
               sg.Text('', size=7, key='-TAR_EL-', border_width=1, font=("Arial", 14), justification='right'),
              ],
              [sg.Text('Dish Position: ', size=15, font=("Arial", 14), justification='right'),
               sg.Text('', size=7, key='-CUR_AZ-', border_width=1, font=("Arial", 14), justification='right'),
               sg.Text('', size=7, key='-CUR_EL-', border_width=1, font=("Arial", 14), justification='right'), ],
            ]
    status = [
              [sg.Text('Comms: ', size=10, font=("Arial", 10), justification='right'),
               sg.Text('Disconnected', size=12, key='-COMMSTATUS-', font=("Arial", 10), justification='left'),
              ],
              [sg.Text('Controller: ', size=10, font=("Arial", 10), justification='right'),
               sg.Text('----', size=12, key='-STATUS-', font=("Arial", 10), justification='left')
              ]
        ]
    times = [
              [sg.Text('Target: ', size=6, font=("Arial", 10), justification='right'),
               sg.Combo(list(target.target_dict.keys()), key='-TARGETNAME-', default_value='Moon', enable_events=True)
              ],
              [sg.Text('Rise:', size=6, font=("Arial", 10), justification='right'),
               sg.Text('---', size=18, key='-RISE-', font=("Arial", 10), justification='left'),
              ],
              [sg.Text('Set:', size=6, font=("Arial", 10), justification='right'),
               sg.Text('---', size=18, key='-SET-', font=("Arial", 10), justification='left')
              ],
              [sg.Text('UTC:', size=6, font=("Arial", 10), justification='right'),
               sg.Text('---', size=18, key='-UTC-', font=("Arial", 10), justification='left')
              ]
        ]

    layout = [[sg.Menu(menu_def)],
              [
                 [ sg.Frame("Status", status, vertical_alignment='top', expand_y=True, expand_x=True),
                  sg.Frame("Times", times, vertical_alignment='bottom', expand_x=True),
                 ]
              ],
              [sg.Frame("Target", angles), sg.Frame("Controls", [[
                    sg.Button('Track', disabled=True),
                    sg.Button('Align', disabled=True),
                    sg.Button('Stop', disabled=True)
                  ]], vertical_alignment='top', expand_y=True, expand_x=True)
              ],
              [sg.Text('Next ...', key='-VERBOSE-')],
              [sg.Text('Port: '), sg.Text(conn.portId, k='-portId-'),
                  sg.Button('Connect', bind_return_key=True),
                  sg.Button('Disconnect', disabled=True),
              ]
            ]

    window = sg.Window('Moon Tracker', layout)
    window.finalize()
    window.start_thread(lambda: target.run(window), ('-TARGET-', '-TARGET ENDED-'))
    update_rise_set(window)

    # --------------------- EVENT LOOP ---------------------
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Exit'):
            break
        elif event == 'Connect':
            try:
                if not conn.is_running():
                    conn.stop()
                    window.start_thread(lambda: conn.run(window), ('-THREAD-', '-THREAD ENDED-'))
                    window['Connect'].update(disabled=True)
            except:
                sg.popup_error("Unknown serial port: "+conn.portId)
        elif event == 'Disconnect':
            window['Connect'].update(disabled=True)
            window['Track'].update(disabled=True)
            window['Stop'].update(disabled=True)
            window['Align'].update(disabled=True)
            conn.stop()
            window['-STATUS-'].update('----')
        elif event == 'Track':
            conn.send('R\n')
        elif event == 'Stop':
            conn.send('S\n')
        elif event == 'Align':
            conn.send('Z\n')
        elif event == 'Moon':
            update_target(window, target.observe())
        elif event[0] == '-THREAD-':
            process_data(window, event[1])
        elif event[0] == '-TARGET-':
            update_target(window, event[1])
        elif event == '-TARGETNAME-':
            if conn.is_running():
                conn.send('S\n')
            target.set_target(values['-TARGETNAME-'])
            update_rise_set(window)
        elif event == 'Comms':
            settings_window()
            window['-portId-'].update(conn.portId)
        elif event == 'Home Position':
            location_settings_window()
    # if user exits the window, then close the window and exit the GUI func
    window.close()
    
    
def make_location_window():

    layout = [[sg.Text('QTH')],
              [sg.Input(sg.user_settings_get_entry('-lat-',52.388211), size=(15), k='-lat-'), sg.Radio('North','north',key='-north-', default=sg.user_settings_get_entry('-north-',True)),sg.Radio('South','north',key='-south-', default=not sg.user_settings_get_entry('-north-',True))],    
              [sg.Input(sg.user_settings_get_entry('-lon-',2.304344), size=(15), k='-lon-'), sg.Radio('West','west',key='-west-', default=sg.user_settings_get_entry('-east-',True)),sg.Radio('East','west',key='-east-',default=not sg.user_settings_get_entry('-east-',True))],
              [sg.Input(sg.user_settings_get_entry('-alt-',69), size=(5), k='-alt-')],          
              [sg.Button('Save'), sg.Button('Exit without saving', k='Exit')]]

    return sg.Window('Location Settings', layout)

def location_settings_window():

    window = make_location_window()

    while True:
        event, values = window.read()
        if event in (sg.WINDOW_CLOSED, 'Exit'):
            window.close()
            break
        if event == 'Save':
            # Save some of the values as user settings
            sg.user_settings_set_entry('-lat-', float(values['-lat-']))
            sg.user_settings_set_entry('-lon-', float(values['-lon-']))
            sg.user_settings_set_entry('-alt-', float(values['-alt-']))
            sg.user_settings_set_entry('-north-', values['-north-'])
            sg.user_settings_set_entry('-west-', values['-west-'])
            target.set_home(
              sg.user_settings_get_entry('-lat-') * (N if sg.user_settings_get_entry('-north-') else S),
              sg.user_settings_get_entry('-lon-') * (W if sg.user_settings_get_entry('-west-') else E),
              sg.user_settings_get_entry('-alt-')
            )
            window.close()
            break;


def make_settings_window():

    layout = [[sg.Text('Serial')],
              [sg.Listbox(conn.get_ports(), default_values=[sg.user_settings_get_entry('-port-')], size=(15, 10), k='-port-')],
              [sg.Listbox(conn.get_port_speeds(), default_values=[sg.user_settings_get_entry('-speed-')], size=(8,1), k='-speed-')],
              [sg.CB('Auto-connect at start', sg.user_settings_get_entry('-option1-', True), k='-auto-')],
              [sg.Button('Save'), sg.Button('Exit without saving', k='Exit')]]

    return sg.Window('Comms Settings', layout)

def settings_window():

    window = make_settings_window()

    while True:
        event, values = window.read()
        if event in (sg.WINDOW_CLOSED, 'Exit'):
            window.close()
            break
        if event == 'Save':
            # Save some of the values as user settings
            sg.user_settings_set_entry('-port-', values['-port-'][0].device)
            sg.user_settings_set_entry('-speed-', values['-speed-'][0])
            sg.user_settings_set_entry('-auto-', values['-auto-'])
            conn.set_port(sg.user_settings_get_entry('-port-'))
            conn.set_speed(sg.user_settings_get_entry('-speed-'))
            window.close()
            break;


def update_rise_set(window):
    window['-RISE-'].update('---')
    window['-SET-'].update('---')
    rise_t=None
    rise=[]
    sets_t=None
    sets=[]
    for ti, yi in target.get_rise_set():
        if yi:
            if rise_t is None:
                window['-RISE-'].update(ti.utc_iso())
                rise_t = ti - target.ts.now()
                rise = divmod(rise_t * 24 * 60, 60)
        else:
            if sets_t is None:
                window['-SET-'].update(ti.utc_iso())
                sets_t = ti - target.ts.now()
                sets = divmod(sets_t * 24 * 60, 60)
            
    if target.is_above_horizon:
        try:
            window['-VERBOSE-'].update(target.human_name + ' is above the horizon and sets in ' + str(int(sets[0])) + ' hours and ' + str(int(sets[1])) + ' minutes')
        except Exception as e:
            sg.eprint("Failed above")
            sg.eprint(e)
            sg.eprint(target.ts.now().utc_datetime())
    else:
        try:
            window['-VERBOSE-'].update(target.human_name + ' is below the horizon and rises in ' + str(int(rise[0])) + ' hours and ' + str(int(rise[1])) + ' minutes')
        except Exception as e:
            sg.eprint("Failed below")
            sg.eprint(e)
            sg.eprint(target.ts.now().utc_datetime())


def update_target(window, data):
    window['-TAR_EL-'].update('{0:.2f}'.format(data[0]))
    window['-TAR_AZ-'].update('{0:.2f}'.format(data[1]))
    window['-UTC-'].update(data[3].strftime("%Y-%m-%dT%H:%M:%SZ"))

    if conn.is_running():
        conn.send('E{0:.2f}\n'.format(data[0]));
        conn.send('A{0:.2f}\n'.format(data[1]));
        
    update_rise_set(window)


def process_data(window, data):
    remote_data = data.split(',')

    if remote_data[0] == "POS":
        window['-CUR_EL-'].update('{0:.2f}'.format(float(remote_data[2])))
        window['-CUR_AZ-'].update('{0:.2f}'.format(float(remote_data[1])))
        
    elif remote_data[0] == 'STATUS':
        stat = remote_data[1].rstrip()
        if stat == 'INIT':
            window['Stop'].update(disabled=True)
            window['Align'].update(disabled=True)
            window['Track'].update(disabled=True)
            window['-STATUS-'].update('Initialising')
        if stat == 'RUN':
            window['Stop'].update(disabled=False)
            window['Align'].update(disabled=True)
            window['Track'].update(disabled=True)
            window['-STATUS-'].update('Tracking')
        elif stat == 'STOP':
            window['Stop'].update(disabled=True)
            window['Align'].update(disabled=False)
            window['Track'].update(disabled=False)
            window['-STATUS-'].update('Stopped')
    
    
if __name__ == '__main__':
    sg.user_settings_filename(path=SETTINGS_PATH)
    conn = Device(sg.user_settings_get_entry('-port-','COM9'),sg.user_settings_get_entry('-speed-',115200))
    target = Target(sg.user_settings_get_entry('lat',52.388211) * (N if sg.user_settings_get_entry('-north-', True) else S), sg.user_settings_get_entry('lon',2.304344) * (W if sg.user_settings_get_entry('-west-', True) else E), 69)
    target.set_target('Moon')
    the_gui()

