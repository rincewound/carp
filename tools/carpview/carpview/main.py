import io
import time
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit, QFileDialog
from PyQt5.QtGui import QStandardItemModel, QStandardItem
import sys
import struct
import json
import sys
import asyncio
from asyncqt import QEventLoop
import zmq
from zmq.asyncio import Context

class Ui(QtWidgets.QMainWindow):
    zeromq_enable = False
    messages = []

    
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi('mainwindow.ui', self)
        self.show()     
        self.model = QStandardItemModel()   
        self.model.setHorizontalHeaderLabels(["Timestamp", "Domain", "Message"])        
        self.tblEntries.setModel(self.model)

        self.list_model = QStandardItemModel()
        self.lstDomains.setModel(self.list_model)
        
        self.actionOpen_Raw.triggered.connect(self.open_raw)
        self.actionLoad_Domain_File.triggered.connect(self.load_domain_file)
        self.actionLoad_aggregate_domain_file.triggered.connect(self.load_multi_domain_file)
        self.actionZeroMqToggle.triggered.connect(self.toggle_zeromq)
        self.actionExit.triggered.connect(self.close)

        self.domains = {}

        self._load_multi_domain_file("./out.domain")
        self.parse_file("./data.bin")
        self.setup_domain_list()      

    def close(self):
        Ui.zeromq_enable = False; 

    def toggle_zeromq(self):
        Ui.zeromq_enable = not Ui.zeromq_enable
        if Ui.zeromq_enable:
            self.lblZeroMqState.setText("ZeroMQ: Enabled")
            self.actionZeroMqToggle.setText("Disable ZeroMQ")
        else:
            self.lblZeroMqState.setText("ZeroMQ: Disabled")
            self.actionZeroMqToggle.setText("Enable ZeroMQ")
    
    def load_domain_file(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.ExistingFile)
        file = dlg.getOpenFileName()[0]
        with open(file, "r") as f:
             domain = json.load(f)
             domain_id = domain["domain"]
             self.domains[domain_id] = domain

    def load_multi_domain_file(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.ExistingFile)
        file = dlg.getOpenFileName()[0]
        self._load_multi_domain_file(file)

    def _load_multi_domain_file(self, filename):
        with open(filename, "r") as f:
             domains = json.load(f)
             self.domains = domains   

    def setup_domain_list(self):
        for domain_id in self.domains:
            domain = self.domains[domain_id]
            item = QStandardItem(domain["name"])
            item.setData(domain_id)
            item.setCheckable(True)
            item.setCheckState(True)

            self.list_model.appendRow(item)

    def open_raw(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.ExistingFile)
        file = dlg.getOpenFileName()
        self.clear_ui()
        self.parse_file(file[0])

    def clear_ui(self):
        self.tblEntries.model().clear()        

    def process_stream(self, stream):
        while not len(stream.peek()) == 0:
            # read timestamp 4 byte unsigned int:
            timestamp = struct.unpack('I',stream.read(4))[0]
            domain_id = struct.unpack('I',stream.read(4))[0]
            message_id = struct.unpack('I',stream.read(4))[0]
            num_args = struct.unpack('B',stream.read(1))[0]

            print(f"found message {message_id} with {num_args} parameters")

            args = []

            for i in range(0, num_args):
                type_id = struct.unpack('B',stream.read(1))[0]
                print(f"type id {type_id}")
                if type_id == 'I' or type_id == 73:      # int32
                    value = struct.unpack('i',stream.read(4))[0]            
                elif type_id == 'U':      # uint32
                    value = struct.unpack('I',stream.read(4))[0]
                elif type_id == 'B':    # uint8
                    value = struct.unpack('b',stream.read(1))[0]
                elif type_id == 'u':    # uint16
                    value = struct.unpack('H',stream.read(2))[0]
                elif type_id == 'F' or type_id == 70:    # float
                    value = struct.unpack('f',stream.read(4))[0]
                elif type_id == 'D':    # double
                    value = struct.unpack('d',stream.read(8))[0]
                elif type_id == 'S' or type_id == 83:    # string
                    string_length = struct.unpack('H',stream.read(2))[0]
                    value = stream.read(string_length).decode('utf-8')
                else:
                    print(f"unknown type {type_id}")
                    value = None
                pass

                print(f" Read value {value} for parameter {i}")    
                args.append(value)    
            if domain_id != 0:
                format_string = self.fetch_format_string(domain_id, message_id, num_args)                    
            else:                    
                format_string = args[0]
                args.pop(0)                    

            try:
                format_string = format_string.format(*args)
            except:
                format_string = f"Invalid Format string '{format_string}' for {num_args} arguments"
            
            row = [QStandardItem(str(timestamp)), 
                    QStandardItem(self.fetch_domain_name(domain_id)), 
                    QStandardItem(format_string)]
            
            self.model.appendRow(row)
        self.tblEntries.resizeColumnToContents(2)

    def parse_file(self, file: str):
        with open(file, 'rb') as f:
            self.process_stream(f)
            

    async def process_incoming_data(self):
        while True:
            if len(self.messages) > 0:
                message = self.messages.pop(0)
                stream = io.BufferedReader(io.BytesIO(message))
                self.process_stream(stream)
            await asyncio.sleep(1)



    def fetch_domain_name(self, domain_id: int) -> str:
        if str(domain_id) in self.domains.keys():
            return self.domains[str(domain_id)]["name"]
        return f"{domain_id}"

    def fetch_format_string(self, domain_id: int, string_id: int, num_args: int) -> str:
        did = str(domain_id)
        if did in self.domains.keys():
            if string_id < len(self.domains[did]["messages"]):
                return self.domains[did]["messages"][string_id]
        return f"No Entry for: {domain_id}, {string_id}. Data:" + "{} " * num_args 


    async def zeromq_task():
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        ctx = zmq.asyncio.Context()
        sock = ctx.socket(zmq.REP)
        print("Binding to tcp://*:5555")
        sock.bind("tcp://*:5555")
        while True:            
            if Ui.zeromq_enable is False:                
                print("ZeroMQ is disabled")  
            else:
                print("ZeroMQ, receive some bytes")
                data = await sock.recv()
                print("send some bytes")
                await sock.send_string("meh")
                print("received some bytes: ", data)
                Ui.messages.append(data)
            await asyncio.sleep(1)


def run():
    app = QtWidgets.QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.set_event_loop(loop)
    
    #with loop:
    w = Ui()
    w.show()        
    asyncio.get_event_loop().create_task(w.process_incoming_data())
    asyncio.get_event_loop().run_until_complete(Ui.zeromq_task())