/*
  # Add comprehensive HR features

  1. New Tables
    - `departments` - Department/team information
      - `id` (uuid, primary key)
      - `name` (text) - Department name
      - `created_at` (timestamptz)
    
    - `work_patterns` - Work schedule patterns (flex, fixed, etc.)
      - `id` (uuid, primary key)
      - `name` (text) - Pattern name (e.g., "Standard 9-5", "Flex time")
      - `start_time` (time) - Standard start time
      - `end_time` (time) - Standard end time
      - `break_duration` (integer) - Break minutes
      - `is_flexible` (boolean) - Whether this is a flexible schedule
      - `created_at` (timestamptz)
    
    - `paid_leaves` - Paid leave records
      - `id` (uuid, primary key)
      - `user_id` (uuid, foreign key to profiles)
      - `leave_date` (date) - Date of leave
      - `leave_type` (text) - Type (annual, sick, etc.)
      - `status` (text) - Status (pending, approved, rejected)
      - `reason` (text) - Reason for leave
      - `approved_by` (uuid) - Admin who approved
      - `created_at` (timestamptz)
    
    - `shifts` - Shift schedule
      - `id` (uuid, primary key)
      - `user_id` (uuid, foreign key to profiles)
      - `date` (date) - Shift date
      - `start_time` (time) - Shift start time
      - `end_time` (time) - Shift end time
      - `notes` (text)
      - `created_by` (uuid) - Admin who created
      - `created_at` (timestamptz)
    
    - `notification_settings` - User notification preferences
      - `id` (uuid, primary key)
      - `user_id` (uuid, foreign key to profiles)
      - `check_in_reminder` (boolean) - Remind to check in
      - `check_out_reminder` (boolean) - Remind to check out
      - `overtime_alert` (boolean) - Alert for overtime
      - `shift_reminder` (boolean) - Shift start reminder
      - `created_at` (timestamptz)

  2. Changes to Existing Tables
    - Add columns to `profiles`:
      - `department_id` (uuid, foreign key to departments)
      - `work_pattern_id` (uuid, foreign key to work_patterns)
      - `annual_leave_balance` (integer) - Remaining annual leave days
      - `hire_date` (date) - Hire date for leave calculation
    
    - Add columns to `attendance_records`:
      - `location_lat` (decimal) - GPS latitude
      - `location_lng` (decimal) - GPS longitude
      - `location_name` (text) - Location name/address
      - `is_late` (boolean) - Whether check-in was late
      - `is_early_leave` (boolean) - Whether check-out was early
      - `overtime_hours` (decimal) - Overtime hours

  3. Security
    - Enable RLS on all new tables
    - Users can view their own records
    - Admins can view and modify all records
*/

-- Create departments table
CREATE TABLE IF NOT EXISTS departments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE departments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view all departments"
  ON departments FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Admins can manage departments"
  ON departments FOR ALL
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND profiles.is_admin = true
    )
  );

-- Create work_patterns table
CREATE TABLE IF NOT EXISTS work_patterns (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  start_time time NOT NULL DEFAULT '09:00:00',
  end_time time NOT NULL DEFAULT '18:00:00',
  break_duration integer DEFAULT 60,
  is_flexible boolean DEFAULT false,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE work_patterns ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view all work patterns"
  ON work_patterns FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Admins can manage work patterns"
  ON work_patterns FOR ALL
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND profiles.is_admin = true
    )
  );

-- Create paid_leaves table
CREATE TABLE IF NOT EXISTS paid_leaves (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES profiles(id) NOT NULL,
  leave_date date NOT NULL,
  leave_type text NOT NULL DEFAULT 'annual',
  status text NOT NULL DEFAULT 'pending',
  reason text,
  approved_by uuid REFERENCES profiles(id),
  created_at timestamptz DEFAULT now()
);

ALTER TABLE paid_leaves ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own leave requests"
  ON paid_leaves FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create own leave requests"
  ON paid_leaves FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Admins can view all leave requests"
  ON paid_leaves FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND profiles.is_admin = true
    )
  );

CREATE POLICY "Admins can manage all leave requests"
  ON paid_leaves FOR ALL
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND profiles.is_admin = true
    )
  );

-- Create shifts table
CREATE TABLE IF NOT EXISTS shifts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES profiles(id) NOT NULL,
  date date NOT NULL,
  start_time time NOT NULL,
  end_time time NOT NULL,
  notes text,
  created_by uuid REFERENCES profiles(id),
  created_at timestamptz DEFAULT now()
);

ALTER TABLE shifts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own shifts"
  ON shifts FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Admins can manage all shifts"
  ON shifts FOR ALL
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND profiles.is_admin = true
    )
  );

-- Create notification_settings table
CREATE TABLE IF NOT EXISTS notification_settings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES profiles(id) UNIQUE NOT NULL,
  check_in_reminder boolean DEFAULT true,
  check_out_reminder boolean DEFAULT true,
  overtime_alert boolean DEFAULT true,
  shift_reminder boolean DEFAULT true,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE notification_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own notification settings"
  ON notification_settings FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own notification settings"
  ON notification_settings FOR ALL
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Add columns to profiles table
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'profiles' AND column_name = 'department_id'
  ) THEN
    ALTER TABLE profiles ADD COLUMN department_id uuid REFERENCES departments(id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'profiles' AND column_name = 'work_pattern_id'
  ) THEN
    ALTER TABLE profiles ADD COLUMN work_pattern_id uuid REFERENCES work_patterns(id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'profiles' AND column_name = 'annual_leave_balance'
  ) THEN
    ALTER TABLE profiles ADD COLUMN annual_leave_balance integer DEFAULT 20;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'profiles' AND column_name = 'hire_date'
  ) THEN
    ALTER TABLE profiles ADD COLUMN hire_date date DEFAULT CURRENT_DATE;
  END IF;
END $$;

-- Add columns to attendance_records table
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'attendance_records' AND column_name = 'location_lat'
  ) THEN
    ALTER TABLE attendance_records ADD COLUMN location_lat decimal(10, 8);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'attendance_records' AND column_name = 'location_lng'
  ) THEN
    ALTER TABLE attendance_records ADD COLUMN location_lng decimal(11, 8);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'attendance_records' AND column_name = 'location_name'
  ) THEN
    ALTER TABLE attendance_records ADD COLUMN location_name text;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'attendance_records' AND column_name = 'is_late'
  ) THEN
    ALTER TABLE attendance_records ADD COLUMN is_late boolean DEFAULT false;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'attendance_records' AND column_name = 'is_early_leave'
  ) THEN
    ALTER TABLE attendance_records ADD COLUMN is_early_leave boolean DEFAULT false;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'attendance_records' AND column_name = 'overtime_hours'
  ) THEN
    ALTER TABLE attendance_records ADD COLUMN overtime_hours decimal(5, 2) DEFAULT 0;
  END IF;
END $$;

-- Insert default work patterns
INSERT INTO work_patterns (name, start_time, end_time, break_duration, is_flexible)
VALUES
  ('標準勤務 (9:00-18:00)', '09:00:00', '18:00:00', 60, false),
  ('早番 (7:00-16:00)', '07:00:00', '16:00:00', 60, false),
  ('遅番 (11:00-20:00)', '11:00:00', '20:00:00', 60, false),
  ('フレックスタイム', '09:00:00', '18:00:00', 60, true)
ON CONFLICT DO NOTHING;

-- Insert default departments
INSERT INTO departments (name)
VALUES
  ('営業部'),
  ('開発部'),
  ('総務部'),
  ('人事部'),
  ('経理部')
ON CONFLICT DO NOTHING;