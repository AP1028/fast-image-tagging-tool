import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import socket
import threading
import struct
import io
import pandas as pd
import os
from io import StringIO
import json

default_setting = {
        "host": "127.0.0.1", # socket bind ip address
        "port": 52973, # socket bind port
        "multiple_selection": False,
        "always_save": True,
    }

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def log_network(str):
    print(f'[{bcolors.OKCYAN}SOCK{bcolors.ENDC}] {str}')

def log_ok(str):
    print(f'[{bcolors.OKGREEN} OK {bcolors.ENDC}] {str}')

def log_error(str):
    print(f'[{bcolors.FAIL}FAIL{bcolors.ENDC}] {str}')

def log_info(str):
    print(f'[{bcolors.OKBLUE}INFO{bcolors.ENDC}] {str}')

def log_warn(str):
    print(f'[{bcolors.WARNING}WARN{bcolors.ENDC}] {str}')

class FrontendClient:
    def __init__(self,setting_path='client_setting.json'):
        # define socket
        self.sock = None
        self.connected = False

        # define vars
        self.data_list = []
        self.data_column_list = []

        self.data_cnt = None
        self.tag_cnt = None
        self.img_cache = []
        self.img_error_msg = []
        self.labeling_status = []

        # initialization (this is temporarily)
        self.load_setting_file(setting_path)
        status = self.connect_to_server(self.host,self.port)
        if status == False: sys.exit(1)

        # request necessary data
        # self.request_data_cnt()
        self.request_csv_tag_info()
        self.request_csv_data()
        self.request_clip_data()
        
        # Lock until at least self.tag_cnt is available
        time.sleep(0.5)
        while (self.tag_cnt == None or self.data_cnt == None):
            log_warn('Resend request for self.tag_cnt and self.data_cnt to be loaded.')
            self.request_csv_tag_info()
            self.request_csv_data()
            time.sleep(0.5)
        
        log_ok(f'successfully loaded self.tag_cnt={self.tag_cnt} and self.data_cnt={self.data_cnt}')
        
        # start UI
        self.create_ui()

        # init first image
        self.img_index = 0
        self.init_frame()

        # update ui
        self.update_ui()

        # enter tkinter loop
        self.start_client()

    def load_setting_file(self, setting_path):
        self.host = '127.0.0.1'
        self.port = 52973
        self.multiple_selection = False
        self.always_save = True

        self.img_index = 0
    
    def load_setting_file(self,setting_path):
        try:
            with open(setting_path, 'r') as setting_file:
                setting_data = json.load(setting_file)
                self.configure_setting(setting_data)
                return
         # Error handing
        except FileNotFoundError:
            log_error(f"'{setting_path}' not found.")
            log_info(f"Writing default setting to '{setting_path}'.")
            try:
                with open(setting_path, 'w') as setting_file: # 'w' for write mode (overwrites existing file)
                    json.dump(default_setting, setting_file, indent=4)
                log_ok(f"Default setting written to {setting_path} successfully.")
            except IOError as error:
                log_error(f"An error occurred while writing to {setting_path}: {error}")
        except json.JSONDecodeError:
            log_error(f"Error: Invalid JSON format in '{setting_path}'.")
        
        log_error(f"Client stopped due to problem with settings.")
        sys.exit(1)
        return
    
    def configure_setting(self,setting_data):
        try:
            self.host = setting_data["host"]
        except KeyError:
            log_warn("Missing host in setting, using 127.0.0.1 as default")
            self.host = "127.0.0.1"
        try:
            self.port = setting_data["port"]
        except KeyError:
            log_warn("Missing port in setting, using 52973 as default")
            self.port = 52973
        try:
            self.multiple_selection = setting_data["multiple_selection"]
        except KeyError:
            log_warn("Missing multiple_selection in setting, using false as default")
            self.multiple_selection = False
        try:
            self.always_save = setting_data["always_save"]
        except KeyError:
            log_warn("Missing multiple_selection in setting, using false as default")
            self.always_save = False
        

    def create_ui(self):
        log_info('Building GUI')
        # init
        self.root = tk.Tk()
        self.root.title("AI Dataset Tagging Tool")
        self.root.geometry("1000x800")

        # button style
        self.style = ttk.Style()
        self.style.configure('White.TButton', 
                         background='#f0f0f0', 
                         foreground='black',
                         font=('Arial', 10),
                         padding=5)
    
        self.style.configure('Blue.TButton', 
                            background='#f0f0f0',  # 蓝色
                            foreground='#4a86e8',
                            font=('Arial', 10, 'bold'),
                            padding=5)
        
        self.style.configure('Red.TButton', 
                            background='#f0f0f0',  # 红色
                            foreground='#e74c3c',
                            font=('Arial', 10, 'bold'),
                            padding=5)

        # main frame
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # status bar in main frame
        self.status_bar = ttk.Frame(self.main_frame, height=25, relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, pady=(0, 5))

        # 状态标签
        self.status_label = ttk.Label(
            self.status_bar, 
            text="X/X",
            anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, padx=5)

        # self.scale_var = tk.IntVar()

        self.slider = tk.Scale(self.status_bar, from_=1, to=self.data_cnt, orient=tk.HORIZONTAL, command=self.on_slider_move)
        self.slider.pack(fill=tk.X, expand=True)

        
        # image display (80% space)
        self.img_frame = ttk.Frame(self.main_frame)
        self.img_frame.pack()
        self.img_label = ttk.Label(self.img_frame)
        self.img_label.pack()

        # button area
        self.control_frame = ttk.Frame(self.root, padding=10)
        self.control_frame.pack(fill=tk.X)

        self.prev_btn = ttk.Button(self.control_frame, text="Previous Frame", command=self.prev_image)
        self.prev_btn.pack(side=tk.LEFT, padx=5)
        
        self.next_btn = ttk.Button(self.control_frame, text="Next Frame", command=self.next_image)
        self.next_btn.pack(side=tk.LEFT, padx=5)

        self.next_btn = ttk.Button(self.control_frame, text="Load All Image", command=self.request_all_image)
        self.next_btn.pack(side=tk.LEFT, padx=5)

        self.next_btn = ttk.Button(self.control_frame, text="[S] Save", command=self.request_save)
        self.next_btn.pack(side=tk.LEFT, padx=5)

        self.root.bind('<Left>', self.keyboard_event)
        self.root.bind('<Right>', self.keyboard_event)
        self.root.bind('s', self.keyboard_event)
        self.root.bind('S', self.keyboard_event)

        # label section
        self.labeling_frame = ttk.Frame(self.root, padding=10)
        self.labeling_frame.pack(fill=tk.X)

        self.labeling_button_list = []
        
        for i in range (0,self.tag_cnt):
            button = ttk.Button(
                self.labeling_frame, 
                text=f'[{i+1}] {self.alias_list[i]}', 
                command=lambda idx=i: self.handle_selection(idx)
                )
            self.labeling_button_list.append(button)
            self.labeling_button_list[i].pack(side=tk.LEFT, padx=5)
            self.root.bind(str(i+1), self.keyboard_event)
        # false button
        self.false_button = ttk.Button(
            self.labeling_frame, 
            text='[F] False', 
            command=lambda idx=-1: self.handle_selection(idx)
            )
        self.false_button.pack(side=tk.LEFT, padx=5)
        self.root.bind('F', self.keyboard_event)
        self.root.bind('f', self.keyboard_event)

        # # input section
        # # may change to sub window
        # self.input_frame = ttk.Frame(self.root, padding=10)
        # self.input_frame.pack(fill=tk.X)

        # self.index_jump_input = tk.Entry(self.input_frame)
        # self.index_jump_input.pack(pady=10)

        # self.jump_button = tk.Button(self.input_frame, text="Jump", command=self.jump_button_input)
        # self.jump_button.pack()

        log_ok('GUI building successful')
    
    def connect_to_server(self,host,port):
        log_network(f'Connecting of {host}:{port}')
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(3.0)
            self.sock.connect((host, port))
            self.connected = True
            threading.Thread(target=self.receive_data, daemon=True).start()
            return True

        except (ConnectionRefusedError,socket.timeout) as e:
            log_error(f"Connection failed: {str(e)}")
            messagebox.showwarning("Connection Error", 
                                  f"Failed to connect to server at {host}:{port}\n{str(e)}")
            return False
            
        except Exception as e:
            self.connected = False
            log_error(f"Unexpected connection error: {str(e)}")
            messagebox.showerror("Connection Error", 
                                f"Unexpected error: {str(e)}")
            return False
            
    def is_connected(self):
        if self.sock is None: self.connected = False
        return self.connected and self.sock is not None
    
    def safe_sendall(self,data):
        if not self.is_connected():
            log_error("Cannot send data: not connected to server")
            raise RuntimeError("Cannot send data: not connected to server")
        try:
            self.sock.sendall(data)
        except (socket.error, OSError) as e:
            log_error(f"Error sending data: {str(e)}")
            self.connected = False
            self.close_sock()
            raise RuntimeError(f"Error sending data: {str(e)}")
        except Exception as e:
            log_error(f"Unexpected error sending data: {str(e)}")
            self.connected = False
            self.close_sock()
            raise RuntimeError(f"Unexpected error sending data: {str(e)}")
    
    def close_sock(self):
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None
        
    def reconnect(self):
        if self.is_connected():
            log_info("Already connected, no need to reconnect")
            return
        self.close_sock()
        self.connect_to_server(self.host, self.port)
        if self.is_connected():
            log_ok("Reconnection successful")
    
    def keyboard_event(self,event):
        if event.keysym == 'Left':
            self.prev_image()
        elif event.keysym == 'Right':
            self.next_image()
        elif event.keysym == 's' or event.keysym == 'S':
            self.request_save()
        elif event.keysym == 'f' or event.keysym == 'F':
            self.handle_selection(-1)
            self.next_image()
        else:
            key_num = int(event.keysym)
            if key_num>0 and key_num<=self.tag_cnt and key_num<=9:
                self.handle_selection(key_num-1)
                if self.multiple_selection == False:
                    self.next_image()
    
    def handle_selection(self,tag_index):
        # write to own csv
        # local data_list write
        log_info(f'selecting tag {tag_index}')
        # false tag
        if tag_index == -1:
            for i in range(0,self.tag_cnt):
                self.data_list[self.img_index][i] = False
        # single selection
        elif self.multiple_selection==False:
            self.data_list[self.img_index][tag_index] = True
            for i in range(0,self.tag_cnt):
                if i!=tag_index:
                    self.data_list[self.img_index][i] = False
        # multiple selection
        else:
            self.data_list[self.img_index][tag_index] = not self.data_list[self.img_index][tag_index]
        self.request_csv_change(self.img_index,self.img_index,self.data_list[self.img_index])
        self.update_ui()

    def prev_image(self):
        if self.img_index > 0:
            self.goto_frame(self.img_index-1)

    def next_image(self):
        if self.img_index < self.data_cnt - 1:
            self.goto_frame(self.img_index+1)

    def on_slider_move(self,value):
        self.goto_frame(int(value)-1)

    # wrapper for goto frame, update both image and ui
    def goto_frame(self,index):
        if index<self.data_cnt and index>=0:
            self.img_index = index
            self.init_frame()
            self.update_ui()
        else:
            return

    # update things on the screen
    def init_frame(self):
        log_info(f"Printing frame with index {self.img_index}")
        # image out of bound
        if self.img_index < 0 or self.img_index >= self.data_cnt:
            self.img_label.image = None
            self.img_label.config(image='')

            self.img_label.config(
            text=f"Image {self.img_index} out of bound!\n Contact developer.",  
            foreground="white", background="gray",font=("Arial", 24), anchor="center", justify="center"
            )
        # image not in cache
        elif self.img_cache[self.img_index] == None:
            # no error, still waiting
            if self.img_error_msg[self.img_index] == None:
                log_info(f"Image {self.img_index} not found in cache, sending web request")
                self.request_image(self.img_index)

                self.img_label.image = None
                self.img_label.config(image='')

                self.img_label.config(
                text=f"Image {self.img_index+1} requested\n Waiting for server response.", 
                foreground="white", background="gray", font=("Arial", 12), anchor="center", justify="center"
                )
            # error, print error msg
            else:
                self.img_label.image = None
                self.img_label.config(image='')

                error_msg = self.img_error_msg[self.img_index]
                
                self.img_label.config(
                text=f"Remote server responded with the following error:\n {error_msg}", 
                foreground="white",background="gray", font=("Arial", 12), wraplength=600,anchor="center", justify="center" 
                )
        # image in cache, process and print image with PIL
        else:
            log_info(f"Image {self.img_index} found in cache, printing...")
            img_data = self.img_cache[self.img_index]
            image = Image.open(io.BytesIO(img_data))
            image.thumbnail((796, 448))  # adjust size
            photo = ImageTk.PhotoImage(image)
                
            self.img_label.config(image=photo)
            self.img_label.image=photo
    
    def update_ui(self):
        # buttons
        for i in range(0,self.tag_cnt):
            if self.data_list[self.img_index][i]:
                self.labeling_button_list[i].config(style='Blue.TButton')
            else:
                self.labeling_button_list[i].config(style='White.TButton')
        if True in self.data_list[self.img_index]:
            self.false_button.config(style='White.TButton')
        else:
            self.false_button.config(style='Blue.TButton')

        self.status_label.config(text=f'{self.img_index+1}/{self.data_cnt}')

        # slider
        self.slider.set(self.img_index+1)

        log_ok('UI status updated')
    
    def request_image(self, index):
        log_network(f'Request image {index}')
        try:
            self.safe_sendall(b'\xff\x01')
            self.safe_sendall(struct.pack('>I', index))
        except RuntimeError as e:
            messagebox.showwarning("Connection error", 
                        f"{e}")

    def request_all_image(self):
        log_info(f'Request all image')
        for i in range(0,self.data_cnt):
            if self.img_cache[i] == None:
                self.request_image(i)

    def request_csv_tag_info(self):
        log_network(f'Request csv tag')
        try:
            self.safe_sendall(b'\xff\x02')
        except RuntimeError as e:
            messagebox.showwarning("Connection error", 
                        f"{e}")

    def request_csv_change(self,index1,index2,write_list):
        log_network(f'Request csv change')
        log_network(f'List to send: {write_list}')
        try:
            self.safe_sendall(b'\xff\x03')
            self.safe_sendall(struct.pack('>III', index1,index2, self.tag_cnt ))
            for i in range(0,self.tag_cnt):
                if write_list[i]:
                    log_info(f'Sending True for tag {i} {self.alias_list[i]}')
                    self.safe_sendall(b'\x01')
                else:
                    log_info(f'Sending False for tag {i} {self.alias_list[i]}')
                    self.safe_sendall(b'\x00')
            # autosave when writing
            if(self.always_save):
                self.request_save()
        except RuntimeError as e:
            messagebox.showwarning("Connection error", 
                        f"{e}")
    
    def request_save(self):
        log_network(f'Request save')
        try:
            self.safe_sendall(b'\xff\x04')
        except RuntimeError as e:
            messagebox.showwarning("Connection error", 
                        f"{e}")
    
    def request_clip_data(self):
        log_network(f'Request clip data')
        try:
            self.safe_sendall(b'\xff\x05')
        except RuntimeError as e:
            messagebox.showwarning("Connection error", 
                        f"{e}")
    
    def request_csv_data(self):
        log_network(f'Request csv data')
        try:
            self.safe_sendall(b'\xff\x06')
        except RuntimeError as e:
            messagebox.showwarning("Connection error", 
                        f"{e}")
    
    def safe_recv(self,size):
        self.sock.settimeout(30.0)
        data = bytearray()
        while len(data) < size:
            try:
                packet = self.sock.recv(size - len(data))
                if not packet:
                    log_error("Socket connection broken")
                data.extend(packet)
            except socket.timeout:
                log_error(f"Timeout, expected length: {size}, received: {len(data)}")
                messagebox.showwarning("Connection error", 
                        f"Timeout, expected length: {size}, received: {len(data)}")
        return bytes(data)

    def receive_data(self):
        log_network(f'Connection established, listening for data')
        try:
            while True:
                self.sock.settimeout(None)
                init_char = self.sock.recv(1)
                if not init_char: break
                else:
                    verifier = struct.unpack('B', init_char)[0]
                    if verifier != 0xFF: 
                        log_network(f"Bad byte of {verifier}, dropping byte")
                        continue
                
                log_network("Header matched, reading socket message")
                cmd = struct.unpack('B', self.safe_recv(1))[0]
                # receive image
                if cmd == 0x01: 
                    self.receive_image()
                # receive csv tag
                elif cmd == 0x02:  
                    self.receive_csv_tag()
                # CSV change completed
                elif cmd == 0x03:
                    self.receive_csv_change_msg()
                # save completed
                elif cmd == 0x04:  
                    self.receive_csv_save_msg()
                # clip data
                elif cmd == 0x05:  
                    self.receive_clip_data()
                # receive csv data
                elif cmd == 0x06:  
                    self.receive_csv_data()
                else:
                    log_warn(f"Unknown cmd byte {cmd}. Maybe check version?")
                    
        except ConnectionResetError:
            log_error("Connection reset by server")
            messagebox.showwarning("Connection error", 
                        f"Connection reset by server")
            self.connected = False
        except socket.timeout:
            log_error("Socket timeout, connection may be lost")
            messagebox.showwarning("Connection error", 
                        f"Socket timeout, connection may be lost")
            self.connected = False
        except Exception as e:
            log_error(f"Unexpected error in receive_data: {str(e)}")
            messagebox.showwarning("Connection error", 
                        f"Unexpected error in receive_data: {str(e)}")
            self.connected = False
        finally:
            if self.sock:
                try:
                    self.sock.close()
                except:
                    pass
                self.sock = None
    
    def receive_image(self):
        data = self.safe_recv(5)
        status, index = struct.unpack('>BI', data)
        # read data through chunk
        if status == 0x00:
            # unset failed state
            self.img_error_msg[index] = None

            data = self.safe_recv(4)
            img_size = struct.unpack('>I', data)[0]
            received = 0
            img_data = b''
            while received < img_size:
                # 4kb per chunk
                chunk = self.safe_recv(min(4096, img_size - received))
                if not chunk:
                    log_warn('Connection closed early')
                img_data += chunk
                received += len(chunk)
            self.handle_image(index,img_data)
            log_network(f"Received image {index}")
        else:
            log_warn(f"Server respond with error with image {index}")
            data = self.safe_recv(4)
            error_size = struct.unpack('>I', data)[0]
            data = self.safe_recv(error_size)
            error_msg = data.decode('utf-8')
            log_warn(f"Error received: {error_msg}")
            self.img_error_msg[index] = error_msg

            if self.img_index == index:
                self.init_frame()
    def receive_csv_tag(self):
        data = self.safe_recv(5)
        status, self.tag_cnt = struct.unpack('>BI',data)
        alias_list = []
        for i in range(0,self.tag_cnt):
            data =  self.safe_recv(4)
            alias_size = struct.unpack('>I', data)[0]
            alias_bytes =  self.safe_recv(alias_size)
            alias = alias_bytes.decode('utf-8')
            alias_list.append(alias)
        log_network("Receive csv tag")
        self.handle_csv_tag(alias_list)
    def receive_csv_change_msg(self):
        data = self.safe_recv(1)
        status = struct.unpack('>B',data)[0]
        if status == 0x00:
            log_ok(f"CSV change complete.")
        else:
            log_warn(f"CSV change failed!")
            messagebox.showwarning("Server error", 
                        f"Server failed to change CSV data. Check server console.")
    def receive_csv_save_msg(self):
        data = self.safe_recv(1)
        status = struct.unpack('>B',data)[0]
        if status == 0x00:
            log_ok(f"Save complete.")
        else:
            log_warn(f"Save failed!")
            messagebox.showwarning("Server error", 
                        f"Server failed to save the csv file. Check server console.")
    
    def receive_clip_data(self):
        data = self.safe_recv(1)
        status = struct.unpack('>B',data)[0]
        if status == 0x00:
            log_network(f"Receiving clip data")
            data = self.safe_recv(4)
            self.clip_cnt = struct.unpack('>I', data)[0]
            self.clip_list = []
            for i in self.clip_cnt:
                clip = {}
                data = self.safe_recv(12)
                clip['begin'],clip['end'],clip['cam'] = struct.unpack('>III', data)
                self.clip_list.append(clip)
            self.handle_clip_data()
        else:
            log_error(f'Error in receiving clip data')
    
    def receive_csv_data(self):
        log_network("receiving csv data")
        data = self.safe_recv(5)
        status, csv_size = struct.unpack('>BI', data)
        # read data through chunk
        if status == 0x00:
            received = 0
            csv_bytes = b''
            while received < csv_size:
                # 4kb per chunk
                chunk = self.safe_recv(min(4096, csv_size - received))
                if not chunk:
                    log_warn('Connection closed early')
                csv_bytes += chunk
                received += len(chunk)
            self.handle_csv(csv_bytes)
        else:
            pass

    def handle_image(self, index, img_data):
        if not img_data:
            self.image_label.config(image=None)
            self.tag_var.set("")
            return
        
        self.img_cache[index] = img_data

        if index == self.img_index:
            self.init_frame()
    
    def handle_csv_tag(self,alias_list):
        self.alias_list = alias_list
    
    def handle_csv(self,csv_bytes):
        csv_str = csv_bytes.decode('utf-8')
        csv_data = pd.read_csv(StringIO(csv_str))
        self.data_list = csv_data.values.tolist()
        self.data_column_list = csv_data.columns.tolist()

        self.data_cnt = len(self.data_list)
        self.img_cache = []
        self.img_error_msg = []
        self.labeling_status = []
        for i in range(0,self.data_cnt):
            self.img_cache.append(None)
            self.img_error_msg.append(None)
            self.labeling_status.append(False)
        
        log_info(f"CSV list received with size of {len(self.data_list)}")
    
    def handle_clip_data(self):
        # self.clip_data = []
        
        # verify all clip cover all the images
        for i in range(0,self.clip_cnt-1):
            if self.clip_list[i]['end'] != self.clip_list[i+1]['begin']:
                log_error(f'Broken clip data! clip {i} end {self.clip_list[i]['end']}, clip {i+1} begin {self.clip_list[i+1]['begin']}')
        
        self.combined_entry_list = []
        self.combined_clip_list = []
        
        for clip in self.clip_list:
            combined_clip_begin_index = len(self.combined_entry_list)
            
            for i in range(clip['begin'],clip['end'],clip['cam']):
                combined_entry = []
                for j in range(i,i+clip['cam']):
                    combined_entry.append(j)
                self.combined_entry_list.append(combined_entry)
                
            combined_clip_end_index = len(self.combined_entry_list)
            
            for i in range(clip['begin'],clip['end'],clip['cam']):
                combined_clip = (combined_clip_begin_index,combined_clip_end_index)
                self.combined_clip_list.append(combined_clip)
            
        
        

    def start_client(self):
        log_info('Starting GUI')
        self.root.mainloop()

if __name__ == "__main__":
      # Main window
    app = FrontendClient() 
    app.start_client()
    # root.protocol("WM_DELETE_WINDOW", app.on_closing)  # bind action when clicking close
      # Start main event loop
