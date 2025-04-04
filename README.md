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
- GET `/threads/{thread_id}` - Get thread
- PUT `/threads/{thread_id}` - Update thread
- DELETE `/threads/{thread_id}` - Delete thread

### 12. Comment Service (Port: 5016)
**Type**: Atomic
**Database**: `comment_db`
**Description**: Manages thread comments

Endpoints:
- GET `/comments/{thread_id}` - Get comments
- POST `/comments` - Create comment
- PUT `/comments/{comment_id}` - Update comment
- DELETE `/comments/{comment_id}` - Delete comment

### 13. Stripe API Service (Port: 5017)
**Type**: Atomic
**Description**: Handles Stripe payment integration

Endpoints:
- POST `/create-payment-intent` - Create payment intent

## Composite Services

### 1. Subscribe Service (Port: 5018)
**Type**: Composite
**Dependencies**: User, Premium Plan, Payment, Receipt, Notification
**Description**: Manages subscription process

Endpoints:
- POST `/subscribe` - Handle subscription

### 2. Add to Waitlist Service (Port: 5002)
**Type**: Composite
**Dependencies**: User, Waitlist, RabbitMQ
**Description**: Manages waitlist additions

Endpoints:
- GET `/addtowishlist/{user_id}/{product_id}` - Add to waitlist

### 3. Add to Cart Service (Port: 5009)
**Type**: Composite
**Dependencies**: User, Cart
**Description**: Manages cart additions

Endpoints:
- GET `/addtocart/{user_id}/{product_id}` - Add to cart

### 4. Update Waitlist Service
**Type**: Composite
**Dependencies**: Waitlist, Notification
**Description**: Updates waitlist status

Endpoints:
- POST `/updatewaitlist` - Update waitlist

### 5. Process Payment Service
**Type**: Composite
**Dependencies**: Payment, Cart
**Description**: Processes book purchases

Endpoints:
- POST `/process_payment` - Process payment

### 6. Book Payment Service
**Type**: Composite
**Dependencies**: Payment, Cart, Receipt
**Description**: Manages book payments

Endpoints:
- POST `/book_payment` - Process book payment

### 7. Read Comic Service
**Type**: Composite
**Dependencies**: Comic, Chapter, Page
**Description**: Manages comic reading

Endpoints:
- GET `/read/{comic_id}/{chapter_id}` - Get reading content

### 8. View Threads Service
**Type**: Composite
**Dependencies**: Thread, Comment
**Description**: Manages thread viewing

Endpoints:
- GET `/view_threads` - Get all threads
- GET `/view_threads/{thread_id}` - Get specific thread

### 9. Verify History Service
**Type**: Composite
**Dependencies**: History, User
**Description**: Verifies reading history

Endpoints:
- GET `/verify_history/{user_id}` - Get verified history
- POST `/verify_history` - Add verified entry

### 10. Delete Cart Entries Service
**Type**: Composite
**Dependencies**: Cart
**Description**: Manages cart deletion

Endpoints:
- DELETE `/deletecartentries/{cart_id}` - Delete entries

### 11. Upload Chapter Pages Service
**Type**: Composite
**Dependencies**: Chapter, Page
**Description**: Manages page uploads

Endpoints:
- POST `/upload_chapter_pages` - Upload pages

## External Integration

### 1. RabbitMQ Consumer
**Type**: Message Queue Consumer
**Description**: Processes waitlist messages
**Dependencies**: RabbitMQ

## Running the Services

```bash
# Start atomic services
python user.py             # Port 5000
python comic.py           # Port 5001
python waitlist.py        # Port 5003
python premium_plan.py     # Port 5004
python chapter.py         # Port 5005
python receipt.py         # Port 5006
python notification.py     # Port 5007
python cart.py            # Port 5008
python page.py            # Port 5013
python history.py         # Port 5014
python thread.py          # Port 5015
python comment.py         # Port 5016
python payment/stripeapi.py # Port 5017

# Start composite services
python subscribe.py        # Port 5018
python addtowaitlist.py   # Port 5002
python addtocart.py       # Port 5009
python updatewaitlist.py
python processpayment.py
python bookpayment.py
python read_comic.py
python view_threads.py
python verify_history.py
python deletecartentries.py
python upload_chapter_pages.py

# Start external integration
python rabbitmq_consumer.py
```

## Architecture Notes

1. Each atomic service:
   - Has its own database
   - Is independently deployable
   - Handles one core business capability

2. Composite services:
   - Orchestrate multiple atomic services
   - Don't have their own databases
   - Handle complex business processes

3. External integration:
   - RabbitMQ for message queuing
   - Stripe for payment processing 