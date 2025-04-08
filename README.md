# ESD-Weebs Comic Reading Platform

A microservice-based web application for reading comics, with features including comic browsing, chapter management, purchasing of physical comic books to support comic artists and more.

## Architecture

This application follows a microservice architecture with multiple Flask-based Python services and a MySQL database. The services include:

- User management service
- Comic listing service
- Chapter viewing service
- Reading history service
- Waitlist service
- Comments and threads services
- Various composite services for complex operations

RabbitMQ has also been implemented to enable a First-Come-First-Serve queue for the waitlist, ensuring that people who waitlist a product first will automically have that item added to their cart first when the product is in stock.

## Docker Setup

This project has been dockerized for easy deployment. The setup includes:

1. A MySQL database container for data storage
2. An application container running all the microservices
3. A rabbitMQ container (hosted on port 15673 and 5673 for the GUI manager and service respectively) to allow rabbitMQ

### Requirements

- Docker
- Docker Compose

### Running the Application

1. Clone the repository:
   ```
   git clone https://github.com/jairelltan/ESD-Weebs
   cd ESD-Weebs
   ```

2. Build and start the containers:
   ```
   docker-compose up --build

   *The docker will start building up the image and running the various microservices. This might take a while. 

   Once everything a ready, you should see "user 'guest' authenticated and granted access to vhost"*

   ```

3. To reset the database:
   ```
   docker-compose down -v
   docker-compose up -d
   ```

4. Access the services:
   - User API: http://localhost:5000
   - Comic API: http://localhost:5001
   - Various other services run on ports 5002-5025


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
- **Port conflicts:** If you see connection refused errors, another service might be using the same port. Check running services with `netstat -ano | findstr :<port-number>`
- **CORS issues:** If browser console shows CORS errors, verify the proper CORS headers are set in the Flask services
- **Missing Python packages:** Some services may require additional packages like 'stripe'. You can install them manually:
  ```
  docker exec -it esd-weebs-app pip install <package-name>
  ```
- **WSL conflicts:** If you're using WSL, be aware it might use the same ports. Consider using 127.0.0.1 instead of localhost for direct connections
- **Important!!!!** When building the container, if you receive the error `exer /use/local/bin/docker-entrypoint.sh: no such file or directory`,
one possible fix is to change your End Of Life Sequence from CRLF to LF. If you are using Visual Code, this can be found at the bottom right of the UI right beside the 'Language Mode'. 

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

**Documentation Link** https://docs.google.com/document/d/1Lbc3l33YEX3n_IBJ10AZ_d1Bu-ziOYd6u4M-HrexDVA/edit?tab=t.0#heading=h.qxh2timmpdao 
## Atomic Services

### 1. User Service (Port: 5000)
**Type**: Atomic
**Database**: `user_db`
**Database Attributes**: 
   user_id | int (Primary Key)		
	user_name | varchar(100)		
	phone_number | int			
	email | varchar(100)		
	address | varchar(255)		
	points | int				
	subscriber_status | enum('MONTHLY', 'QUARTERLY', 'YEARLY', 'NIL')
**Description**: Manages user information and authentication

Endpoints:
- GET `/user` - Get all users' information in the user DB
- GET `/user/{user_id}` - Get specific user based on user_id
- PUT `/user/{user_id}` - Update user details (points or/and status)
- PUT `/user/{user_id}/points` - Update points

### 2. Comic Service (Port: 5001)
**Type**: Atomic
**Database**: `comic_db`
**Database Attributes**
	comic_id | int (Primary Key)
	comic_name | varchar(255)
	author | varchar(255)
	genre | varchar(255)	
	status | enum('ongoing', 'completed', 'hiatus')		
	description | text
	comic_art | blob
**Description**: Manages comic metadata

Endpoints:
- GET `/comic` - Get all comics
- GET `/comic/{comic_id}` - Get specific comic
- POST `/comic` - Create comic
- PUT `/comic/{comic_id}` - Update comic
- POST `/comic/{comic_id}/image` - Upload cover
- GET `/comic/{comic_id}/image` - Get cover

### 3. Waitlist Service (Port: 5003)
**Type**: Atomic
**Database**: `waitlist_db`
**Database Attributes**
id Primary | int			
user_id | int				
username | varchar(255)		
comic_id | int				
comic_name | varchar(255)		
comic_volume | varchar(255)		
price_per_item | decimal(10,2)		
timestamp | datetime		 	
**Description**: Manages waitlist entries

Endpoints:
- GET `/waitlist` - Get all entries
- POST `/waitlist` - Add entry
- DELETE `/waitlistdelete/{id}` - Delete entry

### 4. Premium Plan Service (Port: 5004)
**Type**: Atomic
**Database**: `premium_plan_db`
**Database Attributes**
plan_id | int			
plan_name | varchar(255)		
description | text	
price | decimal(10,2)		
duration | enum('MONTHLY', 'QUARTERLY', 'YEARLY')	
features | text
**Description**: Manages subscription plans

