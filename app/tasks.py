"""
Background tasks executed by the Celery worker.

All tasks use a synchronous SQLAlchemy session (psycopg2) because Celery
workers run in a regular (non-async) context. The async FastAPI app and the
Celery worker share the same database but use different engine/session types.
"""
import logging
import smtplib
from decimal import Decimal
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.celery_app import celery_app
from app.config import settings

logger = logging.getLogger(__name__)

_sync_engine = create_engine(settings.SYNC_DATABASE_URL, pool_pre_ping=True)
SyncSession = sessionmaker(bind=_sync_engine, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_sync_db() -> Session:
    return SyncSession()


def _send_email(to: str, subject: str, body_html: str) -> None:
    if not settings.SMTP_USER:
        logger.info("[Email stub] To=%s | Subject=%s", to, subject)
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to
    msg.attach(MIMEText(body_html, "html"))
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.EMAIL_FROM, to, msg.as_string())


# ---------------------------------------------------------------------------
# Invoice tasks
# ---------------------------------------------------------------------------

@celery_app.task(name="tasks.print_receipt", bind=True, max_retries=3)
def print_receipt(self, invoice_id: int) -> dict:
    """Simulate sending a receipt to the POS printer or email."""
    from app.models import Invoice, Order

    try:
        db = _get_sync_db()
        invoice = db.get(Invoice, invoice_id)
        if not invoice:
            logger.warning("print_receipt: Invoice %d not found", invoice_id)
            return {"status": "skipped", "reason": "invoice_not_found"}

        order = db.get(Order, invoice.order_id)
        logger.info(
            "[RECEIPT] Invoice #%d | Order #%d | Total: %.2f | Method: %s",
            invoice.id,
            invoice.order_id,
            float(invoice.total_amount),
            invoice.payment_method.value,
        )
        db.close()
        return {"status": "printed", "invoice_id": invoice_id}
    except Exception as exc:
        logger.error("print_receipt failed: %s", exc)
        raise self.retry(exc=exc, countdown=10)


@celery_app.task(name="tasks.adjust_inventory_on_invoice", bind=True, max_retries=3)
def adjust_inventory_on_invoice(self, invoice_id: int) -> dict:
    """
    Deducts ingredient stock for every item on a settled invoice.

    Algorithm:
      1. Load all OrderItems for the invoice's order.
      2. For each OrderItem, look up RecipeItem rows mapping that MenuItem
         to Inventory ingredients with required_quantity per unit.
      3. Multiply required_quantity x OrderItem.quantity and subtract from
         Inventory.current_stock.
      4. After all deductions, scan for rows where current_stock < min_alert_level
         and fire a high-priority alert log (or email) for each one.
    """
    from app.models import Inventory, Invoice, OrderItem, RecipeItem

    try:
        db = _get_sync_db()
        invoice = db.get(Invoice, invoice_id)
        if not invoice:
            db.close()
            return {"status": "skipped", "reason": "invoice_not_found"}

        order_items = db.execute(
            select(OrderItem).where(OrderItem.order_id == invoice.order_id)
        ).scalars().all()

        deductions: dict[int, Decimal] = {}

        for order_item in order_items:
            recipe_rows = db.execute(
                select(RecipeItem).where(RecipeItem.menu_item_id == order_item.menu_item_id)
            ).scalars().all()

            if not recipe_rows:
                logger.warning(
                    "[INVENTORY] No recipe mapping for MenuItem #%d — skipping deduction.",
                    order_item.menu_item_id,
                )
                continue

            for recipe in recipe_rows:
                amount = recipe.required_quantity * Decimal(str(order_item.quantity))
                deductions[recipe.ingredient_id] = (
                    deductions.get(recipe.ingredient_id, Decimal("0")) + amount
                )

        low_stock_alerts: list[str] = []

        for ingredient_id, total_deducted in deductions.items():
            ingredient = db.get(Inventory, ingredient_id)
            if not ingredient:
                logger.error("[INVENTORY] Ingredient #%d not found — deduction skipped.", ingredient_id)
                continue

            before = ingredient.current_stock
            ingredient.current_stock = max(
                Decimal("0"), ingredient.current_stock - total_deducted
            )
            db.flush()

            logger.info(
                "[INVENTORY] '%s': %.3f %s → %.3f %s (deducted %.3f)",
                ingredient.ingredient_name,
                float(before), ingredient.unit.value,
                float(ingredient.current_stock), ingredient.unit.value,
                float(total_deducted),
            )

            if ingredient.current_stock < ingredient.min_alert_level:
                alert_msg = (
                    f"LOW STOCK ALERT: '{ingredient.ingredient_name}' is at "
                    f"{ingredient.current_stock:.3f} {ingredient.unit.value} "
                    f"(min: {ingredient.min_alert_level:.3f})"
                )
                logger.warning("[STOCK ALERT] %s", alert_msg)
                low_stock_alerts.append(alert_msg)

        db.commit()
        db.close()

        if low_stock_alerts:
            _send_email(
                settings.EMAIL_FROM,
                f"[Restaurant] Low Stock Alert — {len(low_stock_alerts)} ingredient(s)",
                "<br>".join([f"<p>⚠️ {msg}</p>" for msg in low_stock_alerts]),
            )

        return {
            "status": "ok",
            "invoice_id": invoice_id,
            "ingredients_deducted": len(deductions),
            "low_stock_alerts": len(low_stock_alerts),
        }
    except Exception as exc:
        logger.error("adjust_inventory_on_invoice failed: %s", exc)
        raise self.retry(exc=exc, countdown=15)


