import pandas as pd

# Load OpenFlights datasets
airports = pd.read_csv(
    "../data/raw/airports.dat",
    header=None
)

airlines = pd.read_csv(
    "../data/raw/airlines.dat",
    header=None
)

routes = pd.read_csv(
    "../data/raw/routes.dat",
    header=None
)

print("Airports shape:", airports.shape)
print("Airlines shape:", airlines.shape)
print("Routes shape:", routes.shape)
