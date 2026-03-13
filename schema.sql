DROP TABLE IF EXISTS announcements;
DROP TABLE IF EXISTS submissions;
DROP TABLE IF EXISTS team_members;
DROP TABLE IF EXISTS teams;
DROP TABLE IF EXISTS hackathons;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'participant' -- 'participant', 'organizer', 'admin'
);

CREATE TABLE hackathons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    theme TEXT,
    rules TEXT,
    prize_info TEXT,
    status TEXT DEFAULT 'upcoming', -- 'upcoming', 'active', 'completed'
    organizer_id INTEGER NOT NULL,
    FOREIGN KEY(organizer_id) REFERENCES users(id)
);

CREATE TABLE teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    hackathon_id INTEGER NOT NULL,
    FOREIGN KEY(hackathon_id) REFERENCES hackathons(id)
);

CREATE TABLE team_members (
    team_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    PRIMARY KEY(team_id, user_id),
    FOREIGN KEY(team_id) REFERENCES teams(id),
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    hackathon_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    github_link TEXT,
    demo_video TEXT,
    FOREIGN KEY(team_id) REFERENCES teams(id),
    FOREIGN KEY(hackathon_id) REFERENCES hackathons(id)
);

CREATE TABLE announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    hackathon_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    FOREIGN KEY(hackathon_id) REFERENCES hackathons(id)
);
