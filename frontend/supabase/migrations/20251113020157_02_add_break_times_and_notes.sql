/*
  # Add break times and notes to attendance records

  1. Changes
    - Add `break_start_time` column to store break start timestamp
    - Add `break_end_time` column to store break end timestamp
    - Add `break_duration_minutes` column to calculate total break time
    - Add `notes` column for additional comments or edits
    - Add `last_modified_at` column to track when records were edited
    - Add `last_modified_by` column to track who edited the record
  
  2. Security
    - No RLS changes needed as existing policies cover these new columns
*/

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'attendance_records' AND column_name = 'break_start_time'
  ) THEN
    ALTER TABLE attendance_records ADD COLUMN break_start_time timestamptz;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'attendance_records' AND column_name = 'break_end_time'
  ) THEN
    ALTER TABLE attendance_records ADD COLUMN break_end_time timestamptz;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'attendance_records' AND column_name = 'break_duration_minutes'
  ) THEN
    ALTER TABLE attendance_records ADD COLUMN break_duration_minutes integer DEFAULT 0;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'attendance_records' AND column_name = 'notes'
  ) THEN
    ALTER TABLE attendance_records ADD COLUMN notes text DEFAULT '';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'attendance_records' AND column_name = 'last_modified_at'
  ) THEN
    ALTER TABLE attendance_records ADD COLUMN last_modified_at timestamptz DEFAULT now();
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'attendance_records' AND column_name = 'last_modified_by'
  ) THEN
    ALTER TABLE attendance_records ADD COLUMN last_modified_by uuid REFERENCES auth.users(id);
  END IF;
END $$;