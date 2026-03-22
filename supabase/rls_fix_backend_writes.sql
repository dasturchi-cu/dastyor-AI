-- =============================================================================
-- Bot + FastAPI backend yozuvlari bazaga tushmasa (RLS + anon kalit)
--
-- YAXSHI YECHIM (tavsiya):
--   Server muhitida (Render/Railway/VPS) quyidagilarni qo'ying:
--   SUPABASE_URL=...
--   SUPABASE_SERVICE_ROLE_KEY=...   (Supabase → Project Settings → API → service_role)
--   Service role RLS dan o'tadi, yozish ishlaydi.
--
-- MUVOFIQ YECHIM (faqat ichki bot serveri ishonchli bo'lsa):
--   Quyidagi jadvallarda RLS o'chiriladi — brauzerga ANON kalitni bermasligingiz kerak.
-- =============================================================================

ALTER TABLE public.users DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_usage DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.bot_settings DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.premium_subscriptions DISABLE ROW LEVEL SECURITY;

-- Loyihangizdagi qo'shimcha jadvallar (agar RLS yozishni to'sasa)
ALTER TABLE public.cv_generations DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.generated_files DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.objective_generations DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.obyektivka_exports DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.ocr_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.support_messages DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.mandatory_channels DISABLE ROW LEVEL SECURITY;
