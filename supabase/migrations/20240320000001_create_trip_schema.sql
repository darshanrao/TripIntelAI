-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create trips table
CREATE TABLE trips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    destination TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create trip_states table
CREATE TABLE trip_states (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_id UUID REFERENCES trips(id),
    session_id UUID NOT NULL,
    state JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create places table
CREATE TABLE places (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    location JSONB NOT NULL,
    details JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create restaurants table
CREATE TABLE restaurants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    cuisine TEXT NOT NULL,
    location JSONB NOT NULL,
    details JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create hotels table
CREATE TABLE hotels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    location JSONB NOT NULL,
    details JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_trips_user_id ON trips(user_id);
CREATE INDEX idx_trip_states_trip_id ON trip_states(trip_id);
CREATE INDEX idx_places_name ON places(name);
CREATE INDEX idx_restaurants_name ON restaurants(name);
CREATE INDEX idx_hotels_name ON hotels(name);

-- Create full-text search indexes
CREATE INDEX idx_places_search ON places USING GIN (to_tsvector('english', name || ' ' || details->>'description'));
CREATE INDEX idx_restaurants_search ON restaurants USING GIN (to_tsvector('english', name || ' ' || details->>'description'));
CREATE INDEX idx_hotels_search ON hotels USING GIN (to_tsvector('english', name || ' ' || details->>'description'));

-- Enable Row Level Security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE trip_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE places ENABLE ROW LEVEL SECURITY;
ALTER TABLE restaurants ENABLE ROW LEVEL SECURITY;
ALTER TABLE hotels ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Users can only access their own data"
    ON users FOR ALL
    USING (auth.uid() = id);

CREATE POLICY "Users can only access their own trips"
    ON trips FOR ALL
    USING (auth.uid() = user_id);

CREATE POLICY "Users can only access their own trip states"
    ON trip_states FOR ALL
    USING (EXISTS (
        SELECT 1 FROM trips
        WHERE trips.id = trip_states.trip_id
        AND trips.user_id = auth.uid()
    ));

-- Public access for places, restaurants, and hotels
CREATE POLICY "Public read access for places"
    ON places FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Public read access for restaurants"
    ON restaurants FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Public read access for hotels"
    ON hotels FOR SELECT
    TO authenticated
    USING (true); 