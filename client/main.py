import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import socket
import threading
import struct
import io
import pandas as pd
import os

class FrontendClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI Dataset Tagging Tool")
        self.root.geometry("1000x800")

        # define socket
        self.sock = None

        # initialization (this is temporarily)
        self.load_setting_file()
        self.connect_to_server(self.host,self.port)

        # request necessary data
        self.request_data_cnt()
        self.request_csv_tag_info()
        
        # start UI
        self.create_widgets()

        # enter tkinter loop
        self.start_client()

    def load_setting_file(self):
        self.host = '127.0.0.1'
        self.port = 52973

    def create_widgets(self):
        # 主框架
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 图片显示区域 (80%空间)
        self.img_frame = ttk.Frame(self.main_frame)
        self.img_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.image_label = ttk.Label(self.img_frame, background='#f0f0f0')
        self.image_label.pack(fill=tk.BOTH, expand=True)

        # self.button = tk.Button(self.root, text="Click Me", command=self.get_image(1))
        # self.button.pack(pady=20)
    
    def connect_to_server(self,host,port):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            threading.Thread(target=self.receive_data, daemon=True).start()
            # self.request_csv()
        except ConnectionRefusedError:
            messagebox.showerror("ERROR", "Connection Refused. Check if server is running.")

    def get_image(self,index):
        print(f"Requesting image {index}")
        self.img_index = index
        if self.img_cache[index] == None:
            print(f"image {index} not found in cache, sending web request")
            self.request_image(index)
            # show image not found
        else:
            # process image with PIL
            print(f"image {index} found in cache, printing...")
            img_data = self.img_cache[index]
            image = Image.open(io.BytesIO(img_data))
            image.thumbnail((800, 600))  # adjust size
            photo = ImageTk.PhotoImage(image)
                
            self.image_label.config(image=photo)
            self.image_label.image = photo

    def request_image_multiple(self, index1, index2):
        for i in range(index1, index2+1):
            if self.img_cache == None:
                self.request_image(i)
    
    def request_image(self, index):
        self.sock.sendall(b'\xff\x01')
        self.sock.sendall(struct.pack('>I', index))
    
    def request_csv_tag_info(self):
        self.sock.sendall(b'\xff\x02')
    
    def request_csv_change(self,index1,index2,tag_index,status):
        self.sock.sendall(b'\xff\x03')
        self.sock.sendall(struct.pack('>IIIB', index1,index2, tag_index, status))
    
    def request_save(self):
        self.sock.sendall(b'\xff\x04')
    
    def request_data_cnt(self):
        self.sock.sendall(b'\xff\x05')
            
    def receive_data(self):
        while True:
            init_char = self.sock.recv(1)
            if not init_char: break
            else:
                verifier = struct.unpack('B', init_char)[0]
                if verifier != 0xFF: 
                    print(f"Bad byte of {verifier}, dropping byte")
                    continue
            
            print("Reading socket message")
            cmd = struct.unpack('B', self.sock.recv(1))[0]
            
            # receive image
            if cmd == 0x01: 
                data = self.sock.recv(9)
                status, index, img_size = struct.unpack('>BII', data)

                # read data through chunk
                received = 0
                img_data = b''
                while received < img_size:
                    # 4kb per chunk
                    chunk = self.sock.recv(min(4096, img_size - received))
                    if not chunk:
                        raise ConnectionError("Connection closed early")
                    img_data += chunk
                    received += len(chunk)

                self.handle_image(index,img_data)
            
            # receive csv tag
            elif cmd == 0x02:  
                data = self.sock.recv(5)
                status, tag_cnt = struct.unpack('>BI',data)
                alias_list = []
                for i in range(0,tag_cnt):
                    data =  self.sock.recv(4)
                    alias_size = struct.unpack('>I', data)[0]
                    alias_bytes =  self.sock.recv(alias_size)
                    alias = data.decode('utf-8')
                    alias_list.append(alias)
                self.handle_csv_tag(alias_list)
            
            # CSV change completed
            elif cmd == 0x03:
                pass
                
            # save completed
            elif cmd == 0x04:  
                pass
            
            # ask for data size
            elif cmd == 0x05:  
                data = self.sock.recv(5)
                status, data_count = struct.unpack('>BI',data)
                self.handle_data_count(data_count)

            else:
                print(f"Unknown cmd byte {cmd}. Maybe check version?")

    def handle_image(self, index, img_data):
        if not img_data:
            self.image_label.config(image=None)
            self.tag_var.set("")
            return
        
        self.img_cache[index] = img_data

        if index == self.img_index:
            self.get_image(index)
    
    def handle_csv_tag(self,alias_list):
        self.alias_list = alias_list

    def handle_data_count(self,data_count):
        self.data_count = data_count
        self.img_cache = []
        self.labeling_status = []
        for i in range(0,data_count):
            self.img_cache.append(None)
            self.labeling_status.append(False)


    def start_client(self):
        self.root.mainloop()



   

if __name__ == "__main__":
      # Main window
    app = FrontendClient() 
    app.start_client()
    # root.protocol("WM_DELETE_WINDOW", app.on_closing)  # bind action when clicking close
      # Start main event loop
