import sqlite3
import os
from flask import Flask, render_template, request, url_for, flash, redirect, session, g
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        if user:
            g.user = dict(user)
        else:
            g.user = None

@app.route('/')
def index():
    conn = get_db_connection()
    hackathons = conn.execute('SELECT * FROM hackathons ORDER BY start_date ASC LIMIT 3').fetchall()
    conn.close()
    return render_template('index.html', hackathons=hackathons)

@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        db = get_db_connection()
        error = None

        if not name or not email or not password:
            error = 'All fields are required.'
        elif db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone() is not None:
            error = f"User {email} is already registered."

        if error is None:
            db.execute(
                'INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
                (name, email, generate_password_hash(password))
            )
            db.commit()
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('login'))
        
        flash(error, 'error')
        db.close()

    return render_template('register.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        db = get_db_connection()
        error = None
        user = db.execute(
            'SELECT * FROM users WHERE email = ?', (email,)
        ).fetchone()

        if user is None or not check_password_hash(user['password'], password):
            error = 'Incorrect email or password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            session['role'] = user['role']
            flash('Successfully logged in!', 'success')
            return redirect(url_for('index'))

        flash(error, 'error')
        db.close()

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/hackathons')
def hackathons_list():
    conn = get_db_connection()
    hackathons = conn.execute('SELECT * FROM hackathons ORDER BY start_date ASC').fetchall()
    conn.close()
    return render_template('hackathons.html', hackathons=hackathons)

@app.route('/hackathon/<int:id>')
def hackathon_detail(id):
    conn = get_db_connection()
    hackathon = conn.execute('SELECT * FROM hackathons WHERE id = ?', (id,)).fetchone()
    conn.close()
    if hackathon is None:
        flash('Hackathon not found.', 'error')
        return redirect(url_for('hackathons_list'))
    return render_template('hackathon_detail.html', hackathon=hackathon)

@app.route('/hackathon/create', methods=['GET', 'POST'])
def create_hackathon():
    if g.user is None or g.user['role'] not in ['admin', 'organizer']:
        flash('Only organizers can create new hackathons.', 'error')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        rules = request.form['rules']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        theme = request.form.get('theme', 'Open-ended')
        prizes = request.form.get('prizes', '')
        
        # Validation checks
        if not title or not description or not rules or not start_date or not end_date or not prizes:
            flash('Please fill in all required fields, including rules and prizes.', 'error')
        else:
            conn = get_db_connection()
            status = 'upcoming'
            
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO hackathons (title, description, rules, start_date, end_date, organizer_id, status, theme, prize_info)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, description, rules, start_date, end_date, g.user['id'], status, theme, prizes))
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            flash('Hackathon successfully launched!', 'success')
            return redirect(url_for('hackathon_detail', id=new_id))
            
    return render_template('create_hackathon.html')

