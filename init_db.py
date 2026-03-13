import sqlite3

def init_db():
    connection = sqlite3.connect('database.db')

    with open('schema.sql') as f:
        connection.executescript(f.read())

    cur = connection.cursor()

    # Pre-populate some initial data for testing
    from werkzeug.security import generate_password_hash
    password_hash = generate_password_hash('password123')
    
    cur.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                ('Admin User', 'admin@example.com', password_hash, 'admin'))
    
    cur.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                ('Organizer User', 'organizer@example.com', password_hash, 'organizer'))

    cur.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                ('Participant User', 'participant@example.com', password_hash, 'participant'))

    cur.execute("INSERT INTO hackathons (title, description, start_date, end_date, theme, rules, prize_info, status, organizer_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ('Innovate AI 2026', 'A hackathon focused on building the next generation of AI tools.', '2026-04-01', '2026-04-03', 'Artificial Intelligence', 'No pre-existing projects allowed.', '$5,000 Grand Prize', 'upcoming', 2))

    connection.commit()
    connection.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")