# ---------------------------------------------------------------------------
# Reservation tasks
# ---------------------------------------------------------------------------

@celery_app.task(name="tasks.send_reservation_confirmation", bind=True, max_retries=3)
def send_reservation_confirmation(self, reservation_id: int) -> dict:
    """Send an email/SMS confirmation when a reservation is created."""
    from app.models import Reservation

    try:
        db = _get_sync_db()
        reservation = db.get(Reservation, reservation_id)
        if not reservation:
            db.close()
            return {"status": "skipped"}

        subject = "Your Reservation is Confirmed!"
        body = f"""
        <h2>Reservation Confirmed</h2>
        <p>Dear <strong>{reservation.customer_name}</strong>,</p>
        <p>Your table reservation has been confirmed for
        <strong>{reservation.reservation_datetime.strftime('%A, %d %b %Y at %H:%M')}</strong>.</p>
        <p>Table #{reservation.table_id} | Status: {reservation.status.value}</p>
        <p>See you soon!</p>
        """
        _send_email(f"{reservation.customer_phone}@placeholder.com", subject, body)

        logger.info(
            "[RESERVATION] Confirmation sent for reservation #%d — %s (%s)",
            reservation.id,
            reservation.customer_name,
            reservation.customer_phone,
        )
        db.close()
        return {"status": "sent", "reservation_id": reservation_id}
    except Exception as exc:
        logger.error("send_reservation_confirmation failed: %s", exc)
        raise self.retry(exc=exc, countdown=20)


@celery_app.task(name="tasks.send_reservation_reminder", bind=True, max_retries=2)
def send_reservation_reminder(self, reservation_id: int) -> dict:
    """Send a reminder 1 hour before the reservation (schedule via Celery beat)."""
    from app.models import Reservation

    try:
        db = _get_sync_db()
        reservation = db.get(Reservation, reservation_id)
        if not reservation:
            db.close()
            return {"status": "skipped"}

        subject = "Reminder: Your Table is Ready Soon"
        body = f"""
        <h2>Reservation Reminder</h2>
        <p>Dear <strong>{reservation.customer_name}</strong>,</p>
        <p>This is a friendly reminder that your table is reserved in approximately 1 hour —
        <strong>{reservation.reservation_datetime.strftime('%H:%M')}</strong>.</p>
        <p>Table #{reservation.table_id} | We look forward to seeing you!</p>
        """
        _send_email(f"{reservation.customer_phone}@placeholder.com", subject, body)

        logger.info("[REMINDER] Sent for reservation #%d", reservation_id)
        db.close()
        return {"status": "sent", "reservation_id": reservation_id}
    except Exception as exc:
        logger.error("send_reservation_reminder failed: %s", exc)
        raise self.retry(exc=exc, countdown=30)


# ---------------------------------------------------------------------------
# Reporting tasks (scheduled)
# ---------------------------------------------------------------------------

@celery_app.task(name="tasks.generate_daily_sales_report", bind=True)
def generate_daily_sales_report(self) -> dict:
    """
    Aggregate yesterday's invoices into a daily summary.
    Intended to be triggered nightly via Celery Beat.
    """
    from datetime import date, datetime, timedelta, timezone
    from app.models import Invoice

    yesterday = date.today() - timedelta(days=1)
    start = datetime(yesterday.year, yesterday.month, yesterday.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    db = _get_sync_db()
    from sqlalchemy import func
    row = db.execute(
        select(
            func.coalesce(func.sum(Invoice.total_amount), 0).label("revenue"),
            func.count(Invoice.id).label("count"),
        ).where(Invoice.paid_at.between(start, end))
    ).one()

    revenue = float(row.revenue)
    count = int(row.count)
    db.close()

    logger.info(
        "[DAILY REPORT] %s — Revenue: %.2f | Invoices: %d",
        yesterday.isoformat(),
        revenue,
        count,
    )
    return {"date": yesterday.isoformat(), "revenue": revenue, "invoice_count": count}
