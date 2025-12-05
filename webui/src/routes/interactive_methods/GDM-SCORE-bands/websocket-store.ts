/**
 * WebSocket Service for GDM-SCORE-bands
 *
 * @author Stina Palomäki <palomakistina@gmail.com>
 * @created December 2025
 *
 * @description
 * Manages real-time communication between group members during the GDM-SCORE-bands group decision making process.
 * Unlike GNIMBUS, this service is primarily for RECEIVING websocket messages (voting updates, iteration changes)
 * rather than sending user input through websockets. User actions (vote, confirm) are sent via HTTP endpoints.
 * 
 * @features
 * - Automatic reconnection with exponential backoff (max 5 attempts)
 * - Reconnection callbacks for state synchronization
 * - Connection state management
 * - Message validation and error handling
 * - Read-only message listening (no user message sending)
 *
 */

import { writable, type Writable } from 'svelte/store';

const BASE_URL = import.meta.env.VITE_API_URL;
const wsBase = BASE_URL.replace(/^http/, 'ws');
export class WebSocketService {
	socket: WebSocket | null = null;
	private reconnectAttempts = 0;
	private maxReconnectAttempts = 5;
	private reconnectInterval = 5000; // Start with 5 seconds
	private isReconnecting = false;
	private groupId: number;
	private method: string;
	private token: string;
	
	// Add callback for successful reconnection
	private onReconnectCallback?: () => void;
	
	messageStore: Writable<{
		message:	string;
		messageId: number;
	}> = writable({
		message: '',
		messageId: 0
	});

	/**
	 * Creates a new WebSocket connection for GDM-SCORE-bands group communication
	 *
	 * @param groupId ID of the group session
	 * @param method Method name (default: "gdm-score-bands")
	 * @param token Authentication token
	 * @param onReconnect Callback function to run when reconnected (e.g., refresh voting state)
	 */
	constructor(groupId: number, method = 'gdm-score-bands', token: string, onReconnect?: () => void) {
		this.groupId = groupId;
		this.method = method;
		this.token = token;
		this.onReconnectCallback = onReconnect;
		
		if (this.socket) {
			this.close();
		}
		this.connect();
	}

	private connect() {
		const url = `${wsBase}/gdm/ws?group_id=${this.groupId}&method=${this.method}&token=${this.token}`;
		this.socket = new WebSocket(url);
		if (this.reconnectAttempts > 0) {
			this.messageStore.update((store) => ({
				...store,
				message: `Reconnecting...`,
				messageId: store.messageId + 1
			}));
		}
		this.isReconnecting = false;

		this.socket.addEventListener('open', () => {
			console.log('WebSocket connection established for GDM-SCORE-bands.');
			// Call the reconnection callback if this was a reconnection
			if (this.reconnectAttempts > 0 && this.onReconnectCallback) {
				this.onReconnectCallback();
			}
			
			this.reconnectAttempts = 0; // Reset on successful connection
		});

		this.socket.addEventListener('close', (event) => {
			console.log('WebSocket closed:', { code: event.code, reason: event.reason });
			this.attemptReconnect();
		});

		this.socket.addEventListener('message', (event) => {
			try {
				// Try to parse as JSON in case future backend changes send structured data
				const data = JSON.parse(event.data);
				this.messageStore.update((store) => {
					store.message = data;
					store.messageId += 1;
					return store;
			});
			} catch {
				// If not JSON, treat as plain text message
				this.messageStore.update((store) => {
					store.message = event.data.toString();
					store.messageId += 1;
					return store;
				});
			}
			console.log('GDM-SCORE-bands WebSocket message received:', event.data);
		});
		
		this.socket.addEventListener('error', (event) => {
			console.error('WebSocket error:', event);
			this.messageStore.update((store) => {
				store.message = 'Connection error occurred';
				store.messageId += 1;
				return store;
			});
		});
	}

	private attemptReconnect() {
		if (this.isReconnecting || this.reconnectAttempts >= this.maxReconnectAttempts) {
			if (this.reconnectAttempts >= this.maxReconnectAttempts) {
				this.messageStore.update((store) => ({
					...store,
					message: 'Connection lost. Please refresh the page.',
					messageId: store.messageId + 1
				}));
			}
			return;
		}
		
		this.isReconnecting = true;
		this.reconnectAttempts++;

		const delay = Math.min(this.reconnectInterval * this.reconnectAttempts, 25000); // Max 25 seconds
		const delaySeconds = Math.floor(delay / 1000);
		this.messageStore.update((store) => ({
			...store,
			message: `Connection lost. Retrying in ${delaySeconds} seconds...`,
			messageId: store.messageId + 1
		}));
		console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay} ms`);
		
		setTimeout(() => {
			this.connect();
		}, delay);
	}

	async sendMessage(message: string): Promise<boolean> {
		// GDM-SCORE-bands uses HTTP endpoints for user actions, not websocket messages
		// This method is kept in case the API requires it, we need it in future or we fuse websocket-store-components with GNIMBUS.
		
		console.warn('GDM-SCORE-bands: sendMessage() should not be used. Use HTTP endpoints for user actions.');
		this.messageStore.update((store) => ({
			...store,
			message: 'Use HTTP endpoints for voting and confirmation, not websocket messages.',
			messageId: store.messageId + 1
		}));
		return false;
	}

	close() {
		if (this.socket) {
			this.socket.close();
			this.socket = null;
		}
	}
}
