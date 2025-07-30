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

-- Insert some sample data
INSERT INTO albums (name, artist, price, cover_url) VALUES
    ('Dark Side of the Moon', 'Pink Floyd', 19.99, 'https://upload.wikimedia.org/wikipedia/en/3/3b/Dark_Side_of_the_Moon.png'),
    ('Abbey Road', 'The Beatles', 24.99, 'https://upload.wikimedia.org/wikipedia/en/4/42/Beatles_-_Abbey_Road.jpg'),
    ('Thriller', 'Michael Jackson', 21.99, 'https://upload.wikimedia.org/wikipedia/en/5/55/Michael_Jackson_-_Thriller.png'),
    ('Back in Black', 'AC/DC', 18.99, 'https://upload.wikimedia.org/wikipedia/en/b/be/ACDC_Back_in_Black.png'),
    ('The Wall', 'Pink Floyd', 22.99, 'https://upload.wikimedia.org/wikipedia/en/0/0f/PinkFloydWallCoverOriginalNoText.jpg')
ON CONFLICT DO NOTHING; 