from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.booking import Booking, BookingStatus
from app.models.review import Review
from app.models.service import Service
from app.models.user import User, Role
from app.services.deps import get_current_user
from app.services.content import get_translations, get_profile

router = APIRouter(prefix="/bookings")
templates = Jinja2Templates(directory="app/templates")


def _redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


def _get_lang(request: Request) -> str:
    """Get language from cookie, default to Arabic."""
    return request.cookies.get("lang", "ar")


def _base_context(request: Request, user: User | None = None) -> dict:
    lang = _get_lang(request)
    return {
        "request": request,
        "t": get_translations(lang),
        "profile": get_profile(lang),
        "current_user": user,
        "lang": lang,
        "dir": "rtl" if lang == "ar" else "ltr",
    }


@router.post("")
async def create_booking(
    service_id: int = Form(...),
    contact_name: str = Form(...),
    contact_phone: str = Form(...),
    description: str = Form(""),
    location_lat: float | None = Form(None),
    location_lng: float | None = Form(None),
    address_text: str = Form(""),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    if not service:
        return HTMLResponse("الخدمة غير موجودة", status_code=404)

    booking = Booking(
        client_id=user.id,
        service_id=service_id,
        contact_name=contact_name,
        contact_phone=contact_phone,
        description=description,
        location_lat=location_lat,
        location_lng=location_lng,
        address_text=address_text,
        status=BookingStatus.requested,
    )
    session.add(booking)
    await session.commit()
    return _redirect("/dashboard")


@router.get("", response_class=HTMLResponse)
async def list_bookings(
    request: Request,
    status: str | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    query = select(Booking).options(
        selectinload(Booking.review),
        selectinload(Booking.service),
        selectinload(Booking.client)
    )

    # Role-based access control
    if user.role not in {Role.employee, Role.technical, Role.driver, Role.admin}:
        query = query.where(Booking.client_id == user.id)

    # Status filter
    if status and status != 'all':
        query = query.where(Booking.status == status)

    query = query.order_by(Booking.created_at.desc())
    result = await session.execute(query)
    bookings = result.scalars().all()

    # For employees, pass additional context for action buttons
    context = _base_context(request, user=user)
    context["bookings"] = bookings
    context["is_staff"] = user.role in {Role.employee, Role.technical, Role.driver, Role.admin}
    return templates.TemplateResponse("partials/bookings_list.html", context)


@router.post("/{booking_id}/review")
async def create_review(
    booking_id: int,
    rating: int = Form(...),
    comment: str = Form(""),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(
        select(Booking).options(selectinload(Booking.review)).where(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()
    if not booking or booking.client_id != user.id:
        return HTMLResponse("غير مصرح", status_code=403)
    if booking.status != BookingStatus.completed:
        return HTMLResponse("لا يمكن تقييم الطلب قبل الاكتمال", status_code=400)
    if booking.review:
        return HTMLResponse("تم التقييم مسبقًا", status_code=400)
    review = Review(booking_id=booking.id, rating=rating, comment=comment)
    session.add(review)
    await session.commit()
    return _redirect("/dashboard")


@router.post("/{booking_id}/status")
async def update_booking_status(
    booking_id: int,
    new_status: str = Form(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Allow employees/staff to update booking status."""
    # Only staff can update status
    if user.role not in {Role.employee, Role.technical, Role.driver, Role.admin}:
        return HTMLResponse("غير مصرح لك بهذا الإجراء", status_code=403)
    
    result = await session.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    
    if not booking:
        return HTMLResponse("الطلب غير موجود", status_code=404)
    
    # Update status
    try:
        booking.status = BookingStatus(new_status)
        # If assigning, set the employee
        if new_status == BookingStatus.assigned.value:
            booking.assigned_employee_id = user.id
        await session.commit()
    except ValueError:
        return HTMLResponse("حالة غير صالحة", status_code=400)
    
    return _redirect("/dashboard")
