import pymongo

def connect_mongo() :
      client = pymongo.MongoClient('18.222.188.131',
      username='dw_marketing',
      password='tgeo219',
      authSource='daewoong',
      authMechanism='SCRAM-SHA-1')
      db = client["daewoong"]
      return db

def make_client(table) :
      db = connect_mongo()
      collection = db.get_collection(table)
      print("make_client")
      print(table)
      return collection