-- 为techTB表添加image_url字段
-- 用于存储文章配图URL

ALTER TABLE techTB ADD COLUMN image_url VARCHAR(500) DEFAULT '' COMMENT '文章配图URL';

-- 为已有数据设置默认值
UPDATE techTB SET image_url = '' WHERE image_url IS NULL;
