CREATE TABLE IF NOT EXISTS `warns` (
  `id` int(11) NOT NULL,
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `moderator_id` varchar(20) NOT NULL,
  `reason` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `levels` (
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `xp` int(11) NOT NULL DEFAULT 0,
  `level` int(11) NOT NULL DEFAULT 0,
  `total_messages` int(11) NOT NULL DEFAULT 0,
  `last_xp_time` timestamp NULL,
  PRIMARY KEY (`user_id`, `server_id`)
);

CREATE TABLE IF NOT EXISTS `level_roles` (
  `server_id` varchar(20) NOT NULL,
  `level` int(11) NOT NULL,
  `role_id` varchar(20) NOT NULL,
  PRIMARY KEY (`server_id`, `level`)
);

CREATE TABLE IF NOT EXISTS `claude_conversations` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `channel_id` varchar(20) NOT NULL,
  `user_id` varchar(20) NOT NULL,
  `role` varchar(10) NOT NULL,
  `content` TEXT NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `affirmation_config` (
  `server_id` varchar(20) NOT NULL PRIMARY KEY,
  `channel_id` varchar(20) NOT NULL,
  `post_time` varchar(5) NOT NULL,
  `timezone_offset` int DEFAULT 0,
  `enabled` boolean NOT NULL DEFAULT 1,
  `theme` varchar(50) DEFAULT 'motivation',
  `last_post_date` varchar(10) DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS `news_config` (
  `server_id` varchar(20) NOT NULL,
  `channel_id` varchar(20) NOT NULL,
  `post_time` varchar(5) NOT NULL,
  `timezone_offset` int DEFAULT 0,
  `enabled` boolean NOT NULL DEFAULT 1,
  `last_post_date` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`server_id`, `post_time`)
);

CREATE TABLE IF NOT EXISTS `news_sources` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `server_id` varchar(20) NOT NULL,
  `source_name` varchar(100) NOT NULL,
  `rss_url` TEXT NOT NULL,
  FOREIGN KEY (`server_id`) REFERENCES `news_config`(`server_id`)
);

CREATE TABLE IF NOT EXISTS `posted_articles` (
  `article_id` TEXT NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `posted_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`article_id`, `server_id`)
);

CREATE TABLE IF NOT EXISTS `vibes_config` (
  `server_id` varchar(20) NOT NULL PRIMARY KEY,
  `memory_emoji` varchar(100) DEFAULT '💾',
  `qotd_enabled` boolean NOT NULL DEFAULT 0,
  `throwback_enabled` boolean NOT NULL DEFAULT 1,
  `auto_suggest_memories` boolean NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS `memories` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `server_id` varchar(20) NOT NULL,
  `message_id` varchar(20) NOT NULL,
  `channel_id` varchar(20) NOT NULL,
  `author_id` varchar(20) NOT NULL,
  `saved_by_id` varchar(20) NOT NULL,
  `content` TEXT NOT NULL,
  `context_before` TEXT,
  `context_after` TEXT,
  `save_reason` varchar(20) DEFAULT 'manual',
  `category` varchar(50),
  `reactions_count` int DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `saved_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (`server_id`, `message_id`)
);

CREATE TABLE IF NOT EXISTS `qotd_schedule` (
  `server_id` varchar(20) NOT NULL PRIMARY KEY,
  `channel_id` varchar(20) NOT NULL,
  `post_time` varchar(5) NOT NULL,
  `timezone_offset` int DEFAULT 0,
  `last_post_date` varchar(10) DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS `qotd_questions` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `server_id` varchar(20),
  `question` TEXT NOT NULL,
  `category` varchar(50) DEFAULT 'random',
  `is_custom` boolean NOT NULL DEFAULT 0,
  `submitted_by_id` varchar(20),
  `times_asked` int DEFAULT 0,
  `total_reactions` int DEFAULT 0,
  `last_asked_date` varchar(10) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `trivia_config` (
  `server_id` varchar(20) NOT NULL PRIMARY KEY,
  `channel_id` varchar(20) NOT NULL,
  `post_time` varchar(5) NOT NULL,
  `timezone_offset` int DEFAULT 0,
  `enabled` boolean NOT NULL DEFAULT 1,
  `last_post_date` varchar(10) DEFAULT NULL,
  `questions_per_game` int DEFAULT 5,
  `difficulty` varchar(20) DEFAULT 'medium'
);

CREATE TABLE IF NOT EXISTS `trivia_scores` (
  `server_id` varchar(20) NOT NULL,
  `user_id` varchar(20) NOT NULL,
  `total_correct` int DEFAULT 0,
  `total_answered` int DEFAULT 0,
  `current_streak` int DEFAULT 0,
  `best_streak` int DEFAULT 0,
  `total_points` int DEFAULT 0,
  `last_played` timestamp DEFAULT NULL,
  PRIMARY KEY (`server_id`, `user_id`)
);

CREATE TABLE IF NOT EXISTS `trivia_history` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `server_id` varchar(20) NOT NULL,
  `user_id` varchar(20) NOT NULL,
  `question` TEXT NOT NULL,
  `correct_answer` varchar(10) NOT NULL,
  `user_answer` varchar(10),
  `correct` boolean NOT NULL,
  `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `category` varchar(50) NOT NULL,
  `difficulty` varchar(20) NOT NULL,
  `points_earned` int DEFAULT 0
);

CREATE TABLE IF NOT EXISTS `creative_config` (
  `server_id` varchar(20) NOT NULL PRIMARY KEY,
  `channel_id` varchar(20) NOT NULL,
  `post_time` varchar(5) NOT NULL,
  `timezone_offset` int DEFAULT 0,
  `daily_prompts_enabled` boolean NOT NULL DEFAULT 1,
  `weekly_challenges_enabled` boolean NOT NULL DEFAULT 1,
  `last_daily_post` varchar(10) DEFAULT NULL,
  `last_weekly_post` varchar(10) DEFAULT NULL,
  `current_month_theme` varchar(100) DEFAULT NULL,
  `prompt_rotation` varchar(20) DEFAULT 'writing'
);

CREATE TABLE IF NOT EXISTS `collaborative_works` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `server_id` varchar(20) NOT NULL,
  `channel_id` varchar(20) NOT NULL,
  `thread_id` varchar(20) NOT NULL,
  `work_type` varchar(20) NOT NULL,
  `title` TEXT NOT NULL,
  `prompt` TEXT NOT NULL,
  `started_by_id` varchar(20) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `completed` boolean NOT NULL DEFAULT 0,
  `completed_at` timestamp DEFAULT NULL,
  `contribution_count` int DEFAULT 0
);

CREATE TABLE IF NOT EXISTS `work_contributions` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `work_id` int NOT NULL,
  `user_id` varchar(20) NOT NULL,
  `content` TEXT NOT NULL,
  `contribution_number` int NOT NULL,
  `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `word_count` int DEFAULT 0,
  FOREIGN KEY (`work_id`) REFERENCES `collaborative_works`(`id`)
);

