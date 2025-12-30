from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.booking import Booking, BookingStatus
from app.models.service import Service
from app.models.user import User, Role
from app.models.review import Review
from app.services.deps import get_current_user
from app.services.content import get_translations, get_profile
from app.core.security import hash_password

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


def _redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


def _base_context(request: Request, user: User | None = None) -> dict:
    lang = request.cookies.get("lang", "ar")
    return {
        "request": request,
        "t": get_translations(lang),
        "profile": get_profile(lang),
        "current_user": user,
        "lang": lang,
        "dir": "rtl" if lang == "ar" else "ltr",
    }


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure user is admin"""
    if user.role != Role.admin:
        raise HTTPException(status_code=403, detail="صلاحيات غير كافية")
    return user


# ==================== ADMIN DASHBOARD ====================
@router.get("", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
):
    # Get overview stats
    users_count = await session.execute(select(func.count(User.id)))
    bookings_count = await session.execute(select(func.count(Booking.id)))
    services_count = await session.execute(select(func.count(Service.id)))
    reviews_count = await session.execute(select(func.count(Review.id)))
    
    # Get recent bookings
    recent_bookings = await session.execute(
        select(Booking)
        .options(selectinload(Booking.service), selectinload(Booking.client))
        .order_by(Booking.created_at.desc())
        .limit(5)
    )
    
    # Get users by role
    role_counts = {}
    for role in Role:
        count = await session.execute(select(func.count(User.id)).where(User.role == role))
        role_counts[role.value] = count.scalar()
    
    stats = {
        "users": users_count.scalar(),
        "bookings": bookings_count.scalar(),
        "services": services_count.scalar(),
        "reviews": reviews_count.scalar(),
        "role_counts": role_counts,
    }
    
    context = _base_context(request, user)
    context["stats"] = stats
    context["recent_bookings"] = recent_bookings.scalars().all()
    return templates.TemplateResponse("admin/dashboard.html", context)


# ==================== USERS CRUD ====================
@router.get("/users", response_class=HTMLResponse)
async def list_users(
    request: Request,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    
    context = _base_context(request, user)
    context["users"] = users
    context["roles"] = [r for r in Role]
    return templates.TemplateResponse("admin/partials/users_list.html", context)


@router.post("/users/{user_id}/update", response_class=HTMLResponse)
async def update_user(
    user_id: int,
    full_name: str = Form(...),
    email: str = Form(...),
    role: str = Form(...),
    is_active: bool = Form(False),
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        return HTMLResponse("المستخدم غير موجود", status_code=404)
    
    target_user.full_name = full_name
    target_user.email = email
    target_user.role = Role(role)
    target_user.is_active = is_active
    await session.commit()
    
    return _redirect("/admin")


@router.post("/users/{user_id}/delete", response_class=HTMLResponse)
async def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
):
    from sqlalchemy import delete as sql_delete
    from app.models.review import Review
    
    result = await session.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        return HTMLResponse("المستخدم غير موجود", status_code=404)
    
    # Prevent self-deletion
    if target_user.id == admin.id:
        return HTMLResponse("لا يمكنك حذف حسابك", status_code=400)
    
    # Get all bookings by this user to delete their reviews first
    user_bookings = await session.execute(
        select(Booking).where(Booking.client_id == user_id)
    )
    booking_ids = [b.id for b in user_bookings.scalars().all()]
    
    if booking_ids:
        # Delete reviews for these bookings
        await session.execute(
            sql_delete(Review).where(Review.booking_id.in_(booking_ids))
        )
        # Delete the bookings
        await session.execute(
            sql_delete(Booking).where(Booking.client_id == user_id)
        )
    
    # Also unassign this user from any bookings they were assigned to
    await session.execute(
        select(Booking).where(Booking.assigned_employee_id == user_id)
    )
    # Set assigned_employee_id to NULL for bookings assigned to this user
    from sqlalchemy import update as sql_update
    await session.execute(
        sql_update(Booking).where(Booking.assigned_employee_id == user_id).values(assigned_employee_id=None)
    )
    
    await session.delete(target_user)
    await session.commit()
    return _redirect("/admin")


@router.post("/users/create", response_class=HTMLResponse)
async def create_user(
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone: str = Form(""),
    role: str = Form("client"),
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
):
    exists = await session.execute(select(User).where(User.email == email))
    if exists.scalar_one_or_none():
        return HTMLResponse("البريد مستخدم بالفعل", status_code=400)
    
    user = User(
        email=email,
        full_name=full_name,
        phone=phone,
        hashed_password=hash_password(password),
        role=Role(role),
    )
    session.add(user)
    await session.commit()
    return _redirect("/admin")


# ==================== BOOKINGS CRUD ====================
@router.get("/bookings", response_class=HTMLResponse)
async def list_bookings(
    request: Request,
    status: str | None = None,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
):
    query = select(Booking).options(
        selectinload(Booking.service),
        selectinload(Booking.client),
        selectinload(Booking.assigned_employee)
    )
    
    if status and status != "all":
        query = query.where(Booking.status == status)
    
    query = query.order_by(Booking.created_at.desc())
    result = await session.execute(query)
    bookings = result.scalars().all()
    
    # Get employees for assignment dropdown
    employees = await session.execute(
        select(User).where(User.role.in_([Role.employee, Role.technical, Role.driver]))
    )
    
    context = _base_context(request, admin)
    context["bookings"] = bookings
    context["employees"] = employees.scalars().all()
    context["statuses"] = [s for s in BookingStatus]
    return templates.TemplateResponse("admin/partials/bookings_list.html", context)


@router.post("/bookings/{booking_id}/update", response_class=HTMLResponse)
async def update_booking(
    booking_id: int,
    status: str = Form(...),
    assigned_employee_id: str | None = Form(None),
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        return HTMLResponse("الطلب غير موجود", status_code=404)
    
    booking.status = BookingStatus(status)
    
    # Handle optional employee assignment
    if assigned_employee_id and assigned_employee_id.strip():
        booking.assigned_employee_id = int(assigned_employee_id)
    else:
        booking.assigned_employee_id = None
        
    await session.commit()
    
    return _redirect("/admin")


@router.post("/bookings/{booking_id}/delete", response_class=HTMLResponse)
async def delete_booking(
    booking_id: int,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        return HTMLResponse("الطلب غير موجود", status_code=404)
    
    await session.delete(booking)
    await session.commit()
    return _redirect("/admin")


# ==================== SERVICES CRUD ====================
@router.get("/services", response_class=HTMLResponse)
async def list_services(
    request: Request,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(select(Service).order_by(Service.id))
    services = result.scalars().all()
    
    context = _base_context(request, admin)
    context["services"] = services
    return templates.TemplateResponse("admin/partials/services_list.html", context)


@router.post("/services/create", response_class=HTMLResponse)
async def create_service(
    name_ar: str = Form(...),
    name_en: str = Form(""),
    description: str = Form(""),
    price: float = Form(0.0),
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
):
    service = Service(name_ar=name_ar, name_en=name_en, description=description, price=price)
    session.add(service)
    await session.commit()
    return _redirect("/admin")


@router.post("/services/{service_id}/update", response_class=HTMLResponse)
async def update_service(
    service_id: int,
    name_ar: str = Form(...),
    name_en: str = Form(""),
    description: str = Form(""),
    price: float = Form(0.0),
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    if not service:
        return HTMLResponse("الخدمة غير موجودة", status_code=404)
    
    service.name_ar = name_ar
    service.name_en = name_en
    service.description = description
    service.price = price
    await session.commit()
    return _redirect("/admin")


@router.post("/services/{service_id}/delete", response_class=HTMLResponse)
async def delete_service(
    service_id: int,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    if not service:
        return HTMLResponse("الخدمة غير موجودة", status_code=404)
    
    await session.delete(service)
    await session.commit()
    return _redirect("/admin")
