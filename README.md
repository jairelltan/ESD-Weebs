# Atomic Microservice Architecture

## Overview

This project uses a fully atomic microservice architecture. "Atomic" means each service is completely independent and does not make any calls to other services.

## Services

### User Service (user.py) - Atomic

- **Database**: `user_db`
- **Port**: 5000
- **Responsibility**: Manages user data, points, and subscription status
- **Endpoints**:
  - `GET /user` - Get all users
  - `GET /user/<user_id>` - Get specific user
  - `PUT /user/<user_id>` - Update user data
  - `PUT /user/<user_id>/points` - Update user points (can add/deduct/set points)
  - `PUT /user/<user_id>/status` - Update user subscriber status (MONTHLY/QUARTERLY/YEARLY/NIL)

### Comic Service (comic.py) - Atomic

- **Database**: `comic_db`
- **Port**: 5001
- **Responsibility**: Manages comic metadata
- **Endpoints**:
  - `GET /api/health` - Health check
  - `GET /comic` - Get all comics
  - `GET /comic/<comic_id>` - Get specific comic
  - `POST /comic` - Create new comic
  - `PUT /comic/<comic_id>` - Update comic
  - `DELETE /comic/<comic_id>` - Delete comic
  - `POST /comic/<comic_id>/image` - Upload comic cover image
  - `GET /comic/<comic_id>/image` - Get comic cover image

### Add to Waitlist Service (addtowaitlist.py) - Composite

- **Database**: None
- **Port**: 5002
- **Responsibility**: Manages adding items to the waitlist by integrating user and inventory services, using RabbitMQ for message queuing
- **Endpoints**:
  - `GET /addtowishlist/<user_id>/<product_id>` - Add item to waitlist queue (First-Come, First-Serve)
- **Integration**:
  - Uses RabbitMQ for message queuing (queue: 'fcfs_queue')
  - Integrates with User Service (port 5000) and Inventory Service (Outsystems)
  - Messages are processed by a separate consumer service

### Waitlist Service (waitlist.py) - Atomic

- **Database**: `waitlist_db`
- **Port**: 5003
- **Responsibility**: Manages waitlist entries and their processing
- **Endpoints**:
  - `GET /waitlist` - Get all waitlist entries
  - `POST /waitlist` - Add new waitlist entry
  - `DELETE /waitlistdelete/<id>` - Delete a waitlist entry

### Chapter Service (chapter.py) - Atomic

- **Database**: `chapter_db`
- **Port**: 5005
- **Responsibility**: Manages chapter metadata
- **Endpoints**:
  - `GET /api/health` - Health check
  - `GET /api/comics/<comic_id>/chapters` - Get all chapters for a comic
  - `GET /api/chapters/<chapter_id>` - Get specific chapter
  - `GET /api/chapters/<chapter_id>/navigation` - Get navigation info (prev/next chapter)
  - `POST /api/chapters` - Create new chapter
  - `DELETE /api/chapters/<chapter_id>` - Delete chapter

### Cart Service (cart.py) - Atomic

- **Database**: `cart_db`
- **Port**: 5008
- **Responsibility**: Manages shopping cart entries and quantities
- **Endpoints**:
  - `GET /cart/<user_id>` - Get all cart items for a user
  - `GET /cart/<id>/<comic_id>` - Get specific cart item
  - `POST /cart` - Add or update cart entry (increases quantity if item exists)
  - `DELETE /cart/<id>` - Delete a cart entry

### Chapter Service (addtocart.py) - Composite

- **Database**: None
- **Port**: 5009
- **Responsibility**: Manages adding items to the cart by integrating user, inventory, and cart services.
- **Endpoints**:
- `GET /addtocart/<int:user_id>/<int:product_id>` - Fetch user and product data, add item to the cart, and reduce inventory stock.

### Timer Service (timer.py) - Composite

- **Database**: None
- **Port**: 5010
- **Responsibility**: Manages waitlist processing and cart integration
- **Endpoints**:
  - `POST /start_task` - Start processing waitlist entries and adding items to cart
- **Integration**:
  - Integrates with Waitlist Service (port 5003)
  - Integrates with Cart Service (port 5008)
  - Integrates with Inventory Service (Outsystems)
  - Integrates with Notification Service (port 5007)
  - Processes waitlist entries in First-Come, First-Serve order
  - Sends notifications when items are added to cart

### Page Service (page.py) - Atomic

- **Database**: `page_db`
- **Port**: 5013
- **Responsibility**: Manages page images
- **Endpoints**:
  - `GET /api/health` - Health check
  - `GET /api/pages/chapter/<chapter_id>` - Get all pages for a chapter
  - `GET /api/pages/chapter/<chapter_id>/page/<page_number>` - Get specific page image
  - `POST /api/pages/upload` - Upload a page
  - `DELETE /api/pages/chapter/<chapter_id>/delete` - Delete all pages for a chapter
  - `DELETE /api/pages/chapter/<chapter_id>/page/<page_number>` - Delete specific page

## Database Schema

Each service has its own dedicated database:

1. **comic_db**: Contains comic metadata
2. **chapter_db**: Contains chapter metadata 
3. **page_db**: Contains page images and metadata

## Tools

- **upload_chapter_pages.py**: A utility script that works directly with the databases to upload chapter pages. This tool maintains the atomic architecture by connecting directly to both databases rather than using service APIs. 

### Premium Plan Service (premium_plan.py)

- **Database**: `premium_plan`
- **Port**: 5004
- **Responsibility**: Manages premium subscription plans 