Endpoints:
- GET `/premium_plan` - Get all plan details
- GET `/premium_plan/{plan_id}` - Get plan details of a specific plan

### 5. Chapter Service (Port: 5005)
**Type**: Atomic
**Database** `chapter_db`
**Database Attributes**
   chapter_id | int				
	comic_id | int				
	chapter_number | int			
	title	| varchar(255)	
	release_date | date		
**Description** Manages chapter information

Endpoints:
- GET `/api/comics/{comic_id}/chapters` - Get comic chapters
- GET `/api/chapters/{chapter_id}` - Get chapter
- GET `/api/chapters/{chapter_id}/navigation` - Fetch the navigation details for a specific chapter
- POST `/api/chapters` - Create chapter

### 6. Receipt Service (Port: 5006)
**Type**: Atomic
**Database**: `receipt_db`
**Database Attributes**
   receipt_id | INT (Primary Key)
   user_id | INT 
   transaction_id | VARCHAR(255)
   card_id | INT 
   current_points | INT 
   payment_method | ENUM('CREDIT_CARD', 'DEBIT_CARD')
   receipt_date | TIMESTAMP
   subscriber_status | VARCHAR(50)
   billing_address | TEXT
   amount | DECIMAL(10,2)
**Description**: Manages transaction receipts

Endpoints:
- POST `/receipt` - Create receipt
- GET `/receipt/user/<int:user_id>` - Get all receipts for a user
- GET `/receipt/<int:receipt_id>` - Get specific receipt by receipt_id
- Get `/receipt/transaction/<transaction_id>/` - Get receipt by transaction_id

### 7. Notification Service (Port: 5007)
**Type**: Atomic
**Database**: `notification_db`
**Database Attributes**:
   notification_id | INT,
   user_id | INT,
   description | VARCHAR(255),
   time TIMESTAMP | DEFAULT CURRENT_TIMESTAMP  
**Description**: Manages user notifications

Endpoints:
- POST `/notification` - Create notification
- GET `/notification/user/{user_id}` - Get user notifications
- POST `/notification/bookpayment` - Create Notification (book payment based)
- GET `/notification/<int:notification_id>` - Get notification based on notification id

### 8. Cart Service (Port: 5008)
**Type**: Atomic
**Database**: `cart_db`
**Database Attributes**
    id | INT 
    user_id | INT
    username | VARCHAR(255)
    comic_id | INT
    comic_name | VARCHAR(255)
    comic_volume | VARCHAR(255)
    price_per_item | DECIMAL(10,2)
    quantity | INT
**Description**: Manages cart for users

Endpoints:
- GET `/cart/{user_id}` - Get user's cart
- GET `/cart/specificentry/{id}` – Get specific cart item via cart id
POST `/cart` – Add or update quantity of item item to cart
- DELETE `/cart/{id}` - Delete cart item
- DELETE `/cart/user/{user_id}` – Delete all cart entries for a specific user

### 9. Page Service (Port: 5013)
**Type**: Atomic
**Database**: `page_db`
**Database Attributes**
    page_id | INT 
    comic_id | INT
    chapter_id | INT
    page_number | INT
    page_image | LONGBLOB
    UNIQUE KEY unique_page | (comic_id, chapter_id, page_number)
**Description**: Manages comic pages

Endpoints:
- GET `/api/pages/chapter/{chapter_id}` - Get chapter pages
- GET `/api/pages/chapter/int:chapter_id/page/int:page_number`- Get a specific page image
- POST `/api/pages/upload` - Upload page

### 10. History Service (Port: 5014)
**Type**: Atomic
**Database**: `history_db`
**Database Attributes**
    user_id | INT
    chapter_id | INT
    created_at | TIMESTAMP
    PRIMARY KEY | (user_id, chapter_id)
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

## Composite Services

### 1. Add to Cart Service (Port: 5009)
**Type**: Composite
**Description**: Coordinates adding items to cart

### 2. Update Waitlist Service (Port: 5010)
**Type**: Composite
**Description**: Updates waitlist entries

### 3. Subscribe Service (Port: 5018)
**Type**: Composite
**Description**: Manages premium subscriptions with Stripe integration
**Required packages**: stripe

### 4. Process Payment Service (Port: 5021)
**Type**: Composite
**Description**: Processes payments through Stripe API
**Note**: Was previously on port 5099

### 5. Book Payment Service (Port: 5022)
**Type**: Composite
**Description**: Handles book purchase payments 
**Note**: Was previously on port 5100

## Access Front-end

Need to redo this

## Dependency Installation

The following Python packages are required:
- Flask==2.0.1
- flask-cors==3.0.10
- mysql-connector-python==8.0.28
- requests==2.28.1
- Werkzeug==2.0.3
- python-dotenv==0.20.0
- stripe==12.0.0 (for payment processing)
- pika 