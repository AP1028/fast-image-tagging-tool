# Fast Image Tagging Tool

A very fast image label tagging tool written in Python, based on socket and Tkinter.

## Set Up

The tool is tested with Python 3.12. It probably works in other versions.

If you want to use a virtual environment with Anaconda, do this:

```bash
conda create -n python312 python=3.12
conda activate python312
conda install git
```

Otherwise, install Python and Git on your platform without Anaconda.

Set Up Repository:

```bash
git clone https://github.com/AP1028/fast-image-tagging-tool.git
cd fast-image-tagging-tool
git checkout dev # Only if you want to do some development and testing, use master in production
```

Install Dependencies:

```bash
pip install pandas pillow
```

To run the server:

```bash
conda activate python312 # If you are using conda for virtual environment
python server.py
```

To run the client:

```bash
conda activate python312 # If you are using conda for virtual environment
python client.py
```

## To Do List:

### Backend:
- [x] JSON config file
- [x] Basic socket implementation
- [x] CSV R/W on drive
- [x] Socket CSV request
- [x] Socket image request
- [ ] Proper SIGINT handling
- [ ] Socket receive setting override from frontend
- [x] More error handling
- [ ] Encryption
- [ ] Threading (multi-client)

### Frontend:
- [x] JSON config file
- [x] Basic UI system
- [ ] Multi-selection support
- [x] Basic socket implementation
- [x] CSV R/W through socket
- [x] Socket CSV request
- [x] Real time saving of CSV
- [ ] Configurable automatic saving of CSV (with specified condition)
- [x] Socket image request
- [ ] Proper SIGINT handling
- [ ] Client reconnect
- [ ] Image refresh (resend request)
- [x] Automatically pull all image cache
- [ ] Mass labeling
- [ ] Setting through UI - overwrite setting JSON file
- [x] More error handling
- [ ] Encryption
- [ ] Threadings

## Implementation

### Socket Protocol

| Type            | Action | Data |
| --- | --- | --- |
| Client => Server | Request Image Data | 0xFF 0x01 index(4 bytes) |
| Client => Server | Request CSV Tag | 0xFF 0x02 |
| Client => Server | CSV Change Request | 0xFF 0x03 index1(4 bytes), index2(4 bytes), tag_index_cnt(4 bytes), True/False(1 byte), ... |
| Client => Server | Request Save | 0xFF 0x04 |
| Client => Server | Request Clip Data | 0xFF 0x05 index(4 bytes) |
| Client => Server | Request Partial CSV Data | 0xFF 0x06 |
| Server => Client | Send Image | 0xFF 0x01 OK(0x00, 1 byte) index(4 bytes) size(4 bytes) img_data<br/>0xFF 0x01 ERROR(0x01, 1 byte) index(4 bytes) size(4 bytes) error_msg |
| Server => Client | Send CSV Tag | 0xFF 0x02 OK(0x00, 1 byte) tag_cnt(4 bytes) data_size(4 bytes) <data(True: 0x00, False: 0x01)> ...<br/>0xFF 0x02 ERROR(0x01, 1 byte) size(4 bytes) error_message |
| Server => Client | CSV Change Response | 0xFF 0x03 OK(0x00, 1 byte)<br/>0xFF 0x03 ERROR(0x01, 1 byte) size(4 bytes) error_message |
| Server => Client | Save Response | 0xFF 0x04 OK(0x00, 1 byte)<br/>0xFF 0x04 ERROR(0x01, 1 byte) size(4 bytes) error_message |
| Server => Client | Send Clip Data | 0xFF 0x05 OK(0x00, 1 byte) total_clip_cnt(4 bytes) <clip_start(4 bytes) clip_end(4 bytes) clip_cam_cnt(4byte)>...<br/>0xFF 0x05 ERROR(0x01, 1 byte)|
| Server => Client | Send Partial CSV Data | 0xFF 0x06 OK(0x00, 1 byte) size(4 bytes) partial_csv_data<br/>0xFF 0x06 ERROR(0x01, 1 byte) |