CREATE TABLE IF NOT EXISTS `creative_challenges` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `server_id` varchar(20) NOT NULL,
  `challenge_type` varchar(20) NOT NULL,
  `prompt` TEXT NOT NULL,
  `description` TEXT,
  `start_date` varchar(10) NOT NULL,
  `end_date` varchar(10) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `voting_enabled` boolean NOT NULL DEFAULT 1,
  `winner_id` varchar(20) DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS `challenge_submissions` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `challenge_id` int NOT NULL,
  `user_id` varchar(20) NOT NULL,
  `submission_text` TEXT NOT NULL,
  `submission_url` TEXT,
  `submitted_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `votes` int DEFAULT 0,
  FOREIGN KEY (`challenge_id`) REFERENCES `creative_challenges`(`id`),
  UNIQUE (`challenge_id`, `user_id`)
);

CREATE TABLE IF NOT EXISTS `creative_gallery` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `server_id` varchar(20) NOT NULL,
  `user_id` varchar(20) NOT NULL,
  `work_type` varchar(20) NOT NULL,
  `title` TEXT NOT NULL,
  `content` TEXT NOT NULL,
  `image_url` TEXT,
  `reactions` int DEFAULT 0,
  `showcased_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `collaborative_work_id` int DEFAULT NULL,
  FOREIGN KEY (`collaborative_work_id`) REFERENCES `collaborative_works`(`id`)
);

CREATE TABLE IF NOT EXISTS `saved_recipes` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `user_id` varchar(20) NOT NULL,
  `recipe_name` TEXT NOT NULL,
  `recipe_data` TEXT NOT NULL,
  `cuisine` varchar(50),
  `dietary` varchar(50),
  `difficulty` varchar(20),
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `recipe_daily_config` (
  `server_id` varchar(20) NOT NULL PRIMARY KEY,
  `channel_id` varchar(20) NOT NULL,
  `post_time` varchar(5) NOT NULL,
  `timezone_offset` int DEFAULT 0,
  `enabled` boolean NOT NULL DEFAULT 1,
  `cuisine_preference` varchar(50) DEFAULT 'random',
  `dietary_preference` varchar(50) DEFAULT 'none',
  `last_post_date` varchar(10) DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS `art_config` (
  `server_id` varchar(20) NOT NULL PRIMARY KEY,
  `channel_id` varchar(20) NOT NULL,
  `post_time` varchar(5) NOT NULL,
  `timezone_offset` int DEFAULT 0,
  `enabled` boolean NOT NULL DEFAULT 1,
  `last_post_date` varchar(10) DEFAULT NULL,
  `focus_areas` TEXT DEFAULT 'all',
  `include_contemporary` boolean NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS `art_favorites` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `artwork_title` TEXT NOT NULL,
  `artist` TEXT NOT NULL,
  `museum` varchar(100) NOT NULL,
  `image_url` TEXT,
  `artwork_url` TEXT,
  `saved_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `art_analysis_cache` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `artwork_url` TEXT NOT NULL UNIQUE,
  `image_url` TEXT NOT NULL,
  `artwork_title` TEXT,
  `artist` TEXT,
  `museum` TEXT,
  `vision_story` TEXT NOT NULL,
  `analysis_model` varchar(50) DEFAULT 'claude-3-sonnet-20240229',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_used_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_artwork_url ON art_analysis_cache(artwork_url);