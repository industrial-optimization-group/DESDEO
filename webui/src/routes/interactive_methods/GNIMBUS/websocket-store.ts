/**
 * WebSocket Service for GNIMBUS
 *
 * @author Stina Palomäki <palomakistina@gmail.com>
 * @created September 2025
 * @updated November 2025
 *
 * @description
 * Manages real-time communication between group members during the GNIMBUS group decision making process.
 * Handles connection lifecycle, message parsing, automatic reconnection, and error handling.
 *
 * @features
 * - Automatic reconnection with exponential backoff (max 5 attempts)
 * - Reconnection callbacks for state synchronization
 * - Connection state management
 * - Message validation and error handling
 *
 */

import { writable, type Writable } from 'svelte/store';
import { isLoading } from '../../../stores/uiState';

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
		message: string;
		messageId: number;
	}> = writable({
		message: '',
		messageId: 0
	});

	/**
	 * Creates a new WebSocket connection for GNIMBUS group communication
	 *
	 * @param groupId ID of the group session
	 * @param method Method name (default: "gnimbus")
	 * @param token Authentication token
	 * @param onReconnect Callback function to run when reconnected
	 */
	constructor(groupId: number, method = 'gnimbus', token: string, onReconnect?: () => void) {
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
			console.log('WebSocket connection established.');
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
			console.log('WebSocket message received:', event.data);
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
		console.log(
			`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay} ms`
		);

		setTimeout(() => {
			this.connect();
		}, delay);
	}

	async sendMessage(message: string): Promise<boolean> {
		// If we're currently reconnecting, queue the message or return false
		if (this.isReconnecting) {
			this.messageStore.update((store) => ({
				...store,
				message: 'Reconnecting... Please try again in a moment.',
				messageId: store.messageId + 1
			}));
			return false;
		}

		isLoading.set(true);
		try {
			return await new Promise((resolve) => {
				if (this.socket && this.socket.readyState === WebSocket.OPEN) {
					try {
						this.socket.send(message);

						// Set up a timeout for error handling
						const timeoutId = setTimeout(() => {
							isLoading.set(false);
							resolve(false);
						}, 7000); // 7 second timeout

						// Set up one-time message handler to check for immediate success or error message
						const messageHandler = (event: MessageEvent) => {
							clearTimeout(timeoutId);
							this.socket?.removeEventListener('message', messageHandler);

							// Check if the message indicates an error. All error messages contain 'ERROR'
							const success = !event.data.includes('ERROR');
							isLoading.set(false);
							resolve(success);
						};

						this.socket.addEventListener('message', messageHandler);
					} catch (error) {
						console.error('Failed to send WebSocket message:', error);
						isLoading.set(false);
						resolve(false);
					}
				} else {
					this.messageStore.update((store) => {
						store.message = 'WebSocket not connected';
						store.messageId += 1;
						return store;
					});
					isLoading.set(false);
					resolve(false);
				}
			});
		} catch (error) {
			isLoading.set(false);
			return false;
		}
	}

	close() {
		if (this.socket) {
			this.socket.close();
			this.socket = null;
		}
	}
}
