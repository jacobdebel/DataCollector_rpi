from collections import OrderedDict
from datetime import datetime
from sense_hat import (SenseHat        , DIRECTION_UP    , DIRECTION_DOWN   ,
                       DIRECTION_LEFT  , DIRECTION_RIGHT , DIRECTION_MIDDLE ,
                       ACTION_RELEASED , ACTION_PRESSED)
from time import sleep
from threading import Thread
import sys
import os

# Different colors
y = (255,255,0) # Yellow
r = (255,0,0)   # Red
b = (0,0,255)   # Blue
g = (0,255,0)   # Green
v = (255,0,255) # Violet
w = (255,255,255) # White
_ = (0,0,0)     # No color

# Scroll speed
ss = 0.03

class DataCollector(SenseHat):

    def __init__(self):
        super().__init__()
        self.sensors = OrderedDict([["A", False],
                                   ["T", False],
                                   ["P", False],
                                   ["H", False],
                                   ["G", False],
                                   ["O", False],
                                   ["M", False]])
        self.menu = [sensor for sensor in self.sensors.keys()]
        self.menu.append("S")
        self.menu.append("Q")
        self.menu_letter = self.menu[0]
        self.menu_index = 0
        self.write_freq = 20 # Number of collections
        self.delay = 0.3  # Time between collections
        self.file_name = "SenseLogger.csv" # Default file name for data files. Is renamed later
        self.show_message("Welcome to DataCollector", scroll_speed=ss)
        self.main_menu()

    def file_setup(self):
        # Setup file name
        enabled_detectors = [sensor for sensor in self.sensors if self.sensors[sensor]]
        self.file_name = "".join(enabled_detectors)+"-"+str(datetime.now().replace(microsecond=0))+".csv"

        # Setup header in file
        header = []
        header.append("time")
        if self.sensors["A"]:
            header.extend(["accel_x", "accel_y", "accel_z"])
        if self.sensors["T"]:
            header.append("temp")
        if self.sensors["P"]:
            header.append("pressure")
        if self.sensors["H"]:
            header.append("humidity")
        if self.sensors["G"]:
            header.extend(["gyro_x", "gyro_y", "gyro_z"])
        if self.sensors["O"]:
            header.extend(["pitch", "roll", "yaw"])
        if self.sensors["M"]:
            header.extend(["mag_x", "mag_y", "mag_z"])
        with open(self.file_name,"w") as f:
            f.write(" , ".join(str(value) for value in header) + "\n")

    def get_sense_data(self, start_time):
        """ Returns a list with data from the selected detectors. """
        sense_data = []
        sense_data.append((datetime.now()-start_time).total_seconds())
        if self.sensors["A"]:
            acc = self.get_accelerometer_raw()
            x = acc["x"]
            y = acc["y"]
            z = acc["z"]
            sense_data.extend([x,y,z])
        if self.sensors["T"]:
            sense_data.append(self.get_temperature())
        if self.sensors["P"]:
            sense_data.append(self.get_pressure())
        if self.sensors["H"]:
            sense_data.append(self.get_humidity())
        if self.sensors["G"]:
            gyro = self.get_gyroscope_raw()
            gyro_x = gyro["x"]
            gyro_y = gyro["y"]
            gyro_z = gyro["z"]
            sense_data.extend([gyro_x, gyro_y, gyro_z])
        if self.sensors["O"]:
            orien = self.get_orientation()
            pitch = orien["pitch"]
            roll = orien["roll"]
            yaw = orien["yaw"]
            sense_data.extend([pitch, roll, yaw])
        if self.sensors["M"]:
            mag = self.get_compass_raw()
            mag_x = mag["x"]
            mag_y = mag["y"]
            mag_z = mag["z"]
            sense_data.extend([mag_x, mag_y, mag_z])
        return sense_data

    def log_data(self,data_list,start_time):
        """ Appends collected data to a data list. """
        sense_data = self.get_sense_data(start_time)
        output_string = ",".join(str(value) for value in sense_data)
        data_list.append(output_string)

    def collect_data(self):
        self.show_message("Collecting data", scroll_speed=ss)
        batch_data = []
        start_time = datetime.now()

        # Runs collection of data until the joystick is activated
        # Shows the navigation symbol on the display
        # Is activated if the number of collections is set to zero
        if not self.write_freq:
            self._show_navigation()
            thread = Thread(target=self._thread_wait_for_movement)
            thread.start()
            while thread.is_alive():
                self.log_data(batch_data, start_time)
                sleep(self.delay)
        else:
            thread_collect = Thread(target=self._thread_collect_data,args=(batch_data,start_time))
            thread_collect.start()

            pn = 0 # Used in the annimation below
            while thread_collect.is_alive():
                # Makes an annimation of a dot moving across the display of the sensehat
                # if there is more than 9 collections left
                number = self.write_freq - len(batch_data)
                if number > 9:
                    self.clear()
                    self.set_pixel(pn,4,w)
                    pn = (pn + 1) % 8
                else:
                    # Shows the number of collections left
                    self.show_letter(str(number))
                sleep(self.delay)

        self._write_data(batch_data)

    def _thread_collect_data(self,batch_data, start_time):
        while True:
            self.log_data(batch_data, start_time)
            if len(batch_data) >= self.write_freq:
                break
            sleep(self.delay)

    def _thread_wait_for_movement(self):
        self.stick.wait_for_event(emptybuffer=True)

    def _write_data(self,batch_data):
        """ Writes batch data to the data file """
        with open(self.file_name,"a") as f:
            for line in batch_data:
                f.write(line + "\n")

    def _change_parameter(self, param, param_name, incr_size=0.1):
        """ Internal method used to change either the number of collections or the delay between collections """
        parameter = param
        increment_size = incr_size
        self.show_message("{}: {:.3f}".format(param_name, parameter),scroll_speed=ss)
        while True:
            self._show_navigation()
            event = self.stick.wait_for_event(emptybuffer=True)
            if event.action == ACTION_PRESSED:
                if event.direction == DIRECTION_MIDDLE:
                    break
                if event.direction == DIRECTION_UP:
                    parameter += increment_size 
                    self.show_message("{}: {:.3f}".format(param_name, parameter),scroll_speed=ss)
                if event.direction == DIRECTION_DOWN:
                    if increment_size <= parameter:
                        parameter -= increment_size
                    self.show_message("{}: {:.3f}".format(param_name, parameter),scroll_speed=ss)
                if event.direction == DIRECTION_LEFT:
                    increment_size /= 10
                    self.show_message("increment size: {}".format(increment_size),scroll_speed=ss)
                    continue
                if event.direction == DIRECTION_RIGHT:
                    increment_size *= 10
                    self.show_message("increment size: {}".format(increment_size),scroll_speed=ss)
                    continue
        return parameter


    def _show_navigation(self):
        self.set_pixels([_,_,_,_,_,_,_,_,
                         _,_,_,g,_,_,_,_,
                         _,_,g,g,g,_,_,_,
                         _,y,_,g,_,v,_,_,
                         y,y,y,r,v,v,v,_,
                         _,y,_,b,_,v,_,_,
                         _,_,b,b,b,_,_,_,
                         _,_,_,b,_,_,_,_])


    def choose_delay(self):
        self.delay = self._change_parameter(self.delay, "dt")


    def choose_write_freq(self):
        self.write_freq = int(self._change_parameter(self.write_freq, "freq",incr_size=10))


    def draw_menu(self):
        """ Draws the main menu for choosing detectors """
        if self.menu_letter in ["Q","S"] or not self.sensors[self.menu_letter]:
            self.show_letter(self.menu_letter)
        else:
            self.show_letter(self.menu_letter,r) # Draw in red


    def main_menu(self):
        """ The main menu and the main loop. """
        while True:
            index = self.menu.index(self.menu_letter)
            self.draw_menu()
            event = self.stick.wait_for_event(emptybuffer=True)
            if event.action == ACTION_PRESSED:
                if event.direction == DIRECTION_RIGHT:
                    self.menu_letter = self.menu[(index +1)%len(self.menu)]
                elif event.direction == DIRECTION_LEFT:
                    self.menu_letter = self.menu[(index -1)%len(self.menu)]
                elif self.menu_letter != "Q":
                    if event.direction == DIRECTION_UP:
                        self.sensors[self.menu_letter] = True
                    elif event.direction == DIRECTION_DOWN:
                        self.sensors[self.menu_letter] = False
                if event.direction == DIRECTION_MIDDLE:
                    # Quits the DataCollector program but keeps the RPi running
                    if self.menu_letter == "Q": 
                        self.show_message("Quiting DataCollector",scroll_speed=ss)
                        self.set_pixels([_,_,_,_,_,_,_,_,
                                         w,_,_,_,_,_,_,_,
                                         _,w,_,_,_,_,_,_,
                                         _,_,w,_,_,_,_,_,
                                         _,_,_,w,_,_,_,_,
                                         _,_,w,_,_,_,_,_,
                                         _,w,_,_,_,_,_,_,
                                         w,_,_,_,w,w,w,w])
                        sys.exit(0)
                    # Quits the DataCollector program and shuts down the RPi
                    elif self.menu_letter == "S":
                        self.show_message("Shutting down",scroll_speed=ss)
                        self.clear()
                        os.system('sudo su -c "halt"')  # This part only works on RPi where the root password is unneeded.
                    elif any(self.sensors.values()):
                        self.choose_delay()
                        self.choose_write_freq()
                        self.file_setup()
                        self.collect_data()
                        self.show_message("Finished", scroll_speed=ss)
                    else:
                        self.show_message("No sensors enabled", scroll_speed=ss)

if __name__ == "__main__":
    dataCollector = DataCollector()

