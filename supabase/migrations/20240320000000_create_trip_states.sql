-- Create trip_states table
CREATE TABLE trip_states (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL UNIQUE,
    state JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on session_id for faster lookups
CREATE INDEX idx_trip_states_session_id ON trip_states(session_id);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_trip_states_updated_at
    BEFORE UPDATE ON trip_states
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add RLS (Row Level Security) policies
ALTER TABLE trip_states ENABLE ROW LEVEL SECURITY;

-- Create policy to allow users to only see their own states
CREATE POLICY "Users can only access their own trip states"
    ON trip_states
    FOR ALL
    USING (auth.uid() = session_id::uuid); 