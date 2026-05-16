import paho.mqtt.client as mqtt

def on_message(client, userdata, msg):
    print(f"收到: {msg.topic} -> {msg.payload.decode()}")

client = mqtt.Client("test_local")
client.on_message = on_message
client.connect("localhost", 1883, 60)
client.subscribe("vcar/sensors/+/data")
client.loop_forever()