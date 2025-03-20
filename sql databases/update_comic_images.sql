-- IMPORTANT
--Set secure_file_priv to '' to allow file loading in the MySQL configuration file .ini files

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

-- Verify images were loaded
SELECT comic_name, 
       CASE WHEN comic_art IS NULL THEN 'No image' 
            ELSE 'Has image' 
       END as image_status
FROM comic; 