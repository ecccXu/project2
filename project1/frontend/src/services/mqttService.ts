import mqtt, { MqttClient, IClientOptions } from 'mqtt';
import { MqttConfig } from '../utils/types';

class MqttService {
  private client: MqttClient | null = null;
  private config: MqttConfig | null = null;
  private isConnected: boolean = false;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectInterval: number = 3000;

  // 连接状态回调函数
  private onConnectCallbacks: Array<() => void> = [];
  private onDisconnectCallbacks: Array<() => void> = [];
  private onMessageCallbacks: Array<(topic: string, message: Buffer) => void> = [];
  private onErrorCallbacks: Array<(error: Error) => void> = [];

  /**
   * 连接到MQTT Broker
   */
  connect(config: MqttConfig): Promise<void> {
    return new Promise((resolve, reject) => {
      // 如果已有连接，先断开
      if (this.client && this.client.connected) {
        this.client.end();
      }

      // 保存配置
      this.config = config;

      // 构建WebSocket连接URL
      const protocol = config.brokerPort === 443 ? 'wss' : 'ws';
      const brokerUrl = `${protocol}://${config.brokerHost}:${config.brokerPort}`;

      // MQTT连接选项
      const options: IClientOptions = {
        clientId: config.clientId,
        clean: config.cleanSession,
        connectTimeout: 10000, // 增加连接超时时间
        reconnectPeriod: 3000, // 重连间隔
        // 如果有认证信息则添加
        ...(config.username && { username: config.username }),
        ...(config.password && { password: config.password }),
      };

      // 创建MQTT客户端
      this.client = mqtt.connect(brokerUrl, options);

      // 连接成功回调
      this.client.on('connect', () => {
        console.log('MQTT连接成功');
        this.isConnected = true;
        this.reconnectAttempts = 0; // 重置重连计数
        this.onConnectCallbacks.forEach(callback => callback());
        resolve();
      });

      // 连接错误回调
      this.client.on('error', (error) => {
        console.error('MQTT连接错误:', error);
        this.onErrorCallbacks.forEach(callback => callback(error));
        this.isConnected = false;
        reject(error);
      });

      // 连接断开回调
      this.client.on('close', () => {
        if (this.isConnected) {
          console.log('MQTT连接已断开');
          this.isConnected = false;
          this.onDisconnectCallbacks.forEach(callback => callback());
        }
        
        // 尝试重连（如果未达到最大重连次数）
        if (this.reconnectAttempts < this.maxReconnectAttempts && this.config) {
          this.reconnectAttempts++;
          console.log(`MQTT连接断开，${this.reconnectInterval/1000}秒后尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
          setTimeout(() => {
            console.log('正在尝试重连...');
            this.connect(this.config!);
          }, this.reconnectInterval);
        } else {
          console.warn('MQTT连接重试次数已达上限');
        }
      });

      // 接收消息回调
      this.client.on('message', (topic, message) => {
        this.onMessageCallbacks.forEach(callback => callback(topic, message));
      });
    });
  }

  /**
   * 断开MQTT连接
   */
  disconnect(): void {
    if (this.client) {
      this.client.end(true); // 强制断开连接
      this.isConnected = false;
      this.reconnectAttempts = 0; // 重置重连计数
    }
  }

  /**
   * 订阅主题
   */
  subscribe(topic: string, options?: mqtt.IClientSubscribeOptions): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.client || !this.client.connected) {
        reject(new Error('MQTT客户端未连接'));
        return;
      }

      this.client.subscribe(topic, options, (error, granted) => {
        if (error) {
          console.error('订阅失败:', error);
          reject(error);
        } else {
          console.log('订阅成功:', granted);
          resolve();
        }
      });
    });
  }

  /**
   * 批量订阅主题
   */
  subscribeMultiple(topics: string[], options?: mqtt.IClientSubscribeOptions): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.client || !this.client.connected) {
        reject(new Error('MQTT客户端未连接'));
        return;
      }

      this.client.subscribe(topics, options, (error, granted) => {
        if (error) {
          console.error('批量订阅失败:', error);
          reject(error);
        } else {
          console.log('批量订阅成功:', granted);
          resolve();
        }
      });
    });
  }

  /**
   * 取消订阅主题
   */
  unsubscribe(topic: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.client || !this.client.connected) {
        reject(new Error('MQTT客户端未连接'));
        return;
      }

      this.client.unsubscribe(topic, (error) => {
        if (error) {
          console.error('取消订阅失败:', error);
          reject(error);
        } else {
          console.log('取消订阅成功:', topic);
          resolve();
        }
      });
    });
  }

  /**
   * 发布消息到主题
   */
  publish(topic: string, message: string | Buffer, options?: mqtt.IClientPublishOptions): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.client || !this.client.connected) {
        reject(new Error('MQTT客户端未连接'));
        return;
      }

      this.client.publish(topic, message, options, (error) => {
        if (error) {
          console.error('发布消息失败:', error);
          reject(error);
        } else {
          console.log('消息发布成功:', topic);
          resolve();
        }
      });
    });
  }

  /**
   * 添加连接成功回调
   */
  onConnect(callback: () => void): void {
    this.onConnectCallbacks.push(callback);
  }

  /**
   * 添加断开连接回调
   */
  onDisconnect(callback: () => void): void {
    this.onDisconnectCallbacks.push(callback);
  }

  /**
   * 添加消息接收回调
   */
  onMessage(callback: (topic: string, message: Buffer) => void): void {
    this.onMessageCallbacks.push(callback);
  }

  /**
   * 添加错误回调
   */
  onError(callback: (error: Error) => void): void {
    this.onErrorCallbacks.push(callback);
  }

  /**
   * 移除连接成功回调
   */
  removeOnConnect(callback: () => void): void {
    const index = this.onConnectCallbacks.indexOf(callback);
    if (index > -1) {
      this.onConnectCallbacks.splice(index, 1);
    }
  }

  /**
   * 移除断开连接回调
   */
  removeOnDisconnect(callback: () => void): void {
    const index = this.onDisconnectCallbacks.indexOf(callback);
    if (index > -1) {
      this.onDisconnectCallbacks.splice(index, 1);
    }
  }

  /**
   * 移除消息接收回调
   */
  removeOnMessage(callback: (topic: string, message: Buffer) => void): void {
    const index = this.onMessageCallbacks.indexOf(callback);
    if (index > -1) {
      this.onMessageCallbacks.splice(index, 1);
    }
  }

  /**
   * 移除错误回调
   */
  removeOnError(callback: (error: Error) => void): void {
    const index = this.onErrorCallbacks.indexOf(callback);
    if (index > -1) {
      this.onErrorCallbacks.splice(index, 1);
    }
  }

  /**
   * 检查是否已连接
   */
  isConnectedToBroker(): boolean {
    return this.isConnected && !!this.client && this.client.connected;
  }

  /**
   * 获取当前连接状态
   */
  getConnectionStatus(): 'disconnected' | 'connecting' | 'connected' | 'error' {
    if (!this.client) {
      return 'disconnected';
    }
    
    if (this.client.connecting) {
      return 'connecting';
    }
    
    if (this.client.connected) {
      return 'connected';
    }
    
    return 'disconnected';
  }
}

// 创建单例实例
export const mqttService = new MqttService();