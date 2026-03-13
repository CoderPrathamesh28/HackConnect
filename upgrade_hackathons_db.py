import sqlite3

def upgrade():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('ALTER TABLE hackathons ADD COLUMN prizes TEXT')
        print("Successfully added prizes column to hackathons table.")
    except sqlite3.OperationalError as e:
        print(f"Error (column might already exist): {e}")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    upgrade()
