import pymongo
from sshtunnel import SSHTunnelForwarder

def connect_mongo() :
      client = pymongo.MongoClient('18.222.188.131',
      username='dw_marketing',
      password='tgeo219',
      authSource='daewoong',
      authMechanism='SCRAM-SHA-1')
      db = client["daewoong"]
      
      # host = 'localhost'
      # port = 27017
      # database = 'dwDB'
      # client = pymongo.MongoClient(host = host, port = port)
      # db = client[database]

      # MONGO_HOST = "210.117.182.242"
      # MONGO_PORT = 27017
      # MONGO_DB = "daewoong"
      # MONGO_USER = "dblab"
      # MONGO_PASS = "dbl5511!@"
      # server = SSHTunnelForwarder(
      #     MONGO_HOST,
      #     ssh_username=MONGO_USER,
      #     ssh_password=MONGO_PASS,
      #     remote_bind_address=('127.0.0.1', 27017)
      # )
      # server.start()
      # client = pymongo.MongoClient('127.0.0.1', server.local_bind_port,serverSelectionTimeoutMS=200000)
      # db = client[MONGO_DB]
      return db

def make_client(table) :
      db = connect_mongo()
      collection = db.get_collection(table)
      print("make_client")
      print(table)
      return collection