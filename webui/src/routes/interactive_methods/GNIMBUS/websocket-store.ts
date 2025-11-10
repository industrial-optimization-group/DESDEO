/**
 * WebSocket Service for GNIMBUS
 *
 * Manages real-time communication between group members during the decision making process.
 * Handles connection lifecycle, message parsing, and error handling.
 */

import { writable, type Writable } from 'svelte/store';
import { isLoading } from '../../../stores/uiState';

const BASE_URL = import.meta.env.VITE_API_URL;
const wsBase = BASE_URL.replace(/^http/, 'ws');
export class WebSocketService {
	socket: WebSocket | null = null;
	messageStore: Writable<{
		message:	string;
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

	async sendMessage(message: string): Promise<boolean> {
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
						}, 3000); // 3 second timeout

						// Set up one-time message handler to check for immediate success or error message
						const messageHandler = (event: MessageEvent) => {
							clearTimeout(timeoutId);
							this.socket?.removeEventListener('message', messageHandler);
							
							// Check if the message indicates an error. 
							// TODO: when API changes, all error msgs will have keyword ERROR, other conditions can be removed.
							const success = !(event.data.includes('ERROR')  || event.data.includes('error') || event.data.includes('failed'));
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
