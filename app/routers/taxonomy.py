from fastapi import APIRouter

router = APIRouter()

# Sample data for countries, states, and cities
COUNTRIES = [
    {"id": 1, "name": "Pakistan"},
    {"id": 2, "name": "United States"},
    {"id": 3, "name": "United Kingdom"}
]

STATES = {
    1: [  # Pakistan
        {"id": 1, "name": "Punjab"},
        {"id": 2, "name": "Sindh"},
        {"id": 3, "name": "Khyber Pakhtunkhwa"},
        {"id": 4, "name": "Balochistan"}
    ],
    2: [  # United States
        {"id": 5, "name": "California"},
        {"id": 6, "name": "New York"},
        {"id": 7, "name": "Texas"}
    ],
    3: [  # United Kingdom
        {"id": 8, "name": "England"},
        {"id": 9, "name": "Scotland"},
        {"id": 10, "name": "Wales"}
    ]
}

CITIES = {
    1: [  # Punjab
        {"id": 1, "name": "Lahore"},
        {"id": 2, "name": "Faisalabad"},
        {"id": 3, "name": "Rawalpindi"}
    ],
    2: [  # Sindh
        {"id": 4, "name": "Karachi"},
        {"id": 5, "name": "Hyderabad"},
        {"id": 6, "name": "Sukkur"}
    ],
    5: [  # California
        {"id": 7, "name": "Los Angeles"},
        {"id": 8, "name": "San Francisco"},
        {"id": 9, "name": "San Diego"}
    ],
    6: [  # New York
        {"id": 10, "name": "New York City"},
        {"id": 11, "name": "Buffalo"},
        {"id": 12, "name": "Albany"}
    ],
    8: [  # England
        {"id": 13, "name": "London"},
        {"id": 14, "name": "Manchester"},
        {"id": 15, "name": "Birmingham"}
    ]
}

@router.get("/countries")
async def get_countries():
    return COUNTRIES

@router.get("/states/{country_id}")
async def get_states(country_id: int):
    if country_id not in STATES:
        return []
    return STATES[country_id]

@router.get("/states")
async def get_states_query(country_id: int):
    if country_id not in STATES:
        return []
    return STATES[country_id]

@router.get("/cities/{state_id}")
async def get_cities(state_id: int):
    if state_id not in CITIES:
        return []
    return CITIES[state_id]

@router.get("/cities")
async def get_cities_query(state_id: int):
    if state_id not in CITIES:
        return []
    return CITIES[state_id]