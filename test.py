	
import pandas as pd
import sqlalchemy as sql

connect_string = 'mysql://root:kuroko32!@localhost:3306/libsat'
sql_engine = sql.create_engine(connect_string)

query = "select * from sensor_data where name='df' order by date desc limit 1"

df = pd.read_sql_query(query, sql_engine)

if df.empty:
    print('hi')
print(df)
