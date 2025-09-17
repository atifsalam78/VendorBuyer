from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
try:
    from app.deps import get_db
    from app.models import User, Profile
    from app.schemas import UserCreate, ProfileCreate
    from app.auth import get_password_hash
except ImportError:
    from deps import get_db
    from models import User, Profile
    from schemas import UserCreate, ProfileCreate
    from auth import get_password_hash
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
try:
    from app.routers.taxonomy import COUNTRIES, STATES, CITIES
except ImportError:
    from routers.taxonomy import COUNTRIES, STATES, CITIES

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.post("/register")
async def register_user(
    request: Request,
    email: str = Form(...),
    mobileCode: str = Form(None),
    mobile: str = Form(...),
    password: str = Form(...),
    is_vendor: bool = Form(False),
    company_name: str = Form(None),
    ntn: str = Form(None),
    address: str = Form(None),
    country: str = Form(None),
    state: str = Form(None),
    city: str = Form(None),
    postalCode: str = Form(None),
    website: str = Form(None),
    businessCategory: str = Form(None),
    businessType: str = Form(None),
    ownerName: str = Form(None),
    establishmentYear: str = Form(None),
    landlineCode: str = Form(None),
    landline: str = Form(None),
    vendorGender: str = Form(None),
    buyerName: str = Form(None),
    buyerCompanyName: str = Form(None),
    buyerDesignation: str = Form(None),
    buyerGender: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    # Debug logging
    print(f"Received registration: email={email}, mobileCode={mobileCode}, mobile={mobile}, is_vendor={is_vendor}, company_name={company_name}")
    print(f"Additional fields: ntn={ntn}, country={country}, state={state}, city={city}, address={address}")
    print(f"Vendor fields: ownerName={ownerName}, establishmentYear={establishmentYear}, landline={landline}, gender={vendorGender}")
    print(f"Buyer fields: buyerName={buyerName}, buyerCompanyName={buyerCompanyName}, buyerDesignation={buyerDesignation}, buyerGender={buyerGender}")
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == email))
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = get_password_hash(password)
    new_user = User(
        email=email,
        mobile_code=mobileCode,
        mobile=mobile,
        hashed_password=hashed_password,
        is_vendor=is_vendor,
        gender=vendorGender if is_vendor else buyerGender
    )
    
    db.add(new_user)
    try:
        await db.commit()
        await db.refresh(new_user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Registration failed")
    
    # Convert IDs to names for country, state, and city
    country_name = None
    state_name = None
    city_name = None
    
    # Convert country ID to name
    if country and country.isdigit():
        country_id = int(country)
        for c in COUNTRIES:
            if c["id"] == country_id:
                country_name = c["name"]
                break
    
    # Convert state ID to name
    if state and state.isdigit():
        state_id = int(state)
        if country and country.isdigit() and int(country) in STATES:
            for s in STATES[int(country)]:
                if s["id"] == state_id:
                    state_name = s["name"]
                    break
    
    # Convert city ID to name
    if city and city.isdigit():
        city_id = int(city)
        if state and state.isdigit() and int(state) in CITIES:
            for c in CITIES[int(state)]:
                if c["id"] == city_id:
                    city_name = c["name"]
                    break
    
    print(f"Location conversion: country_id={country} -> {country_name}, state_id={state} -> {state_name}, city_id={city} -> {city_name}")
    
    # Create profile with appropriate fields based on account type
    if is_vendor:
        # For vendor accounts
        new_profile = Profile(
            user_id=new_user.id,
            company_name=company_name,
            ntn=ntn,
            address=address,
            country=country_name,
            state=state_name,
            city=city_name,
            postal_code=postalCode,
            website=website,
            business_category=businessCategory,
            business_type=businessType,
            name=ownerName,  # Use vendor's owner name
            establishment_year=int(establishmentYear) if establishmentYear and establishmentYear.isdigit() else None,
            landline_code=landlineCode,
            landline=landline,
            connections_count=0,
            followers_count=0,
            following_count=0,
            tagline="Innovative Technology for Modern Businesses"  # Default tagline
        )
    else:
        # For buyer accounts
        new_profile = Profile(
            user_id=new_user.id,
            company_name=buyerCompanyName,  # Use buyer's company name
            ntn=ntn,
            address=address,
            country=country_name,
            state=state_name,
            city=city_name,
            postal_code=postalCode,
            website=website,
            business_category=businessCategory,
            business_type=businessType,
            name=buyerName,  # Use buyer's name
            establishment_year=int(establishmentYear) if establishmentYear and establishmentYear.isdigit() else None,
            landline_code=landlineCode,
            landline=landline,
            designation=buyerDesignation,  # Save buyer's designation
            connections_count=0,
            followers_count=0,
            following_count=0,
            tagline="Professional Buyer"  # Default tagline for buyers
        )
    
    db.add(new_profile)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Profile creation failed")
    
    # Redirect to profile page
    return RedirectResponse(url="/profile", status_code=303)