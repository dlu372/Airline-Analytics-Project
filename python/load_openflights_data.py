import pandas as pd

# Load OpenFlights datasets
airports = pd.read_csv(
    "/Users/luxun/Downloads/Airline-Analytics-Project/data/raw/airports.dat",
    header=None
)

airlines = pd.read_csv(
    "/Users/luxun/Downloads/Airline-Analytics-Project/data/raw/airlines.dat",
    header=None
)

routes = pd.read_csv(
    "/Users/luxun/Downloads/Airline-Analytics-Project/data/raw/routes.dat",
    header=None
)

print("Airports shape:", airports.shape)
print("Airlines shape:", airlines.shape)
print("Routes shape:", routes.shape)


# Assign column names based on OpenFlights documentation
airports.columns = [
    "airport_id", "name", "city", "country",
    "iata", "icao", "latitude", "longitude",
    "altitude", "timezone", "dst",
    "tz_database_time_zone", "type", "source"
]

airlines.columns = [
    "airline_id", "name", "alias",
    "iata", "icao", "callsign",
    "country", "active"
]

routes.columns = [
    "airline", "airline_id",
    "source_airport", "source_airport_id",
    "destination_airport", "destination_airport_id",
    "codeshare", "stops", "equipment"
]

# Replace "\N" with NA(pandas) for better handling of missing values
airports.replace("\\N", pd.NA, inplace=True)
airlines.replace("\\N", pd.NA, inplace=True)
routes.replace("\\N", pd.NA, inplace=True)

# Save the cleaned airport data to a CSV file for further analysis
airports.to_csv("data/processed/airports_clean.csv", index=False)
airlines.to_csv("data/processed/airlines_clean.csv", index=False)
routes.to_csv("data/processed/routes_clean.csv", index=False)

##### STAGE 02 #####

# Prepare airport lookup tables for joins
airports_src = airports[[
    "airport_id", "name", "city", "country",
    "iata", "latitude", "longitude"
]].rename(columns={
    "airport_id": "source_airport_id",
    "name": "source_airport_name",
    "city": "source_city",
    "country": "source_country",
    "iata": "source_iata",
    "latitude": "source_latitude",
    "longitude": "source_longitude"
})

airports_dest = airports[[
    "airport_id", "name", "city", "country",
    "iata", "latitude", "longitude"
]].rename(columns={
    "airport_id": "destination_airport_id",
    "name": "destination_airport_name",
    "city": "destination_city",
    "country": "destination_country",
    "iata": "destination_iata",
    "latitude": "destination_latitude",
    "longitude": "destination_longitude"
})

# Join routes with source airport
routes_enriched = routes.merge(
    airports_src,
    on="source_airport_id",
    how="left"
)

# Join routes with destination airport
routes_enriched = routes_enriched.merge(
    airports_dest,
    on="destination_airport_id",
    how="left"
)

# Save final analysis-ready dataset
routes_enriched.to_csv(
    "data/processed/routes_enriched.csv",
    index=False
)
