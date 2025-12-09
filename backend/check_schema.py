import sqlite3

conn = sqlite3.connect('betai.db')
cursor = conn.cursor()

# Check data_source values
cursor.execute("SELECT DISTINCT data_source FROM scraped_events")
sources = [row[0] for row in cursor.fetchall()]
print("Distinct data_source values:", sources)

cursor.execute("SELECT COUNT(*) FROM scraped_events WHERE data_source != 'real_scrape'")
non_real = cursor.fetchone()[0]
print("Records with data_source != 'real_scrape':", non_real)

cursor.execute("SELECT COUNT(*) FROM scraped_events WHERE data_source = 'real_scrape'")
real = cursor.fetchone()[0]
print("Records with data_source = 'real_scrape':", real)

conn.close()
