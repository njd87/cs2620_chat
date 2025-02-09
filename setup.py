import os
import sqlite3

database_path = "data/messenger.db"

def reset_database() -> None:
    '''
    Reset the database by deleting the file if it exists.
    '''

    # check to make sure the "data" directory exists
    # database stored here
    os.makedirs("data", exist_ok=True)

    # delete database if exists to reset it
    if os.path.exists(database_path):
        os.remove(database_path)
        print(f"Deleted existing {database_path}")

def structure_tables() -> None:
    '''
    Create the tables for the database.
    '''

    with sqlite3.connect(database_path) as conn:
        cursor = conn.cursor()
        
        # set up users table in messenger.db file
        cursor.execute("""
            CREATE TABLE users (
                user_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                passhash TEXT NOT NULL
            );
        """)

        # set up messages table in messenger.db file
        cursor.execute("""
            CREATE TABLE messages (
                message_id INTEGER PRIMARY KEY,
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL,
                message TEXT NOT NULL,
                time DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        print(f"Created users table.")
        print(f"Created messages table.")

if __name__ == "__main__":
    reset_database()
    structure_tables()