# Request User Location Tool

## Description
Ask the browser client to request the user's current GPS location. The backend cannot read device coordinates directly, so this tool returns a client-side directive.

## Parameters
- `reason`: Why the location is needed. Use `find_nearby_showrooms` for test-drive showroom search.

## Security
This tool does not receive or store coordinates. The browser asks the user for permission, then sends latitude and longitude only to the normal showroom search flow.
