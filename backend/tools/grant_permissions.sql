-- SQL скрипт для предоставления прав пользователю zone_user
-- Выполните этот скрипт от суперпользователя PostgreSQL (например, postgres)

-- Предоставляем права на INSERT, UPDATE, DELETE в таблице regions
GRANT INSERT, UPDATE, DELETE ON regions TO zone_user;

-- Предоставляем права на использование последовательностей (если нужно)
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO zone_user;
