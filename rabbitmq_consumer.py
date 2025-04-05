import pika
import json
import requests
import os

# Connect to RabbitMQ
def connect_to_rabbitmq():
    RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
    connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue='fcfs_queue', durable=True)
    return connection, channel

# Send data to waitlist service
def send_to_waitlist_service(data):
    url = "http://waitlist:5003/waitlist"  # Use container name, not localhost
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 201:
            print("✅ Data successfully added to the waitlist service!")
            return True
        else:
            print(f"❌ Failed to add data: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Error connecting to waitlist service: {e}")
        return False

# Process message from RabbitMQ
def process_message(ch, method, properties, body):
    data = json.loads(body)
    print(f"📦 Received: {data}")
    send_to_waitlist_service(data)
    ch.basic_ack(delivery_tag=method.delivery_tag)

# Main loop
def main():
    connection, channel = connect_to_rabbitmq()
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='fcfs_queue', on_message_callback=process_message)
    print("🎧 Waiting for messages. Press CTRL+C to exit.")
    channel.start_consuming()

if __name__ == '__main__':
    main()
