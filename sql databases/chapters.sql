-- Create a new database for chapters
CREATE DATABASE IF NOT EXISTS chapters_db;
USE chapters_db;

-- Create chapters table
CREATE TABLE IF NOT EXISTS chapters (
    chapter_id INT PRIMARY KEY AUTO_INCREMENT,
    comic_id INT NOT NULL,
    chapter_number INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    release_date DATE NOT NULL,
    image VARCHAR(255) NOT NULL, -- Path to the chapter's folder in the Chapters directory
    UNIQUE KEY unique_chapter (comic_id, chapter_number)
);

-- Insert sample chapters data
INSERT INTO chapters (comic_id, chapter_number, title, release_date, image) VALUES
-- Attack on Titan (comic_id = 3)
(3, 1, 'To You, 2000 Years From Now', '2023-01-01', 'Chapters/Attack on Titan/chapter1'),
(3, 2, 'That Day', '2023-01-08', 'Chapters/Attack on Titan/chapter2'),
(3, 3, 'Night of the Disbanding Ceremony', '2023-01-15', 'Chapters/Attack on Titan/chapter3'),

-- Solo Leveling (comic_id = 4)
(4, 1, 'I Am an E-Rank Hunter', '2023-02-01', 'Chapters/Solo Leveling/chapter1'),
(4, 2, 'The Secret to Strength', '2023-02-08', 'Chapters/Solo Leveling/chapter2'),
(4, 3, 'A Rank', '2023-02-15', 'Chapters/Solo Leveling/chapter3'); 