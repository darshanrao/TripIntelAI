/**
 * WebSocket service for real-time trip planning updates
 * This eliminates the need for polling or multiple HTTP requests
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_URL = API_URL.replace(/^http/, 'ws');

class TripPlannerWebSocket {
  constructor() {
    this.socket = null;
    this.conversationId = null;
    this.isConnected = false;
    this.messageListeners = new Set();
    this.connectionListeners = new Set();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000; // Start with 1 second
    this.pingInterval = null;
  }

  /**
   * Connect to the WebSocket server
   * @param {string} conversationId - Conversation ID to subscribe to
   * @returns {Promise} - Resolves when connected
   */
  connect(conversationId) {
    // Don't reconnect if we're already connected to this conversation
    if (this.isConnected && this.conversationId === conversationId) {
      return Promise.resolve();
    }
    
    // If we're connected to a different conversation, disconnect first
    if (this.isConnected) {
      this.disconnect();
    }
    
    this.conversationId = conversationId;
    
    return new Promise((resolve, reject) => {
      try {
        // Create WebSocket connection
        this.socket = new WebSocket(`${WS_URL}/ws/${conversationId}`);
        
        // Set up event handlers
        this.socket.onopen = () => {
          console.log(`WebSocket connection established for conversation: ${conversationId}`);
          this.isConnected = true;
          this.reconnectAttempts = 0;
          this.startPing();
          
          // Notify listeners
          this.connectionListeners.forEach(listener => 
            listener({ type: 'connected', conversationId })
          );
          
          resolve();
        };
        
        this.socket.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            // Notify listeners, except for pong messages
            if (message.type !== 'pong') {
              this.messageListeners.forEach(listener => listener(message));
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };
        
        this.socket.onclose = (event) => {
          console.log(`WebSocket connection closed for conversation: ${conversationId}`, event);
          this.isConnected = false;
          this.stopPing();
          
          // Notify listeners
          this.connectionListeners.forEach(listener => 
            listener({ type: 'disconnected', conversationId, code: event.code })
          );
          
          // Attempt to reconnect if not closed cleanly
          if (event.code !== 1000 && event.code !== 1001) {
            this.attemptReconnect();
          }
        };
        
        this.socket.onerror = (error) => {
          console.error(`WebSocket error for conversation: ${conversationId}`, error);
          
          // Notify listeners
          this.connectionListeners.forEach(listener => 
            listener({ type: 'error', conversationId, error })
          );
          
          reject(error);
        };
        
      } catch (error) {
        console.error('Error connecting to WebSocket:', error);
        reject(error);
      }
    });
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect() {
    if (this.socket && this.isConnected) {
      this.stopPing();
      this.socket.close(1000, 'Client disconnected');
      this.isConnected = false;
      this.socket = null;
    }
  }

  /**
   * Add a listener for WebSocket messages
   * @param {Function} callback - Callback function(message)
   */
  addMessageListener(callback) {
    this.messageListeners.add(callback);
    return () => this.messageListeners.delete(callback);
  }

  /**
   * Add a listener for connection state changes
   * @param {Function} callback - Callback function(event)
   */
  addConnectionListener(callback) {
    this.connectionListeners.add(callback);
    return () => this.connectionListeners.delete(callback);
  }

  /**
   * Request the current state from the server
   */
  requestState() {
    if (this.isConnected) {
      this.socket.send(JSON.stringify({ type: 'request_state' }));
    }
  }

  /**
   * Start sending ping messages to keep the connection alive
   */
  startPing() {
    this.stopPing(); // Clear any existing interval
    
    // Send a ping every 30 seconds
    this.pingInterval = setInterval(() => {
      if (this.isConnected) {
        this.socket.send(JSON.stringify({ 
          type: 'ping', 
          timestamp: Date.now() 
        }));
      }
    }, 30000);
  }

  /**
   * Stop sending ping messages
   */
  stopPing() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Attempt to reconnect to the WebSocket server
   */
  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log(`Maximum reconnect attempts (${this.maxReconnectAttempts}) reached`);
      return;
    }
    
    // Exponential backoff
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
    this.reconnectAttempts++;
    
    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    setTimeout(() => {
      if (!this.isConnected && this.conversationId) {
        this.connect(this.conversationId).catch(() => {
          // Connection failed, the next attempt will be scheduled by onclose
        });
      }
    }, delay);
  }
}

// Create a singleton instance
const tripPlannerWebSocket = new TripPlannerWebSocket();

export default tripPlannerWebSocket; 