from email.message import EmailMessage
import aiosmtplib
from app.core.config import get_settings

settings = get_settings()

async def send_email(subject: str, recipient: str, body: str, html: bool = False):
    """
    Generic asynchronous function to send an email.
    """
    if not settings.smtp_password:
        print(f"DEBUG: Internal email logging (No SMTP Password): To: {recipient} | Subject: {subject}")
        return

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message["Subject"] = subject
    
    if html:
        message.add_alternative(body, subtype="html")
    else:
        message.set_content(body)

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=settings.smtp_tls,
        )
    except Exception as e:
        print(f"CRITICAL: Failed to send email to {recipient}: {str(e)}")
        # In a real app, we might raise an exception or log to a file
        pass

async def send_password_reset_email(email: str, token: str):
    """
    Send a password reset email with a link.
    """
    # Use centralized base URL from settings
    base_url = settings.base_url.rstrip("/")
    reset_link = f"{base_url}/reset/verify/{token}"
    
    subject = "إعادة تعيين كلمة المرور - ANHA Trading"
    body = f"""
    مرحباً،
    
    لقد تلقينا طلباً لإعادة تعيين كلمة المرور الخاصة بك. يرجى النقر على الرابط أدناه للمتابعة:
    
    {reset_link}
    
    إذا لم تطلب هذا، يرجى تجاهل هذا البريد.
    
    شكراً،
    فريق انها التجارية
    """
    
    # Simple plain text for now, can be upgraded to HTML later
    await send_email(subject, email, body)
