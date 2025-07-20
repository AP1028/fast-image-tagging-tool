# fast-image-tagging-tool

## To do list:

### Backend:
- [x] JSON config file
- [x] Basic socket implementation
- [x] CSV R/W on drive
- [x] Socket CSV request
- [x] Socket image request
- [ ] Real time saving of CSV
- [ ] Automatic saving of CSV (with specified condition)
- [ ] Socket receive setting override from frontend
- [ ] Threading

### Frontend:
- [ ] JSON config file
- [ ] Basic UI system
- [ ] Basic socket implementation
- [ ] CSV R/W through socket
- [ ] Socket CSV request
- [ ] Socket image request
- [ ] Threadings

## Implementation

### Socket

#### Client to server:

##### 1. Request image: 

0xFF 0x01 index(4 byte)

##### 2. Request CSV tag info: 

0xFF 0x02

##### 3. CSV change request: 

0xFF 0x03 index 1(4 byte), index 2(4 byte), tag index (4 byte), True/False(1 byte) 

##### 4. Request save: 

0xFF 0x04

##### 5. Request data count 

0xFF 0x05

#### Server to client:

##### 1. Send image: 

0xFF 0x01 OK(0x00, 1 byte) index(4 bytes) size(4 bytes) Image Data

0xFF 0x01 ERROR(0x01, 1 byte) size(4 bytes) ERROR message

##### 2. Send CSV tag info: 

0xFF 0x02 OK(0x00, 1 byte) tag_cnt(4 byte) data size(4 bytes) data ...

0xFF 0x02 ERROR(0x01, 1 byte) size(4 bytes) ERROR message

##### 3. CSV change completed: 

0xFF 0x03 OK(0x00, 1 byte)

0xFF 0x03 ERROR(0x01, 1 byte) size(4 byte) ERROR message

##### 4. Save completed: 

0xFF 0x04 OK(0x00, 1 byte)

0xFF 0x04 ERROR(0x01, 1 byte) size(4 byte) ERROR message

##### 5. Data count

0xFF 0x05 OK(0x00, 1 byte) data_count(4 bytes)

0xFF 0x05 ERROR(0x01, 1 byte) 






