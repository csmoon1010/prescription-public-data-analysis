import pandas as pd
import connect_mongo



atc = connect_mongo.make_client('atc')
atc_df = pd.DataFrame.from_dict(atc.find())
atc_df.to_csv('code_list.csv')