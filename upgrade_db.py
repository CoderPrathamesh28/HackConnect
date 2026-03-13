import sqlite3

def upgrade():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN bio TEXT')
        cursor.execute('ALTER TABLE users ADD COLUMN github TEXT')
        print("Successfully added bio and github columns to users table.")
    except sqlite3.OperationalError as e:
        print(f"Error (they might already exist): {e}")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    upgrade()
