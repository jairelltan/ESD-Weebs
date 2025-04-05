# ESD-Weebs Comic Reading Platform

A microservice-based web application for reading comics, with features including user management, comic browsing, chapter management, and more.

## Architecture

This application follows a microservice architecture with multiple Flask-based Python services and a MySQL database. The services include:

- User management service
- Comic listing service
- Chapter viewing service
- Reading history service
- Waitlist service
- Comments and threads services
- Various composite services for complex operations

## Docker Setup

This project has been dockerized for easy deployment. The setup includes:

1. A MySQL database container for data storage
2. An application container running all the microservices

### Requirements

- Docker
- Docker Compose

### Running the Application

1. Clone the repository:
   ```
   git clone <repository-url>
   cd ESD-Weebs
   ```

2. Build and start the containers:
   ```
   docker-compose up -d
   ```

3. Access the services:
   - User API: http://localhost:5000
   - Various other services run on ports 5001-5025

### Database Initialization

The database is automatically initialized on startup with sample data for:
- Comics (One Piece, Attack on Titan, Demon Slayer, etc.)
- Chapters
- Users
- Reading history
- Premium plans
- And more

## Development

### Adding New Services

To add a new service:

1. Create a new Python file with your Flask service
2. Add any required database schema to the combined.txt file
3. Rebuild the Docker images: `docker-compose up -d --build`

### Connecting to the Database

From your application code, use the database configuration:

```python
db_config = {
    'host': 'db',  # Use 'db' as the hostname inside Docker containers
    'user': 'root',
    'password': 'root_password',
    'database': '[your_database_name]'
}
```

## Troubleshooting

- **Services not starting:** Check the logs with `docker-compose logs`
- **Database connection issues:** Ensure the database is initialized properly by checking `docker-compose logs db`

## Adding New Comics

To add new comics to the system:

1. **Prepare your comic files**:
   - Place cover images in the `./images` directory named after the comic (e.g., `comic_name.jpg`)
   - Create comic directories in `./Chapters/<Comic Name>/<Chapter Name>`
   - Make sure chapter names contain chapter numbers that can be parsed (e.g., "Chapter 1", "Ch.0001", etc.)
   - Add page images to each chapter directory, named numerically (e.g., "01.jpg", "02.jpg")

2. **Run the following commands** to copy your comics to the Docker container and update the database:
   ```
   # Copy assets to the Docker container
   .\copy_assets_to_docker.ps1
   
   # Run the upload script to process the assets
   docker exec -it esd-weebs-app python upload_chapter_pages.py
   ```

3. **Restart the container** if needed:
   ```
   docker-compose restart app
   ```

The upload script will automatically:
- Process all cover images and associate them with comics in the database
- Process all chapter pages and add them to the database
- Skip any files that are already in the database

Note: On first container startup, the system will automatically import any comics found in the mounted volumes.

# ESD-Weebs Microservices Architecture

## Overview
This system consists of 25 microservices:
- 13 Atomic Services
- 11 Composite Services
- 1 External Integration

## Atomic Services

### 1. User Service (Port: 5000)
**Type**: Atomic
**Database**: `user_db`
**Description**: Manages user information and authentication

Endpoints:
- GET `/user` - Get all users
- GET `/user/{user_id}` - Get specific user
- PUT `/user/{user_id}` - Update user details
- PUT `/user/{user_id}/points` - Update points
- PUT `/user/{user_id}/status` - Update subscription status

### 2. Comic Service (Port: 5001)
**Type**: Atomic
**Database**: `comic_db`
**Description**: Manages comic metadata

Endpoints:
- GET `/comic` - Get all comics
- GET `/comic/{comic_id}` - Get specific comic
- POST `/comic` - Create comic
- PUT `/comic/{comic_id}` - Update comic
- DELETE `/comic/{comic_id}` - Delete comic
- POST `/comic/{comic_id}/image` - Upload cover
- GET `/comic/{comic_id}/image` - Get cover

### 3. Waitlist Service (Port: 5003)
**Type**: Atomic
**Database**: `waitlist_db`
**Description**: Manages waitlist entries

Endpoints:
- GET `/waitlist` - Get all entries
- POST `/waitlist` - Add entry
- DELETE `/waitlistdelete/{id}` - Delete entry

### 4. Premium Plan Service (Port: 5004)
**Type**: Atomic
**Database**: `premium_plan_db`
**Description**: Manages subscription plans

Endpoints:
- GET `/premium_plan/{plan_id}` - Get plan details

### 5. Chapter Service (Port: 5005)
**Type**: Atomic
**Database**: `chapter_db`
**Description**: Manages chapter information

Endpoints:
- GET `/api/comics/{comic_id}/chapters` - Get comic chapters
- GET `/api/chapters/{chapter_id}` - Get chapter
- POST `/api/chapters` - Create chapter
- DELETE `/api/chapters/{chapter_id}` - Delete chapter

### 6. Receipt Service (Port: 5006)
**Type**: Atomic
**Database**: `receipt_db`
**Description**: Manages transaction receipts

Endpoints:
- POST `/receipt` - Create receipt

### 7. Notification Service (Port: 5007)
**Type**: Atomic
**Database**: `notification_db`
**Description**: Manages user notifications

Endpoints:
- POST `/notification` - Create notification
- GET `/notification/{user_id}` - Get user notifications

### 8. Cart Service (Port: 5008)
**Type**: Atomic
**Database**: `cart_db`
**Description**: Manages shopping cart

Endpoints:
- GET `/cart/{user_id}` - Get user's cart
- POST `/cart` - Add/update cart item
- DELETE `/cart/{id}` - Delete cart item

### 9. Page Service (Port: 5013)
**Type**: Atomic
**Database**: `page_db`
**Description**: Manages comic pages

Endpoints:
- GET `/api/pages/chapter/{chapter_id}` - Get chapter pages
- POST `/api/pages/upload` - Upload page
- DELETE `/api/pages/chapter/{chapter_id}/page/{page_number}` - Delete page

### 10. History Service (Port: 5014)
**Type**: Atomic
**Database**: `history_db`
**Description**: Manages reading history

Endpoints:
- GET `/history/{user_id}` - Get user history
- POST `/history` - Add history entry
- DELETE `/history/{id}` - Delete entry

### 11. Thread Service (Port: 5015)
**Type**: Atomic
**Database**: `thread_db`
**Description**: Manages discussion threads

Endpoints:
- GET `/threads` - Get all threads
- POST `/threads` - Create thread
- GET `/threads/{thread_id}`