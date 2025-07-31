-- Create version table to track database schema version
CREATE TABLE IF NOT EXISTS db_version (
    id INTEGER PRIMARY KEY,
    version VARCHAR(50) NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Check current version
DO $$
DECLARE
    current_version VARCHAR(50);
BEGIN
    SELECT version INTO current_version FROM db_version WHERE id = 1;
    
            -- If version is different or doesn't exist, reinitialize
        IF current_version IS NULL OR current_version != '1.0.12' THEN
        -- Drop existing tables
        DROP TABLE IF EXISTS albums CASCADE;
        
        -- Update version
        DELETE FROM db_version WHERE id = 1;
                    INSERT INTO db_version (id, version) VALUES (1, '1.0.12');
    END IF;
END $$;

-- Create albums table
CREATE TABLE IF NOT EXISTS albums (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    artist VARCHAR(255) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    cover_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create orders table
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    album_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (album_id) REFERENCES albums(id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_albums_artist ON albums(artist);
CREATE INDEX IF NOT EXISTS idx_albums_price ON albums(price);
CREATE INDEX IF NOT EXISTS idx_orders_album_id ON orders(album_id);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_albums_updated_at 
    BEFORE UPDATE ON albums 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

    -- Insert some sample data with local album cover images
    INSERT INTO albums (name, artist, price, cover_url) VALUES
        ('Vulgar Display of Power', 'Pantera', 24.99, '/static/covers/Pantera-VulgarDisplayofPower.jpg'),
        ('...And Justice for All', 'Metallica', 22.99, '/static/covers/Metallica_-_...And_Justice_for_All_cover.jpg'),
        ('Superunknown', 'Soundgarden', 21.99, '/static/covers/Sound_garden-Superunknown.jpg'),
        ('Colony', 'In Flames', 19.99, '/static/covers/Inflames_colony.jpeg'),
        ('System of a Down', 'System of a Down', 20.99, '/static/covers/System_of_a_down-system_of_a_down.jpg'),
        ('Somewhere in Time', 'Iron Maiden', 23.99, '/static/covers/Iron_Maiden-Somewhere_in_Time.jpg')
    ON CONFLICT DO NOTHING; 