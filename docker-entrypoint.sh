#!/bin/bash
set -e

echo "Starting docker-entrypoint.sh"

# Ensure required Python packages are installed
echo "Checking required Python packages..."
pip list | grep -q "stripe" || {
    echo "Installing missing stripe package..."
    pip install stripe
}

# Wait for the database to be ready
echo "Waiting for MySQL to be ready..."
max_retries=30
counter=0
while ! mysqladmin ping -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" --silent 2>/dev/null; do
    counter=$((counter+1))
    if [ $counter -gt $max_retries ]; then
        echo "Error: MySQL did not become ready in time"
        exit 1
    fi
    echo "MySQL not ready yet... waiting (attempt $counter/$max_retries)"
    sleep 5
done
echo "MySQL is ready!"

# Check if we can connect to each database
echo "Verifying database connections..."
for db in cart_db comic_db chapter_db comments_db history_db notification_db page_db premium_plan_db receipt_db thread_db user_db waitlist_db; do
    echo "Checking connection to $db..."
    if ! mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "use $db" 2>/dev/null; then
        echo "Database $db not found, initializing databases..."
        mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" < /docker-entrypoint-initdb.d/init.sql
        echo "Databases initialized!"
        break
    fi
done
echo "Database connection verified!"

# Update database connection configs in all Python files
echo "Updating service configurations..."
find . -name "*.py" -type f -exec sed -i "s/'host': 'localhost'/'host': '$MYSQL_HOST'/g" {} \;
find . -name "*.py" -type f -exec sed -i "s/'user': 'root'/'user': '$MYSQL_USER'/g" {} \;
find . -name "*.py" -type f -exec sed -i "s/'password': ''/'password': '$MYSQL_PASSWORD'/g" {} \;

# Update service URLs to use Docker service names
find . -name "*.py" -type f -exec sed -i "s/http:\/\/localhost/http:\/\/app/g" {} \;

# Fix CORS issues in all Python Flask applications
echo "Fixing CORS configuration in all Flask applications..."
find . -name "*.py" -type f -exec grep -l "app = Flask" {} \; | while read flask_app; do
    echo "Adding proper CORS configuration to $flask_app"
    # Add proper CORS configuration
    sed -i '/app = Flask/a \
# Configure CORS to allow requests from any origin\
CORS(app, resources={r"/*": {"origins": "*", "allow_headers": ["Content-Type", "Authorization"], "expose_headers": ["Content-Type", "X-Total-Count"]}})\
' "$flask_app"
    
    # Also make sure CORS is imported
    if ! grep -q "from flask_cors import CORS" "$flask_app"; then
        sed -i '1a from flask_cors import CORS' "$flask_app"
    fi
done
echo "CORS configurations updated!"

# Special fix for cart.py which seems to have CORS issues
echo "Applying special CORS fix for cart.py..."
if [ -f "./cart.py" ]; then
    # Remove any existing CORS configuration to avoid conflicts
    sed -i '/CORS(/d' cart.py
    sed -i '/@app.after_request/,/return response/d' cart.py
    sed -i '/@cross_origin/d' cart.py
    
    # Insert our special CORS configuration right after app definition
    sed -i '/app = Flask/a \
# Special CORS configuration for cart service\
CORS(app)\
\
@app.after_request\
def add_cors_headers(response):\
    response.headers[\"Access-Control-Allow-Origin\"] = \"*\"\
    response.headers[\"Access-Control-Allow-Headers\"] = \"Content-Type, Authorization\"\
    response.headers[\"Access-Control-Allow-Methods\"] = \"GET, POST, PUT, DELETE, OPTIONS\"\
    return response\
\
@app.route(\"/cart/<int:user_id>\", methods=[\"OPTIONS\"])\
def options_cart_user_id(user_id):\
    response = make_response()\
    response.headers[\"Access-Control-Allow-Origin\"] = \"*\"\
    response.headers[\"Access-Control-Allow-Headers\"] = \"Content-Type, Authorization\"\
    response.headers[\"Access-Control-Allow-Methods\"] = \"GET, OPTIONS\"\
    return response\
' cart.py

    # Make sure we have the right imports
    if ! grep -q "make_response" cart.py; then
        sed -i 's/from flask import Flask, request, jsonify/from flask import Flask, request, jsonify, make_response/' cart.py
    fi
    
    echo "Special CORS fix applied to cart.py"
fi

# Create a directory for log files
mkdir -p /app/logs

# Start all microservices in background
echo "Starting microservices..."

# Find all Python files with Flask apps and run them
for app in $(find . -name "*.py" -type f -exec grep -l "app.run" {} \;); do
    port=$(grep -o "port=[0-9]\+" "$app" | cut -d= -f2)
    if [ -n "$port" ]; then
        app_name=$(basename "$app" .py)
        echo "Starting app on port $port: $app as $app_name"
        
        # Add host='0.0.0.0' to app.run to make it accessible from outside the container
        sed -i "s/app.run(debug=True, port=$port)/app.run(host='0.0.0.0', debug=True, port=$port)/g" "$app"
        sed -i "s/app.run(port=$port, debug=True)/app.run(host='0.0.0.0', port=$port, debug=True)/g" "$app"
        
        # Start the app
        python "$app" > "/app/logs/$app_name.log" 2>&1 &
        sleep 1
    fi
done

echo "All microservices started!"
echo "Checking service health..."
sleep 5

echo "Starting background task... (rabbitmq_consumser)"
python rabbitmq_consumer.py > "/app/logs/background_task.log" 2>&1 &

# Check if services are running
for port in $(seq 5000 5025); do
    if nc -z localhost $port 2>/dev/null; then
        echo "Service on port $port is running"
    else
        echo "Note: No service detected on port $port"
    fi
done

# Import comic data
echo ""
echo "=================================================================="
echo "Importing comic data..."

# Create necessary directories if they don't exist
mkdir -p /app/images
mkdir -p /app/Chapters

# Run the upload script to import comic data
echo "Running upload_chapter_pages.py to import comic data"
python upload_chapter_pages.py > "/app/logs/upload_chapter_pages.log" 2>&1
if [ $? -eq 0 ]; then
    echo "Comic data import completed successfully"
else
    echo "Warning: Comic data import had some issues. Check /app/logs/upload_chapter_pages.log for details."
fi
echo "=================================================================="

# Print information about how to access the services
echo ""
echo "=================================================================="
echo "Your ESD-Weebs microservices are now running!"
echo "You can access the services at:"
echo "  - User API: http://localhost:5000"
echo "  - Comic API: http://localhost:5001 (if available)"
echo "  - Chapter API: http://localhost:5005 (if available)"
echo "  - Waitlist API: http://localhost:5003 (if available)"
echo "  - Verification Service: http://localhost:5015 (if available)"
echo ""
echo "The MySQL database is available at:"
echo "  - Host: localhost"
echo "  - Port: 3307"
echo "  - User: root"
echo "  - Password: root_password"
echo "=================================================================="

# Sleep to keep the container running and monitor logs
echo "Container is now running. To view logs use: docker-compose logs app"
tail -f /app/logs/*.log 