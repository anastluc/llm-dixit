-- SQLite
SELECT model, count(*)
FROM analysis_cache
WHERE prompt LIKE 'Generate a creative%'
GROUP BY model 
ORDER BY ff DESC;