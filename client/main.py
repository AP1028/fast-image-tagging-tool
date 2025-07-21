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

        # init first image
        self.get_image(self.img_index)

        # enter tkinter loop
        self.start_client()

    def load_setting_file(self):
        self.host = '127.0.0.1'
        self.port = 52973

        self.img_index = 0
        self.multiple_selection = False

    def create_widgets(self):
        # main frame
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
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

        self.next_btn = ttk.Button(self.control_frame, text="SAVE", command=self.request_save)
        self.next_btn.pack(side=tk.LEFT, padx=5)

        self.root.bind('<Left>', self.keyboard_event)
        self.root.bind('<Right>', self.keyboard_event)
        self.root.bind('s', self.keyboard_event)
        self.root.bind('S', self.keyboard_event)

        # label section
        self.labeling_frame = ttk.Frame(self.root, padding=10)
        self.labeling_frame.pack(fill=tk.X)


        self.labeling_button_list = []
        # single choice
        for i in range (0,self.tag_cnt):
            button = ttk.Button(
                self.labeling_frame, 
                text=self.alias_list[i], 
                command=lambda idx=i: self.handle_selection(idx)
                )
            self.labeling_button_list.append(button)
            self.labeling_button_list[i].pack(side=tk.LEFT, padx=5)
            self.root.bind(str(i+1), self.keyboard_event)
        # multiple choice
        # ...
        # false button
        false_button = ttk.Button(
            self.labeling_frame, 
            text='FALSE', 
            command=lambda idx=-1: self.handle_selection(idx)
            )
        false_button.pack(side=tk.LEFT, padx=5)
        self.root.bind('F', self.keyboard_event)
        self.root.bind('f', self.keyboard_event)

        
    
    def connect_to_server(self,host,port):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            threading.Thread(target=self.receive_data, daemon=True).start()
            # self.request_csv()
        except ConnectionRefusedError:
            messagebox.showerror("ERROR", "Connection Refused. Check if server is running.")\
    
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
        print(f'selecting tag {tag_index}')
        if tag_index == -1:
            for i in range(0,self.tag_cnt):
                self.request_csv_change(self.img_index, self.img_index, i, False)
        elif self.multiple_selection==False:
            self.request_csv_change(self.img_index, self.img_index, tag_index, True)
            for i in range(0,self.tag_cnt):
                if i!=tag_index:
                    self.request_csv_change(self.img_index, self.img_index, i, False)
        else:
            # TO DO: multiple selection
            pass


    def prev_image(self):
        if self.img_index > 0:
            self.get_image(self.img_index-1)

    def next_image(self):
        if self.img_index < self.data_cnt - 1:
            self.get_image(self.img_index + 1)

    def get_image(self,index):
        print(f"Requesting image {index}")
        self.img_index = index

        if index < 0 or index >= self.data_cnt:
            self.img_label.image = None
            self.img_label.config(image='')

            self.img_label.config(
            text=f"Image {index} out of bound!",  # 错误信息
            foreground="white",  # 文字颜色
            background="gray",  # 背景颜色
            font=("Arial", 24),  # 字体大小
            anchor="center",  # 文字居中
            justify="center"  # 多行文字居中
            )
            # 确保标签有足够大小显示文字
            self.img_label.config(width=800, height=600)

        elif self.img_cache[index] == None:
            if self.img_error_msg[index] == None:
                print(f"image {index} not found in cache, sending web request")
                self.request_image(index)

                self.img_label.image = None
                self.img_label.config(image='')

                # show image not found
                # fake_image = Image.new("RGB", (800, 600), "gray")
                # fake_photo = ImageTk.PhotoImage(fake_image)
                # self.img_label.config(image=fake_photo)
                # self.img_label.image=fake_photo

                self.img_label.config(
                text=f"Image {index} not available",  # 错误信息
                foreground="white",  # 文字颜色
                background="gray",  # 背景颜色
                font=("Arial", 24),  # 字体大小
                anchor="center",  # 文字居中
                justify="center"  # 多行文字居中
                )
                # 确保标签有足够大小显示文字
                # self.img_label.config(width=800, height=600)
            else:
                self.img_label.image = None
                self.img_label.config(image='')

                error_msg = self.img_error_msg[index]
                
                self.img_label.config(
                text=f"Remote respond the error: {error_msg}",  # 错误信息
                foreground="white",  # 文字颜色
                background="gray",  # 背景颜色
                font=("Arial", 24),  # 字体大小
                anchor="center",  # 文字居中
                justify="center"  # 多行文字居中
                )
        else:
            # process image with PIL
            print(f"image {index} found in cache, printing...")
            img_data = self.img_cache[index]
            image = Image.open(io.BytesIO(img_data))
            image.thumbnail((800, 600))  # adjust size
            photo = ImageTk.PhotoImage(image)
                
            self.img_label.config(image=photo)
            self.img_label.image=photo

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
                data = self.sock.recv(5)
                status, index = struct.unpack('>BI', data)
                # read data through chunk
                if status == 0x00:
                    data = self.sock.recv(4)
                    img_size = struct.unpack('>I', data)[0]
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
                else:
                    print("server respond with error with photo")
                    data = self.sock.recv(4)
                    error_size = struct.unpack('>I', data)[0]
                    data = self.sock.recv(error_size)
                    error_msg = data.decode('utf-8')
                    print(f"error is: {error_msg}")
                    self.img_error_msg[index] = error_msg
                    self.get_image(index)

            
            # receive csv tag
            elif cmd == 0x02:  
                data = self.sock.recv(5)
                status, self.tag_cnt = struct.unpack('>BI',data)
                alias_list = []
                for i in range(0,self.tag_cnt):
                    data =  self.sock.recv(4)
                    alias_size = struct.unpack('>I', data)[0]
                    alias_bytes =  self.sock.recv(alias_size)
                    alias = alias_bytes.decode('utf-8')
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
                status, data_cnt = struct.unpack('>BI',data)
                self.handle_data_cnt(data_cnt)

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

    def handle_data_cnt(self,data_cnt):
        self.data_cnt = data_cnt
        self.img_cache = []
        self.img_error_msg = []
        self.labeling_status = []
        for i in range(0,data_cnt):
            self.img_cache.append(None)
            self.img_error_msg.append(None)
            self.labeling_status.append(False)


    def start_client(self):
        self.root.mainloop()

if __name__ == "__main__":
      # Main window
    app = FrontendClient() 
    app.start_client()
    # root.protocol("WM_DELETE_WINDOW", app.on_closing)  # bind action when clicking close
      # Start main event loop
