import pika
import json
import mysql.connector
from mysql.connector import Error

# Function to connect to RabbitMQ
def connect_to_rabbitmq():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='fcfs_queue', durable=True)
    return connection, channel

# Function to insert data into MySQL database
def insert_data_to_mysql(data):
    try:
        # Establish MySQL connection
        connection = mysql.connector.connect(
            host='localhost',  # Change to your MySQL host if necessary
            user='root',       # Change to your MySQL username
            password='',  # Change to your MySQL password
            database='waitlist_db'  # Replace with your actual database name
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Define your SQL insert statement
            insert_query = """
            INSERT INTO waitlist (user_id, username, comic_id, comic_name, comic_volume, price_per_item, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            # Extract values from the received data
            values = (
                data['user_id'],
                data['username'],
                data['comic_id'],
                data['comic_name'],
                data['comic_volume'],
                data['price_per_item'],
                data['timestamp']
            )
            
            # Execute the insert query
            cursor.execute(insert_query, values)
            
            # Commit the changes to the database
            connection.commit()
            print("Data inserted into MySQL successfully!")
    
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
    
    finally:
        # Close the cursor and connection
        if connection.is_connected():
            cursor.close()
            connection.close()

# Function to process messages from RabbitMQ and insert into MySQL
def process_message(ch, method, properties, body):
    data = json.loads(body)
    print(f" [x] Processing data: {data}")  # Log the received data
    
    # Insert data into MySQL
    insert_data_to_mysql(data)
    
    # Acknowledge the message after processing
    ch.basic_ack(delivery_tag=method.delivery_tag)

# Main function to consume messages from RabbitMQ
def main():
    connection, channel = connect_to_rabbitmq()

    # Set up a consumer on the 'fcfs_queue'
    channel.basic_qos(prefetch_count=1)  # Limit to one message at a time
    channel.basic_consume(queue='fcfs_queue', on_message_callback=process_message)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    main()
