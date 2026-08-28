# Track Environments

Pit Wall currently includes five selectable stock-car race environments:

- Daytona International Speedway
- Bristol Motor Speedway
- Darlington Raceway
- Pocono Raceway
- Watkins Glen International

All tracks use the same race engine and WebMCP interface.

## Track Simulation Profiles

Track configuration is centralized through `TrackSimulationProfile`.

A track profile provides simulation configuration including:

- track identity
- track type
- track length
- race length
- stage structure
- modeled fuel window
- modeled tire behavior
- modeled caution environment
- modeled restart behavior
- traffic effects
- pit-road effects
- strategy volatility

The engine consumes the selected profile instead of implementing separate race engines for individual tracks.

## Daytona International Speedway

**Type:** Superspeedway

Daytona provides a longer, volatile race environment with strong track-position, fuel, caution, and strategy considerations.

## Bristol Motor Speedway

**Type:** Short Track

Bristol emphasizes traffic, frequent interaction with surrounding cars, shorter race cycles, and short-track strategy.

## Darlington Raceway

**Type:** Oval

Darlington is configured with greater long-run and tire-management emphasis.

## Pocono Raceway

**Type:** Large / Unique Oval

Pocono emphasizes long runs, fuel windows, track position, and pit sequencing.

## Watkins Glen International

**Type:** Road Course

Watkins Glen provides a shorter road-course race with different traffic characteristics and strategic sequencing.

## Data and Modeling Boundary

Pit Wall grew from prior NASCAR data and analytics research.

Real-world information used during development includes:

- track identity
- track classification
- track length
- historical research context

The standalone game's operational parameters for the following systems are modeled simulation inputs:

- fuel
- tires
- cautions
- traffic
- pit effects
- strategy volatility

Pit Wall does not claim these modeled parameters reproduce official NASCAR engineering data, historical race control, or exact historical pit strategy.

## WebMCP Track Context

The selected track is included in observable race state.

An external WebMCP agent can determine:

- where it is racing
- track type
- track length
- race length
- current race context

without requiring the user to manually provide track information.

The same eight WebMCP Site Tools operate across all five environments.