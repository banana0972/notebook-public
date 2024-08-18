CREATE TABLE Users(
    email PRIMARY KEY,
    role TEXT, --TODO Enum this? TODO notnull too
    creds TEXT
);

CREATE TABLE Items (
    id TEXT primary key,
    fileType TEXT NOT NULL,
    owner TEXT NOT NULL,
    metadata TEXT NOT NULL,
    FOREIGN KEY (owner) REFERENCES Users(email)
);

CREATE TABLE ClosureTable(
    n INTEGER PRIMARY KEY AUTOINCREMENT,
    childId TEXT NOT NULL,
    parentId TEXT NOT NULL,
    depth INTEGER,
    FOREIGN KEY (childId) REFERENCES Items(id),
    FOREIGN KEY (parentId) references Items(id)
);
