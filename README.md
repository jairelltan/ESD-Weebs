# Atomic Microservice Architecture

## Overview

This project uses a fully atomic microservice architecture. "Atomic" means each service is completely independent and does not make any calls to other services.

## Services

### Comic Service (comic.py)

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

### Chapter Service (chapter.py)

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

### Page Service (page.py)

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

## Client-Side Service Composition

In this atomic architecture, the frontend or API gateway is responsible for service composition. For example:

1. To display a comic chapter, the client would:
   - Call Comic Service to get comic details
   - Call Chapter Service to get chapter details
   - Call Page Service to get page images

## Benefits of Atomic Architecture

1. **Complete Independence**: Each service functions independently
2. **Improved Resilience**: Failure in one service doesn't cascade to others
3. **Simplified Development**: Each service has a clear, focused responsibility
4. **Easy Scaling**: Services can be scaled individually based on demand
5. **Independent Deployment**: Services can be updated separately without affecting others

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