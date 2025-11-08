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