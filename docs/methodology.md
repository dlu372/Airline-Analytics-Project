# Methodology

## Scope

This project analyzes the OpenFlights June 2014 historical route snapshot. The
route file is a list of directional airline–airport-pair presences; it is not a
flight-event or schedule-frequency dataset.

## Network definitions

- **Primary network:** unique non-codeshare airline–origin–destination route
  presences with both airport IDs matched to the airport dimension. It is an
  operating-network proxy only.
- **Sensitivity network:** unique route presences including codeshare rows.
- **Directed edge:** airline A lists origin airport O to destination airport D.
- **Undirected pair:** used only when testing reverse-route availability or
  summarizing an airport pair.

## Hub dependence

For each airline, count its directed route presences by origin airport. If
origin airport `j` accounts for share `s_j` of the airline's routes:

```text
origin_airport_hhi = sum(s_j ** 2)
effective_hubs = 1 / origin_airport_hhi
```

`top1_origin_share` and `top3_origin_share` are the shares accounted for by the
largest one and three origin airports. These metrics measure structural route
distribution across origins, not flight or passenger concentration.

## Geographic reach

Route distance uses the haversine great-circle formula and an Earth mean radius
of 6,371.0088 km. Only records with non-missing coordinates inside valid
latitude/longitude ranges are included in distance statistics. Calculations
retain full floating-point values; presentation layers may format them.

Domestic and international shares use only rows where both endpoint countries
are known. Country coverage is the union of source and destination countries.

## Connectivity and carrier diversity

Airport connectivity counts distinct route-presence endpoints and listed
airlines. Reciprocal connectivity is the share of an airport's outgoing airport
pairs for which the reverse airport pair is also present in the primary network.

Carrier diversity groups the primary network by directed airport pair and
counts distinct listed airlines. A single-listed-carrier flag is descriptive
and must not be interpreted as monopoly or market dominance.

## Codeshare sensitivity

For each airline, the all-listed network is compared with the non-codeshare
proxy. Uplifts are `all-listed minus non-codeshare`. Differences in top-origin
share, origin HHI, and effective hubs use the same direction. Neither view is a
complete source of actual operations.
