CREATE TABLE users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, email TEXT NOT NULL, role TEXT NOT NULL);
CREATE TABLE courses(code TEXT PRIMARY KEY, title TEXT NOT NULL, credits INTEGER NOT NULL);
CREATE TABLE comments(id INTEGER PRIMARY KEY, author TEXT NOT NULL, body TEXT NOT NULL);
CREATE TABLE enrollments(id INTEGER PRIMARY KEY, reference TEXT UNIQUE NOT NULL, user_id INTEGER NOT NULL REFERENCES users(id), course_code TEXT NOT NULL REFERENCES courses(code));
INSERT INTO users VALUES(1,'admin','AdminPass!26','admin@campushub.invalid','administrator'),(2,'student','StudentPass!26','student@campushub.invalid','student');
INSERT INTO courses VALUES('CS403','Information Security',3),('CS301','Database Systems',3),('CS302','Software Engineering',3),('CS201','Data Structures',4);
INSERT INTO comments(author,body) VALUES('Ayesha','The security lab is open this week. Bring your questions!');
INSERT INTO enrollments VALUES(1,'ENR-2026-001',2,'CS403');
