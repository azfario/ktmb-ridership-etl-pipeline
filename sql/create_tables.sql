CREATE TABLE IF NOT EXISTS ktmb_ridership (
    date DATE NOT NULL,
    service VARCHAR(50) NOT NULL,
    ridership INTEGER NOT NULL CHECK (ridership >= 0),
    day_of_week VARCHAR(9) NOT NULL,
    month VARCHAR(9) NOT NULL,
    year INTEGER NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    PRIMARY KEY (date, service)
);