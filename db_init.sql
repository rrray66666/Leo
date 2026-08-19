-- CRM System - MySQL initialization script
-- Run once with a MySQL root account:
--   mysql -uroot -p < db_init.sql
-- (or paste the statements into a MySQL client such as MySQL Workbench)
--
-- Creates the `crm` database and the `crm` user used by the application.
-- Adjust the password below to match backend/.env DATABASE_URL if needed.

CREATE DATABASE IF NOT EXISTS crm
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'crm'@'localhost' IDENTIFIED BY 'crm123';

GRANT ALL PRIVILEGES ON crm.* TO 'crm'@'localhost';
FLUSH PRIVILEGES;
