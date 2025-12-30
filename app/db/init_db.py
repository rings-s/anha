from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service import Service


SERVICE_SEED = [
    {
        "name_ar": "إدارة المرافق العامة",
        "description": "حلول متكاملة لتشغيل وإدارة المرافق لضمان استمرارية الأعمال ورفع الكفاءة التشغيلية.",
    },
    {
        "name_ar": "اللالندسكيب والمساحات الخضراء",
        "description": "تصميم وتطوير المساحات الخضراء وصيانتها بأنظمة ري مستدامة.",
    },
    {
        "name_ar": "الكهرباء",
        "description": "تمديد الشبكات، تركيب اللوحات، أعمال التأريض والإنارة الداخلية والخارجية.",
    },
    {
        "name_ar": "السباكة",
        "description": "تمديد الأنابيب، إصلاح التسريبات والانسدادات، وصيانة الخزانات.",
    },
    {
        "name_ar": "الميكانيكا",
        "description": "صيانة المصاعد وأنظمة التكييف والمضخات والأنابيب.",
    },
    {
        "name_ar": "النظافة",
        "description": "نظافة يومية وعميقة، تعقيم وتطهير، تنظيف الواجهات وإدارة النفايات.",
    },
    {
        "name_ar": "أنظمة المباني والكاميرات",
        "description": "توريد وتركيب أنظمة المراقبة وربطها بغرف التحكم والصيانة الدورية.",
    },
    {
        "name_ar": "الضيافة",
        "description": "توفير أطقم ضيافة مدربة وتنظيم المناسبات وصالات الانتظار.",
    },
]


async def init_db(session: AsyncSession) -> None:
    existing = await session.execute(select(Service))
    if existing.scalars().first():
        return
    session.add_all(Service(**item) for item in SERVICE_SEED)
    await session.commit()
