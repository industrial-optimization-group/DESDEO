<script lang="ts">
	import CircleUser from '@lucide/svelte/icons/user-circle';
	import Method from '@lucide/svelte/icons/brain-circuit';
	import Logo from '@lucide/svelte/icons/orbit';
	import Problem from '@lucide/svelte/icons/puzzle';
	import Archive from '@lucide/svelte/icons/archive';
	import HelpCircle from '@lucide/svelte/icons/circle-help';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import * as Sheet from '$lib/components/ui/sheet/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { goto } from '$app/navigation';
	import { auth } from '../../../../stores/auth';

	function logout() {
		auth.clearAuth();
		localStorage.removeItem('authState');
		goto('/home');
	}
</script>

<header class="bg-primary sticky top-0 flex h-14 items-center gap-4 border-b px-4 md:px-6">
	<!-- Left: DESDEO logo and name -->
	<a
		href="/"
		class="text-primary-foreground flex items-center gap-2 text-lg font-semibold md:text-base"
	>
		<Logo class="h-6 w-6" />
		<span>DESDEO</span>
	</a>

	<!-- Right: Navigation -->
	<nav
		class="flex flex-1 flex-col justify-end gap-6 text-lg font-medium md:flex md:flex-row md:items-center md:gap-5 md:text-sm lg:gap-6"
	>
		<a
			href="/problem"
			class="text-primary-foreground hover:text-secondary flex items-center gap-1 transition-colors"
		>
			<Problem class="h-4 w-4" />
			Problems
		</a>
		<a
			href="##"
			class="text-primary-foreground hover:text-secondary flex items-center gap-1 transition-colors"
		>
			<Method class="h-4 w-4" />
			Methods
		</a>
		<a
			href="##"
			class="text-primary-foreground hover:text-secondary flex items-center gap-1 transition-colors"
		>
			<Archive class="h-4 w-4" />
			Archive
		</a>
		<a
			href="##"
			class="text-primary-foreground hover:text-secondary flex items-center gap-1 transition-colors"
		>
			<HelpCircle class="h-4 w-4" />
			Help
		</a>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				<span
					class="text-primary-foreground hover:text-secondary flex items-center gap-1 transition-colors"
				>
					<CircleUser class="h-4 w-4" />
					User
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
