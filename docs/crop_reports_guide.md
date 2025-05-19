# Crop Reports Guide

## Overview

The crop reports feature allows users to submit, edit, and delete reports about crops in specific locations. Each report includes information about the crop type, location (latitude and longitude), and area size.

## Submitting a Crop Report

To submit a new crop report:

1. **Log in to your account**
2. **Navigate to the dashboard**
3. **Fill out the crop report form**:
   - Select the crop type
   - Specify the location (latitude and longitude)
   - Enter the area size in hectares
4. **Submit the form**

## Viewing Your Crop Reports

To view your submitted crop reports:

1. **Log in to your account**
2. **Navigate to the dashboard**
3. **Click on "My Reports"**

This will display a list of all the crop reports you have submitted, including details such as crop type, location, area size, and submission date.

## Editing a Crop Report

To edit an existing crop report:

1. **Log in to your account**
2. **Navigate to "My Reports"**
3. **Find the report you want to edit**
4. **Click the "Edit" button**
5. **Update the information as needed**
6. **Save your changes**

Note: You can only edit reports that you have submitted, unless you have admin privileges.

## Deleting a Crop Report

To delete a crop report:

1. **Log in to your account**
2. **Navigate to "My Reports"**
3. **Find the report you want to delete**
4. **Click the "Delete" button**
5. **Confirm the deletion**

Note: You can only delete reports that you have submitted, unless you have admin privileges.

## API Endpoints

For developers, the following API endpoints are available:

- `POST /submit`: Submit a new crop report
- `GET /reports`: Get all crop reports (public)
- `GET /my-reports`: Get all crop reports submitted by the current user
- `PUT /reports/<report_id>`: Update a specific crop report
- `DELETE /reports/<report_id>`: Delete a specific crop report

Each endpoint requires authentication except for the public reports endpoint.

## Data Format

Crop reports include the following data:

- `crop_type`: The type of crop (e.g., wheat, cotton, rice)
- `latitude`: The latitude coordinate of the crop location
- `longitude`: The longitude coordinate of the crop location
- `area_size`: The size of the crop area in hectares
- `user_id`: The ID of the user who submitted the report (automatically added)
- `created_at`: The date and time when the report was submitted
- `updated_at`: The date and time when the report was last updated