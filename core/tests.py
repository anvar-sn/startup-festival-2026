import asyncio
import datetime
import json
from unittest.mock import AsyncMock, patch

from aiogram.fsm.storage.base import StorageKey
from django.conf import settings
from django.test import TransactionTestCase

from core.bot_engine import (
    DjangoORMStorage,
    get_webhook_secret,
    parse_festival_datetime,
    shift_datetime_months,
    update_festival_date_db,
)
from core.models import AuditLog, FestivalSetting, get_tashkent_tz


class FestivalDateAndWebhookTests(TransactionTestCase):
    def test_festival_setting_updates_home_page_dynamically(self):
        tz = get_tashkent_tz()
        cfg = FestivalSetting.get_solo()
        cfg.festival_date = datetime.datetime(2026, 12, 25, 10, 30, tzinfo=tz)
        cfg.location = "Urganch"
        cfg.save()

        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")
        self.assertIn("2026-12-25T10:30:00+05:00", html)
        self.assertIn("25-Dekabr, 2026 (Urganch)", html)
        self.assertIn("25-dekabr kuni festival soat 10:30", html)

    def test_parse_festival_datetime_and_month_shift(self):
        tz = get_tashkent_tz()
        base = datetime.datetime(2026, 11, 19, 9, 0, tzinfo=tz)

        dt1 = parse_festival_datetime("25.12.2026", base)
        self.assertEqual((dt1.year, dt1.month, dt1.day, dt1.hour, dt1.minute), (2026, 12, 25, 9, 0))

        dt2 = parse_festival_datetime("25.12.2026 14:45", base)
        self.assertEqual((dt2.year, dt2.month, dt2.day, dt2.hour, dt2.minute), (2026, 12, 25, 14, 45))

        dt3 = parse_festival_datetime("2027-01-10 11:00", base)
        self.assertEqual((dt3.year, dt3.month, dt3.day, dt3.hour, dt3.minute), (2027, 1, 10, 11, 0))

        self.assertIsNone(parse_festival_datetime("31.02.2026", base))
        self.assertIsNone(parse_festival_datetime("not a date", base))

        shifted = shift_datetime_months(datetime.datetime(2026, 1, 31, 9, 0, tzinfo=tz), 1)
        self.assertEqual((shifted.year, shifted.month, shifted.day), (2026, 2, 28))

    def test_update_festival_date_db_logs_audit(self):
        tz = get_tashkent_tz()
        new_dt = datetime.datetime(2026, 12, 20, 10, 0, tzinfo=tz)
        res = asyncio.run(update_festival_date_db(new_dt, "@anvar_sn"))
        self.assertIn("20-Dekabr, 2026", res["new_full"])
        self.assertTrue(AuditLog.objects.filter(action="tg_festival_date_changed").exists())

    def test_django_orm_fsm_storage(self):
        storage = DjangoORMStorage()
        key = StorageKey(bot_id=1, chat_id=123, user_id=456)

        async def _flow():
            self.assertIsNone(await storage.get_state(key))
            await storage.set_state(key, "BotStates:waiting_for_festival_date")
            self.assertEqual(await storage.get_state(key), "BotStates:waiting_for_festival_date")
            await storage.set_data(key, {"full_name": "Aliyev Vali", "step": 2})
            self.assertEqual(await storage.get_data(key), {"full_name": "Aliyev Vali", "step": 2})
            await storage.set_state(key, None)
            await storage.set_data(key, {})
            self.assertIsNone(await storage.get_state(key))
            self.assertEqual(await storage.get_data(key), {})

        asyncio.run(_flow())

    def test_health_and_webhook_endpoints(self):
        resp_health = self.client.get("/health/")
        self.assertEqual(resp_health.status_code, 200)
        data = resp_health.json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["db_ok"])

        # Unauthorized webhook -> 403
        resp_403 = self.client.post(
            "/telegram/webhook/",
            data=json.dumps({"update_id": 1}),
            content_type="application/json",
        )
        self.assertEqual(resp_403.status_code, 403)

        # Valid webhook secret -> 200
        with patch("core.bot_engine.process_webhook_update", new_callable=AsyncMock) as mock_proc:
            resp_ok = self.client.post(
                "/telegram/webhook/",
                data=json.dumps({"update_id": 99}),
                content_type="application/json",
                HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=get_webhook_secret(),
            )
            self.assertEqual(resp_ok.status_code, 200)
            self.assertEqual(resp_ok.json(), {"ok": True})
            mock_proc.assert_awaited_once()

        # Unauthorized setup-webhook -> 403
        self.assertEqual(self.client.get("/telegram/setup-webhook/?key=bad").status_code, 403)

        # Authorized setup-webhook -> 200
        with patch(
            "core.bot_engine.setup_telegram_webhook",
            new_callable=AsyncMock,
            return_value={"ok": True, "url": "https://startup-festival-2026.vercel.app/telegram/webhook/"},
        ):
            setup_resp = self.client.get(f"/telegram/setup-webhook/?key={settings.SECRET_KEY}")
            self.assertEqual(setup_resp.status_code, 200)
            self.assertTrue(setup_resp.json()["ok"])
