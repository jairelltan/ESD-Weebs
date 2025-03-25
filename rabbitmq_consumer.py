import pika
import json
import mysql.connector
from mysql.connector import Error
import requests

# Function to connect to RabbitMQ
def connect_to_rabbitmq():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='fcfs_queue', durable=True)
    return connection, channel

# Function to insert data into MySQL database
def send_to_waitlist_service(data):
    url = "http://localhost:5003/waitlist"
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 201:
            print("Data successfully added to the waitlist service!")
            return True
        else:
            print(f"Failed to add data: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to waitlist service: {e}")
        return False

# Function to process messages from RabbitMQ and insert into MySQL
def process_message(ch, method, properties, body):
    data = json.loads(body)
    print(f" [x] Processing data: {data}")  # Log the received data
    
    # Insert data into MySQL
    send_to_waitlist_service(data)
    
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
