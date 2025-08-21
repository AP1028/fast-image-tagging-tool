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
        
        self.combined_entry_list_cnt = None
        self.combined_clip_list_cnt = None
        self.widget_order = []

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
        while (self.tag_cnt == None or self.data_cnt == None or self.combined_clip_list_cnt == None):
            log_warn('Resend request for self.tag_cnt and self.data_cnt to be loaded.')
            self.request_csv_tag_info()
            self.request_csv_data()
            time.sleep(0.5)
        
        log_ok(f'successfully loaded self.tag_cnt={self.tag_cnt} and self.data_cnt={self.data_cnt}')
        
        # start UI
        self.create_ui()

        # init first image
        # self.img_index = 0
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
        # try:
        #     self.always_save = setting_data["always_save"]
        # except KeyError:
        #     log_warn("Missing multiple_selection in setting, using false as default")
        #     self.always_save = False
        # auto save
        try:
            self.autosave = setting_data["autosave"]
            if self.autosave == 0: self.autosave = 1
        except KeyError:
            log_warn("Missing autosave in setting, using 1 as default")
            self.autosave = 1
        

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

        self.slider = tk.Scale(self.status_bar, from_=1, to=self.combined_entry_list_cnt, orient=tk.HORIZONTAL, command=self.on_slider_move)
        self.slider.pack(fill=tk.X, expand=True)
        
        # === MODIFIED SECTION STARTS HERE ===
        # Create scrollable frame for widgets
        self.scroll_canvas = tk.Canvas(self.main_frame, bg="white")
        self.scroll_canvas.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Add vertical scrollbar
        self.v_scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.scroll_canvas.yview)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure canvas scrolling
        self.scroll_canvas.configure(yscrollcommand=self.v_scrollbar.set)
        
        # Create frame inside canvas for widgets
        self.widget_frame = ttk.Frame(self.scroll_canvas)
        self.canvas_window = self.scroll_canvas.create_window((0, 0), window=self.widget_frame, anchor="nw")
        
        # Bind events for scrolling and resizing
        self.widget_frame.bind("<Configure>", self._on_frame_configure)
        self.scroll_canvas.bind("<Configure>", self._on_canvas_configure)
        self.scroll_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Make canvas focusable for keyboard events
        self.scroll_canvas.focus_set()
        self.scroll_canvas.bind("<Up>", self._on_scroll_up)
        self.scroll_canvas.bind("<Down>", self._on_scroll_down)
        # === MODIFIED SECTION ENDS HERE ===
        
        # create list for all cameras
        self.widget_list = []
        
        self.combined_index=0
        

        self.control_frame = ttk.Frame(self.root, padding=10)
        self.control_frame.pack(fill=tk.X)

        self.prev_btn = ttk.Button(self.control_frame, text="Previous Frame", command=self.prev_img_group)
        self.prev_btn.pack(side=tk.LEFT, padx=5)
        
        self.next_btn = ttk.Button(self.control_frame, text="Next Frame", command=self.next_img_group)
        self.next_btn.pack(side=tk.LEFT, padx=5)

        self.next_btn = ttk.Button(self.control_frame, text="Load All Image", command=self.request_all_image)
        self.next_btn.pack(side=tk.LEFT, padx=5)

        self.next_btn = ttk.Button(self.control_frame, text="[S] Save", command=self.request_save)
        self.next_btn.pack(side=tk.LEFT, padx=5)

        self.root.bind('<Left>', self.keyboard_event)
        self.root.bind('<Right>', self.keyboard_event)
        self.root.bind('s', self.keyboard_event)
        self.root.bind('S', self.keyboard_event)

        # ADD THIS LINE:
        self.root.bind("<Button-1>", self._on_canvas_click)

        log_ok('GUI building successful')
    
    # Add these new methods to the FrontendClient class:

    def _on_frame_configure(self, event):
        """Reset the scroll region to encompass the inner frame"""
        self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        """Configure the inner frame size when canvas size changes"""
        # Update the inner frame width to match canvas width
        canvas_width = event.width
        self.scroll_canvas.itemconfig(self.canvas_window, width=canvas_width)

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        self.scroll_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _on_scroll_up(self, event):
        """Handle up arrow key scrolling"""
        self.scroll_canvas.yview_scroll(-1, "units")
        return "break"  # Prevent default behavior

    def _on_scroll_down(self, event):
        """Handle down arrow key scrolling"""
        self.scroll_canvas.yview_scroll(1, "units")
        return "break"  # Prevent default behavior
    
    def _on_canvas_click(self, event):
        """Set focus to canvas when clicked for keyboard scrolling"""
        self.scroll_canvas.focus_set()
    
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
    
    def get_combined_index_list(self):
        return self.combined_entry_list[self.combined_index]
    
    def keyboard_event(self,event):
        log_info(f"key: {event}")
        if event.keysym == 'Left':
            self.prev_img_group()
        elif event.keysym == 'Right':
            self.next_img_group()
        elif event.keysym == 's' or event.keysym == 'S':
            self.request_save()
        else:
            key_num = int(event.keysym)
            log_info(f"key_num: {key_num}")
            if key_num>0 and key_num<=9:
                log_info(f"call: {key_num}")
                self.handle_selection(key_num)
                if self.multiple_selection == False and self.get_cam_cnt()<=1:
                    self.next_img_group()
                    pass
                    
    def keyboard_event_false(self,event):
        if event.keysym == 'f' or event.keysym == 'F':
            self.handle_selection_false(-1)
            self.next_img_group()
            
    def handle_selection_false(self,group_index):
        if group_index == -1:
            for img_index in self.get_combined_index_list():
                for i in range(0,self.tag_cnt):
                    self.data_list[img_index][i] = False
                self.request_csv_change(img_index,img_index,self.data_list[img_index])
        else:
            img_index = self.get_combined_index_list()[group_index]
            for i in range(0,self.tag_cnt):
                self.data_list[img_index][i] = False
            self.request_csv_change(img_index,img_index,self.data_list[img_index])
                
        # self.request_csv_change(img_index,img_index,self.data_list[img_index])
        self.update_ui()
    
    def handle_selection(self,key_num):
        key_num-=1
        tag_index = key_num % self.tag_cnt
        img_index = self.get_combined_index_list()[self.widget_order[int(key_num / self.tag_cnt)]]
        # write to own csv
        # local data_list write
        log_info(f'selecting tag {tag_index}, alias {self.alias_list[tag_index]}')
        # false tag
        
        # single selection
        if self.multiple_selection==False:
            self.data_list[img_index][tag_index] = True
            for i in range(0,self.tag_cnt):
                if i!=tag_index:
                    self.data_list[img_index][i] = False
        # multiple selection
        else:
            self.data_list[img_index][tag_index] = not self.data_list[img_index][tag_index]
        self.request_csv_change(img_index,img_index,self.data_list[img_index])
        self.update_ui()

    def prev_img_group(self):
        if self.combined_index > 0:
            self.goto_img_group(self.combined_index-1)

    def next_img_group(self):
        if self.combined_index < self.combined_entry_list_cnt - 1:
            self.goto_img_group(self.combined_index+1)

    def on_slider_move(self,value):
        self.goto_img_group(int(value)-1)

    # wrapper for goto frame, update both image and ui
    def goto_img_group(self,index):
        if index<self.combined_entry_list_cnt and index>=0:
            self.combined_index = index
            self.init_frame()
            self.update_ui()
        else:
            return
    
    def get_cam_cnt(self):
        return len(self.get_combined_index_list())
    
    def init_frame(self):
        if self.get_cam_cnt()!=len(self.widget_list):
            log_info('Destroy frames due to mismatch')
            for widget in self.widget_list:
                widget.destroy_all()
                self.widget_order = []
            log_info(f'Create {self.get_cam_cnt()} frame')
            self.widget_list = []
            for i in range(0,self.get_cam_cnt()):
                self.widget_order.append(i)
            for i in self.widget_order:
                self.widget_list.append(DisplayWidget(self.widget_frame,i,self))
        
        for widget in self.widget_list:
            widget.display_img()
    
    def update_order(self):
        for widget in self.widget_list:
            widget.destroy_all()
        self.widget_list = []
        for i in self.widget_order:
            self.widget_list.append(DisplayWidget(self.widget_frame,i,self))
        
        # === ADD THIS LINE ===
        # Trigger frame reconfigure to update scroll region
        self.widget_frame.update_idletasks()
        self._on_frame_configure(None)
        
    
    def update_ui(self):
        for widget in self.widget_list:
            widget.update_ui()
        
        # label
        self.status_label.config(text=f'{self.combined_index+1}/{self.combined_entry_list_cnt}')

        # slider
        self.slider.set(self.combined_index+1)
        pass
    
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
            if(index1%self.autosave == 0 or index1 == self.data_cnt):
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

            if index in self.get_combined_index_list():
                self.root.after(0,self.init_frame())
            
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
            for i in range(0,self.clip_cnt):
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
            log_warn("empty image data")
            return
        
        image = Image.open(io.BytesIO(img_data))
        
        # image.thumbnail((796, 448))  # adjust size
        # photo = ImageTk.PhotoImage(image)
        
        self.img_cache[index] = image

        for i in range(0,len(self.get_combined_index_list())):
            if index == self.get_combined_index_list()[i]:
                self.root.after(0,self.init_frame())
    
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
        
        self.combined_entry_list_cnt = None
        self.combined_clip_list_cnt = None
        
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
        
        self.combined_entry_list_cnt = len(self.combined_entry_list)
        self.combined_clip_list_cnt = len(self.combined_clip_list)
    
    def change_widget_order(self,pos_index, dir):
        log_info("try to change order")
        if(dir == 1):
            log_info(">>")
            if len(self.widget_order)-1>pos_index:
                temp = self.widget_order[pos_index+1]
                self.widget_order[pos_index+1] = self.widget_order[pos_index]
                self.widget_order[pos_index] = temp
        elif(dir == -1):
            if pos_index>0:
                log_info("<<")
                temp = self.widget_order[pos_index-1]
                self.widget_order[pos_index-1] = self.widget_order[pos_index]
                self.widget_order[pos_index] = temp
        self.update_order()
        self.init_frame()
        self.update_ui()
        log_info(f"order: {self.widget_order}")
        
            
    def start_client(self):
        log_info('Starting GUI')
        self.root.mainloop()
    
