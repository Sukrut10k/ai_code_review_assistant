SELECT * FROM code_review_db.reviews; -- without using USE DATABASE_NAME
TRUNCATE TABLE reviews; -- Delete all previous records

USE code_review_db;

-- View all stored reviews
SELECT * FROM reviews;

-- View only important columns
SELECT id, created_at, filenames, summary
FROM reviews
ORDER BY created_at DESC;

-- Get a specific review by ID
SELECT * FROM reviews WHERE id = 1;

-- Count total reviews
SELECT COUNT(*) AS total_reviews FROM reviews;

-- View only reviews that have issues
SELECT id, filenames, issues_json
FROM reviews
WHERE issues_json IS NOT NULL
  AND issues_json != '[]';

-- Show reviews created today
SELECT * FROM reviews
WHERE DATE(created_at) = CURDATE();