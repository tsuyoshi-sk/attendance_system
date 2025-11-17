/*
  # Create Attendance System Tables

  1. New Tables
    - `profiles` - User profiles with employee information
      - `id` (uuid, primary key, links to auth.users)
      - `name` (text)
      - `email` (text)
      - `created_at` (timestamp)
    
    - `attendance_records` - Daily attendance check-in/check-out records
      - `id` (uuid, primary key)
      - `user_id` (uuid, foreign key to profiles)
      - `check_in_time` (timestamp)
      - `check_out_time` (timestamp, nullable)
      - `date` (date)
      - `created_at` (timestamp)

  2. Security
    - Enable RLS on both tables
    - Users can only read/write their own records
    - Profiles are readable by all authenticated users for directory purposes
*/

CREATE TABLE IF NOT EXISTS profiles (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  name text NOT NULL,
  email text NOT NULL,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read all profiles"
  ON profiles FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Users can update own profile"
  ON profiles FOR UPDATE
  TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

CREATE TABLE IF NOT EXISTS attendance_records (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  check_in_time timestamptz NOT NULL,
  check_out_time timestamptz,
  date date NOT NULL,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE attendance_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own attendance records"
  ON attendance_records FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own attendance records"
  ON attendance_records FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own attendance records"
  ON attendance_records FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_attendance_user_date ON attendance_records(user_id, date);
CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance_records(date);
