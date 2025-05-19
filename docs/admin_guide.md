# Admin Guide

## Creating an Admin Account

To create an admin account, follow these steps:

1. **Register a user normally**:
   - Go to the registration page and create a new user account
   - Fill in the required fields (username, email, password)
   - Submit the form

2. **Update the user's role in the database**:
   - Access the PostgreSQL database using pgAdmin or the command line
   - Connect to the `agromap_db` database
   - Run the following SQL query to update the user's role:

   ```sql
   UPDATE "user" SET role = 'admin' WHERE username = 'your_username';
   ```

   Replace `'your_username'` with the username of the account you want to make an admin.

3. **Verify the change**:
   - Log in with the user account
   - You should now have access to admin-only features

## Admin Capabilities

As an admin, you have the following capabilities:

- Access to the admin dashboard
- Ability to view all users' crop reports
- Ability to edit and delete any crop report
- Access to system statistics and analytics

## Security Considerations

- Admin accounts have significant power in the system
- Only grant admin privileges to trusted users
- Regularly audit admin actions
- Consider implementing additional security measures for admin accounts