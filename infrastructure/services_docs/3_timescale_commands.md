docker exec -it foundation_timescale psql -U postgres -d analytics_prod
SELECT * FROM pg_extension;