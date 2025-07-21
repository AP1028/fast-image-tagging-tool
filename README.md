# Fast Image Tagging Tool

## To Do List:

### Backend:
- [x] JSON config file
- [x] Basic socket implementation
- [x] CSV R/W on drive
- [x] Socket CSV request
- [x] Socket image request
- [ ] Socket receive setting override from frontend
- [ ] Threading

### Frontend:
- [ ] JSON config file
- [x] Basic UI system
- [ ] UI interation to overwite setting
- [ ] Multi-selection support
- [x] Basic socket implementation
- [ ] CSV R/W through socket
- [x] Socket CSV request
- [x] Real time saving of CSV
- [ ] Automatic saving of CSV (with specified condition)
- [x] Socket image request
- [ ] Threadings

## Implementation

### Socket Protocol

#### Client to Server:

##### 1. Request Image Data: 

0xFF 0x01 index(4 byte)

##### 2. Request CSV Tag: 

0xFF 0x02

##### 3. CSV Change Request: 

0xFF 0x03 index1(4 byte), index2(4 byte), tag_index_cnt(4 byte,) True/False(1 byte), True/False(1 byte)...

##### 4. Request Save: 

0xFF 0x04

<!-- ##### 5. Request Data Count 

0xFF 0x05 -->

##### 6. Request Partial CSV Data

0xFF 0x06

#### Server to Client:

##### 1. Send image: 

0xFF 0x01 OK(0x00, 1 byte) index(4 bytes) size(4 bytes) Image Data

0xFF 0x01 ERROR(0x01, 1 byte) index(4 bytes) size(4 bytes) ERROR message

##### 2. Send CSV tag info: 

0xFF 0x02 OK(0x00, 1 byte) tag_cnt(4 byte) data size(4 bytes) data ...

0xFF 0x02 ERROR(0x01, 1 byte) size(4 bytes) ERROR message

##### 3. CSV Change Completed: 

0xFF 0x03 OK(0x00, 1 byte)

0xFF 0x03 ERROR(0x01, 1 byte) size(4 byte) ERROR message

##### 4. Save Completed: 

0xFF 0x04 OK(0x00, 1 byte)

0xFF 0x04 ERROR(0x01, 1 byte) size(4 byte) ERROR message

<!-- ##### 5. Data Count

0xFF 0x05 OK(0x00, 1 byte) data_count(4 bytes)

0xFF 0x05 ERROR(0x01, 1 byte)  -->

##### 6. Send Partial CSV Data

0xFF 0x06 OK(0x00, 1 byte) size(4 byte) partial_csv_data

0xFF 0x06 ERROR(0x01, 1 byte) 






