import socket
import threading
import json
import os
import struct
import time
import sys
import pandas as pd
from PIL import Image, ImageTk

default_setting = {
        "host": "0.0.0.0", # socket bind ip address
        "port": 52973, # socket bind port
        "csv_dir": "data", # csv data folder
        "csv_save_dir": "data", # csv data save folder
        "tag_path": "tag.csv", # tag file location
    }

class BackendServer:
    def load_setting_file(self,setting_path):
        try:
            with open(setting_path, 'r') as setting_file:
                setting_data = json.load(setting_file)
                self.configure_setting(setting_data)
                return
        # Error handing
        except FileNotFoundError:
            print(f"[WARN] '{setting_path}' not found.")
            print(f"Writing default setting to '{setting_path}'.")
            try:
                with open(setting_path, 'w') as setting_file: # 'w' for write mode (overwrites existing file)
                    json.dump(default_setting, setting_file, indent=4)
                print(f"Default setting written to {setting_path} successfully.")
            except IOError as error:
                print(f"An error occurred while writing to {setting_path}: {error}")
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON format in '{setting_path}'.")
        print("Using default setting.")
        self.configure_setting(default_setting)
        return

    def configure_setting(self,setting_data):
        try:
            self.host = setting_data["host"]
        except KeyError:
            print("Missing host in setting, using 0.0.0.0 as default")
            self.host = "0.0.0.0"
        try:
            self.port = setting_data["port"]
        except KeyError:
            print("Missing port in setting, using 52973 as default")
            self.port = 52973
        try:
            self.csv_dir = setting_data["csv_dir"]
        except KeyError:
            print("Missing csv_dir, using 'data' as default")
            self.csv_dir = "data"
        try:
            self.csv_save_dir = setting_data["csv_save_dir"]
        except KeyError:
            print("Missing csv_save_dir, using 'data' as default")
            self.csv_save_dir = "data"
        try:
            self.tag_path = setting_data["tag_path"]
        except KeyError:
            print("Missing tag_path, using 'tag.csv' as default")
            self.tag_path = "tag.csv"

    

    def handle_csv(self):
        self.data_csv = pd.read_csv(self.csv_dir)
        self.tag_csv = pd.read_csv(self.tag_path)

        self.data_list = self.data_csv.values.tolist()
        self.data_column_list = self.data_csv.columns.tolist()
        self.tag_data_list = self.tag_csv.values.tolist()
        self.tag_data_column_list = self.tag_csv.columns.tolist()
        
        # self.data_list[row][column]

        # get tag code entry
        cnt = 0
        for entry in self.tag_data_column_list:
            if entry.strip() == 'code':
                self.tag_entry_code = cnt
                break
            cnt+=1
        
        # get tag alias entry
        cnt = 0
        for entry in self.tag_data_column_list:
            if entry.strip() == 'alias':
                self.tag_entry_alias = cnt
                break
            cnt+=1
        
        # get data file_path entry
        cnt = 0
        for entry in self.data_column_list:
            if entry.strip() == 'file_path':
                self.tag_entry_file_path = cnt
                break
            cnt+=1

        # get list of tags containing column location in data csv
        # and its alias
        self.tag_code_list=[]
        self.tag_column_entry=[]
        self.tag_column_alias=[]
        cnt = 0
        # search for column entry matching tag_code_ to get required tag code
        # and column entry number
        for entry in self.data_column_list:
            if entry.strip()[0:9] == 'tag_code_':
                self.tag_code_list.append(int(entry.strip()[9:19]))
                self.tag_column_entry.append(cnt)
            cnt+=1
        # search matching tag code in 'code' entry in tag csv list 
        # and record the alias
        for tag_code in self.tag_code_list:
            alias = f"{tag_code}_fallback"
            for i in range(0,len(self.tag_data_list)):
                if tag_code == self.tag_data_list[i][self.tag_entry_code]:
                    alias = self.tag_data_list[i][self.tag_entry_alias]
                    break
            self.tag_column_alias.append(alias)
        # get total tag cnt
        self.tag_cnt = len(self.tag_column_entry)
        self.data_cnt = len(self.data_list)
    
    def save_csv(self):
        df = pd.DataFrame(self.data_list, columns=self.data_column_list)
        if os.path.isdir(self.csv_save_dir)==False:
            os.mkdir(self.csv_save_dir)
            
        df.to_csv(f"{self.csv_save_dir}/save.csv", index=False)
        print(f"File saved to: {self.csv_save_dir}/save.csv")
    
    
    
    def start(self):
        
        self.handle_csv()

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen()
            print(f"Server listening on {self.host}:{self.port}")

            while True:
                conn, addr = s.accept()
                print(f"Connected by {addr}")
                client_thread = threading.Thread(
                    target=self.handle_client, 
                    args=(conn, addr),
                    daemon=True
                )
                client_thread.start()

    def handle_client(self, conn, addr):
        try:
            while True:
                init_char = conn.recv(1)
                if not init_char: break
                else:
                    verifier = struct.unpack('B', init_char)[0]
                    if verifier != 0xFF: 
                        print(f"Bad byte of {verifier}, dropping byte")
                        continue
                
                print("Reading socket message")
                cmd = struct.unpack('B', conn.recv(1))[0]
                
                # request image
                if cmd == 0x01: 
                    data = conn.recv(8)
                    index= struct.unpack('>I', data)[0]
                    self._send_image(conn, index)
                
                # request csv tag
                elif cmd == 0x02:  
                    self._send_tag(conn)
                    
                elif cmd == 0x03:  # request csv change
                    data = conn.recv(13)
                    index1, index2, tag_index, status = struct.unpack('>IIIB', data)
                    self._update_tag(conn, index1, index2, tag_index, status)
                    

                elif cmd == 0x04:  # save
                    self.save_csv()
                    # change complete
                    conn.sendall(b'\x04\x00')  

                elif cmd == 0x05:  # request data count
                    self._send_data_count(conn)

                else:
                    print(f"Unknown cmd byte {cmd}. Maybe check version?")
                    
        except ConnectionResetError:
            print(f"Client {addr} disconnected")
        finally:
            conn.close()

    def _send_image(self, conn, index):
        # server will send image from index1 to index2
        print(f"send image {index}")
        
        if index>= self.data_cnt or index<0:
            print("Error: you are requesting out of bound operation")
            sys.exit(1)
        
        image_path = self.data_list[index][self.tag_entry_file_path]
        print(f'Need to send image {index}, path is {image_path}')
        
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            print("sending image")
            image_size = len(image_data)
            conn.sendall(b'\xFF\x01\x00')
            conn.sendall(struct.pack('>I', index))
            conn.sendall(struct.pack('>I', image_size))
            conn.sendall(image_data)
        
        except IOError as error:
            print("image ioerror")
            error_str = str(error)
            error_bytes = error_str.encode('utf-8')
            error_size = len(error_bytes)

            conn.sendall(b'\xFF\x01\x01')
            conn.sendall(struct.pack('>I', error_size))
            conn.sendall(error_bytes)            

    def _send_tag(self, conn):
        # send csv tag encoded
        print(f'Need to send {self.tag_column_alias}')
        conn.sendall(b'\xff\x02\x00')
        conn.sendall(struct.pack('>I', self.tag_cnt))
        for alias in self.tag_column_alias:
            alias_bytes = alias.encode('utf-8')
            alias_size = len(alias_bytes)
            conn.sendall(struct.pack('>I', alias_size))
            conn.sendall(alias_bytes)  

    def _update_tag(self, conn, index1, index2, tag_index, status):
        # update tag in csv database, from index1 to index2
        print(f"update tag {index1}, {index2}, {tag_index}, {status}")

        if index2 >= self.data_cnt or tag_index<0 or tag_index>=self.tag_cnt:
            print("Error: you are requesting out of bound operation")
            sys.exit(1)

        for i in range(index1, index2+1):
            self.data_list[i][self.tag_column_entry[tag_index]] = bool(status)
            print(f'writing {i} {self.tag_column_entry[tag_index]} to {bool(status)}')
        
        conn.sendall(b'\x03\x00')  
    
    def _send_data_count(self,conn):
        conn.sendall(b'\xff\x05\x00')
        conn.sendall(struct.pack('>I', self.data_cnt))
        


    def __init__(self, setting_path='server_setting.json'):
        self.load_setting_file(setting_path)

if __name__ == "__main__":
    server = BackendServer()
    server.start()
