import os
import sys

try:
    import sqlite3
except ImportError:
    print("tsm requires sqlite3")

options = [("Ticker", 's'),
           ("Last", 'l1'),
           ("Change", 'c1'),
           ("Change (%)", 'p2'),
           ("Low", 'g'),
           ("High", 'h'),
           ("Volume", 'v')]

def create_log_file():
    if not os.path.exists(os.path.join(os.getcwd(), 'log')):
        os.mkdir(os.join(os.getcwd(), 'log'))

def create_database(db_name='monitor.db'):
    if not os.path.exists(os.path.join(os.getcwd(), 'db')):
        db_path = os.join(os.getcwd(), 'db')
        os.mkdir(db_path)
        fh = open(os.join(db_path, db_name))
        fh.close()
    elif not os.path.exists(os.path.join(os.getcwd(), 'db/' + db_name)):
        fh = open(os.path.join(os.getcwd(), 'db/' + db_name))
        fh.close()

    conn = sqlite3.connect(os.path.join(os.getcwd(), 'db/' + db_name))
    curr = conn.cursor()
    curr.execute("""CREATE TABLE IF NOT EXISTS portfolio
                        (ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                         symbol TEXT UNIQUE);""")
    curr.close()
    conn.close()

def run():
    create_log_file()
    create_database()

if __name__ == "__main__":
    run()
