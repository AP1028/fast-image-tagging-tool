import socket
import threading
import json
import os
import struct
import sys
import pandas as pd

default_setting = {
        "host": "0.0.0.0", # socket bind ip address
        "port": 52973, # socket bind port
        "csv_dir": "data", # csv data folder
        "csv_save_dir": "data", # csv data save folder
        "tag_path": "tag.csv", # tag file location
        "save_to_same_file": False
    }

def log_network(str):
    print(f'[SOCK] {str}')

def log_ok(str):
    print(f'[ OK ] {str}')

def log_error(str):
    print(f'[FAIL] {str}')

def log_info(str):
    print(f'[INFO] {str}')

def log_warn(str):
    print(f'[WARN] {str}')

class BackendServer:
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
            log_error(f"Invalid JSON format in '{setting_path}'.")
        log_error(f"Server stopped due to problem with settings.")
        sys.exit(1)
        return

    def configure_setting(self,setting_data):
        # host
        try:
            self.host = setting_data["host"]
        except KeyError:
            log_warn("Missing host in setting, using 0.0.0.0 as default")
            self.host = "0.0.0.0"
        
        # port
        try:
            self.port = setting_data["port"]
        except KeyError:
            log_warn("Missing port in setting, using 52973 as default")
            self.port = 52973
        
        # get input csv dir/path
        try:
            self.csv_dir = setting_data["csv_dir"] # placeholder as folder
            self.csv_path = setting_data["csv_dir"] # input csv file
        except KeyError:
            log_error("Missing csv_dir!")
            sys.exit()

        # get tag csv path
        try:
            self.tag_path = setting_data["tag_path"]
        except KeyError:
            log_error("Missing tag_path!")
            sys.exit()
        
        # check if write to same file
        try:
            self.save_to_same_file = setting_data["save_to_same_file"]
        except KeyError:
            log_warn("Missing multiple_selection in setting, using false as default")
            self.save_to_same_file = False
        
        # handle write dir
        if self.save_to_same_file == False:
            try:
                self.csv_save_dir = setting_data["csv_save_dir"]
                # get input csv file name
                csv_filename = os.path.basename(self.csv_path)
                csv_filename_noext, _ =os.path.splitext(csv_filename)
                self.csv_save_path = f"{self.csv_save_dir}/{csv_filename_noext}__labelled__.csv"

            except KeyError:
                log_error("Missing csv_save_dir!")
                sys.exit()
        else:
            self.csv_save_path = self.csv_path
            self.csv_save_dir = os.path.dirname(self.csv_path)
                    
        write_status = self.is_writeable()
        if write_status == False:
            log_error('Error: Closing server due to cannot write to specified output file')
            sys.exit()
            
    def is_writeable(self):
        # create if does not exist
        if os.path.exists(self.csv_save_dir)==False:
            try:
                log_warn(f'{self.csv_save_dir} does not exist, creating')
                os.mkdir(self.csv_save_dir)
                return True
            except OSError as e:
                log_error(f'Error: {self.csv_save_dir} cannot be created with error {e}')
                return False
        # dir exists, check if directory accessable
        elif os.access(self.csv_save_dir, os.W_OK) == False:
            log_error(f'Error: {self.csv_save_dir} is not writeable.')
            return False
        # dir exists and accessable, check if file writable if exists
        elif os.path.exists(self.csv_save_path):
            if os.path.isfile(self.csv_save_path):
                if os.access(self.csv_save_path, os.W_OK):
                    return True
                else:
                    log_error(f'Error: Permission denied writing to {self.csv_save_path}')
                    return False
            else:
                log_error(f'Error: {self.csv_save_dir} is a directory.')
                return False
        else:
            return True
    

    def handle_csv(self):
        # handle data csv
        self.data_csv = pd.read_csv(self.csv_path)
        log_ok(f"Data CSV loaded with size of {len(self.data_csv)}")
        
        self.data_column_list = self.data_csv.columns.tolist()
        log_info(f"data_column_list: \n{self.data_column_list}")
        
        self.data_list = self.data_csv.values.tolist()
        self.data_cnt = len(self.data_list)
        log_ok(f"data_list loaded with size of {len(self.data_list)}")
        
        # handle tag csv
        self.tag_csv = pd.read_csv(self.tag_path)
        log_ok(f"Tag CSV loaded with size of {len(self.tag_csv)}")
        
        self.tag_data_column_list = self.tag_csv.columns.tolist()
        log_info(f"tag_data_column_list: \n{self.tag_data_column_list}")
        
        self.tag_data_list = self.tag_csv.values.tolist()
        log_ok(f"tag_data_list loaded with size of {len(self.tag_data_list)}")
        
        # format: self.data_list[row][column]

        self.get_tag_entry_code() 
        self.get_tag_entry_alias() 
        self.get_tag_entry_file_path() 
        
        self.get_tag_code_and_entry_list()
        self.get_tag_column_alias()
    
    def get_tag_entry_code(self):
        # get tag code entry
        cnt = 0
        for entry in self.tag_data_column_list:
            if entry.strip() == 'code':
                self.tag_entry_code = cnt
                log_info(f"Tag CSV has column at {self.tag_entry_code} matching 'code'")
                break
            cnt+=1
    
    def get_tag_entry_alias(self):
        # get tag alias entry
        cnt = 0
        for entry in self.tag_data_column_list:
            if entry.strip() == 'alias':
                self.tag_entry_alias = cnt
                log_info(f"Tag CSV has column at {self.tag_entry_alias} matching 'alias'")
                break
            cnt+=1
            
    def get_tag_entry_file_path(self):
        # get data file_path entry
        cnt = 0
        for entry in self.data_column_list:
            if entry.strip() == 'file_path':
                self.tag_entry_file_path = cnt
                log_ok(f"Data CSV has column at {self.tag_entry_file_path} matching 'file_path'")
                return
            cnt+=1
        log_error(f"Data CSV has column at 'file_path'")
    
    def get_tag_code_and_entry_list(self):
        # get list of tags containing column location in data csv
        # and its alias
        self.tag_code_list=[]
        self.tag_column_entry=[]
        self.non_tag_data_column_list=[]
        cnt = 0
        # search for column entry matching tag_code_ to get required tag code
        # and column entry number
        log_info("Checking data_column_list for entry matching 'tag_code_*'")
        for entry in self.data_column_list:
            if entry.strip()[0:9] == 'tag_code_':
                self.tag_code_list.append(int(entry.strip()[9:19]))
                self.tag_column_entry.append(cnt)
                log_info(f"Found tag code at column {cnt} with code {int(entry.strip()[9:19])}")
            else:
                self.non_tag_data_column_list.append(entry)
            cnt+=1
            
        if self.tag_code_list:
            log_ok(f"Successfully extracted tag code list {self.tag_code_list}")
        else:
            log_error(f"Error: No column matching 'tag_code_' found.")
            log_error(f"Check input CSV data.")
            sys.exit(1)
            
        # get total tag cnt
        self.tag_cnt = len(self.tag_column_entry)
    
    def get_tag_column_alias(self):
        # search matching tag code in 'code' entry in tag csv list 
        # and record the alias
        self.tag_column_alias=[]
        log_info("Checking tag code list for alias name")
        for tag_code in self.tag_code_list:
            alias = f"{tag_code}_fallback"
            for i in range(0,len(self.tag_data_list)):
                if tag_code == self.tag_data_list[i][self.tag_entry_code]:
                    alias = self.tag_data_list[i][self.tag_entry_alias]
                    break
            if alias == f"{tag_code}_fallback":
                log_warn(f'No alias found for tag code {tag_code}. Using {alias} as fallback.')
            else:
                log_info(f"Found alias {alias}")
            self.tag_column_alias.append(alias)
            
        if self.tag_column_alias:
            log_ok(f"Successfully extracted alias list {self.tag_column_alias}")
        else:
            log_error(f'Error: alias list empty.')
            log_error(f'You are not supposed to see this as you should have exited in self.get_tag_code_and_entry_list()')
            sys.exit(1)
        
        
    def save_csv(self):
        df = pd.DataFrame(self.data_list, columns=self.data_column_list)

        if self.is_writeable() == True:
            df.to_csv(f"{self.csv_save_path}", index=False)
            log_ok(f"File saved to: {self.csv_save_path}")
            return True
        else:
            log_warn('You break something and now the server cannot write to the specified output file.')
            log_warn('The server will not stop, but you probably want to resolve this if you don\'t want to lose your work.')
            log_warn('Retry saving once you resolved the problem.')
            return False
            
    
    def start(self):
        self.handle_csv()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen()
            log_network(f"Server listening on {self.host}:{self.port}")

            while True:
                conn, addr = s.accept()
                log_network(f"Connected by {addr}")
                client_thread = threading.Thread(
                    target=self.handle_client, 
                    args=(conn, addr),
                    daemon=True
                )
                client_thread.start()

    def safe_recv(self,conn,size):
        conn.settimeout(30.0)
        data = bytearray()
        while len(data) < size:
            try:
                packet = conn.recv(size - len(data))
                if not packet:
                    log_network("Socket connection broken")
                data.extend(packet)
            except socket.timeout:
                log_network(f"Timeout, expected length: {size}, received: {len(data)}")
        return bytes(data)
    
    def handle_client(self, conn, addr):
        try:
            while True:
                conn.settimeout(None)
                init_char = conn.recv(1)
                if not init_char: break
                else:
                    verifier = struct.unpack('B', init_char)[0]
                    if verifier != 0xFF: 
                        log_network(f"Bad byte of {verifier}, dropping byte")
                        continue
                
                log_network("Header matched, reading socket message")
                cmd = struct.unpack('B', self.safe_recv(conn,1))[0]
                
                # request image
                if cmd == 0x01: 
                    data = self.safe_recv(conn,4)
                    index= struct.unpack('>I', data)[0]

                    log_network(f'Received request for image {index}')

                    self.send_image(conn, index)
                
                # request csv tag
                elif cmd == 0x02:  
                    log_network(f'Received request for CSV tag name')
                    self.send_tag(conn)
                    
                elif cmd == 0x03:  # request csv change
                    data = self.safe_recv(conn,12)
                    csv_data_slice = []
                    index1, index2, tag_index_cnt = struct.unpack('>III', data)
                    
                    for i in range (0,tag_index_cnt):
                        byte = self.safe_recv(conn,1)
                        if byte == b'\x01':
                            status = True
                        else:
                            status = False
                        
                        csv_data_slice.append(status)
                    
                    log_network(f'Received request for CSV change, from index {index1} to {index2}')
                    self.update_tag(conn, index1, index2, csv_data_slice)
                    conn.sendall(b'\xff\x03\x00')  

                elif cmd == 0x04:  # save
                    log_network('Received request saving')
                    
                    # save
                    if self.save_csv():
                        conn.sendall(b'\xff\x04\x00')  
                    else:
                        conn.sendall(b'\xff\x04\x01')  

                # elif cmd == 0x05:  # request data count
                #     self.send_data_count(conn)

                elif cmd == 0x06:  # request partial csv data
                    log_network('Received request for partial CSV data')
                    self.send_partial_csv(conn)

                else:
                    log_warn(f"Unknown cmd byte {cmd}. Maybe check version?")
                    
        except ConnectionResetError:
            log_network(f"Client {addr} disconnected")
        finally:
            conn.close()

    def send_image(self, conn, index):
        # server will send image from index1 to index2
        if index>= self.data_cnt or index<0:
            log_error("Error: you are requesting out of bound operation")
            return
        
        image_path = self.data_list[index][self.tag_entry_file_path]
        log_info(f'Request received sending image {index} with path {image_path}')
        
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            image_size = len(image_data)
            log_network(f"Sending image with size {image_size}")
            conn.sendall(b'\xFF\x01\x00')
            conn.sendall(struct.pack('>I', index))
            conn.sendall(struct.pack('>I', image_size))
            conn.sendall(image_data)
            log_network(f"Sending complete")
        
        except IOError as error:
            log_error("Image ioerror!")
            error_str = str(error)
            error_bytes = error_str.encode('utf-8')
            error_size = len(error_bytes)

            conn.sendall(b'\xFF\x01\x01')
            conn.sendall(struct.pack('>I', index))
            conn.sendall(struct.pack('>I', error_size))
            conn.sendall(error_bytes)            

    def send_tag(self, conn):
        # send csv tag encoded
        log_info(f'Need to send {self.tag_column_alias}')
        conn.sendall(b'\xff\x02\x00')
        conn.sendall(struct.pack('>I', self.tag_cnt))
        for alias in self.tag_column_alias:
            alias_bytes = alias.encode('utf-8')
            alias_size = len(alias_bytes)
            conn.sendall(struct.pack('>I', alias_size))
            conn.sendall(alias_bytes)  

    def update_tag(self, conn, index1, index2, csv_data_slice):
        # update tag in csv database, from index1 to index2
        log_info(f"update tag {index1}, {index2}, {csv_data_slice}")

        if index2 >= self.data_cnt or len(csv_data_slice)!=self.tag_cnt:
            log_error("Error: you are requesting mismatch / out of bound operation")
            return

        for i in range(index1, index2+1):
            for j in range (0,self.tag_cnt):
                self.data_list[i][self.tag_column_entry[j]] = csv_data_slice[j]
                log_info(f'writing row {i} column {self.tag_column_entry[j]} to {csv_data_slice[j]}')
        
    def send_partial_csv(self,conn):
        # build partial CSV
        partial_csv = self.data_csv.copy(deep=True)
        for entry in self.non_tag_data_column_list:
            partial_csv.drop(entry, inplace=True, axis=1)
        partial_csv_str = partial_csv.to_csv(index=False)

        # encode CSV ready to send
        self.partial_csv_bytes = partial_csv_str.encode('utf-8')
        self.partial_csv_bytes_length = len(self.partial_csv_bytes)

        conn.sendall(b'\xff\x06\x00')
        conn.sendall(struct.pack('>I', self.partial_csv_bytes_length))
        conn.sendall(self.partial_csv_bytes)

    def __init__(self, setting_path='server_setting.json'):
        self.load_setting_file(setting_path)

if __name__ == "__main__":
    server = BackendServer()
    server.start()
