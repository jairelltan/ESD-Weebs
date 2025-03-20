-- IMPORTANT

-- Update One Piece image (CHANGE TO YOUR OWN PATH)
UPDATE comic 
SET comic_art = LOAD_FILE('C:/wamp64/www/ESD/ESD-Weebs/images/one_piece.webp')
WHERE comic_name = 'One Piece';

SELECT ROW_COUNT() as rows_updated, 'One Piece' as comic;

-- Update Attack on Titan image (CHANGE TO YOUR OWN PATH)
UPDATE comic 
SET comic_art = LOAD_FILE('C:/wamp64/www/ESD/ESD-Weebs/images/attack_on_titan.webp')
WHERE comic_name = 'Attack on Titan';

SELECT ROW_COUNT() as rows_updated, 'Attack on Titan' as comic;

-- Update Demon Slayer image (CHANGE TO YOUR OWN PATH)
UPDATE comic 
SET comic_art = LOAD_FILE('C:/wamp64/www/ESD/ESD-Weebs/images/demon_slayer.webp')
WHERE comic_name = 'Demon Slayer';

SELECT ROW_COUNT() as rows_updated, 'Demon Slayer' as comic;


-- Update Attack on Titan image (CHANGE TO YOUR OWN PATH)
UPDATE comic 
SET comic_art = LOAD_FILE('C:/wamp64/www/ESD/ESD-Weebs/images/invincible.jpg')
WHERE comic_name = 'Invincible';

SELECT ROW_COUNT() as rows_updated, 'Invincible' as comic;

UPDATE comic 
SET comic_art = LOAD_FILE('C:/wamp64/www/ESD/ESD-Weebs/images/kagurabachi.jpg')
WHERE comic_name = 'Kagurabachi';

SELECT ROW_COUNT() as rows_updated, 'Kagurabachi' as comic;

UPDATE comic 
SET comic_art = LOAD_FILE('C:/wamp64/www/ESD/ESD-Weebs/images/naruto.webp')
WHERE comic_name = 'Naruto';

SELECT ROW_COUNT() as rows_updated, 'Naruto' as comic;

UPDATE comic 
SET comic_art = LOAD_FILE('C:/wamp64/www/ESD/ESD-Weebs/images/bleach.jpg')
WHERE comic_name = 'Bleach';

SELECT ROW_COUNT() as rows_updated, 'Bleach' as comic;

UPDATE comic 
SET comic_art = LOAD_FILE('C:/wamp64/www/ESD/ESD-Weebs/images/solo_levelling.webp')
WHERE comic_name = 'Solo Leveling';

SELECT ROW_COUNT() as rows_updated, 'Solo Leveling' as comic;

UPDATE comic 
SET comic_art = LOAD_FILE('C:/wamp64/www/ESD/ESD-Weebs/images/sweet_home.webp')
WHERE comic_name = 'Sweet Home';

SELECT ROW_COUNT() as rows_updated, 'Sweet Home' as comic;

UPDATE comic 
SET comic_art = LOAD_FILE('C:/wamp64/www/ESD/ESD-Weebs/images/tower_of_god.webp')
WHERE comic_name = 'Tower of God';

SELECT ROW_COUNT() as rows_updated, 'Tower of God' as comic;


-- Verify images were loaded
SELECT comic_name, 
       CASE WHEN comic_art IS NULL THEN 'No image' 
            ELSE 'Has image' 
       END as image_status
FROM comic; 