# Dastyor AI — Database Schema (Supabase / PostgreSQL)

Currently, the bot relies on local JSON files (`user_profiles.json`, `usage_data.json`, `bot_settings.json`) for data persistence. To scale the bot, we plan to migrate to **Supabase (PostgreSQL)**. 

Below is the proposed relational database schema mapped directly from the current JSON structures.

## 1. `users` Table
Stores all user profile data, statistics, and preferences.

| Column Name         | Data Type                  | Constraints                  | Description                                      |
|---------------------|----------------------------|------------------------------|--------------------------------------------------|
| `id`                | `BIGINT`                   | PRIMARY KEY                  | Telegram User ID                                 |
| `first_name`        | `TEXT`                     | NOT NULL                     | User's Telegram first name                       |
| `username`          | `TEXT`                     | NULL                         | User's Telegram username                         |
| `joined_at`         | `TIMESTAMP WITH TIME ZONE` | DEFAULT NOW()                | When the user first started the bot              |
| `last_active`       | `TIMESTAMP WITH TIME ZONE` | DEFAULT NOW()                | Timestamp of the user's last interaction         |
| `interaction_count` | `INTEGER`                  | DEFAULT 0                    | Total number of standard interactions            |
| `activity_count`    | `INTEGER`                  | DEFAULT 0                    | Total number of general activities               |
| `files_processed`   | `INTEGER`                  | DEFAULT 0                    | Total number of files the user has processed     |
| `sessions`          | `INTEGER`                  | DEFAULT 0                    | Number of active sessions the user has started   |
| `chat_id`           | `BIGINT`                   | NOT NULL                     | Telegram Chat ID (usually same as user ID)       |
| `lang`              | `VARCHAR(10)`              | DEFAULT 'uz_lat'             | User language preference (`uz_lat`, `en`, etc.)  |
| `feedback_count`    | `INTEGER`                  | DEFAULT 0                    | Number of feedbacks submitted by the user        |
| `blocked_bot`       | `BOOLEAN`                  | DEFAULT FALSE                | Whether the user has blocked the bot             |
| `is_banned`         | `BOOLEAN`                  | DEFAULT FALSE                | Whether the user is banned from using the bot    |
| `ban_reason`        | `TEXT`                     | NULL                         | Reason for the ban (if applicable)               |
| `ban_date`          | `TIMESTAMP WITH TIME ZONE` | NULL                         | When the user was banned                         |
| `last_service`      | `VARCHAR(50)`              | NULL                         | The last feature/service used by the user        |

## 2. `premium_subscriptions` Table
Tracks premium access granted to users.

| Column Name   | Data Type                  | Constraints                           | Description                               |
|---------------|----------------------------|---------------------------------------|-------------------------------------------|
| `id`          | `UUID`                     | PRIMARY KEY, DEFAULT gen_random_uuid()| Unique subscription record ID             |
| `user_id`     | `BIGINT`                   | FOREIGN KEY (`users.id`)              | The user who holds the subscription       |
| `granted_by`  | `TEXT`                     | NULL                                  | Admin/System who granted the subscription |
| `start_date`  | `TIMESTAMP WITH TIME ZONE` | DEFAULT NOW()                         | When the premium access started           |
| `end_date`    | `TIMESTAMP WITH TIME ZONE` | NOT NULL                              | When the premium access expires           |

## 3. `daily_usage` Table
Tracks daily feature usage for rate-limiting (e.g., max 10 requests/day for free users).

| Column Name | Data Type | Constraints                               | Description                               |
|-------------|-----------|-------------------------------------------|-------------------------------------------|
| `id`        | `UUID`    | PRIMARY KEY, DEFAULT gen_random_uuid()    | Unique usage record ID                    |
| `user_id`   | `BIGINT`  | FOREIGN KEY (`users.id`)                  | The user making requests                  |
| `usage_date`| `DATE`    | NOT NULL, DEFAULT CURRENT_DATE            | The date of the usage record              |
| `count`     | `INTEGER` | DEFAULT 0                                 | Number of requests made on this date      |

> **Index:** A unique constraint should be placed on `(user_id, usage_date)` to allow easy "UPSERT" operations.

## 4. `bot_settings` Table
A single-row configuration table for global bot settings.

| Column Name        | Data Type | Constraints             | Description                                  |
|--------------------|-----------|-------------------------|----------------------------------------------|
| `id`               | `INTEGER` | PRIMARY KEY, CHECK (id=1) | Enforces single-row table                    |
| `daily_limit`      | `INTEGER` | DEFAULT 10              | Default daily usage limit for non-premium    |
| `maintenance_mode` | `BOOLEAN` | DEFAULT FALSE           | If true, bot is disabled for normal users    |

## 5. `mandatory_channels` Table
Channels that users MUST subscribe to in order to use the bot.

| Column Name | Data Type | Constraints | Description                                       |
|-------------|-----------|-------------|---------------------------------------------------|
| `channel_id`| `BIGINT`  | PRIMARY KEY | Telegram Channel ID                               |
| `name`      | `TEXT`    | NOT NULL    | Display name of the channel                       |
| `url`       | `TEXT`    | NOT NULL    | Invite link or public username (e.g. `@channel`)  |

---

## Migration Strategy
1. **Provision DB:** Create the Supabase project and execute the SQL script for these tables.
2. **Data Export:** Write a Python script to iterate through `user_profiles.json`, `usage_data.json`, and `bot_settings.json`, converting timestamps and data types.
3. **Data Import:** Use the `supabase-py` client to bulk-insert the exported data into the new tables.
4. **Code Update:** Replace `bot.services.user_service.py` file-based logic with async Supabase queries.
