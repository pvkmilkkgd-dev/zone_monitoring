-- SQL скрипт для добавления столбца name_original в таблицу regions
-- Выполните этот скрипт от суперпользователя PostgreSQL

-- Добавляем столбец для хранения исходного названия из GeoJSON
ALTER TABLE regions ADD COLUMN IF NOT EXISTS name_original TEXT;

-- Создаем индекс для быстрого поиска по исходному названию
CREATE INDEX IF NOT EXISTS idx_regions_name_original ON regions(name_original);

-- Комментарий к столбцу
COMMENT ON COLUMN regions.name_original IS 'Исходное название региона из GeoJSON файла для сопоставления';
