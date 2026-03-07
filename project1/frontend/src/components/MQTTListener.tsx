import { useEffect, useRef } from 'react';
import { mqttService } from '../services/mqttService';

const MQTTListener: React.FC = () => {
  const messageHandlerRef = useRef<(topic: string, message: Buffer) => void>();
  const connectHandlerRef = useRef<() => void>();
  const disconnectHandlerRef = useRef<() => void>();

  useEffect(() => {
    // MQTT消息处理函数
    const handleMqttMessage = (topic: string, message: Buffer) => {
      console.log(`收到MQTT消息 - 主题: ${topic}, 内容: ${message.toString()}`);
      
      // 根据主题处理不同类型的消息
      if (topic.includes('sensor/data')) {
        try {
          const sensorData = JSON.parse(message.toString());
          console.log('传感器数据:', sensorData);
          // 这里可以触发实时数据更新
        } catch (error) {
          console.error('解析传感器数据失败:', error);
        }
      }
    };

    // 连接状态变化处理
    const handleConnect = () => {
      console.log('MQTT连接已建立');
      // 连接成功后订阅主题
      const subscribeTopic = 'vehicle/sensor/data/+';
      mqttService.subscribe(subscribeTopic)
        .then(() => console.log(`已订阅主题: ${subscribeTopic}`))
        .catch(error => console.error('订阅主题失败:', error));
    };

    const handleDisconnect = () => {
      console.log('MQTT连接已断开');
    };

    // 保存引用以确保在清理时移除正确的回调
    messageHandlerRef.current = handleMqttMessage;
    connectHandlerRef.current = handleConnect;
    disconnectHandlerRef.current = handleDisconnect;

    // 注册回调函数
    if (messageHandlerRef.current) {
      mqttService.onMessage(messageHandlerRef.current);
    }
    if (connectHandlerRef.current) {
      mqttService.onConnect(connectHandlerRef.current);
    }
    if (disconnectHandlerRef.current) {
      mqttService.onDisconnect(disconnectHandlerRef.current);
    }

    // 组件卸载时清理
    return () => {
      if (messageHandlerRef.current) {
        mqttService.removeOnMessage(messageHandlerRef.current);
      }
      if (connectHandlerRef.current) {
        mqttService.removeOnConnect(connectHandlerRef.current);
      }
      if (disconnectHandlerRef.current) {
        mqttService.removeOnDisconnect(disconnectHandlerRef.current);
      }
    };
  }, []);

  // 这个组件不渲染任何UI，只负责MQTT消息监听
  return null;
};

export default MQTTListener;