@app.route('/hackathon/<int:id>/edit', methods=['GET', 'POST'])
def edit_hackathon(id):
    if g.user is None or g.user['role'] not in ['admin', 'organizer']:
        flash('Unauthorized.', 'error')
        return redirect(url_for('dashboard'))
        
    conn = get_db_connection()
    hackathon = conn.execute('SELECT * FROM hackathons WHERE id = ?', (id,)).fetchone()
    
    # Ownership Check
    if not hackathon or (hackathon['organizer_id'] != g.user['id'] and g.user['role'] != 'admin'):
        conn.close()
        flash('You do not have permission to edit this hackathon.', 'error')
        return redirect(url_for('admin'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        rules = request.form['rules']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        theme = request.form.get('theme', 'Open-ended')
        prizes = request.form.get('prizes', '')
        status = request.form.get('status', hackathon['status'])
        
        if not title or not description or not rules or not start_date or not end_date or not prizes:
            flash('Please fill required fields, including rules and prizes.', 'error')
        else:
            conn.execute('''
                UPDATE hackathons 
                SET title = ?, description = ?, rules = ?, start_date = ?, end_date = ?, theme = ?, prize_info = ?, status = ?
                WHERE id = ?
            ''', (title, description, rules, start_date, end_date, theme, prizes, status, id))
            conn.commit()
            flash('Hackathon updated successfully.', 'success')
            conn.close()
            return redirect(url_for('admin'))
            
    conn.close()
    return render_template('edit_hackathon.html', hackathon=hackathon)

@app.route('/hackathon/<int:id>/close', methods=['POST'])
def close_hackathon(id):
    if g.user is None or g.user['role'] not in ['admin', 'organizer']:
        flash('Unauthorized.', 'error')
        return redirect(url_for('dashboard'))
        
    conn = get_db_connection()
    hackathon = conn.execute('SELECT * FROM hackathons WHERE id = ?', (id,)).fetchone()
    
    if not hackathon or (hackathon['organizer_id'] != g.user['id'] and g.user['role'] != 'admin'):
        conn.close()
        flash('You do not have permission to close this hackathon.', 'error')
        return redirect(url_for('admin'))
        
    conn.execute("UPDATE hackathons SET status = 'closed' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash('Hackathon has been officially closed.', 'success')
    return redirect(url_for('admin'))

@app.route('/hackathon/<int:id>/delete', methods=['POST'])
def delete_hackathon(id):
    if g.user is None or g.user['role'] not in ['admin', 'organizer']:
        flash('Unauthorized.', 'error')
        return redirect(url_for('dashboard'))
        
    conn = get_db_connection()
    hackathon = conn.execute('SELECT * FROM hackathons WHERE id = ?', (id,)).fetchone()
    
    if not hackathon or (hackathon['organizer_id'] != g.user['id'] and g.user['role'] != 'admin'):
        conn.close()
        flash('You do not have permission to delete this hackathon.', 'error')
        return redirect(url_for('admin'))
        
    # Delete related data first
    conn.execute('DELETE FROM announcements WHERE hackathon_id = ?', (id,))
    conn.execute('DELETE FROM submissions WHERE hackathon_id = ?', (id,))
    conn.execute('DELETE FROM team_members WHERE team_id IN (SELECT id FROM teams WHERE hackathon_id = ?)', (id,))
    conn.execute('DELETE FROM teams WHERE hackathon_id = ?', (id,))
    conn.execute('DELETE FROM hackathons WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Hackathon deleted successfully.', 'success')
    return redirect(url_for('admin'))

@app.route('/dashboard')
def dashboard():
    if g.user is None:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    user_role = g.user['role']
    
    # Depending on role, fetch relevant data
    organized_hackathons = []
    joined_teams = []
    
    if user_role in ['organizer', 'admin']:
        organized_hackathons = conn.execute('SELECT * FROM hackathons WHERE organizer_id = ?', (g.user['id'],)).fetchall()
        
    # Get teams user is part of
    joined_teams = conn.execute('''
        SELECT t.name as team_name, t.id as team_id, h.title as hackathon_title, h.id as hackathon_id
        FROM teams t
        JOIN team_members tm ON t.id = tm.team_id
        JOIN hackathons h ON t.hackathon_id = h.id
        WHERE tm.user_id = ?
    ''', (g.user['id'],)).fetchall()
    
    conn.close()
    return render_template('dashboard.html', organized_hackathons=organized_hackathons, joined_teams=joined_teams)

@app.route('/hackathon/<int:id>/create_team', methods=['POST'])
def create_team(id):
    if g.user is None:
        return redirect(url_for('login'))
        
    team_name = request.form['team_name']
    if not team_name:
        flash('Team name is required.', 'error')
        return redirect(url_for('hackathon_detail', id=id))
        
    conn = get_db_connection()
    
    # Check if already in a team for this hackathon
    existing = conn.execute('''
        SELECT t.id FROM teams t
        JOIN team_members tm ON t.id = tm.team_id
        WHERE t.hackathon_id = ? AND tm.user_id = ?
    ''', (id, g.user['id'])).fetchone()
    
    if existing:
        flash('You are already in a team for this hackathon.', 'error')
        conn.close()
        return redirect(url_for('hackathon_detail', id=id))

    cursor = conn.cursor()
    cursor.execute('INSERT INTO teams (name, hackathon_id) VALUES (?, ?)', (team_name, id))
    team_id = cursor.lastrowid
    cursor.execute('INSERT INTO team_members (team_id, user_id) VALUES (?, ?)', (team_id, g.user['id']))
    conn.commit()
    conn.close()
    
    flash('Team created successfully!', 'success')
    return redirect(url_for('team_detail', team_id=team_id))

@app.route('/team/<int:team_id>', methods=['GET', 'POST'])
def team_detail(team_id):
    if g.user is None:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    team = conn.execute('''
        SELECT t.*, h.title as hackathon_title 
        FROM teams t
        JOIN hackathons h ON t.hackathon_id = h.id
        WHERE t.id = ?
    ''', (team_id,)).fetchone()
    
    if not team:
        conn.close()
        flash('Team not found', 'error')
        return redirect(url_for('dashboard'))
        
    # Check if user is in team
    is_member = conn.execute('SELECT * FROM team_members WHERE team_id = ? AND user_id = ?', (team_id, g.user['id'])).fetchone()
    
    if not is_member:
        conn.close()
        flash('You are not a member of this team.', 'error')
        return redirect(url_for('dashboard'))
        
    members = conn.execute('''
        SELECT u.name, u.email 
        FROM users u 
        JOIN team_members tm ON u.id = tm.user_id 
        WHERE tm.team_id = ?
    ''', (team_id,)).fetchall()
    
    submission = conn.execute('SELECT * FROM submissions WHERE team_id = ?', (team_id,)).fetchone()
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        github_link = request.form.get('github_link', '')
        demo_video = request.form.get('demo_video', '')
        
        if submission:
            conn.execute('''
                UPDATE submissions SET title = ?, description = ?, github_link = ?, demo_video = ?
                WHERE id = ?
            ''', (title, description, github_link, demo_video, submission['id']))
            flash('Submission updated successfully!', 'success')
        else:
            conn.execute('''
                INSERT INTO submissions (team_id, hackathon_id, title, description, github_link, demo_video)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (team_id, team['hackathon_id'], title, description, github_link, demo_video))
            flash('Project submitted successfully!', 'success')
            
        conn.commit()
        return redirect(url_for('team_detail', team_id=team_id))
        
    conn.close()
    return render_template('team.html', team=team, members=members, submission=submission)

@app.route('/admin')
def admin():
    if g.user is None or g.user['role'] not in ['admin', 'organizer']:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    hackathons = conn.execute('SELECT * FROM hackathons WHERE organizer_id = ?', (g.user['id'],)).fetchall()
    
    # Get all submissions for hackathons organized by this user
    submissions = conn.execute('''
        SELECT s.*, t.name as team_name, h.title as hackathon_title
        FROM submissions s
        JOIN teams t ON s.team_id = t.id
        JOIN hackathons h ON s.hackathon_id = h.id
        WHERE h.organizer_id = ?
    ''', (g.user['id'],)).fetchall()
    
    conn.close()
    return render_template('admin.html', hackathons=hackathons, submissions=submissions)

@app.route('/db_view')
def db_view():
    if g.user is None or g.user['role'] not in ['admin', 'organizer']:
        flash('Unauthorized access. Admins only.', 'error')
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    tables = {
        'Users': conn.execute('SELECT * FROM users').fetchall(),
        'Hackathons': conn.execute('SELECT * FROM hackathons').fetchall(),
        'Teams': conn.execute('SELECT * FROM teams').fetchall(),
        'Submissions': conn.execute('SELECT * FROM submissions').fetchall()
    }
    conn.close()
    
    return render_template('db_view.html', tables=tables)

@app.route('/leaderboard')
def leaderboard():
    conn = get_db_connection()
    # Simple leaderboard based on submissions existence for now
    submissions = conn.execute('''
        SELECT s.*, t.name as team_name, h.title as hackathon_title
        FROM submissions s
        JOIN teams t ON s.team_id = t.id
        JOIN hackathons h ON s.hackathon_id = h.id
        ORDER BY s.id DESC
    ''').fetchall()
    conn.close()
    return render_template('leaderboard.html', submissions=submissions)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        message = request.form['message']
        
        # Send email to admin
        admin_email = os.getenv('ADMIN_EMAIL', 'hackconnect28@gmail.com')  # Set your admin email
        
        msg = MIMEMultipart()
        msg['From'] = os.getenv('EMAIL_USER', 'hackconnect28@gmail.com')
        msg['To'] = admin_email
        msg['Reply-To'] = email
        msg['Subject'] = f"HackConnect Contact: {subject}"
        
        body = f"Name: {name}\nEmail: {email}\nSubject: {subject}\n\nMessage:\n{message}"
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            email_user = os.getenv('EMAIL_USER')
            email_pass = os.getenv('EMAIL_PASS')
            if not email_user or not email_pass:
                flash('Email service not configured. Message not sent.', 'error')
                print("Email credentials not set")
            else:
                # Using Gmail SMTP with SSL
                server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
                server.login(email_user, email_pass)
                server.sendmail(email_user, admin_email, msg.as_string())
                server.quit()
                flash('Thanks for reaching out! We will get back to you soon.', 'success')
        except Exception as e:
            flash('Sorry, there was an error sending your message. Please try again later.', 'error')
            print(f"Email error: {e}")  # For debugging
        
        return redirect(url_for('index'))
    return render_template('contact.html')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if g.user is None:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form['name']
        bio = request.form.get('bio', '')
        github = request.form.get('github', '')
        
        conn.execute('UPDATE users SET name = ?, bio = ?, github = ? WHERE id = ?', (name, bio, github, g.user['id']))
        conn.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
        
    user = conn.execute('SELECT * FROM users WHERE id = ?', (g.user['id'],)).fetchone()
    conn.close()
    return render_template('profile.html', current_user=user)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