class DisplayWidget():
    def __init__(self,widget_frame,group_index,outer):
        self.group_index = group_index
        log_info(f'Init {self.group_index}')
        self.init = True
        # self.in_print = False
        # self.in_update = False
        self.is_deleted = False
        for i in range(0,len(outer.widget_order)):
            if group_index == outer.widget_order[i]:
                self.order_index = i
                break

        self.outer = outer
        
        # === MODIFIED SECTION STARTS HERE ===
        # Calculate grid position for wrapping layout
        try:
            window_width = self.outer.scroll_canvas.winfo_width()
            if window_width <= 1:  # Canvas not yet rendered
                window_width = 1000  # Use default window width
        except:
            window_width = 1000  # Fallback
        
        widgets_per_row = max(1, window_width // 820)  # 820 = widget width + padding
        row = self.order_index // widgets_per_row
        col = self.order_index % widgets_per_row
        
        # UI stuff - image display frame
        self.img_frame = ttk.Frame(widget_frame)
        self.img_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nw")
        # === MODIFIED SECTION ENDS HERE ===
        
        self.img_canvas = tk.Canvas(self.img_frame, width=796, height=448, bg="gray")
        self.img_canvas.pack()
        
        self.label_frame = ttk.Frame(self.img_frame)
        self.label_frame.pack(side=tk.TOP, padx=5, pady=5)
        
        self.labeling_button_list = []
        for i in range (0,self.outer.tag_cnt):
            button = ttk.Button(
                self.label_frame, 
                text=f'[{i+1+self.order_index*self.outer.tag_cnt}] {self.outer.alias_list[i]}', 
                command=lambda idx=i+1+self.order_index*self.outer.tag_cnt: self.outer.handle_selection(idx)
                )
            self.labeling_button_list.append(button)
            self.labeling_button_list[i].pack(side=tk.LEFT, padx=5)
            
            log_info(f'bind key {str(i+1+self.order_index*self.outer.tag_cnt)}')
            self.outer.root.bind(str(i+1+self.order_index*self.outer.tag_cnt), self.outer.keyboard_event)
            
        # false button
        self.false_button = ttk.Button(
            self.label_frame, 
            text='[F] False', 
            command=lambda idx=group_index: self.outer.handle_selection_false(idx)
            )
        self.false_button.pack(side=tk.LEFT, padx=5)
        
        self.outer.root.bind('F', self.outer.keyboard_event_false)
        self.outer.root.bind('f', self.outer.keyboard_event_false)
        
        self.control_frame = ttk.Frame(self.img_frame)
        self.control_frame.pack(side=tk.TOP, padx=5, pady=5)
        
        self.order_left = ttk.Button(
            self.control_frame, 
            text='<<', 
            command=lambda idx1=self.order_index, idx2=-1: self.outer.change_widget_order(idx1,idx2)
            )
        self.order_left.pack(side=tk.LEFT, padx=5)
        
        self.order_right = ttk.Button(
            self.control_frame, 
            text='>>', 
            command=lambda idx1=self.order_index, idx2=1: self.outer.change_widget_order(idx1,idx2)
            )
        self.order_right.pack(side=tk.LEFT, padx=5)
        self.init = False
        
    def display_img(self):
        if self.is_deleted == True or self.init == True: return
        
        if self.img_canvas.winfo_exists == False: 
            log_error(f'Unexpected error. self.is_deleted: {self.is_deleted}, self.init: {self.init} self.group_index: {self.group_index}')  # Remove img_index reference
            sys.exit(1)

        # log_info(f'get_combined_index_list: {self.outer.get_combined_index_list()}')
        # log_info(f'self.group_index: {self.group_index}')
        if self.group_index>=len(self.outer.get_combined_index_list()): log_error("Out of bound!")

        img_index = self.outer.get_combined_index_list()[self.group_index]
        
        log_info(f"Printing frame with index {img_index}")
        self.img_canvas.delete("all")
        # image out of bound
        if img_index < 0 or img_index >= self.outer.data_cnt:
            self.img_canvas.create_text(
            398, 224,  # Center position
            text=f"Image {img_index} out of bound!\nContact developer.",
            fill="white", font=("Arial", 24),
            anchor="center", justify="center"
            )
        # image not in cache
        elif self.outer.img_cache[img_index] == None:
            # no error, still waiting
            if self.outer.img_error_msg[img_index] == None:
                log_info(f"Image {img_index} not found in cache, sending web request")
                self.outer.request_image(img_index)
                self.img_canvas.create_text(
                398, 224,  # Center position
                text=f"Image {img_index+1} requested\nWaiting for server response.",
                fill="white", font=("Arial", 12),
                anchor="center", justify="center"
                )
            # error, print error msg
            else:

                error_msg = self.outer.img_error_msg[img_index]
                
                self.img_canvas.create_text(
                398, 224,  # Center position
                text=f"Remote server responded with the following error:\n{error_msg}",
                fill="white", font=("Arial", 12),
                width=600, anchor="center", justify="center"
                )
        # image in cache, process and print image with PIL
        else:
            log_info(f"Image {img_index} found in cache, printing...")
            
            image = self.outer.img_cache[img_index]
            
            image.thumbnail((796, 448))  # adjust size
            photo = ImageTk.PhotoImage(image)
                
            self.img_canvas.image = photo
            self.img_canvas.delete("all")
            self.img_canvas.create_image(0, 0, anchor="nw", image=photo)
            
    def update_ui(self):
        if self.is_deleted == True or self.init == True: return

        img_index = self.outer.get_combined_index_list()[self.group_index]

        # buttons
        for i in range(0,self.outer.tag_cnt):
            if self.outer.data_list[img_index][i]:
                self.labeling_button_list[i].config(style='Blue.TButton')
            else:
                self.labeling_button_list[i].config(style='White.TButton')
        if True in self.outer.data_list[img_index]:
            self.false_button.config(style='White.TButton')
        else:
            self.false_button.config(style='Blue.TButton')

        log_ok('UI status updated')
        
    def destroy_all(self):
        self.is_deleted = True


        # 解绑所有键盘事件
        try:
            for i in range(0, self.outer.tag_cnt):
                self.outer.root.unbind(str(i+1+self.group_index*self.outer.tag_cnt))
            self.outer.root.unbind('F')
            self.outer.root.unbind('f')
        except:
            pass

        self.order_left.destroy()
        self.order_right.destroy()
        self.control_frame.destroy()

        for button in self.labeling_button_list:
            button.destroy()
        self.false_button.destroy()
        self.label_frame.destroy()
        
        # 销毁画布和框架
        self.img_canvas.destroy()
        self.img_frame.destroy()
        
        # 清空引用列表
        self.labeling_button_list = []
    

if __name__ == "__main__":
      # Main window
    app = FrontendClient() 
    app.start_client()
    # root.protocol("WM_DELETE_WINDOW", app.on_closing)  # bind action when clicking close
      # Start main event loop
