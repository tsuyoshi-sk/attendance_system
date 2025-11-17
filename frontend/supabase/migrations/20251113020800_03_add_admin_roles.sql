/*
  # Add admin role management

  1. Changes
    - Add `is_admin` column to profiles table to designate admin users
    - Add default value of false for regular users
    - Add index for faster admin queries
  
  2. Security
    - Existing RLS policies continue to work
    - Admin status can be checked in application logic
    - Only admins should be able to view all employee data
*/

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'profiles' AND column_name = 'is_admin'
  ) THEN
    ALTER TABLE profiles ADD COLUMN is_admin boolean DEFAULT false;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_profiles_is_admin ON profiles(is_admin) WHERE is_admin = true;