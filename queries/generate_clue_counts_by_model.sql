-- SQLite
SELECT model, count(*) AS ff 
FROM analysis_cache
WHERE prompt LIKE 'Generate a creative%'
GROUP BY model 
ORDER BY ff DESC;