<script lang="ts">
	/**
    Topbar.svelte

    Author: Giomara Larraga
    Created: June 2025

    This component renders the top navigation bar for the DESDEO web application.

    Features:
    - Displays the DESDEO logo and name on the left, linking to the dashboard.
    - Provides navigation for Problems, Methods, Archive, Help, and User Account.
    - Utilizes dropdown menus for Problems, Methods, and User Account for better organization.
    - Supports responsive design, adapting to different screen sizes.
    - Includes logout functionality, clearing user authentication and redirecting to the home page.
    - Written in Svelte with TypeScript, leveraging shadcn UI components.

	 */
	import CircleUser from '@lucide/svelte/icons/user-circle';
	import Method from '@lucide/svelte/icons/brain-circuit';
	import Problem from '@lucide/svelte/icons/puzzle';
	import Archive from '@lucide/svelte/icons/archive';
	import HelpCircle from '@lucide/svelte/icons/circle-help';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { goto } from '$app/navigation';
	import { auth } from '../../../../stores/auth';
	import { derived } from 'svelte/store';
	import desdeo_logo from '$lib/assets/desdeo_logo.svg';

	async function logout() {
		try {
			await fetch(`${import.meta.env.VITE_API_URL}/logout`, {
				method: 'POST',
				credentials: 'include' // ensure cookies are sent
			});
		} catch (error) {
			console.warn('Logout request failed', error);
		}

		auth.clearAuth();
		localStorage.removeItem('authState');
		goto('/home');
	}

	const userDisplay = derived(auth, ($auth) => {
		if ($auth.user) {
			return `${$auth.user.username} (${$auth.user.role})`;
		}
		return '';
	});
</script>

<header class="bg-primary sticky top-0 flex h-14 items-center gap-4 border-b px-4 md:px-6">
	<!-- Left: DESDEO logo and name -->
	<a
		href="/dashboard"
		class="text-primary-foreground flex items-center gap-2 text-lg font-semibold md:text-base"
	>
		<img src={desdeo_logo} alt="DESDEO Logo" class="h-6 w-6" />
		<span>DESDEO</span>
	</a>

	<!-- Right: Navigation -->
	<nav
		class="flex flex-1 flex-col justify-end gap-6 text-lg font-medium md:flex md:flex-row md:items-center md:gap-5 md:text-sm lg:gap-6"
	>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				<span
					class="text-primary-foreground hover:text-secondary flex items-center gap-1 transition-colors hover:cursor-pointer"
				>
					<Problem class="h-4 w-4" />
					Problems
				</span>
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="start">
				<DropdownMenu.Item onSelect={() => goto('/problems')}>Explore problems</DropdownMenu.Item>
				<DropdownMenu.Item onSelect={() => goto('/problems/define')}>
					Define problem
				</DropdownMenu.Item>
			</DropdownMenu.Content>
		</DropdownMenu.Root>

		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				<span
					class="text-primary-foreground hover:text-secondary flex items-center gap-1 transition-colors hover:cursor-pointer"
				>
					<Problem class="h-4 w-4" />
					Methods
				</span>
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="start">
				<DropdownMenu.Item onSelect={() => goto('/methods/initialize')}
					>Initialize a new method</DropdownMenu.Item
				>
				<DropdownMenu.Item onSelect={() => goto('/methods/sessions')}>Sessions</DropdownMenu.Item>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
		<a
			href="/archive"
			class="text-primary-foreground hover:text-secondary flex items-center gap-1 transition-colors"
		>
			<Archive class="h-4 w-4" />
			Archive
		</a>
		<a
			href="/help"
			class="text-primary-foreground hover:text-secondary flex items-center gap-1 transition-colors"
		>
			<HelpCircle class="h-4 w-4" />
			Help
		</a>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				<span
					class="text-primary-foreground hover:text-secondary flex items-center gap-1 transition-colors hover:cursor-pointer"
				>
					<CircleUser class="h-4 w-4" />
					{$userDisplay}
				</span>
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="end">
				<DropdownMenu.Label>My Account</DropdownMenu.Label>
				<DropdownMenu.Separator />
				<DropdownMenu.Item>Settings</DropdownMenu.Item>
				<DropdownMenu.Item>Support</DropdownMenu.Item>
				<DropdownMenu.Separator />
				<DropdownMenu.Item onSelect={logout}>Logout</DropdownMenu.Item>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</nav>
</header>
