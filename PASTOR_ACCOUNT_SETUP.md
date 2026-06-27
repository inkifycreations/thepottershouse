# Pastor Account Setup Guide

This guide explains how to create pastor accounts from the Django backend.

## Overview

- **Pastor accounts** have access to:
  - Upload videos
  - Manage live streams
  - Edit/delete their own videos

- **Regular users** (referred by pastors):
  - Can only view videos and live streams
  - Cannot upload or manage streams

## Creating a Pastor Account from Backend

### Step 1: Create the Pastor Record

First, add a Pastor record through Django Admin:

1. Go to: `http://localhost:8000/admin/`
2. Navigate to "Pastors"
3. Click "Add Pastor"
4. Fill in:
   - **Name**: Pastor's name
   - **State**: Select the state they serve in
   - **Referral Code**: Unique code (e.g., `JOHN_WB` for John from West Bengal)
5. Save the pastor record
6. Note the **Pastor ID** (visible in the list or URL)

### Step 2: Create the Pastor User Account

Run this command in your terminal:

```bash
python manage.py create_pastor_user <username> <email> <pastor_id>
```

**Example:**
```bash
python manage.py create_pastor_user john_pastor john@pottershouseministry.com 1
```

The command will prompt you to enter a password securely.

**With password option (less secure):**
```bash
python manage.py create_pastor_user john_pastor john@pottershouseministry.com 1 --password MySecurePassword123
```

### Step 3: Verify the Account

1. Login with the pastor account credentials
2. You should see:
   - Upload Video button becomes available
   - Live Stream page is accessible
   - Can manage your own videos

## Available Management Commands

### create_pastor_user
Create a new pastor user account with upload and streaming permissions.

**Usage:**
```
python manage.py create_pastor_user <username> <email> <pastor_id> [--password PASSWORD]
```

**Arguments:**
- `username`: Username for login
- `email`: Email address
- `pastor_id`: ID of the pastor from the Pastor model
- `--password`: (Optional) Password for the account. If not provided, you'll be prompted securely.

**Examples:**
```bash
# With secure password prompt
python manage.py create_pastor_user alice alice@church.com 5

# With password option
python manage.py create_pastor_user bob bob@church.com 3 --password "SecurePass123!"
```

## Admin Interface

### Managing Pastor Users

Visit the Django Admin to manage pastor accounts:

1. Go to: `http://localhost:8000/admin/missions/customuser/`
2. Click on a user to edit
3. You'll see:
   - **is_pastor**: Checkbox (should be checked for pastor accounts)
   - **pastor_profile**: Select the associated pastor record
   - **referred_by**: (Leave empty for pastors)

### Managing Pastors

Visit: `http://localhost:8000/admin/missions/pastor/`

- View all pastors
- See how many users are referred by each pastor
- Edit referral codes if needed

## Features Summary

### For Pastor Users

**Upload Videos:**
- Access the "Upload Video" page
- Videos are automatically assigned to their pastor profile and state
- Can group videos by topic or event

**Manage Live Streams:**
- Access the "Live Stream" page
- Start/stop streams for their assigned state and pastor profile
- View active streams in real-time

**Edit/Delete Videos:**
- Can edit metadata of videos they uploaded
- Can delete their own videos
- Videos auto-archive to the gallery

### Access Control

The following views are restricted to pastors only:
- `/upload-video/` - Video upload
- `/live-stream/` - Live streaming controls
- Video edit/delete pages - Only for the uploader or staff

## Troubleshooting

**Error: "Pastor with ID X does not exist"**
- The pastor ID doesn't match any Pastor record
- Go to Admin > Pastors and verify the correct ID

**Error: "User with username X already exists"**
- The username is already taken
- Choose a different username

**Password prompt not appearing?**
- Make sure you're running the command in an interactive terminal
- Use `--password` flag to provide password directly (less secure)

## Security Notes

1. **Always use secure passwords** for pastor accounts
2. **Use the password prompt** instead of `--password` flag when creating accounts
3. **Manage access** through Django Admin permissions
4. **Regular backups** of your database recommended

---

For more information, see the Django documentation on custom commands.
