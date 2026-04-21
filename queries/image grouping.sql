SELECT image_hash, count(*) AS ff 
FROM analysis_cache
GROUP BY image_hash 
ORDER BY ff DESC;