
import { writable, type Writable } from 'svelte/store';

const BASE_URL = import.meta.env.VITE_API_URL;



export class WebSocketService {
  socket: WebSocket | null = null;
  messageStore: Writable<string> = writable("");

  constructor(groupId: number, method = "gnimbus", token: string) {
    if (this.socket) {
      this.close();
    }
    const url = `${BASE_URL}/gdm/ws?group_id=${groupId}&method=${method}&token=${token}`;
    this.socket = new WebSocket(url);

    this.socket.addEventListener("open", () => {
      console.log("WebSocket connection established.");
    });

    this.socket.addEventListener("close", () => {
      this.messageStore.set("Websocket closed. Info from socket store");
    });

    this.socket.addEventListener("message", (event) => {
      try {
        const data = JSON.parse(event.data);
        this.messageStore.set(data);
      } catch {
        this.messageStore.set(event.data.toString());
      }
      console.log("WebSocket message received:", event.data);
    });
  }

  sendMessage(message: string) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(message);
    } else {
      this.messageStore.set("WebSocket not connected");
    }
  }

  close() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
}