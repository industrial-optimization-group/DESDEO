/**
 * WebSocket Service for GNIMBUS
 *
 * Manages real-time communication between group members during the decision making process.
 * Handles connection lifecycle, message parsing, and error handling.
 */

import { writable, type Writable } from 'svelte/store';

const BASE_URL = import.meta.env.VITE_API_URL;
const wsBase = BASE_URL.replace(/^http/, 'ws');
export class WebSocketService {
	socket: WebSocket | null = null;
	messageStore: Writable<string> = writable('');

	/**
	 * Creates a new WebSocket connection for GNIMBUS group communication
	 *
	 * @param groupId ID of the group session
	 * @param method Method name (default: "gnimbus")
	 * @param token Authentication token
	 */
	constructor(groupId: number, method = 'gnimbus', token: string) {
		if (this.socket) {
			this.close();
		}
		console.log('BASE_URL:', BASE_URL);
		console.log('wsBase:', wsBase);
		const url = `${wsBase}/gdm/ws?group_id=${groupId}&method=${method}&token=${token}`;
		console.log('WebSocket URL:', url);
		this.socket = new WebSocket(url);

		this.socket.addEventListener('open', () => {
			console.log('WebSocket connection established.');
		});

		this.socket.addEventListener('close', (event) => {
			console.log('WebSocket closed:', { code: event.code, reason: event.reason });
		});

		this.socket.addEventListener('message', (event) => {
			try {
				// Try to parse as JSON in case future backend changes send structured data
				const data = JSON.parse(event.data);
				this.messageStore.set(data);
			} catch {
				// If not JSON, treat as plain text message
				this.messageStore.set(event.data.toString());
			}
			console.log('WebSocket message received:', event.data);
		});

		this.socket.addEventListener('error', (event) => {
			console.error('WebSocket error:', event);
			this.messageStore.set('Connection error occurred');
		});
	}

	sendMessage(message: string) {
		if (this.socket && this.socket.readyState === WebSocket.OPEN) {
			this.socket.send(message);
		} else {
			this.messageStore.set('WebSocket not connected');
		}
	}

	close() {
		if (this.socket) {
			this.socket.close();
			this.socket = null;
		}
	}
}
