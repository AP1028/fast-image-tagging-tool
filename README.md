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
## Setting

Both the server and client will need a config file to run.

### Server Setting
server_setting.json:
```json
{
    "host": "0.0.0.0",
    "port": 52973,
    "csv_dir": "data/your_data.csv",
    "csv_save_dir": "data",
    "meta_path": "meta.csv",
    "save_to_same_file": false
}
```
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `host` | string | No | `"0.0.0.0"` | IP address for server to bind to. Use `"0.0.0.0"` for all interfaces or `"127.0.0.1"` for localhost only |
| `port` | integer | No | `52973` | Port number for socket communication |
| `csv_dir` | string | **Yes** | - | Path to your input CSV file containing the dataset |
| `csv_save_dir` | string | No* | - | Directory where labeled CSV will be saved (*required if `save_to_same_file` is false) |
| `meta_path` | string | **Yes** | - | Path to metadata CSV file containing tag definitions |
| `save_to_same_file` | boolean | No | `false` | If `true`, overwrites the original CSV. If `false`, saves to `csv_save_dir` with `__labelled__` suffix |
---

**Note:** When `save_to_same_file` is `false`, the output file will be named: `{original_filename}__labelled__.csv`

### Client Setting
client_setting.json:
```json
{
    "host": "127.0.0.1",
    "port": 52973,
    "multiple_selection": false,
    "autosave": 10
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `host` | string | No | `"127.0.0.1"` | IP address of the server to connect to |
| `port` | integer | No | `52973` | Port number for socket communication (must match server) |
| `multiple_selection` | boolean | No | `false` | If `true`, allows multiple tags per image. If `false`, selecting a tag deselects others |
| `autosave` | integer | No | `1` | Auto-saves every N entries. Set to `1` to save on every change, higher values save less frequently |

---

**Note:** When `multiple_selection` is `false`, hitting the keyboard hotkey for labels (0, 1, 2, etc) will automatically jump to the next frame. hitting the keyboard hotkey for 'False' (F key) will jump to the next frame regardless of this option.

## CSV Format Requirements

Your data CSV must contain the following:

Required Columns:

1. `clip_id` - Groups images into clips/sequences

2. `file_path` (required) - Full or relative path to image files

3. Tag columns (at least one required) - Either format:

    + Format A: `tag_code_XXXX` where `XXXX` is the numeric tag code (e.g., `tag_code_100`, `tag_code_200`)
    + Format B: Combination of `tag_code` + `label` columns

Optional Columns:

1. `modality` (optional) - Camera/sensor name for multi-camera support

Example:
```csv
clip_id,modality,file_path,tag_code_100,tag_code_200,tag_code_300
1,camera_front,images/img_001.jpg,True,False,False,
1,camera_rear,images/img_002.jpg,False,True,False,
2,camera_front,images/img_003.jpg,False,False,True
```

## Metadata CSV Format

The metadata file defines your tag labels and must contain:

Required Columns

1. `code` or `tag_code` - Numeric tag identifier matching your data CSV
2. `alias` or `scenario` - Human-readable tag name displayed in UI

Example:
```csv
code,alias
100,Clear Weather
200,Rainy
300,Foggy
400,Night Time
500,Heavy Traffic
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
| Client => Server | Request Clip Data | 0xFF 0x05 |
| Client => Server | Request Partial CSV Data | 0xFF 0x06 |
| Server => Client | Send Image | 0xFF 0x01 OK(0x00, 1 byte) index(4 bytes) size(4 bytes) img_data<br/>0xFF 0x01 ERROR(0x01, 1 byte) index(4 bytes) size(4 bytes) error_msg |
| Server => Client | Send CSV Tag | 0xFF 0x02 OK(0x00, 1 byte) tag_cnt(4 bytes) data_size(4 bytes) <data(True: 0x00, False: 0x01)> ...<br/>0xFF 0x02 ERROR(0x01, 1 byte) size(4 bytes) error_message |
| Server => Client | CSV Change Response | 0xFF 0x03 OK(0x00, 1 byte)<br/>0xFF 0x03 ERROR(0x01, 1 byte) size(4 bytes) error_message |
| Server => Client | Save Response | 0xFF 0x04 OK(0x00, 1 byte)<br/>0xFF 0x04 ERROR(0x01, 1 byte) size(4 bytes) error_message |
| Server => Client | Send Clip Data | 0xFF 0x05 OK(0x00, 1 byte) total_clip_cnt(4 bytes) <clip_start(4 bytes) clip_end(4 bytes) clip_cam_cnt(4byte)>...<br/>0xFF 0x05 ERROR(0x01, 1 byte)|
| Server => Client | Send Partial CSV Data | 0xFF 0x06 OK(0x00, 1 byte) size(4 bytes) partial_csv_data<br/>0xFF 0x06 ERROR(0x01, 1 byte) |





