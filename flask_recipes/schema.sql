
DROP TABLE IF EXISTS recipes;
DROP TABLE IF EXISTS users;


CREATE TABLE users (
    admin BOOLEAN DEFAULT FALSE,
    head_admin BOOLEAN DEFAULT FALSE,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    picture_ID BLOB NOT NULL,
    description TEXT
);

-- Add music for a recipe, maybe. And make sure it's mutable and optional to include.
CREATE TABLE recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draft BOOLEAN DEFAULT TRUE,
    title TEXT NOT NULL,
    ingredients TEXT NOT NULL,
    equipment TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    steps TEXT NOT NULL,
    prep_time INTEGER NOT NULL,
    cook_time INTEGER NOT NULL,
    serving_size TEXT NOT NULL,
    picture_ID BLOB NOT NULL,
    video_url TEXT NOT NULL,
    approved BOOLEAN DEFAULT FALSE,
    author_id TEXT NOT NULL,
    FOREIGN KEY (author_id) REFERENCES users (id) ON DELETE CASCADE
);
