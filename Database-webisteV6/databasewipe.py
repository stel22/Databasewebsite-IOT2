import sqlite3

conn = sqlite3.connect('test.db')
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS Mytable;")
cur.execute("""CREATE TABLE Mytable (
   ID INTEGER PRIMARY KEY AUTOINCREMENT,
   Temperature REAL,
   Humidity TEXT,
   CO2 TEXT,
   Timestamp DATETIME DEAFUALT CURRENT_TIMESTAMP
);
""")
conn.commit()
conn.close()